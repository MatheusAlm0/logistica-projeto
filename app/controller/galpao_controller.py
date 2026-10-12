from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import requer_empresa
from app.core.database import get_db
from app.model.galpao import Galpao
from app.model.usuario import Usuario
from app.schema.galpao import GalpaoCreate, GalpaoResponse

router = APIRouter(prefix="/galpoes", tags=["galpoes"])


@router.post("", response_model=GalpaoResponse, status_code=201)
def criar_galpao(
    body: GalpaoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requer_empresa),
):
    galpao = Galpao(**body.model_dump())
    db.add(galpao)
    db.commit()
    db.refresh(galpao)
    return galpao


@router.get("", response_model=list[GalpaoResponse])
def listar_galpoes(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requer_empresa),
):
    return list(db.scalars(select(Galpao).where(Galpao.ativo == True).order_by(Galpao.nome)))
