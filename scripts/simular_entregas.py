"""
scripts/simular_entregas.py

Simula um fluxo completo de entregas chamando a API REST local.
Cria entregas com dados sintéticos realistas, finaliza cada uma com uma
data de entrega sorteada e acompanha o ciclo de retreino automático.

Requisito: servidor rodando em localhost:8000 (uvicorn app.main:app --reload).

Uso:
  python scripts/simular_entregas.py [--n 500] [--delay 0.2] [--seed 42]
  python scripts/simular_entregas.py --n 500 --fast   # sem chamadas OSRM/Open-Meteo (~5 min)
  python scripts/simular_entregas.py --n 100           # modo completo com APIs externas
"""
import argparse
import math
import random
import sys
import time
from datetime import datetime, timedelta

import httpx

# ─────────────────────────────────────────────────────────────────────────────
# Cidades (mesmas do gerar_dados_sinteticos.py)
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

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _log(*args, **kwargs) -> None:
    """print com flush imediato para funcionar em background/pipe."""
    print(*args, **kwargs, flush=True)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _fmt(dt: datetime) -> str:
    """Formata datetime para o formato esperado pela API (sem fuso)."""
    return dt.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")


def _gerar_body(rng: random.Random, fast: bool = False) -> tuple[dict, datetime, datetime]:
    """
    Gera um body válido para POST /entregas.

    fast=False (padrão): envia coordenadas → servidor chama OSRM + Open-Meteo (~4-8s/entrega).
    fast=True           : passa distancia_km via haversine, sem coordenadas → servidor
                          pula OSRM e Open-Meteo (~0.3s/entrega).
    """
    while True:
        orig, dest = rng.sample(CIDADES, 2)

        # Pedido no passado (2-120 dias atrás) para que a API use Open-Meteo Archive
        dias_atras = rng.randint(2, 120)
        pedido = datetime.now() - timedelta(
            days=dias_atras,
            hours=rng.randint(7, 22),
            minutes=rng.randint(0, 59),
        )

        dist = _haversine(orig["lat"], orig["lng"], dest["lat"], dest["lng"])
        if dist < 100:
            est_days = rng.randint(3, 5)
        elif dist < 500:
            est_days = rng.randint(4, 8)
        elif dist < 1200:
            est_days = rng.randint(6, 12)
        else:
            est_days = rng.randint(10, 22)

        prevista = pedido + timedelta(days=est_days)

        # Garante que ambas as datas ficam no passado
        if prevista >= datetime.now():
            continue

        peso_g = rng.randint(100, 20_000)
        valor  = round(rng.uniform(20.0, 800.0), 2)
        frete  = round(valor * rng.uniform(0.05, 0.40), 2)

        body: dict = {
            "data_pedido":    _fmt(pedido),
            "data_prevista":  _fmt(prevista),
            "peso_g":         peso_g,
            "valor":          valor,
            "frete":          frete,
            "estado_origem":  orig["uf"],
            "estado_destino": dest["uf"],
        }
        if fast:
            # Passa distância calculada; sem lat/lng → sem OSRM nem Open-Meteo
            body["distancia_km"] = round(dist * 1.35, 2)  # fator estrada ~1.35× linha reta
        else:
            # Coordenadas completas → servidor chama OSRM + Open-Meteo
            body["origem_lat"]  = orig["lat"]
            body["origem_lng"]  = orig["lng"]
            body["destino_lat"] = dest["lat"]
            body["destino_lng"] = dest["lng"]

        return body, pedido, prevista


def _gerar_data_entregue(
    pedido: datetime,
    prevista: datetime,
    rng: random.Random,
    prob_atraso: float = 0.25,
) -> tuple[datetime, bool]:
    """Sorteia uma data_entregue e indica se é atraso."""
    est_days = max(1, (prevista - pedido).days)
    atrasou = rng.random() < prob_atraso

    if atrasou:
        data = prevista + timedelta(days=rng.randint(1, 15))
    else:
        antecipa = rng.randint(0, max(0, est_days - 1))
        data = pedido + timedelta(days=max(1, est_days - antecipa))
        # garante que não passa da data prevista
        if data > prevista:
            data = prevista - timedelta(days=1)
        if data <= pedido:
            data = pedido + timedelta(days=1)

    return data, atrasou


