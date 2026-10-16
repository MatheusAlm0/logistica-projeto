# Guia de Instalação e Execução

## Pré-requisitos

| Ferramenta | Versão | Observação |
|---|---|---|
| Python | 3.12 ou 3.13 | **Não use 3.14**: o `pydantic==2.10.3` fixado não tem pacote pronto para ela e a instalação falha |
| PostgreSQL | 17 (mínimo 14) | Banco principal da aplicação. O dump em `data/` foi gerado pelo `pg_dump` 17 |
| Node.js | 20 ou superior | Para o front-end (`guia-frontend/`) |
| Git | qualquer | Para clonar o repositório |

> Os testes rodam com SQLite in-memory — **não precisam de PostgreSQL**.

No Windows, o Python 3.12 e o PostgreSQL podem ser instalados pelo winget:

```powershell
winget install -e --id Python.Python.3.12
winget install PostgreSQL.PostgreSQL
```

---

## 1. Clonar e escolher a branch

O front-end e as funcionalidades mais recentes ficam nas branches `release/*`. A `main` ainda não tem o front-end.

```bash
git clone https://github.com/MatheusAlm0/logistica-projeto.git
cd logistica-projeto
git switch release/1.0.0.2
```

---

## 2. Back-end: ambiente virtual e dependências

```bash
# Windows (PowerShell) — use o Python 3.12 explicitamente se houver outras versões instaladas
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest e afins, necessário para rodar os testes
```

---

## 3. Configurar variáveis de ambiente

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Abra `.env` e preencha:

```env
# Banco de dados PostgreSQL
DATABASE_URL=postgresql+psycopg2://postgres:SUA_SENHA@localhost:5432/logistica

# JWT
SECRET_KEY=<cole aqui a chave gerada abaixo>
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ML
ARTIFACTS_DIR=app/ml/artifacts
RETREINO_MIN_AMOSTRAS=100
```

A `SECRET_KEY` é **obrigatória**. A aplicação não sobe se ela tiver menos de 32 caracteres ou for igual ao valor de exemplo do `.env.example`. Gere uma chave própria:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> Nunca commite o `.env`. Ele já está no `.gitignore`.

---

## 4. Banco de dados

### Opção A — restaurar o dump (recomendado)

O dump em `data/dump_logistica.sql` traz todas as tabelas e os dados no mesmo ponto em que o projeto está, incluindo a base histórica usada pelo modelo. No Windows:

```powershell
.\scripts\restore_banco.ps1          # cria o banco 'logistica' se ele não existir e restaura
.\scripts\restore_banco.ps1 -Force   # apaga o banco e restaura do zero (use após um dump novo)
```

O script lê usuário, senha e host da `DATABASE_URL` do `.env` e procura o `psql` em `C:\Program Files\PostgreSQL`.

O dump inclui um usuário de exemplo: **`empresa@exemplo.com` / `senha123`** (perfil empresa). Use-o só em ambiente local.

### Opção B — montar do zero

```sql
CREATE DATABASE logistica;
```

As tabelas são criadas automaticamente pelo SQLAlchemy no primeiro startup (`Base.metadata.create_all`). Não há migrações: `create_all` não altera tabelas que já existem, então ao receber colunas novas o caminho mais simples é restaurar o dump com `-Force`.

Depois, popule a base histórica e treine o modelo:

```bash
python scripts/carga_csv.py      # carrega ~96 mil pedidos do Olist em entregas_historico
python -m app.ml.train v2        # gera app/ml/artifacts/modelo_v2.joblib
```

O arquivo `modelo_v2.joblib` já vem no repositório. Sem ele a aplicação não sobe. O modelo atual tem ROC-AUC ≈ 0,55 e PR-AUC ≈ 0,15; melhorar essas métricas está no cronograma da Sprint 4.

---

## 5. Rodar o back-end

```bash
python -m uvicorn app.main:app --reload
```

Ou pelo botão de play do PyCharm com a run configuration **Logistica IA**.

- **Docs interativas (Swagger):** http://127.0.0.1:8000/docs
- **Redoc:** http://127.0.0.1:8000/redoc
- **Health check:** http://127.0.0.1:8000/health

> O uvicorn escuta em `127.0.0.1`. Se `localhost:8000` não abrir no navegador, use `127.0.0.1:8000`.

---

## 6. Rodar o front-end

Em outro terminal:

```bash
cd guia-frontend
npm install
npm run dev
```

O front abre em http://localhost:5173 e chama a API em `http://localhost:8000`. O back-end precisa estar rodando.

---

## 7. Criar o primeiro usuário admin

O `/auth/registro` cria apenas usuários com `role=empresa`, que ficam pendentes até um admin aprovar. Para criar um admin, insira direto no banco:

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

## 8. Rodar os testes

Os testes usam SQLite in-memory e mockam todas as dependências externas (OSRM, Open-Meteo, PostgreSQL, APScheduler). Não precisam de banco rodando, mas precisam do `requirements-dev.txt` instalado.

```bash
python -m pytest tests/ -q
```

Todos os testes devem passar. Para rodar um arquivo específico ou ver a cobertura:

```bash
python -m pytest tests/test_endpoints_entregas.py -v
python -m pytest tests/ --cov=app --cov-report=term-missing
```

---

## 9. Testar os endpoints com o Postman

Importe o arquivo `postman_collection.json` no Postman:

1. Abra o Postman → **Import** → selecione `postman_collection.json`.
2. Execute **Login** (`POST /auth/login`) com as credenciais criadas.
3. Copie o `access_token` da resposta.
4. Substitua `SEU_TOKEN_AQUI` nos requests protegidos (Postman → Find and Replace: `SEU_TOKEN_AQUI`).

---

## Resumo dos comandos (Windows)

```powershell
# 1. código
git clone https://github.com/MatheusAlm0/logistica-projeto.git
cd logistica-projeto
git switch release/1.0.0.2

# 2. back-end
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env      # edite DATABASE_URL e gere a SECRET_KEY

# 3. banco
.\scripts\restore_banco.ps1

# 4. servidores (um terminal para cada)
python -m uvicorn app.main:app --reload
cd guia-frontend; npm install; npm run dev

# 5. testes
python -m pytest tests/ -q
```
