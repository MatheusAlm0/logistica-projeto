"""Lógica de negócio para consulta e disparo manual de retreinos."""
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import RegraDeNegocioError
from app.ml.predictor import predictor
from app.repository import (
    buscar_retreino,
    buscar_ultimo_retreino_ok,
    contar_entregas_desde_ultimo_retreino,
    contar_retreinos,
    listar_retreinos,
)


def listar(
    db: Session,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    VALIDOS = {"rodando", "ok", "erro", None}
    if status not in VALIDOS:
        raise RegraDeNegocioError(f"status inválido: {status}. Use: rodando, ok, erro")

    items = listar_retreinos(db, status=status, limit=limit, offset=offset)
    pendentes = contar_retreinos(db, status="rodando")
    total = contar_retreinos(db, status=status)

    return {"total": total, "pendentes": pendentes, "items": items}


def detalhar(db: Session, retreino_id: int) -> Any:
    retreino = buscar_retreino(db, retreino_id)
    if not retreino:
        raise RegraDeNegocioError(f"retreino {retreino_id} não encontrado")
    return retreino


def status_geral(db: Session) -> dict[str, Any]:
    """Visão geral do ciclo de aprendizado: modelo ativo, métricas e próximo retreino."""
    ultimo = buscar_ultimo_retreino_ok(db)
    novas = contar_entregas_desde_ultimo_retreino(db)
    min_amostras = settings.retreino_min_amostras

    return {
        "modelo_ativo": predictor.versao,
        "metricas_ativas": predictor.metricas,
        "ultimo_retreino": ultimo,
        "entregas_desde_ultimo_retreino": novas,
        "min_para_retreinar": min_amostras,
        "pronto_para_retreinar": novas >= min_amostras,
    }
