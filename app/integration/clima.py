import logging
from datetime import date, timedelta
from typing import Optional

import httpx

log = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def obter_chuva_mm(lat: float, lng: float, dia: date) -> Optional[float]:
    """Chuva do dia em mm: previsão para datas futuras, histórico para passadas. None se falhar."""
    url = ARCHIVE_URL if dia < date.today() - timedelta(days=1) else FORECAST_URL
    try:
        r = httpx.get(
            url,
            params={
                "latitude": lat, "longitude": lng,
                "daily": "precipitation_sum",
                "start_date": dia.isoformat(), "end_date": dia.isoformat(),
                "timezone": "America/Sao_Paulo",
            },
            timeout=5.0,
        )
        r.raise_for_status()
        valor = r.json()["daily"]["precipitation_sum"][0]
        return float(valor) if valor is not None else None
    except Exception as e:
        log.warning("Open-Meteo falhou (%s); chuva desconhecida", e)
        return None