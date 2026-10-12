# Guia de Instalação e Execução

## Pré-requisitos

| Ferramenta | Versão mínima | Observação |
|---|---|---|
| Python | 3.12 | Testado com 3.12.x |
| PostgreSQL | 14 | Banco principal da aplicação |
| Git | qualquer | Para clonar o repositório |

> Os testes rodam com SQLite in-memory — **não precisam de PostgreSQL**.

---

## 1. Clonar e criar ambiente virtual

```bash
git clone <url-do-repositorio>
cd logistica-ia

python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

---

## 2. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## 3. Configurar variáveis de ambiente

Copie o arquivo de exemplo e edite conforme o seu ambiente:

```bash
cp .env.example .env
```

Abra `.env` e preencha:

```env
# Banco de dados PostgreSQL
DATABASE_URL=postgresql+psycopg2://postgres:SUA_SENHA@localhost:5432/logistica

# JWT — gere uma chave aleatória segura para produção
SECRET_KEY=troque-para-um-valor-longo-e-aleatorio
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ML
ARTIFACTS_DIR=app/ml/artifacts
RETREINO_MIN_AMOSTRAS=100
```

Para gerar uma `SECRET_KEY` segura:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 4. Criar o banco de dados

No PostgreSQL, crie o banco antes de subir a aplicação:

```sql
CREATE DATABASE logistica;
```

As tabelas são criadas automaticamente pelo SQLAlchemy no primeiro startup da aplicação (`Base.metadata.create_all`). Não há arquivos de migração — basta rodar a aplicação.

---

## 5. Carregar o dataset histórico

O modelo XGBoost é treinado sobre dados do Olist. Antes de treinar, popule a tabela `entregas_historico`:

```bash
python scripts/carga_csv.py
```

Saída esperada:

```
linhas lidas: 96470
(96470, Decimal('0.081'))   ← total de linhas e taxa de atraso (~8 %)
```

> O arquivo CSV já está em `data/olist_analytical_novo.csv`. Se precisar regenerá-lo a partir do dataset bruto do Olist, use `scripts/extract.py`.

---

## 6. Treinar o modelo

```bash
python -m app.ml.train v2
```

Isso gera o arquivo `app/ml/artifacts/modelo_v2.joblib`. Sem esse arquivo a aplicação não sobe.

Métricas esperadas após o treino:

```
ROC-AUC ≈ 0.83
PR-AUC  ≈ 0.31
```

---

## 7. Rodar a aplicação

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Ou pelo botão de play do PyCharm com a run configuration **Logistica IA** (`.idea/runConfigurations/Logistica_IA.xml`).

A API estará disponível em:

- **Docs interativas (Swagger):** http://localhost:8000/docs
- **Redoc:** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health

---

## 8. Criar o primeiro usuário admin

Os endpoints `/auth/registro` criam apenas usuários com `role=empresa`. Para criar um admin, insira diretamente no banco:

```python
# execute uma vez, no shell do Python com o .venv ativado
from app.core.auth import hash_senha
from app.core.database import SessionLocal
from app.model.usuario import Usuario
import uuid

db = SessionLocal()
admin = Usuario(
    email="admin@suaempresa.com",
    senha_hash=hash_senha("senha-segura"),
    role="admin",
    nome="Administrador",
    cliente_id=str(uuid.uuid4()),
)
db.add(admin)
db.commit()
db.close()
print("admin criado")
```

---

## 9. Rodar os testes

Os testes usam SQLite in-memory e mockam todas as dependências externas (OSRM, Open-Meteo, PostgreSQL, APScheduler). Não precisam de banco rodando.

```bash
pytest tests/ -v
```

Resultado esperado: **115 passed**.

Para rodar um arquivo específico:

```bash
pytest tests/test_endpoints_entregas.py -v
```

Para rodar com cobertura:

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

---

## 10. Testar os endpoints com o Postman

Importe o arquivo `postman_collection.json` no Postman:

1. Abra o Postman → **Import** → selecione `postman_collection.json`.
2. Execute **Login** (`POST /auth/login`) com as credenciais criadas.
3. Copie o `access_token` da resposta.
4. Substitua `SEU_TOKEN_AQUI` nos requests protegidos (Postman → Find and Replace: `SEU_TOKEN_AQUI`).

---

## Resumo dos comandos

```bash
# 1. ambiente
python -m venv .venv && source .venv/bin/activate  # ou Scripts\Activate.ps1 no Windows
pip install -r requirements.txt

# 2. configuração
cp .env.example .env   # edite DATABASE_URL e SECRET_KEY

# 3. banco
psql -U postgres -c "CREATE DATABASE logistica;"

# 4. dataset + modelo
python scripts/carga_csv.py
python -m app.ml.train v2

# 5. servidor
uvicorn app.main:app --reload

# 6. testes
pytest tests/ -v
```
