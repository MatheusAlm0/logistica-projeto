from typing import Optional, TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.model.tabela_preco import TabelaPreco


class FaixaPreco(Base):
    __tablename__ = "faixas_preco"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tabela_id: Mapped[int] = mapped_column(Integer, ForeignKey("tabelas_preco.id"), nullable=False)
    peso_min_kg: Mapped[float] = mapped_column(Float, nullable=False)
    peso_max_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preco_por_km: Mapped[float] = mapped_column(Float, nullable=False)

    tabela: Mapped["TabelaPreco"] = relationship("TabelaPreco", back_populates="faixas")
