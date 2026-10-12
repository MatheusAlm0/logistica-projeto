from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entrega_id: Mapped[int] = mapped_column(Integer, ForeignKey("entregas.id"), nullable=False, index=True)
    galpao_id: Mapped[int] = mapped_column(Integer, ForeignKey("galpoes.id"), nullable=False)
    chegou_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    registrado_por: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    galpao: Mapped["Galpao"] = relationship("Galpao")
    entrega: Mapped["Entrega"] = relationship("Entrega", back_populates="checkpoints")
