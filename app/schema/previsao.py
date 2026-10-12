from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class PrevisaoRequest(BaseModel):
    data_pedido: datetime
    data_prevista: datetime
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


class PrevisaoResponse(BaseModel):
    probabilidade: float
    nivel: str
    modelo_versao: str
    features_usadas: dict[str, Any]
    contexto: dict[str, Any] = {}