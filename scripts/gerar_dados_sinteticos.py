"""
scripts/gerar_dados_sinteticos.py

Gera N registros sintéticos de entregas brasileiras com dados reais de:
  - OSRM public  : distância (km) + duração (min) por par de cidades
  - Open-Meteo   : precipitação diária via Archive API (1 chamada por cidade)
Calcula is_late com regras probabilísticas baseadas em distância, chuva e prazo.
Insere em entregas_historico e retreina o modelo v2 ao final.

Uso:
  python -m scripts.gerar_dados_sinteticos [--n 5000] [--seed 42]
  python scripts/gerar_dados_sinteticos.py --n 1000
"""
import argparse
import math
import random
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd
from sqlalchemy import inspect, text

# ── garante que o pacote app esteja no path ───────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import engine
from app.ml.train import treinar

# ─────────────────────────────────────────────────────────────────────────────
# 20 cidades brasileiras reais com lat/lng e UF
# ─────────────────────────────────────────────────────────────────────────────
CIDADES = [
    {"nome": "São Paulo",       "uf": "SP", "lat": -23.5505, "lng": -46.6333},
    {"nome": "Rio de Janeiro",  "uf": "RJ", "lat": -22.9068, "lng": -43.1729},
    {"nome": "Belo Horizonte",  "uf": "MG", "lat": -19.9167, "lng": -43.9345},
    {"nome": "Brasília",        "uf": "DF", "lat": -15.7797, "lng": -47.9297},
    {"nome": "Salvador",        "uf": "BA", "lat": -12.9714, "lng": -38.5014},
    {"nome": "Fortaleza",       "uf": "CE", "lat":  -3.7319, "lng": -38.5267},
    {"nome": "Manaus",          "uf": "AM", "lat":  -3.1019, "lng": -60.0250},
    {"nome": "Curitiba",        "uf": "PR", "lat": -25.4284, "lng": -49.2733},
    {"nome": "Recife",          "uf": "PE", "lat":  -8.0578, "lng": -34.8829},
    {"nome": "Porto Alegre",    "uf": "RS", "lat": -30.0346, "lng": -51.2177},
    {"nome": "Belém",           "uf": "PA", "lat":  -1.4558, "lng": -48.4902},
    {"nome": "Goiânia",         "uf": "GO", "lat": -16.6869, "lng": -49.2648},
    {"nome": "São Luís",        "uf": "MA", "lat":  -2.5297, "lng": -44.3028},
    {"nome": "Maceió",          "uf": "AL", "lat":  -9.6658, "lng": -35.7350},
    {"nome": "Natal",           "uf": "RN", "lat":  -5.7945, "lng": -35.2110},
    {"nome": "Teresina",        "uf": "PI", "lat":  -5.0892, "lng": -42.8019},
    {"nome": "Campo Grande",    "uf": "MS", "lat": -20.4697, "lng": -54.6201},
    {"nome": "João Pessoa",     "uf": "PB", "lat":  -7.1195, "lng": -34.8450},
    {"nome": "Aracaju",         "uf": "SE", "lat": -10.9472, "lng": -37.0731},
    {"nome": "Florianópolis",   "uf": "SC", "lat": -27.5954, "lng": -48.5480},
]

CIDADE_MAP = {c["nome"]: c for c in CIDADES}

DATA_INI = datetime(2023, 1, 1)
DATA_FIM = datetime(2024, 12, 15)   # deixa margem para prazo de entrega


# ─────────────────────────────────────────────────────────────────────────────
# Fallback: distância haversine quando OSRM falha
# ─────────────────────────────────────────────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ─────────────────────────────────────────────────────────────────────────────
# OSRM: rotas para todos os pares de cidades
# ─────────────────────────────────────────────────────────────────────────────

def _rota_osrm(orig: dict, dest: dict, cli: httpx.Client) -> dict:
    """Retorna {distancia_km, duracao_min}. Usa haversine como fallback."""
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{orig['lng']},{orig['lat']};{dest['lng']},{dest['lat']}"
        "?overview=false"
    )
    try:
        r = cli.get(url, timeout=15)
        r.raise_for_status()
        rota = r.json()["routes"][0]
        return {
            "distancia_km": rota["distance"] / 1000,
            "duracao_min":  rota["duration"] / 60,
        }
    except Exception:
        dist = _haversine(orig["lat"], orig["lng"], dest["lat"], dest["lng"])
        return {"distancia_km": dist, "duracao_min": None}


