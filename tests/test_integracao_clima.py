"""Testes para app/integration/clima.py — Open-Meteo mockado."""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.integration.clima import ARCHIVE_URL, FORECAST_URL, obter_chuva_mm


def _mock_resp(chuva: float | None = 5.2):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"daily": {"precipitation_sum": [chuva]}}
    return resp


# ── URL correta por data ───────────────────────────────────────────────────────

def test_usa_forecast_para_data_futura():
    dia = date.today() + timedelta(days=3)
    with patch("httpx.get", return_value=_mock_resp()) as mock_get:
        obter_chuva_mm(-23.5, -46.6, dia)
    url_chamada = mock_get.call_args[0][0]
    assert url_chamada == FORECAST_URL


def test_usa_archive_para_data_passada():
    dia = date.today() - timedelta(days=10)
    with patch("httpx.get", return_value=_mock_resp()) as mock_get:
        obter_chuva_mm(-23.5, -46.6, dia)
    url_chamada = mock_get.call_args[0][0]
    assert url_chamada == ARCHIVE_URL


# ── valor retornado ───────────────────────────────────────────────────────────

def test_retorna_float_quando_api_ok():
    dia = date.today() + timedelta(days=1)
    with patch("httpx.get", return_value=_mock_resp(7.8)):
        resultado = obter_chuva_mm(-15.0, -47.0, dia)
    assert resultado == 7.8


def test_retorna_zero_quando_sem_chuva():
    dia = date.today() + timedelta(days=1)
    with patch("httpx.get", return_value=_mock_resp(0.0)):
        resultado = obter_chuva_mm(-15.0, -47.0, dia)
    assert resultado == 0.0


def test_retorna_none_quando_api_retorna_none():
    dia = date.today() + timedelta(days=1)
    with patch("httpx.get", return_value=_mock_resp(None)):
        resultado = obter_chuva_mm(-15.0, -47.0, dia)
    assert resultado is None


# ── falhas ────────────────────────────────────────────────────────────────────

def test_retorna_none_quando_api_falha():
    dia = date.today() + timedelta(days=1)
    with patch("httpx.get", side_effect=Exception("timeout")):
        resultado = obter_chuva_mm(-15.0, -47.0, dia)
    assert resultado is None


def test_retorna_none_quando_http_error():
    dia = date.today() + timedelta(days=1)
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("HTTP 503")
    with patch("httpx.get", return_value=resp):
        resultado = obter_chuva_mm(-15.0, -47.0, dia)
    assert resultado is None


# ── parâmetros enviados à API ─────────────────────────────────────────────────

def test_parametros_enviados_corretamente():
    dia = date.today() + timedelta(days=2)
    with patch("httpx.get", return_value=_mock_resp()) as mock_get:
        obter_chuva_mm(-23.5505, -46.6333, dia)

    kwargs = mock_get.call_args[1]["params"]
    assert kwargs["latitude"] == -23.5505
    assert kwargs["longitude"] == -46.6333
    assert kwargs["start_date"] == dia.isoformat()
    assert kwargs["end_date"] == dia.isoformat()
    assert kwargs["timezone"] == "America/Sao_Paulo"
