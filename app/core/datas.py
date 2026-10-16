"""Normalização de datas/horas de entrada.

O banco guarda datas de negócio (data_pedido, data_prevista, data_entregue...) como
DateTime sem fuso, interpretadas como horário local de São Paulo. Para evitar
comparações naive x aware (TypeError → HTTP 500), toda data recebida passa por aqui:
  - aware (ex.: "2024-03-13T14:00:00Z") → convertida para America/Sao_Paulo e sem tzinfo;
  - naive (ex.: "2024-03-13T14:00:00")  → mantida como está (já é horário local).
"""
from datetime import datetime
from typing import Annotated, Optional
from zoneinfo import ZoneInfo

from pydantic import AfterValidator

FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")


def normalizar_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Converte para horário local de São Paulo sem fuso (naive). None passa direto."""
    if dt is None or dt.tzinfo is None:
        return dt
    return dt.astimezone(FUSO_LOCAL).replace(tzinfo=None)


# Tipo para schemas Pydantic: aplica normalizar_datetime após o parse.
DataHoraLocal = Annotated[datetime, AfterValidator(normalizar_datetime)]
