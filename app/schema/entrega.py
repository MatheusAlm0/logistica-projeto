"""Schemas Pydantic para os endpoints de entregas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.core.datas import DataHoraLocal


# ── Request ──────────────────────────────────────────────────────────────────

# DataHoraLocal: datas com fuso são convertidas para America/Sao_Paulo e gravadas sem fuso
class EntregaCreate(BaseModel):
    data_pedido: DataHoraLocal
    data_prevista: DataHoraLocal
    peso_g: float
    valor: float
    frete: float
    estado_origem: Optional[str] = None
    estado_destino: Optional[str] = None
    distancia_km: Optional[float] = None
    origem_lat: Optional[float] = None
    origem_lng: Optional[float] = None
    destino_lat: Optional[float] = None
    destino_lng: Optional[float] = None


class FinalizarRequest(BaseModel):
    data_entregue: DataHoraLocal


# ── Response ──────────────────────────────────────────────────────────────────

class PrevisaoEmbutida(BaseModel):
    id: int
    probabilidade: float
    nivel: str
    modelo_versao: str
    chuva_mm: Optional[float] = None
    rota_fonte: Optional[str] = None
    criado_em: datetime

    model_config = {"from_attributes": True}


class EntregaResponse(BaseModel):
    id: int
    criado_em: datetime
    data_pedido: datetime
    data_prevista: datetime
    data_entregue: Optional[datetime] = None
    peso_g: float
    valor: float
    frete: float
    estado_origem: Optional[str] = None
    estado_destino: Optional[str] = None
    distancia_km: Optional[float] = None
    status: str
    codigo_rastreio: Optional[str] = None
    ultima_previsao: Optional[PrevisaoEmbutida] = None

    model_config = {"from_attributes": True}


class EntregaCriadaResponse(EntregaResponse):
    previsao: Optional[dict[str, Any]] = None   # resultado completo do predictor


class EntregaListResponse(BaseModel):
    total: int
    items: list[EntregaResponse]
