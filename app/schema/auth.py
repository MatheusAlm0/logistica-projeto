"""Schemas Pydantic para autenticação."""
from pydantic import BaseModel, EmailStr


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioResponse(BaseModel):
    id: int
    email: str
    nome: str
    role: str
    cliente_id: str
    ativo: bool

    model_config = {"from_attributes": True}
