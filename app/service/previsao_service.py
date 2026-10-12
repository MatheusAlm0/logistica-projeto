from typing import Any

from app.core.exceptions import RegraDeNegocioError
from app.integration.clima import obter_chuva_mm
from app.integration.rota import obter_rota
from app.ml.predictor import predictor

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def _normalizar(d: dict[str, Any]) -> dict[str, Any]:
    """Padroniza os dados: datas sem fuso horário e UF em maiúsculas."""
    d = dict(d)
    d["data_pedido"] = d["data_pedido"].replace(tzinfo=None)
    d["data_prevista"] = d["data_prevista"].replace(tzinfo=None)
    for campo in ("estado_origem", "estado_destino"):
        if d.get(campo):
            d[campo] = d[campo].upper()
    return d


def _validar(d: dict[str, Any]) -> None:
    """Regras de negócio. Acumula os erros e levanta um só."""
    erros = []
    if d["peso_g"] <= 0:
        erros.append("peso_g deve ser maior que zero")
    if d["valor"] < 0:
        erros.append("valor não pode ser negativo")
    if d["frete"] < 0:
        erros.append("frete não pode ser negativo")
    if d["data_prevista"] <= d["data_pedido"]:
        erros.append("data_prevista deve ser posterior à data_pedido")
    if d.get("distancia_km") is not None and d["distancia_km"] < 0:
        erros.append("distancia_km não pode ser negativa")
    for campo in ("estado_origem", "estado_destino"):
        uf = d.get(campo)
        if uf is not None and uf not in UFS:
            erros.append(f"{campo} inválido: {uf}")
    for lat, lng, nome in (
        ("origem_lat", "origem_lng", "origem"),
        ("destino_lat", "destino_lng", "destino"),
    ):
        if (d.get(lat) is None) != (d.get(lng) is None):
            erros.append(f"informe latitude e longitude de {nome} juntas")
    if erros:
        raise RegraDeNegocioError("; ".join(erros))


def prever(dados: dict[str, Any]) -> dict[str, Any]:
    dados = _normalizar(dados)   # primeiro padroniza (fuso, UF)
    _validar(dados)              # depois valida
    contexto: dict[str, Any] = {}

    olat, olng = dados.get("origem_lat"), dados.get("origem_lng")
    dlat, dlng = dados.get("destino_lat"), dados.get("destino_lng")

    # distância + tempo de rota: usa a informada; senão, calcula pelo OSRM
    if dados.get("distancia_km") is None and None not in (olat, olng, dlat, dlng):
        rota = obter_rota(olat, olng, dlat, dlng)
        dados["distancia_km"] = rota["distancia_km"]
        dados["duracao_min"] = rota.get("duracao_min")   # None se usou haversine
        contexto["rota"] = rota

    # clima no destino, no dia previsto → agora passado como feature ao modelo
    if dlat is not None and dlng is not None:
        chuva = obter_chuva_mm(dlat, dlng, dados["data_prevista"].date())
        contexto["chuva_mm"] = chuva
        dados["chuva_mm"] = chuva   # feature do modelo

    resultado = predictor.prever(dados)
    resultado["contexto"] = contexto
    return resultado