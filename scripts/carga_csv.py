import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

BASE = Path(__file__).resolve().parents[1]
CSV = BASE / "data" / "olist_analytical_novo.csv"
URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres@localhost:5432/logistica")

df = pd.read_csv(CSV, sep=";", decimal=",", encoding="utf-8-sig")
print("linhas lidas:", len(df))   # esperado: 96470

# datas viram timestamp de verdade no banco
for c in ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
          "order_delivered_customer_date", "order_estimated_delivery_date"]:
    if c in df.columns:
        df[c] = pd.to_datetime(df[c], errors="coerce")

df["origem_dado"] = "real"

engine = create_engine(URL)
df.to_sql("entregas_historico", engine, if_exists="replace", index=False,
          chunksize=1000, method="multi")

with engine.begin() as conn:
    conn.execute(text("ALTER TABLE entregas_historico ADD PRIMARY KEY (order_id)"))
    conn.execute(text("CREATE INDEX idx_hist_data ON entregas_historico (order_purchase_timestamp)"))
    print(conn.execute(text(
        "SELECT COUNT(*), ROUND(AVG(is_late::int)::numeric, 3) FROM entregas_historico"
    )).fetchone())   # esperado: (96470, 0.081)