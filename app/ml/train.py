import sys

import joblib
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from xgboost import XGBClassifier

from app.core.config import settings
from app.core.database import engine
from app.ml.features import ALVO, TEMPO, colunas


def carregar_dados(features: list[str]) -> pd.DataFrame:
    """Lê features + alvo + tempo de entregas_historico.

    Colunas ausentes na tabela (ex.: chuva_mm, duracao_min, adicionadas depois do
    dataset Olist) são lidas como NULL → NaN no DataFrame.
    O XGBoost lida com NaN nativamente: aprende a usar a feature quando disponível
    e a ignorar quando não está (dados históricos).
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existentes = {c["name"] for c in inspector.get_columns("entregas_historico")}

    partes = []
    for col in features + [ALVO, TEMPO]:
        if col in existentes:
            partes.append(col)
        else:
            partes.append(f"NULL AS {col}")   # coluna nova: NaN para dados antigos

    cols_sql = ", ".join(partes)
    return pd.read_sql(text(f"SELECT {cols_sql} FROM entregas_historico"), engine)


def treinar(versao: str = "v2") -> dict:
    features, numericas, categoricas = colunas(versao)
    df = carregar_dados(features)
    print(f"[{versao}] linhas lidas do Postgres:", len(df))   # esperado: 96470

    df[ALVO] = df[ALVO].astype(int)
    # colunas numéricas: cast explícito para float (evita dtype 'object' em colunas
    # all-NULL como chuva_mm e duracao_min que vieram de 'NULL AS col' no SQL)
    for c in numericas:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in categoricas:
        df[c] = df[c].astype("category")

    # divisão por tempo: 80% mais antigos treinam, 20% mais recentes testam
    df = df.sort_values(TEMPO)
    corte = int(len(df) * 0.8)
    treino, teste = df.iloc[:corte], df.iloc[corte:]
    X_tr, y_tr = treino[features], treino[ALVO]
    X_te, y_te = teste[features], teste[ALVO]

    modelo = XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=(y_tr == 0).sum() / (y_tr == 1).sum(),
        enable_categorical=True, tree_method="hist",
        eval_metric="aucpr", random_state=42,
    )
    modelo.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)

    prob = modelo.predict_proba(X_te)[:, 1]
    metricas = {
        "versao": versao,
        "roc_auc": float(roc_auc_score(y_te, prob)),
        "pr_auc": float(average_precision_score(y_te, prob)),
        "baseline_pr_auc": float(y_te.mean()),
    }

    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    saida = settings.artifacts_dir / f"modelo_{versao}.joblib"
    joblib.dump({
        "versao": versao,
        "modelo": modelo,
        "features": features,
        "categoricas": categoricas,
        "categorias": {c: list(df[c].cat.categories) for c in categoricas},
        "metricas": metricas,
    }, saida)
    print("modelo salvo em:", saida)
    return metricas


if __name__ == "__main__":
    versao = sys.argv[1] if len(sys.argv) > 1 else "v2"
    print(treinar(versao))