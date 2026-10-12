"""Utilitários JWT e dependências FastAPI de autenticação."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.model.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_ALGORITHM = "HS256"


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode(), senha_hash.encode())


def criar_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=_ALGORITHM)


def get_usuario_logado(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credenciais_invalidas
    except JWTError:
        raise credenciais_invalidas

    usuario = db.get(Usuario, int(user_id))
    if usuario is None or not usuario.ativo:
        raise credenciais_invalidas
    return usuario


def requer_admin(usuario: Usuario = Depends(get_usuario_logado)) -> Usuario:
    if usuario.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return usuario


def requer_empresa(usuario: Usuario = Depends(get_usuario_logado)) -> Usuario:
    if usuario.role not in ("admin", "empresa"):
        raise HTTPException(status_code=403, detail="Acesso restrito a empresas")
    return usuario
