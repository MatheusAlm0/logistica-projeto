from typing import Optional

from pydantic import BaseModel

from app.service.previsao_service import UFS


class GalpaoCreate(BaseModel):
    nome: str
    cidade: str
    estado: str
    lat: Optional[float] = None
    lng: Optional[float] = None

    def model_post_init(self, __context):
        self.estado = self.estado.upper()
        if self.estado not in UFS:
            raise ValueError(f"estado inválido: {self.estado}")


class GalpaoResponse(BaseModel):
    id: int
    nome: str
    cidade: str
    estado: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    ativo: bool

    model_config = {"from_attributes": True}
