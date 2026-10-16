"""Endpoint público de rastreio por código."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repository import buscar_entrega_por_codigo
from app.schema.rastreio import CheckpointPublico, RastreioResponse

router = APIRouter(prefix="/rastreio", tags=["rastreio"])


@router.get("/{codigo}", response_model=RastreioResponse)
def rastrear(codigo: str, db: Session = Depends(get_db)):
    """Consulta pública de status e histórico de checkpoints pelo código de rastreio."""
    entrega = buscar_entrega_por_codigo(db, codigo.upper())
    if not entrega:
        raise HTTPException(status_code=404, detail="Código de rastreio não encontrado")
    ultima = entrega.previsoes[-1] if entrega.previsoes else None
    return RastreioResponse(
        codigo_rastreio=entrega.codigo_rastreio,
        status=entrega.status,
        estado_origem=entrega.estado_origem,
        estado_destino=entrega.estado_destino,
        data_prevista=entrega.data_prevista,
        data_prevista_revisada=entrega.data_prevista_revisada,
        data_entregue=entrega.data_entregue,
        nivel_risco=ultima.nivel if ultima else None,
        checkpoints=[CheckpointPublico.model_validate(c) for c in entrega.checkpoints],
    )
