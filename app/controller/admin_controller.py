"""Endpoints de administração: aprovação e bloqueio de empresas."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import requer_admin
from app.core.database import get_db
from app.model.usuario import Usuario
from app.schema.auth import UsuarioResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/empresas/pendentes", response_model=list[UsuarioResponse])
def listar_pendentes(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requer_admin),
):
    """Lista empresas com cadastro aguardando aprovação."""
    return list(db.scalars(
        select(Usuario)
        .where(Usuario.role == "empresa", Usuario.ativo == False)
        .order_by(Usuario.criado_em)
    ))


@router.patch("/empresas/{usuario_id}/aprovar", response_model=UsuarioResponse)
def aprovar_empresa(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requer_admin),
):
    """Aprova o cadastro de uma empresa (ativo=True)."""
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    usuario.ativo = True
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/empresas/{usuario_id}/bloquear", response_model=UsuarioResponse)
def bloquear_empresa(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requer_admin),
):
    """Bloqueia uma empresa ativa ou recusa uma pendente (ativo=False)."""
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    usuario.ativo = False
    db.commit()
    db.refresh(usuario)
    return usuario
