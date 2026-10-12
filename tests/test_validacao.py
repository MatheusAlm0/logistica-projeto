"""Testes das regras de negócio em previsao_service._validar / _normalizar."""
from datetime import datetime, timezone

import pytest

from app.core.exceptions import RegraDeNegocioError
from app.service.previsao_service import _normalizar, _validar


def _dados_validos(**overrides):
    d = {
        "data_pedido": datetime(2024, 3, 5, 10, 0),
        "data_prevista": datetime(2024, 3, 15, 10, 0),
        "peso_g": 800.0,
        "valor": 120.0,
        "frete": 18.0,
        "estado_origem": "SP",
        "estado_destino": "RJ",
        "distancia_km": None,
        "origem_lat": None,
        "origem_lng": None,
        "destino_lat": None,
        "destino_lng": None,
    }
    d.update(overrides)
    return d


# ── _normalizar ────────────────────────────────────────────────────────────────

def test_normalizar_remove_fuso():
    d = _dados_validos(
        data_pedido=datetime(2024, 3, 5, 10, tzinfo=timezone.utc),
        data_prevista=datetime(2024, 3, 15, 10, tzinfo=timezone.utc),
    )
    n = _normalizar(d)
    assert n["data_pedido"].tzinfo is None
    assert n["data_prevista"].tzinfo is None


def test_normalizar_uf_maiuscula():
    d = _dados_validos(estado_origem="sp", estado_destino="rj")
    n = _normalizar(d)
    assert n["estado_origem"] == "SP"
    assert n["estado_destino"] == "RJ"


def test_normalizar_uf_none_permitido():
    d = _dados_validos(estado_origem=None, estado_destino=None)
    n = _normalizar(d)
    assert n["estado_origem"] is None


# ── _validar: casos válidos ────────────────────────────────────────────────────

def test_validar_dados_ok():
    _validar(_dados_validos())   # não deve levantar


def test_validar_sem_estados_ok():
    _validar(_dados_validos(estado_origem=None, estado_destino=None))


def test_validar_sem_coordenadas_ok():
    _validar(_dados_validos(origem_lat=None, origem_lng=None,
                            destino_lat=None, destino_lng=None))


def test_validar_com_coordenadas_completas_ok():
    _validar(_dados_validos(
        origem_lat=-23.5, origem_lng=-46.6,
        destino_lat=-22.9, destino_lng=-43.1,
    ))


# ── _validar: peso ────────────────────────────────────────────────────────────

def test_peso_zero_invalido():
    with pytest.raises(RegraDeNegocioError, match="peso_g"):
        _validar(_dados_validos(peso_g=0))


def test_peso_negativo_invalido():
    with pytest.raises(RegraDeNegocioError, match="peso_g"):
        _validar(_dados_validos(peso_g=-1))


# ── _validar: valor / frete ───────────────────────────────────────────────────

def test_valor_negativo_invalido():
    with pytest.raises(RegraDeNegocioError, match="valor"):
        _validar(_dados_validos(valor=-0.01))


def test_frete_negativo_invalido():
    with pytest.raises(RegraDeNegocioError, match="frete"):
        _validar(_dados_validos(frete=-5))


def test_valor_zero_valido():
    _validar(_dados_validos(valor=0.0))   # zero é aceito


# ── _validar: datas ───────────────────────────────────────────────────────────

def test_data_prevista_igual_pedido_invalida():
    ts = datetime(2024, 3, 5, 10)
    with pytest.raises(RegraDeNegocioError, match="data_prevista"):
        _validar(_dados_validos(data_pedido=ts, data_prevista=ts))


def test_data_prevista_anterior_pedido_invalida():
    with pytest.raises(RegraDeNegocioError, match="data_prevista"):
        _validar(_dados_validos(
            data_pedido=datetime(2024, 3, 10),
            data_prevista=datetime(2024, 3, 5),
        ))


# ── _validar: estados ─────────────────────────────────────────────────────────

def test_uf_invalida_origem():
    with pytest.raises(RegraDeNegocioError, match="estado_origem"):
        _validar(_dados_validos(estado_origem="XX"))


def test_uf_invalida_destino():
    with pytest.raises(RegraDeNegocioError, match="estado_destino"):
        _validar(_dados_validos(estado_destino="ZZ"))


def test_todas_ufs_brasileiras_validas():
    ufs = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
           "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
           "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
    for uf in ufs:
        _validar(_dados_validos(estado_origem=uf, estado_destino=uf))


# ── _validar: coordenadas parciais ───────────────────────────────────────────

def test_lat_sem_lng_invalido():
    with pytest.raises(RegraDeNegocioError, match="origem"):
        _validar(_dados_validos(origem_lat=-23.5, origem_lng=None))


def test_lng_sem_lat_invalido():
    with pytest.raises(RegraDeNegocioError, match="destino"):
        _validar(_dados_validos(destino_lat=None, destino_lng=-43.1))


# ── acúmulo de erros ──────────────────────────────────────────────────────────

def test_multiplos_erros_acumulados():
    """_validar deve levantar uma exceção com todos os erros juntos."""
    with pytest.raises(RegraDeNegocioError) as exc_info:
        _validar(_dados_validos(peso_g=0, valor=-10, frete=-5))
    msg = str(exc_info.value)
    assert "peso_g" in msg
    assert "valor" in msg
    assert "frete" in msg
