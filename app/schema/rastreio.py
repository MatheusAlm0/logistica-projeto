"""Schemas da consulta pública de rastreio.

Endpoint sem autenticação: expõe só o que a página pública precisa. Nada de ids
internos, observações, quem registrou, probabilidade, versão do modelo ou features.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GalpaoPublico(BaseModel):
    nome: str
    cidade: str
    estado: str
    lat: Optional[float] = None
    lng: Optional[float] = None

    model_config = {"from_attributes": True}


class CheckpointPublico(BaseModel):
    chegou_em: datetime
    galpao: Optional[GalpaoPublico] = None

    model_config = {"from_attributes": True}


class RastreioResponse(BaseModel):
    codigo_rastreio: str
    status: str
    estado_origem: Optional[str] = None
    estado_destino: Optional[str] = None
    data_prevista: Optional[datetime] = None
    data_prevista_revisada: Optional[datetime] = None
    data_entregue: Optional[datetime] = None
    nivel_risco: Optional[str] = None   # só o nível (baixo | medio | alto) da última previsão
    checkpoints: list[CheckpointPublico] = []
