"""
Job periódico de reavaliação de risco das entregas pendentes.

Roda a cada 6 horas via APScheduler. Para cada entrega pendente:
  - Se data_prevista já passou → marca como 'atrasada' e estima nova data (+3 dias úteis).
  - Senão → recalcula risco com o modelo atual e nova consulta de clima; persiste
    nova previsão apenas se o nível de risco mudou.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.model.entrega import Entrega
from app.repository.entrega_repository import salvar_previsao
from app.service.previsao_service import prever as prever_risco

log = logging.getLogger(__name__)

# Coordenadas aproximadas das capitais estaduais para re-consulta do Open-Meteo.
_CAPITAL_COORDS: dict[str, tuple[float, float]] = {
    "AC": (-9.97, -67.81),
    "AL": (-9.67, -35.74),
    "AM": (-3.10, -60.02),
    "AP": (0.04, -51.07),
    "BA": (-12.97, -38.50),
    "CE": (-3.72, -38.54),
    "DF": (-15.78, -47.93),
    "ES": (-20.32, -40.34),
    "GO": (-16.69, -49.25),
    "MA": (-2.53, -44.30),
    "MT": (-15.60, -56.10),
    "MS": (-20.44, -54.65),
    "MG": (-19.92, -43.94),
    "PA": (-1.46, -48.50),
    "PB": (-7.12, -34.86),
    "PR": (-25.43, -49.27),
    "PE": (-8.05, -34.88),
    "PI": (-5.09, -42.80),
    "RJ": (-22.91, -43.18),
    "RN": (-5.79, -35.21),
    "RS": (-30.03, -51.23),
    "RO": (-8.76, -63.90),
    "RR": (2.82, -60.67),
    "SC": (-27.59, -48.55),
    "SP": (-23.55, -46.63),
    "SE": (-10.91, -37.07),
    "TO": (-10.18, -48.33),
}


def _adicionar_dias_uteis(data: datetime, dias: int) -> datetime:
    atual = data
    adicionados = 0
    while adicionados < dias:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            adicionados += 1
    return atual


def reavaliar_entregas_pendentes() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        pendentes = list(db.scalars(select(Entrega).where(Entrega.status == "pendente")))

        log.info("reavaliação: %d entregas pendentes encontradas", len(pendentes))

        for entrega in pendentes:
            # --- entrega atrasada: prazo já expirou --------------------------
            if entrega.data_prevista < now:
                entrega.status = "atrasada"
                entrega.data_prevista_revisada = _adicionar_dias_uteis(now, 3)
                log.info("entrega %d marcada como atrasada; nova previsão: %s",
                         entrega.id, entrega.data_prevista_revisada)
                continue

            # --- reavaliação de risco ----------------------------------------
            dados: dict = {
                "data_pedido": entrega.data_pedido,
                "data_prevista": entrega.data_prevista,
                "peso_g": entrega.peso_g,
                "valor": entrega.valor,
                "frete": entrega.frete,
                "estado_origem": entrega.estado_origem,
                "estado_destino": entrega.estado_destino,
                "distancia_km": entrega.distancia_km,
            }

            # Injeta coordenadas da capital do estado destino para re-consultar Open-Meteo.
            if entrega.estado_destino and entrega.estado_destino in _CAPITAL_COORDS:
                dlat, dlng = _CAPITAL_COORDS[entrega.estado_destino]
                dados["destino_lat"] = dlat
                dados["destino_lng"] = dlng

            try:
                resultado = prever_risco(dados)
                ultima = entrega.previsoes[-1] if entrega.previsoes else None
                if ultima is None or ultima.nivel != resultado["nivel"]:
                    salvar_previsao(db, entrega.id, resultado, resultado.get("contexto", {}))
                    log.info("entrega %d: nível atualizado para '%s'", entrega.id, resultado["nivel"])
            except Exception as exc:
                log.warning("reavaliação falhou para entrega %d: %s", entrega.id, exc)

        db.commit()
        log.info("reavaliação concluída")

    except Exception as exc:
        log.error("erro no job de reavaliação: %s", exc)
        db.rollback()
    finally:
        db.close()