def buscar_todas_rotas() -> dict:
    """Chama OSRM para todos os ~380 pares únicos (com cache simétrico)."""
    pares = sorted(
        (o["nome"], d["nome"])
        for o in CIDADES for d in CIDADES if o["nome"] != d["nome"]
    )
    cache: dict = {}
    total = len(pares)
    print(f"\n[OSRM] {total} pares a buscar (cache simétrico reduz ~50%)…")

    with httpx.Client() as cli:
        for i, (on, dn) in enumerate(pares, 1):
            if (dn, on) in cache:           # aproveita direção inversa
                cache[(on, dn)] = cache[(dn, on)]
            else:
                cache[(on, dn)] = _rota_osrm(CIDADE_MAP[on], CIDADE_MAP[dn], cli)
                time.sleep(0.1)

            if i % 50 == 0 or i == total:
                n_api = sum(1 for v in cache.values() if v.get("duracao_min") is not None)
                print(f"  {i}/{total} pares  |  {n_api} via OSRM  |  {i - n_api} haversine")

    return cache


# ─────────────────────────────────────────────────────────────────────────────
# Open-Meteo Archive: precipitação para todas as cidades
# ─────────────────────────────────────────────────────────────────────────────

def buscar_clima_cidades(
    start: str = "2023-01-01",
    end: str   = "2024-12-31",
) -> dict:
    """
    Uma chamada por cidade para o período completo.
    Retorna {cidade_nome: {date_str: chuva_mm}}.
    """
    print(f"\n[Open-Meteo] Buscando precipitação para {len(CIDADES)} cidades…")
    clima: dict = {}
    with httpx.Client() as cli:
        for cidade in CIDADES:
            try:
                r = cli.get(
                    "https://archive-api.open-meteo.com/v1/archive",
                    params={
                        "latitude":        cidade["lat"],
                        "longitude":       cidade["lng"],
                        "daily":           "precipitation_sum",
                        "start_date":      start,
                        "end_date":        end,
                        "timezone":        "America/Sao_Paulo",
                    },
                    timeout=30,
                )
                r.raise_for_status()
                diario = r.json()["daily"]
                clima[cidade["nome"]] = {
                    d: (mm if mm is not None else 0.0)
                    for d, mm in zip(diario["time"], diario["precipitation_sum"])
                }
                print(f"  ok  {cidade['nome']:20s}  ({len(clima[cidade['nome']])} dias)")
                time.sleep(0.25)
            except Exception as exc:
                print(f"  err {cidade['nome']:20s}  ({exc}) — usando 0 mm")
                clima[cidade["nome"]] = {}
    return clima


# ─────────────────────────────────────────────────────────────────────────────
# Geração de registros sintéticos
# ─────────────────────────────────────────────────────────────────────────────

def _dias_estimados(distancia_km: float, rng: random.Random) -> int:
    if distancia_km < 200:
        return rng.randint(3, 5)
    if distancia_km < 500:
        return rng.randint(4, 8)
    if distancia_km < 1000:
        return rng.randint(6, 12)
    if distancia_km < 2000:
        return rng.randint(8, 18)
    return rng.randint(12, 25)


def _prob_atraso(distancia_km: float, chuva_mm: float, est_days: int, same: int) -> float:
    p = 0.08
    if chuva_mm > 10:
        p += 0.10
    if chuva_mm > 30:
        p += 0.15
    if distancia_km > 800:
        p += 0.08
    if distancia_km > 2000:
        p += 0.12
    if est_days < 5:
        p += 0.10
    if not same and distancia_km > 1000:
        p += 0.07
    return min(p, 0.65)


