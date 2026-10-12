import logging
import math
from typing import Optional

import httpx

log = logging.getLogger(__name__)

OSRM_URL = "https://router.project-osrm.org"


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def obter_rota(olat: float, olng: float, dlat: float, dlng: float) -> dict[str, Optional[float]]:
    """Distância (km) e duração (min) pela estrada. Se o OSRM falhar, usa linha reta."""
    try:
        # o OSRM usa a ordem LONGITUDE,LATITUDE
        url = f"{OSRM_URL}/route/v1/driving/{olng},{olat};{dlng},{dlat}"
        r = httpx.get(url, params={"overview": "false"}, timeout=5.0)
        r.raise_for_status()
        rota = r.json()["routes"][0]
        return {"distancia_km": rota["distance"] / 1000, "duracao_min": rota["duration"] / 60, "fonte": "osrm"}
    except Exception as e:
        log.warning("OSRM falhou (%s); usando haversine", e)
        return {"distancia_km": haversine_km(olat, olng, dlat, dlng), "duracao_min": None, "fonte": "haversine"}