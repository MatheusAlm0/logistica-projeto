import logging
from typing import Any, Optional

import joblib
import pandas as pd

from app.core.config import settings
from app.ml.features import montar_features_v2

log = logging.getLogger(__name__)

# Limites provisórios dos níveis. O treino usa scale_pos_weight, então a saída é
# um escore relativo (não é a probabilidade real). Ajuste olhando a distribuição.
LIMITE_MEDIO = 0.40
LIMITE_ALTO = 0.60


class ModeloNaoEncontrado(Exception):
    pass


def classificar(prob: float) -> str:
    if prob >= LIMITE_ALTO:
        return "alto"
    if prob >= LIMITE_MEDIO:
        return "medio"
    return "baixo"


class Predictor:
    """Carrega o modelo uma vez e prevê em milissegundos."""

    def __init__(self, versao: str = "v2") -> None:
        self.versao = versao
        self._pacote: Optional[dict] = None

    def carregar(self, versao: Optional[str] = None) -> None:
        versao = versao or self.versao
        caminho = settings.artifacts_dir / f"modelo_{versao}.joblib"
        if not caminho.exists():
            raise ModeloNaoEncontrado(
                f"{caminho} não existe. Rode: python -m app.ml.train {versao}"
            )
        self._pacote = joblib.load(caminho)
        self.versao = versao
        log.info("modelo %s carregado de %s", versao, caminho)

    @property
    def metricas(self) -> dict:
        if self._pacote is None:
            self.carregar()
        return self._pacote["metricas"]

    def prever(self, dados: dict[str, Any]) -> dict[str, Any]:
        """dados: data_pedido, data_prevista, peso_g, valor, frete,
        estado_origem, estado_destino e distancia_km (pode ser None)."""
        if self._pacote is None:
            self.carregar()
        p = self._pacote

        feats = montar_features_v2(dados)
        df = pd.DataFrame([{f: feats.get(f) for f in p["features"]}])
        for c in p["features"]:
            if c in p["categoricas"]:
                # mesmas categorias do treino (o XGBoost exige)
                df[c] = pd.Categorical(df[c], categories=p["categorias"][c])
            else:
                # None vira NaN, que o XGBoost aceita
                df[c] = pd.to_numeric(df[c], errors="coerce")

        prob = float(p["modelo"].predict_proba(df)[:, 1][0])
        return {
            "probabilidade": round(prob, 4),
            "nivel": classificar(prob),
            "modelo_versao": p["versao"],
            "features_usadas": feats,   # guardar junto da previsão no banco
        }


predictor = Predictor()


if __name__ == "__main__":
    from datetime import datetime

    curta = {
        "data_pedido": datetime(2018, 3, 5, 10), "data_prevista": datetime(2018, 3, 15, 10),
        "peso_g": 800, "valor": 120.0, "frete": 15.0,
        "estado_origem": "SP", "estado_destino": "SP", "distancia_km": 30,
    }
    longa = {
        "data_pedido": datetime(2018, 3, 5, 10), "data_prevista": datetime(2018, 3, 11, 10),
        "peso_g": 8000, "valor": 120.0, "frete": 85.0,
        "estado_origem": "SP", "estado_destino": "AM", "distancia_km": 3100,
    }
    print("curta:", predictor.prever(curta))
    print("longa:", predictor.prever(longa))