def gerar_registros(
    n: int,
    rotas: dict,
    clima: dict,
    seed: int = 42,
) -> pd.DataFrame:
    rng = random.Random(seed)
    pares_validos = list(rotas.keys())
    delta_dias = (DATA_FIM - DATA_INI).days

    registros = []
    tentativas = 0
    while len(registros) < n:
        tentativas += 1
        if tentativas > n * 10:
            print(f"[WARN] abortando após {tentativas} tentativas com {len(registros)} registros")
            break

        on, dn = rng.choice(pares_validos)
        rota = rotas[(on, dn)]
        orig = CIDADE_MAP[on]
        dest = CIDADE_MAP[dn]

        pedido = DATA_INI + timedelta(
            days=rng.randint(0, delta_dias),
            hours=rng.randint(7, 22),
            minutes=rng.randint(0, 59),
        )
        est_days = _dias_estimados(rota["distancia_km"], rng)
        estimada = pedido + timedelta(days=est_days)
        if estimada > datetime(2025, 3, 1):
            continue

        data_str = estimada.date().isoformat()
        chuva = clima.get(dn, {}).get(data_str, 0.0)

        same = int(orig["uf"] == dest["uf"])
        is_late = int(rng.random() < _prob_atraso(rota["distancia_km"], chuva, est_days, same))

        if is_late:
            entregue = estimada + timedelta(days=rng.randint(1, 15))
        else:
            antecipa = rng.randint(1, max(1, est_days - 1))
            entregue = pedido + timedelta(days=antecipa)

        peso_g = rng.randint(100, 20_000)
        valor  = round(rng.uniform(20.0, 800.0), 2)
        frete  = round(valor * rng.uniform(0.05, 0.40), 2)

        duracao = rota.get("duracao_min")

        registros.append({
            "order_id":                     "sint_" + uuid.uuid4().hex[:19],
            "order_purchase_timestamp":      pedido,
            "order_estimated_delivery_date": estimada,
            "order_delivered_customer_date": entregue,
            "customer_state":                dest["uf"],
            "seller_state":                  orig["uf"],
            "distance_km":                   round(rota["distancia_km"], 2),
            "duracao_min":                   round(duracao, 2) if duracao else None,
            "total_weight_g":                peso_g,
            "total_price":                   valor,
            "total_freight":                 frete,
            "freight_ratio":                 round(frete / valor, 4) if valor else 0.0,
            "estimated_delivery_days":       est_days,
            "same_state":                    same,
            "is_sao_paulo_seller":           int(orig["uf"] == "SP"),
            "purchase_day_of_week":          pedido.weekday(),
            "purchase_hour":                 pedido.hour,
            "purchase_is_weekend":           int(pedido.weekday() >= 5),
            "chuva_mm":                      round(chuva, 2),
            "is_late":                       is_late,
            "origem_dado":                   "sintetico",
        })

    return pd.DataFrame(registros)


# ─────────────────────────────────────────────────────────────────────────────
# Banco de dados
# ─────────────────────────────────────────────────────────────────────────────

def garantir_colunas_novas() -> None:
    """Adiciona chuva_mm e duracao_min se não existirem."""
    existentes = {c["name"] for c in inspect(engine).get_columns("entregas_historico")}
    with engine.begin() as conn:
        for col, tipo in [("chuva_mm", "DOUBLE PRECISION"), ("duracao_min", "DOUBLE PRECISION")]:
            if col not in existentes:
                conn.execute(text(f"ALTER TABLE entregas_historico ADD COLUMN {col} {tipo}"))
                print(f"  + coluna {col} adicionada")
            else:
                print(f"  v coluna {col} ja existe")


def inserir(df: pd.DataFrame) -> None:
    print(f"\n[DB] Inserindo {len(df)} registros…")
    df.to_sql(
        "entregas_historico",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )
    print("[DB] Inserção concluída.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(n: int = 5000, seed: int = 42) -> None:
    print(f"=== Gerando {n} registros sintéticos (seed={seed}) ===")

    print("\n[DB] Verificando schema…")
    garantir_colunas_novas()

    rotas = buscar_todas_rotas()
    clima = buscar_clima_cidades()

    print(f"\n[GEN] Gerando {n} registros…")
    df = gerar_registros(n, rotas, clima, seed=seed)

    taxa = df["is_late"].mean() * 100
    print(f"  Registros: {len(df)}")
    print(f"  Taxa de atraso simulada: {taxa:.1f}%")
    print(f"  chuva_mm nao-nulo: {df['chuva_mm'].notna().sum()}")
    print(f"  duracao_min nao-nulo: {df['duracao_min'].notna().sum()}")

    inserir(df)

    print("\n[ML] Retreinando modelo v2 (Olist + sinteticos)…")
    metricas = treinar("v2")

    print("\n=== Retreino concluido ===")
    print(f"  ROC-AUC : {metricas['roc_auc']:.4f}")
    print(f"  PR-AUC  : {metricas['pr_auc']:.4f}")
    print(f"  Baseline: {metricas['baseline_pr_auc']:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera dados sinteticos e retreina o modelo v2."
    )
    parser.add_argument("--n",    type=int, default=5000, help="Numero de registros (padrao: 5000)")
    parser.add_argument("--seed", type=int, default=42,   help="Semente aleatoria (padrao: 42)")
    args = parser.parse_args()
    main(n=args.n, seed=args.seed)
