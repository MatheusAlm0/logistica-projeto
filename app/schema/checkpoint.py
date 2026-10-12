from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schema.galpao import GalpaoResponse


class CheckpointCreate(BaseModel):
    galpao_id: int
    chegou_em: datetime
    observacao: Optional[str] = None


class CheckpointResponse(BaseModel):
    id: int
    entrega_id: int
    galpao_id: int
    chegou_em: datetime
    registrado_por: int
    observacao: Optional[str] = None
    galpao: Optional[GalpaoResponse] = None

    model_config = {"from_attributes": True}
