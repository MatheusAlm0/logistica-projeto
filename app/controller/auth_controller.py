"""Endpoints de autenticação: registro, login e perfil."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import criar_token, get_usuario_logado, hash_senha, verificar_senha
from app.core.database import get_db
from app.model.usuario import Usuario
from app.schema.auth import LoginRequest, RegistroRequest, TokenResponse, UsuarioResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro", response_model=UsuarioResponse, status_code=201)
def registro(body: RegistroRequest, db: Session = Depends(get_db)):
    """Cadastra uma nova empresa no sistema."""
    if db.query(Usuario).filter(Usuario.email == body.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    usuario = Usuario(
        email=body.email,
        senha_hash=hash_senha(body.senha),
        role="empresa",
        nome=body.nome,
        cliente_id=str(uuid.uuid4()),
        ativo=False,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Valida e-mail/senha e retorna JWT."""
    usuario = db.query(Usuario).filter(Usuario.email == body.email).first()
    if not usuario or not verificar_senha(body.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Conta aguardando aprovação do administrador")
    token = criar_token({
        "sub": str(usuario.id),
        "email": usuario.email,
        "role": usuario.role,
    })
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UsuarioResponse)
def me(usuario: Usuario = Depends(get_usuario_logado)):
    """Retorna dados do usuário autenticado."""
    return usuario
