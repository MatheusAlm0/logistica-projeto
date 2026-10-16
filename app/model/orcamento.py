from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Orcamento(Base):
    __tablename__ = "orcamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    cliente_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    galpao_origem_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("galpoes.id"), nullable=True)
    destino_tipo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    destino_descricao: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    estado_origem: Mapped[str] = mapped_column(String(2), nullable=False)
    estado_destino: Mapped[str] = mapped_column(String(2), nullable=False)

    peso_kg: Mapped[float] = mapped_column(Float, nullable=False)
    comprimento_cm: Mapped[float] = mapped_column(Float, nullable=False)
    largura_cm: Mapped[float] = mapped_column(Float, nullable=False)
    altura_cm: Mapped[float] = mapped_column(Float, nullable=False)

    distancia_km: Mapped[float] = mapped_column(Float, nullable=False)
    duracao_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    veiculo_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("veiculos.id"), nullable=True)
    tipo_frete: Mapped[str] = mapped_column(String(20), nullable=False)

    valor_frete: Mapped[float] = mapped_column(Float, nullable=False)
    prazo_dias: Mapped[int] = mapped_column(Integer, nullable=False)

    galpoes_rota: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    clima_resumo: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="rascunho", nullable=False)
    validade_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
