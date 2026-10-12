"""Modelo SQLAlchemy para usuários do sistema SaaS."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # admin | empresa | usuario_final
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cliente_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
