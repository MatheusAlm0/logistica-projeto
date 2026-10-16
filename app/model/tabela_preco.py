from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.model.faixa_preco import FaixaPreco


class TabelaPreco(Base):
    __tablename__ = "tabelas_preco"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    modalidade: Mapped[str] = mapped_column(String(30), nullable=False)
    preco_base_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    multiplicador_expresso: Mapped[float] = mapped_column(Float, default=1.4, nullable=False)
    raio_galpao_km: Mapped[float] = mapped_column(Float, default=150.0, nullable=False)
    taxa_dimensao_extra: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    limite_dimensao_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    faixas: Mapped[list["FaixaPreco"]] = relationship(
        "FaixaPreco", back_populates="tabela", cascade="all, delete-orphan",
        lazy="selectin",
    )
