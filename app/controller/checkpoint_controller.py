from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import requer_empresa
from app.core.database import get_db
from app.model.checkpoint import Checkpoint
from app.model.entrega import Entrega
from app.model.galpao import Galpao
from app.model.usuario import Usuario
from app.repository import buscar_entrega
from app.schema.checkpoint import CheckpointCreate, CheckpointResponse

router = APIRouter(prefix="/entregas", tags=["checkpoints"])


def _entrega_acessivel(db: Session, entrega_id: int, usuario: Usuario) -> Entrega:
    entrega = buscar_entrega(db, entrega_id)
    if not entrega:
        raise HTTPException(status_code=404, detail=f"entrega {entrega_id} não encontrada")
    if usuario.role != "admin" and entrega.cliente_id != usuario.cliente_id:
        raise HTTPException(status_code=404, detail=f"entrega {entrega_id} não encontrada")
    return entrega


@router.post("/{entrega_id}/checkpoints", response_model=CheckpointResponse, status_code=201)
def registrar_checkpoint(
    entrega_id: int,
    body: CheckpointCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    _entrega_acessivel(db, entrega_id, usuario)

    galpao = db.get(Galpao, body.galpao_id)
    if not galpao or not galpao.ativo:
        raise HTTPException(status_code=404, detail=f"galpão {body.galpao_id} não encontrado")

    checkpoint = Checkpoint(
        entrega_id=entrega_id,
        galpao_id=body.galpao_id,
        chegou_em=body.chegou_em,
        registrado_por=usuario.id,
        observacao=body.observacao,
    )
    db.add(checkpoint)
    db.commit()
    db.refresh(checkpoint)
    return checkpoint


@router.get("/{entrega_id}/checkpoints", response_model=list[CheckpointResponse])
def listar_checkpoints(entrega_id: int, db: Session = Depends(get_db)):
    entrega = buscar_entrega(db, entrega_id)
    if not entrega:
        raise HTTPException(status_code=404, detail=f"entrega {entrega_id} não encontrada")
    return list(
        db.scalars(
            select(Checkpoint)
            .where(Checkpoint.entrega_id == entrega_id)
            .order_by(Checkpoint.chegou_em)
        )
    )
