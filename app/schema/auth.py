"""Schemas Pydantic para autenticação."""
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

# bcrypt só considera os primeiros 72 BYTES da senha (e o bcrypt 5 lança ValueError
# acima disso). Caracteres acentuados ocupam 2+ bytes em UTF-8, então validamos
# também o tamanho codificado, não só a quantidade de caracteres.
SENHA_MAX_BYTES = 72


def _email_minusculo(v: str) -> str:
    return v.lower()


def _senha_ate_72_bytes(v: str) -> str:
    if len(v.encode("utf-8")) > SENHA_MAX_BYTES:
        raise ValueError(f"senha não pode ultrapassar {SENHA_MAX_BYTES} bytes")
    return v


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=SENHA_MAX_BYTES)
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, v: str) -> str:
        return _email_minusculo(v)

    @field_validator("senha")
    @classmethod
    def _validar_senha(cls, v: str) -> str:
        return _senha_ate_72_bytes(v)


class LoginRequest(BaseModel):
    email: EmailStr
    # sem min_length: não bloqueia usuários antigos com senha curta
    senha: str = Field(max_length=SENHA_MAX_BYTES)

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, v: str) -> str:
        return _email_minusculo(v)

    @field_validator("senha")
    @classmethod
    def _validar_senha(cls, v: str) -> str:
        return _senha_ate_72_bytes(v)


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
