from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Galpao(Base):
    __tablename__ = "galpoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cidade: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, server_default="galpao")
    permite_retirada: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
