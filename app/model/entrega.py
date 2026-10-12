"""Modelos SQLAlchemy: entregas, previsoes, retreinos."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Entrega(Base):
    __tablename__ = "entregas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    data_pedido: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    data_prevista: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    data_entregue: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)

    peso_g: Mapped[float] = mapped_column(Float, nullable=False)
    valor: Mapped[float] = mapped_column(Float, nullable=False)
    frete: Mapped[float] = mapped_column(Float, nullable=False)

    estado_origem: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    estado_destino: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    distancia_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # status: pendente | entregue | cancelado | atrasada
    status: Mapped[str] = mapped_column(String(20), default="pendente", nullable=False)

    codigo_rastreio: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    cliente_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    data_prevista_revisada: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)

    previsoes: Mapped[list["Previsao"]] = relationship(
        "Previsao", back_populates="entrega", order_by="Previsao.criado_em"
    )
    checkpoints: Mapped[list["Checkpoint"]] = relationship(
        "Checkpoint", back_populates="entrega", order_by="Checkpoint.chegou_em"
    )


class Previsao(Base):
    __tablename__ = "previsoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entrega_id: Mapped[int] = mapped_column(Integer, ForeignKey("entregas.id"), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    probabilidade: Mapped[float] = mapped_column(Float, nullable=False)
    nivel: Mapped[str] = mapped_column(String(10), nullable=False)       # baixo | medio | alto
    modelo_versao: Mapped[str] = mapped_column(String(20), nullable=False)

    features_json: Mapped[dict] = mapped_column(JSON, nullable=False)    # snapshot das features
    chuva_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rota_fonte: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # osrm | haversine

    entrega: Mapped["Entrega"] = relationship("Entrega", back_populates="previsoes")


class Retreino(Base):
    __tablename__ = "retreinos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    concluido_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    versao: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    n_amostras: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    roc_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pr_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    erro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # status: rodando | ok | erro
    status: Mapped[str] = mapped_column(String(20), default="rodando", nullable=False)
