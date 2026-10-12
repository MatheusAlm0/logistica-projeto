"""Endpoints REST para entregas."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_usuario_logado, requer_empresa
from app.core.database import get_db
from app.job.retreino_job import verificar_e_retreinar
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


def _cliente_id_ou_none(usuario: Usuario) -> Optional[str]:
    """Admin vê tudo (retorna None); empresa vê só as suas."""
    return None if usuario.role == "admin" else usuario.cliente_id


@router.post("", response_model=EntregaCriadaResponse, status_code=201)
def criar_entrega(
    body: EntregaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    resultado = entrega_service.criar(db, body.model_dump(), cliente_id=usuario.cliente_id)
    entrega = resultado["entrega"]
    previsao_resultado = resultado["previsao"]

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
