import os
import urllib.request
import pandas as pd

# Dataset: https://huggingface.co/datasets/samuelalex37/olist-delivery-risk-data
URL = ("https://huggingface.co/datasets/samuelalex37/olist-delivery-risk-data"
       "/resolve/main/olist_analytical.parquet")

# salva na mesma pasta deste arquivo (coloque o convert.py na raiz do projeto)
PASTA = os.path.dirname(os.path.abspath(__file__))
PARQUET = os.path.join(PASTA, "olist_analytical.parquet")
CSV = os.path.join(PASTA, "olist_analytical_novo.csv")

# 1. baixa o parquet (só se ainda não existir)
if not os.path.exists(PARQUET):
    print("baixando...")
    urllib.request.urlretrieve(URL, PARQUET)
print("tamanho do parquet (MB):", round(os.path.getsize(PARQUET) / 1e6, 1))  # esperado: ~21.6

# 2. lê e confere
df = pd.read_parquet(PARQUET)
print("linhas no parquet:", len(df))   # esperado: 96470
print("colunas:", len(df.columns))     # esperado: 53

# 3. grava um único CSV (padrão do Excel PT-BR: ; e vírgula decimal)
df.to_csv(CSV, index=False, sep=";", decimal=",", encoding="utf-8-sig")

# 4. confere o CSV gerado
chk = pd.read_csv(CSV, sep=";", decimal=",", encoding="utf-8-sig")
print("linhas no csv:", len(chk))
print("tamanho do csv (MB):", round(os.path.getsize(CSV) / 1e6, 1))
print("CSV salvo em:", CSV)