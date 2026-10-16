"""Endpoints REST para entregas."""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_usuario_logado, requer_empresa
from app.core.database import get_db
from app.job.retreino_job import verificar_e_retreinar
from app.model.checkpoint import Checkpoint
from app.model.entrega import Entrega
from app.model.galpao import Galpao
from app.model.usuario import Usuario
from app.schema.entrega import (
    EntregaCriadaResponse,
    EntregaListResponse,
    EntregaResponse,
    EntregaCreate,
    FinalizarRequest,
    PrevisaoEmbutida,
)
from app.service import entrega_service

router = APIRouter(prefix="/entregas", tags=["entregas"])

TRANSICOES_VALIDAS: dict[str, set[str]] = {
    "pendente": {"em_transito", "cancelado"},
    "em_transito": {"entregue", "cancelado"},
    "atrasada": {"em_transito", "entregue", "cancelado"},
}


def _cliente_id_ou_none(usuario: Usuario) -> Optional[str]:
    """Admin vê tudo (retorna None); empresa vê só as suas."""
    return None if usuario.role == "admin" else usuario.cliente_id


class EntregaCreateWithHubs(EntregaCreate):
    hubs_planejados: list[int] = []


class EditarEntregaRequest(BaseModel):
    data_prevista: Optional[datetime] = None
    peso_g: Optional[float] = None
    valor: Optional[float] = None
    frete: Optional[float] = None


class AtualizarStatusRequest(BaseModel):
    status: str


def _to_response(entrega: Entrega) -> EntregaResponse:
    ultima = entrega.previsoes[-1] if entrega.previsoes else None
    return EntregaResponse(
        **{k: getattr(entrega, k) for k in EntregaResponse.model_fields if hasattr(entrega, k)},
        ultima_previsao=PrevisaoEmbutida.model_validate(ultima) if ultima else None,
    )


@router.post("", response_model=EntregaCriadaResponse, status_code=201)
def criar_entrega(
    body: EntregaCreateWithHubs,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    resultado = entrega_service.criar(db, body.model_dump(), cliente_id=usuario.cliente_id)
    entrega = resultado["entrega"]
    previsao_resultado = resultado["previsao"]

    for galpao_id in body.hubs_planejados:
        galpao = db.get(Galpao, galpao_id)
        if galpao and galpao.ativo:
            db.add(Checkpoint(
                entrega_id=entrega.id,
                galpao_id=galpao.id,
                registrado_por=usuario.id,
                observacao="Hub planejado",
            ))
    if body.hubs_planejados:
        db.commit()
        db.refresh(entrega)

    ultima_previsao = entrega.previsoes[-1] if entrega.previsoes else None

    return EntregaCriadaResponse(
        **{k: getattr(entrega, k) for k in EntregaResponse.model_fields if hasattr(entrega, k)},
        ultima_previsao=PrevisaoEmbutida.model_validate(ultima_previsao) if ultima_previsao else None,
        previsao=previsao_resultado,
    )


@router.get("", response_model=EntregaListResponse)
def listar_entregas(
    status: Optional[str] = Query(None, description="pendente | entregue | cancelado"),
    estado_destino: Optional[str] = Query(None, description="UF de destino (ex: SP)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    """Lista entregas com filtros opcionais."""
    return entrega_service.listar(
        db,
        status=status,
        estado_destino=estado_destino,
        cliente_id=_cliente_id_ou_none(usuario),
        limit=limit,
        offset=offset,
    )


@router.get("/{entrega_id}", response_model=EntregaResponse)
def detalhar_entrega(
    entrega_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    """Detalha uma entrega com a última previsão gerada."""
    resultado = entrega_service.detalhar(db, entrega_id, cliente_id=_cliente_id_ou_none(usuario))
    entrega = resultado["entrega"]
    ultima = resultado["ultima_previsao"]

    return EntregaResponse(
        **{k: getattr(entrega, k) for k in EntregaResponse.model_fields if hasattr(entrega, k)},
        ultima_previsao=PrevisaoEmbutida.model_validate(ultima) if ultima else None,
    )


@router.patch("/{entrega_id}/finalizar", response_model=EntregaResponse)
def finalizar_entrega(
    entrega_id: int,
    body: FinalizarRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    """
    Marca a entrega como entregue e agenda o retreino automático em background.

    O retreino só executa de fato se houver >= RETREINO_MIN_AMOSTRAS novas entregas
    desde o último retreino bem-sucedido (configurável via .env).
    """
    entrega = entrega_service.finalizar(
        db, entrega_id, body.data_entregue, cliente_id=_cliente_id_ou_none(usuario)
    )

    background_tasks.add_task(verificar_e_retreinar)

    ultima = entrega.previsoes[-1] if entrega.previsoes else None
    return EntregaResponse(
        **{k: getattr(entrega, k) for k in EntregaResponse.model_fields if hasattr(entrega, k)},
        ultima_previsao=PrevisaoEmbutida.model_validate(ultima) if ultima else None,
    )


@router.delete("/{entrega_id}", status_code=204)
def deletar_entrega(
    entrega_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    entrega = db.get(Entrega, entrega_id)
    if not entrega or entrega.cliente_id != usuario.cliente_id:
        raise HTTPException(404, "Entrega não encontrada")
    if entrega.status in ("entregue", "em_transito"):
        raise HTTPException(422, f"Entrega com status '{entrega.status}' não pode ser removida")
    for p in list(entrega.previsoes):
        db.delete(p)
    for c in list(entrega.checkpoints):
        db.delete(c)
    db.delete(entrega)
    db.commit()


@router.patch("/{entrega_id}/editar", response_model=EntregaResponse)
def editar_entrega(
    entrega_id: int,
    body: EditarEntregaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    entrega = db.get(Entrega, entrega_id)
    if not entrega or entrega.cliente_id != usuario.cliente_id:
        raise HTTPException(404, "Entrega não encontrada")
    if body.data_prevista is not None:
        if body.data_prevista.date() < date.today():
            raise HTTPException(422, "data_prevista não pode ser anterior a hoje")
        entrega.data_prevista = body.data_prevista
    if body.peso_g is not None:
        entrega.peso_g = body.peso_g
    if body.valor is not None:
        entrega.valor = body.valor
    if body.frete is not None:
        entrega.frete = body.frete
    db.commit()
    db.refresh(entrega)
    return _to_response(entrega)


@router.patch("/{entrega_id}/status", response_model=EntregaResponse)
def atualizar_status_entrega(
    entrega_id: int,
    body: AtualizarStatusRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    entrega = db.get(Entrega, entrega_id)
    if not entrega or entrega.cliente_id != usuario.cliente_id:
        raise HTTPException(404, "Entrega não encontrada")
    permitidos = TRANSICOES_VALIDAS.get(entrega.status, set())
    if body.status not in permitidos:
        raise HTTPException(422, f"Não é possível mudar de '{entrega.status}' para '{body.status}'")
    entrega.status = body.status
    if body.status == "entregue":
        entrega.data_entregue = datetime.now()
    db.commit()
    db.refresh(entrega)
    return _to_response(entrega)
