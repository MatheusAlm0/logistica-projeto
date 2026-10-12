"""Testes unitários para app/ml/features.py — sem banco nem modelo."""
from datetime import datetime

import pytest

from app.ml.features import PROIBIDAS, colunas, montar_features_v2


# ── colunas() ─────────────────────────────────────────────────────────────────

def test_colunas_v2_sem_vazamento():
    """Nenhuma feature da v2 pode estar na lista de PROIBIDAS (data leakage)."""
    feats, num, cat = colunas("v2")
    assert not set(feats) & set(PROIBIDAS), "feature com vazamento detectada em v2"


def test_colunas_v1_sem_vazamento():
    feats, _, _ = colunas("v1")
    assert not set(feats) & set(PROIBIDAS)


def test_colunas_versao_invalida():
    with pytest.raises(KeyError):
        colunas("v99")


# ── montar_features_v2() ──────────────────────────────────────────────────────

def _base(overrides=None):
    d = {
        "data_pedido": datetime(2024, 3, 5, 10, 0),   # terça-feira
        "data_prevista": datetime(2024, 3, 15, 10, 0),
        "peso_g": 800.0,
        "valor": 120.0,
        "frete": 18.0,
        "estado_origem": "SP",
        "estado_destino": "SP",
        "distancia_km": 50.0,
    }
    if overrides:
        d.update(overrides)
    return d


def test_estimated_delivery_days():
    f = montar_features_v2(_base())
    assert f["estimated_delivery_days"] == pytest.approx(10.0)


def test_freight_ratio():
    f = montar_features_v2(_base())
    assert f["freight_ratio"] == pytest.approx(18.0 / 120.0)


def test_freight_ratio_zero_valor():
    """Não deve explodir se valor == 0."""
    f = montar_features_v2(_base({"valor": 0}))
    assert f["freight_ratio"] is None


def test_same_state_igual():
    f = montar_features_v2(_base({"estado_origem": "SP", "estado_destino": "SP"}))
    assert f["same_state"] == 1


def test_same_state_diferente():
    f = montar_features_v2(_base({"estado_destino": "AM"}))
    assert f["same_state"] == 0


def test_same_state_none_quando_falta_uf():
    f = montar_features_v2(_base({"estado_origem": None, "estado_destino": None}))
    assert f["same_state"] is None


def test_is_sao_paulo_seller_true():
    f = montar_features_v2(_base({"estado_origem": "SP"}))
    assert f["is_sao_paulo_seller"] == 1


def test_is_sao_paulo_seller_false():
    f = montar_features_v2(_base({"estado_origem": "RS"}))
    assert f["is_sao_paulo_seller"] == 0


def test_purchase_day_of_week():
    # 2024-03-05 é terça-feira → 1
    f = montar_features_v2(_base())
    assert f["purchase_day_of_week"] == 1


def test_purchase_is_weekend_false():
    f = montar_features_v2(_base())
    assert f["purchase_is_weekend"] == 0


def test_purchase_is_weekend_true():
    # 2024-03-09 é sábado → weekday() == 5
    f = montar_features_v2(_base({"data_pedido": datetime(2024, 3, 9, 14, 0),
                                   "data_prevista": datetime(2024, 3, 20, 14, 0)}))
    assert f["purchase_is_weekend"] == 1


def test_purchase_hour():
    f = montar_features_v2(_base({"data_pedido": datetime(2024, 3, 5, 23, 0),
                                   "data_prevista": datetime(2024, 3, 15, 23, 0)}))
    assert f["purchase_hour"] == 23


def test_estados_em_maiusculo():
    f = montar_features_v2(_base({"estado_origem": "sp", "estado_destino": "rj"}))
    assert f["seller_state"] == "SP"
    assert f["customer_state"] == "RJ"


def test_distancia_propagada():
    f = montar_features_v2(_base({"distancia_km": 350.5}))
    assert f["distance_km"] == pytest.approx(350.5)


def test_distancia_none_quando_ausente():
    f = montar_features_v2(_base({"distancia_km": None}))
    assert f["distance_km"] is None
