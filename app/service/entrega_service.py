"""Lógica de negócio para entregas: criação, finalização e consulta."""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import RegraDeNegocioError
from app.model.entrega import Entrega
from app.repository import (
    buscar_entrega,
    contar_entregas,
    criar_entrega,
    finalizar_entrega,
    listar_entregas,
    salvar_previsao,
)
from app.service.previsao_service import prever


def _entrega_ou_404(db: Session, entrega_id: int) -> Entrega:
    entrega = buscar_entrega(db, entrega_id)
    if not entrega:
        raise RegraDeNegocioError(f"entrega {entrega_id} não encontrada")
    return entrega


def _verificar_acesso(entrega: Entrega, cliente_id: Optional[str]) -> None:
    """Lança RegraDeNegocioError se a entrega não pertence ao cliente (None = admin, sem restrição)."""
    if cliente_id and entrega.cliente_id != cliente_id:
        raise RegraDeNegocioError(f"entrega {entrega.id} não encontrada")


def criar(db: Session, dados: dict[str, Any], cliente_id: Optional[str] = None) -> dict[str, Any]:
    """
    Cadastra uma nova entrega, executa a previsão de risco e persiste tudo.
    Retorna a entrega + resultado da previsão.

    Ordem: predict primeiro → a rota é calculada (se necessário) e o estado é
    normalizado dentro do prever(); depois criamos a entrega com os dados completos.
    """
    # 1. previsão: valida, busca rota/clima, roda o modelo
    resultado = prever(dados)

    # 2. estado normalizado (prever() normaliza para maiúsculas internamente)
    estado_origem = (dados.get("estado_origem") or "").upper() or None
    estado_destino = (dados.get("estado_destino") or "").upper() or None

    # 3. distância: usa a informada; senão, a calculada pela rota durante o prever()
    distancia_km = dados.get("distancia_km") or resultado["features_usadas"].get("distance_km")

    campos_entrega = {
        "data_pedido": dados["data_pedido"],
        "data_prevista": dados["data_prevista"],
        "peso_g": dados["peso_g"],
        "valor": dados["valor"],
        "frete": dados["frete"],
        "estado_origem": estado_origem,
        "estado_destino": estado_destino,
        "distancia_km": distancia_km,
        "status": "pendente",
        "codigo_rastreio": f"TRK-{uuid.uuid4().hex[:8].upper()}",
        "cliente_id": cliente_id,
    }

    entrega = criar_entrega(db, campos_entrega)
    previsao = salvar_previsao(db, entrega.id, resultado, resultado.get("contexto", {}))

    db.commit()
    db.refresh(entrega)
    db.refresh(previsao)

    return {
        "entrega": entrega,
        "previsao": resultado,
    }


def finalizar(
    db: Session,
    entrega_id: int,
    data_entregue: datetime,
    cliente_id: Optional[str] = None,
) -> Entrega:
    """Marca a entrega como entregue. O job de retreino é disparado pelo controller."""
    entrega = _entrega_ou_404(db, entrega_id)
    _verificar_acesso(entrega, cliente_id)
    if entrega.status != "pendente":
        raise RegraDeNegocioError(
            f"entrega {entrega_id} já está com status '{entrega.status}'"
        )
    if data_entregue < entrega.data_pedido:
        raise RegraDeNegocioError("data_entregue não pode ser anterior à data_pedido")

    entrega = finalizar_entrega(db, entrega, data_entregue)
    db.commit()
    db.refresh(entrega)
    return entrega


def detalhar(
    db: Session,
    entrega_id: int,
    cliente_id: Optional[str] = None,
) -> dict[str, Any]:
    entrega = _entrega_ou_404(db, entrega_id)
    _verificar_acesso(entrega, cliente_id)
    ultima = entrega.previsoes[-1] if entrega.previsoes else None
    return {"entrega": entrega, "ultima_previsao": ultima}


def listar(
    db: Session,
    status: Optional[str] = None,
    estado_destino: Optional[str] = None,
    cliente_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    items = listar_entregas(db, status=status, estado_destino=estado_destino,
                            cliente_id=cliente_id, limit=limit, offset=offset)
    total = contar_entregas(db, status=status, estado_destino=estado_destino,
                            cliente_id=cliente_id)
    return {"total": total, "items": items}
