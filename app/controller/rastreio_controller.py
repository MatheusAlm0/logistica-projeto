"""Endpoint público de rastreio por código."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repository import buscar_entrega_por_codigo
from app.schema.checkpoint import CheckpointResponse
from app.schema.entrega import PrevisaoEmbutida

router = APIRouter(prefix="/rastreio", tags=["rastreio"])


class RastreioResponse(BaseModel):
    codigo_rastreio: str
    status: str
    ultima_previsao: Optional[PrevisaoEmbutida] = None
    checkpoints: list[CheckpointResponse] = []


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
        ultima_previsao=PrevisaoEmbutida.model_validate(ultima) if ultima else None,
        checkpoints=[CheckpointResponse.model_validate(c) for c in entrega.checkpoints],
    )
