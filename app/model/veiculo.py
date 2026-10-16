from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Veiculo(Base):
    __tablename__ = "veiculos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    peso_max_kg: Mapped[float] = mapped_column(Float, nullable=False)
    comprimento_max_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    largura_max_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    altura_max_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preco_por_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
