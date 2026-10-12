"""Única fonte da lista de features. Treino e previsão importam daqui."""
from datetime import datetime
from typing import Any, Optional

ALVO = "is_late"
TEMPO = "order_purchase_timestamp"

# v1: todas as colunas do Olist conhecidas no checkout (baseline)
NUMERICAS_V1 = [
    "distance_km", "customer_lat", "customer_lng", "seller_lat", "seller_lng",
    "n_items", "n_distinct_products", "n_sellers", "multi_seller_order",
    "total_price", "total_freight", "max_item_price", "price_per_item",
    "freight_ratio", "freight_per_kg", "total_weight_g", "weight_per_item_g",
    "max_volume_cm3", "avg_photos_qty", "avg_description_len",
    "total_payment_value", "max_installments", "n_payment_methods",
    "estimated_delivery_days", "same_state", "is_sao_paulo_seller",
    "purchase_month", "purchase_day_of_week", "purchase_hour",
    "purchase_is_weekend", "purchase_week_of_year",
]
CATEGORICAS_V1 = ["customer_state", "seller_state", "primary_category", "payment_type"]

# v2: só o que o CADASTRO de uma entrega consegue fornecer
# chuva_mm e duracao_min são NULL no dataset histórico (Olist não tem);
# o XGBoost lida com NaN nativamente — aprende a usá-los quando disponíveis.
NUMERICAS_V2 = [
    "distance_km", "duracao_min", "total_weight_g", "total_price", "total_freight",
    "freight_ratio", "estimated_delivery_days", "same_state", "is_sao_paulo_seller",
    "purchase_day_of_week", "purchase_hour", "purchase_is_weekend",
    "chuva_mm",
]
CATEGORICAS_V2 = ["customer_state", "seller_state"]

# versão -> (numéricas, categóricas)
VERSOES = {
    "v1": (NUMERICAS_V1, CATEGORICAS_V1),
    "v2": (NUMERICAS_V2, CATEGORICAS_V2),
}

# só existem depois da entrega: nunca podem ser feature (vazamento)
PROIBIDAS = [
    "is_late", "actual_delivery_days", "days_late", "order_status",
    "order_delivered_customer_date", "order_delivered_carrier_date",
    "order_approved_at", "order_estimated_delivery_date", "purchase_year",
]


def colunas(versao: str) -> tuple[list[str], list[str], list[str]]:
    """Devolve (features, numericas, categoricas) da versão, já validando vazamento."""
    num, cat = VERSOES[versao]
    feats = num + cat
    vazadas = set(feats) & set(PROIBIDAS)
    assert not vazadas, f"feature com vazamento: {vazadas}"
    return feats, num, cat


def montar_features_v2(d: dict[str, Any]) -> dict[str, Any]:
    """Converte o cadastro de uma entrega nos nomes de feature da v2.

    Campos esperados em d: data_pedido, data_prevista (datetime), peso_g, valor,
    frete, estado_origem, estado_destino, distancia_km (pode ser None),
    chuva_mm (pode ser None) e duracao_min (pode ser None — vem da rota OSRM).
    """
    pedido: datetime = d["data_pedido"]
    prevista: datetime = d["data_prevista"]
    origem: Optional[str] = (d.get("estado_origem") or "").upper() or None
    destino: Optional[str] = (d.get("estado_destino") or "").upper() or None
    valor = d.get("valor") or 0
    return {
        "distance_km": d.get("distancia_km"),
        "duracao_min": d.get("duracao_min"),            # tempo de rota OSRM (None = haversine/sem rota)
        "total_weight_g": d.get("peso_g"),
        "total_price": d.get("valor"),
        "total_freight": d.get("frete"),
        "freight_ratio": (d["frete"] / valor) if valor else None,
        "estimated_delivery_days": (prevista - pedido).total_seconds() / 86400,
        "same_state": int(origem == destino) if origem and destino else None,
        "is_sao_paulo_seller": int(origem == "SP") if origem else None,
        "purchase_day_of_week": pedido.weekday(),   # 0 = segunda
        "purchase_hour": pedido.hour,
        "purchase_is_weekend": int(pedido.weekday() >= 5),
        "chuva_mm": d.get("chuva_mm"),              # precipitação no destino no dia previsto
        "customer_state": destino,
        "seller_state": origem,
    }