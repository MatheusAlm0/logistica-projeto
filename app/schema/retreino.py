"""Schemas Pydantic para os endpoints de retreinos."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, computed_field


class RetreinoResponse(BaseModel):
    id: int
    iniciado_em: datetime
    concluido_em: Optional[datetime] = None
    versao: Optional[str] = None
    n_amostras: Optional[int] = None
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    status: str           # rodando | ok | erro
    erro: Optional[str] = None

    @computed_field
    @property
    def duracao_segundos(self) -> Optional[float]:
        if self.iniciado_em and self.concluido_em:
            return (self.concluido_em - self.iniciado_em).total_seconds()
        return None

    model_config = {"from_attributes": True}


class RetreinoListResponse(BaseModel):
    total: int
    pendentes: int          # retreinos ainda rodando
    items: list[RetreinoResponse]


class RetreinoStatusResponse(BaseModel):
    """Resposta do endpoint /retreinos/status — visão geral do ciclo de aprendizado."""
    modelo_ativo: str
    metricas_ativas: dict
    ultimo_retreino: Optional[RetreinoResponse] = None
    entregas_desde_ultimo_retreino: int
    min_para_retreinar: int
    pronto_para_retreinar: bool
