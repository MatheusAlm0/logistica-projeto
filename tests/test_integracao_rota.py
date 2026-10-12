"""Testes para app/integration/rota.py — OSRM mockado via unittest.mock."""
from unittest.mock import MagicMock, patch

import pytest

from app.integration.rota import haversine_km, obter_rota


# ── haversine_km ──────────────────────────────────────────────────────────────

def test_haversine_mesma_coordenada():
    assert haversine_km(-23.5, -46.6, -23.5, -46.6) == pytest.approx(0.0, abs=1e-6)


def test_haversine_sp_rj_aproximado():
    # São Paulo → Rio de Janeiro: ~357 km em linha reta
    dist = haversine_km(-23.5505, -46.6333, -22.9068, -43.1729)
    assert 340 < dist < 380, f"esperado ~357 km, obteve {dist:.1f}"


def test_haversine_valores_positivos():
    dist = haversine_km(-10.0, -40.0, -20.0, -50.0)
    assert dist > 0


# ── obter_rota: OSRM disponível ───────────────────────────────────────────────

def _mock_httpx_ok(distancia_m=150_000, duracao_s=5400):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "routes": [{"distance": distancia_m, "duration": duracao_s}]
    }
    return resp


def test_obter_rota_osrm_sucesso():
    with patch("httpx.get", return_value=_mock_httpx_ok(150_000, 5400)):
        r = obter_rota(-23.5, -46.6, -22.9, -43.1)

    assert r["distancia_km"] == pytest.approx(150.0)
    assert r["duracao_min"] == pytest.approx(90.0)
    assert r["fonte"] == "osrm"


def test_obter_rota_osrm_converte_metros_para_km():
    with patch("httpx.get", return_value=_mock_httpx_ok(1_000, 60)):
        r = obter_rota(0, 0, 0, 0)
    assert r["distancia_km"] == pytest.approx(1.0)
    assert r["duracao_min"] == pytest.approx(1.0)


# ── obter_rota: fallback haversine ────────────────────────────────────────────

def test_obter_rota_fallback_quando_osrm_falha():
    with patch("httpx.get", side_effect=Exception("timeout")):
        r = obter_rota(-23.5505, -46.6333, -22.9068, -43.1729)

    assert r["fonte"] == "haversine"
    assert r["duracao_min"] is None
    assert 340 < r["distancia_km"] < 380


def test_obter_rota_fallback_quando_osrm_retorna_erro_http():
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("HTTP 500")
    with patch("httpx.get", return_value=resp):
        r = obter_rota(-23.5505, -46.6333, -22.9068, -43.1729)

    assert r["fonte"] == "haversine"


def test_obter_rota_fallback_distancia_positiva():
    with patch("httpx.get", side_effect=ConnectionError("offline")):
        r = obter_rota(-15.0, -47.0, -3.0, -60.0)
    assert r["distancia_km"] > 0