def _mostrar_status(cli: httpx.Client, base_url: str, finalizadas: int) -> int:
    """Chama GET /retreinos/status e imprime o progresso. Retorna id do último retreino ok."""
    try:
        r = cli.get(f"{base_url}/retreinos/status", timeout=10)
        r.raise_for_status()
        s = r.json()
        ok = s.get("ultimo_retreino") or {}
        retreinos_ok = ok.get("id", 0) if ok else 0

        _log(
            f"\n{'─'*60}\n"
            f"  [STATUS após {finalizadas} finalizações]\n"
            f"  Modelo ativo   : {s.get('modelo_ativo', '?')}\n"
            f"  ROC-AUC        : {(s.get('metricas_ativas') or {}).get('roc_auc', '?')}\n"
            f"  PR-AUC         : {(s.get('metricas_ativas') or {}).get('pr_auc', '?')}\n"
            f"  Desde retreino : {s.get('entregas_desde_ultimo_retreino', '?')} "
            f"/ {s.get('min_para_retreinar', '?')} necessárias\n"
            f"  Pronto         : {'SIM' if s.get('pronto_para_retreinar') else 'não'}\n"
            f"{'─'*60}\n"
        )
        return retreinos_ok
    except Exception as exc:
        _log(f"  [WARN] /retreinos/status falhou: {exc}")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(n: int, base_url: str, delay: float, seed: int, fast: bool) -> None:
    rng = random.Random(seed)
    modo = "fast (sem OSRM/Open-Meteo)" if fast else "completo (com OSRM + Open-Meteo)"

    # Verifica se o servidor está no ar
    try:
        with httpx.Client() as cli:
            r = cli.get(f"{base_url}/health", timeout=5)
            r.raise_for_status()
            health = r.json()
        _log(f"Servidor ok — modelo: {health.get('modelo', '?')}")
    except Exception as exc:
        _log(f"[ERRO] Servidor não responde em {base_url}: {exc}")
        _log("Inicie a API com:  uvicorn app.main:app --reload")
        sys.exit(1)

    # Contadores
    criadas            = 0
    finalizadas        = 0
    erros_criar        = 0
    erros_final        = 0
    atrasadas          = 0
    ultimo_retreino_id = 0
    retreinos_disparados = 0
    inicio = time.time()

    _log(f"\nSimulação: {n} entregas | modo={modo} | delay={delay}s | seed={seed}\n")

    with httpx.Client(timeout=30) as cli:
        i = 0
        while criadas < n:
            i += 1

            # ── 1. Gera dados e cria a entrega ────────────────────────────────
            body, pedido, prevista = _gerar_body(rng, fast=fast)

            try:
                r = cli.post(f"{base_url}/entregas", json=body)
                if r.status_code == 201:
                    resp  = r.json()
                    eid   = resp["id"]
                    nivel = (resp.get("ultima_previsao") or {}).get("nivel", "?")
                    criadas += 1
                    _log(
                        f"  [{criadas:04d}/{n}] criada id={eid:5d}  "
                        f"risco={nivel:5s}  "
                        f"{body['estado_origem']}→{body['estado_destino']}"
                    )
                else:
                    erros_criar += 1
                    _log(f"  [ERRO criar #{i}] HTTP {r.status_code}: {r.text[:120]}")
                    time.sleep(delay)
                    continue
            except Exception as exc:
                erros_criar += 1
                _log(f"  [ERRO criar #{i}] {exc}")
                time.sleep(delay)
                continue

            time.sleep(delay)

            # ── 2. Finaliza a entrega ─────────────────────────────────────────
            data_ent, atrasou = _gerar_data_entregue(pedido, prevista, rng)

            try:
                r = cli.patch(
                    f"{base_url}/entregas/{eid}/finalizar",
                    json={"data_entregue": _fmt(data_ent)},
                )
                if r.status_code == 200:
                    finalizadas += 1
                    if atrasou:
                        atrasadas += 1
                    tag = "ATRASADA" if atrasou else "no prazo"
                    _log(
                        f"           finalizada id={eid:5d}  {tag:8s}  "
                        f"entregue={data_ent.strftime('%Y-%m-%d')}"
                    )
                else:
                    erros_final += 1
                    _log(f"  [ERRO final id={eid}] HTTP {r.status_code}: {r.text[:120]}")
            except Exception as exc:
                erros_final += 1
                _log(f"  [ERRO final id={eid}] {exc}")

            time.sleep(delay)

            # ── 3. A cada 100 finalizações: mostra status do retreino ─────────
            if finalizadas > 0 and finalizadas % 100 == 0:
                rid = _mostrar_status(cli, base_url, finalizadas)
                if rid > ultimo_retreino_id:
                    retreinos_disparados += rid - ultimo_retreino_id
                    ultimo_retreino_id = rid

    # ── Resumo final ─────────────────────────────────────────────────────────
    duracao = time.time() - inicio
    taxa_atraso = (atrasadas / finalizadas * 100) if finalizadas else 0

    with httpx.Client(timeout=10) as cli:
        _mostrar_status(cli, base_url, finalizadas)
        try:
            r = cli.get(f"{base_url}/retreinos", params={"status": "ok", "limit": 100})
            r.raise_for_status()
            retreinos_ok = r.json().get("total", 0)
        except Exception:
            retreinos_ok = "?"

    _log(
        f"\n{'═'*60}\n"
        f"  RESUMO FINAL\n"
        f"{'═'*60}\n"
        f"  Modo                 : {modo}\n"
        f"  Entregas criadas     : {criadas}\n"
        f"  Entregas finalizadas : {finalizadas}\n"
        f"  Erros (criar)        : {erros_criar}\n"
        f"  Erros (finalizar)    : {erros_final}\n"
        f"  Atrasadas            : {atrasadas} ({taxa_atraso:.1f}%)\n"
        f"  No prazo             : {finalizadas - atrasadas} ({100 - taxa_atraso:.1f}%)\n"
        f"  Retreinos ok (total) : {retreinos_ok}\n"
        f"  Tempo total          : {duracao:.0f}s ({duracao/60:.1f} min)\n"
        f"{'═'*60}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simula entregas chamando a API local e exercita o retreino automático."
    )
    parser.add_argument(
        "--n", type=int, default=500,
        help="Número de entregas a criar (padrão: 500)",
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000",
        help="URL base da API (padrão: http://localhost:8000)",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Segundos de pausa entre chamadas (padrão: 1.0)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Semente aleatória (padrão: 42)",
    )
    parser.add_argument(
        "--fast", action="store_true",
        help="Modo rápido: passa distancia_km diretamente, sem chamar OSRM nem Open-Meteo (~5 min p/ 500)",
    )
    args = parser.parse_args()
    main(n=args.n, base_url=args.base_url, delay=args.delay, seed=args.seed, fast=args.fast)
