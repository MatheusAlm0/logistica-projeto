# Arquitetura do Backend

## Diagrama de camadas

```
┌─────────────────────────────────────────────────────┐
│                    HTTP / FastAPI                    │
│  auth  entregas  previsoes  galpoes  retreinos       │
│  checkpoints  rastreio                               │
└──────────────────────┬──────────────────────────────┘
                       │ Depends()
┌──────────────────────▼──────────────────────────────┐
│                   Controllers                        │
│  Validação de entrada (Pydantic) · auth JWT          │
│  Monta response models                               │
└──────────────────────┬──────────────────────────────┘
                       │ chamada direta
┌──────────────────────▼──────────────────────────────┐
│                    Services                          │
│  Regras de negócio · orquestra repo + ML             │
│  entrega_service  previsao_service  retreino_service │
└────────────┬──────────────────────┬─────────────────┘
             │                      │
┌────────────▼──────────┐  ┌────────▼────────────────┐
│      Repository        │  │       ML Module          │
│  entrega_repository   │  │  predictor · features    │
│  (SQLAlchemy selects) │  │  train · predictor cache │
└────────────┬──────────┘  └─────────────────────────┘
             │
┌────────────▼──────────────────────────────────────┐
│               Models (SQLAlchemy ORM)              │
│  Entrega  Previsao  Retreino  Usuario              │
│  Galpao   Checkpoint                               │
└────────────┬──────────────────────────────────────┘
             │
┌────────────▼──────────────────────────────────────┐
│              PostgreSQL                            │
└───────────────────────────────────────────────────┘

Integrações externas (chamadas HTTP, sem ORM):
  OSRM (roteamento) ──── app/integration/rota.py
  Open-Meteo (clima) ─── app/integration/clima.py
```

---

## Estrutura de pastas

```
logistica-ia/
├── app/
│   ├── controller/          # Routers FastAPI — entrada/saída HTTP
│   │   ├── auth_controller.py
│   │   ├── entrega_controller.py
│   │   ├── checkpoint_controller.py
│   │   ├── galpao_controller.py
│   │   ├── previsao_controller.py
│   │   ├── rastreio_controller.py
│   │   └── retreino_controller.py
│   ├── service/             # Regras de negócio
│   │   ├── entrega_service.py
│   │   ├── previsao_service.py
│   │   └── retreino_service.py
│   ├── repository/          # Acesso ao banco — apenas queries/mutations
│   │   └── entrega_repository.py
│   ├── model/               # Modelos SQLAlchemy (mapeamento ORM)
│   │   ├── entrega.py       # Entrega, Previsao, Retreino
│   │   ├── usuario.py
│   │   ├── galpao.py
│   │   └── checkpoint.py
│   ├── schema/              # Schemas Pydantic (request/response)
│   │   ├── entrega.py
│   │   ├── auth.py
│   │   ├── galpao.py
│   │   ├── checkpoint.py
│   │   ├── previsao.py
│   │   └── retreino.py
│   ├── core/
│   │   ├── auth.py          # JWT helpers + dependências FastAPI
│   │   ├── config.py        # Settings via pydantic-settings / .env
│   │   ├── database.py      # Engine, SessionLocal, Base, get_db
│   │   └── exceptions.py    # RegraDeNegocioError
│   ├── ml/
│   │   ├── predictor.py     # Singleton Predictor — carrega .joblib, expõe prever()
│   │   ├── features.py      # Engenharia de features (montar_features_v2)
│   │   ├── train.py         # Pipeline de treino XGBoost
│   │   └── artifacts/       # Modelos serializados (.joblib)
│   ├── integration/
│   │   ├── rota.py          # Consulta OSRM (fallback: haversine)
│   │   └── clima.py         # Consulta Open-Meteo
│   ├── job/
│   │   ├── retreino_job.py       # Job disparado após finalização de entrega
│   │   └── reavaliacao_job.py    # Job periódico (APScheduler, 30 min)
│   └── main.py              # App FastAPI — lifespan, routers, scheduler
├── scripts/
│   ├── carga_csv.py         # Carga inicial do dataset histórico no banco
│   ├── extract.py           # Extração/transformação de dados
│   └── simular_entregas.py  # Geração de dados sintéticos para testes
├── tests/
│   ├── conftest.py          # Fixtures compartilhadas (SQLite in-memory, mocks)
│   ├── test_endpoints_entregas.py
│   ├── test_endpoints_retreinos.py
│   ├── test_features.py
│   ├── test_validacao.py
│   ├── test_integracao_rota.py
│   └── test_integracao_clima.py
├── data/
│   └── olist_analytical_novo.csv   # Dataset histórico Olist
├── .env.example
├── requirements.txt
└── postman_collection.json
```

---

## Camadas em detalhe

### Controllers (`app/controller/`)
- Recebem e validam o payload via schemas Pydantic.
- Resolvem dependências de autenticação (`get_usuario_logado`, `requer_admin`, `requer_empresa`).
- Delegam lógica para o service e formatam a resposta.
- Não contêm queries SQL nem regras de negócio.

### Services (`app/service/`)
- Orquestram o fluxo: validam regras de domínio, chamam o repositório e o módulo ML.
- `entrega_service` — cria entrega com código de rastreio, aplica isolamento por `cliente_id`, delega finalização e listagem.
- `previsao_service` — normaliza dados, chama rota/clima se necessário, executa o predictor.
- `retreino_service` — consulta estatísticas do ciclo de aprendizado, lista histórico.

### Repository (`app/repository/`)
- Única camada que escreve SQL/ORM diretamente.
- Funções puras: recebem `Session` e retornam modelos ORM.
- Sem regras de negócio — só queries.

### Models (`app/model/`)
- Mapeamento SQLAlchemy 2.x com `Mapped` e `mapped_column`.
- `Entrega` — tabela central; relacionamentos com `Previsao`, `Checkpoint`.
- `Previsao` — snapshot de features + resultado do modelo a cada avaliação de risco.
- `Retreino` — log de cada ciclo de treinamento com métricas ROC-AUC e PR-AUC.
- `Usuario` — autenticação SaaS; campo `cliente_id` isola dados por empresa.
- `Galpao` — pontos de passagem registráveis.
- `Checkpoint` — registro de passagem de um pacote por um galpão.

---

## Módulo de ML (`app/ml/`)

### Features (`features.py`)
Monta um dicionário de features a partir dos dados brutos da entrega:

| Feature | Descrição |
|---|---|
| `distance_km` | Distância calculada pelo OSRM ou haversine |
| `estimated_delivery_days` | Dias entre pedido e prazo previsto |
| `freight_ratio` | frete / valor do pedido |
| `same_state` | Origem e destino no mesmo estado |
| `is_sao_paulo_seller` | Vendedor em SP (maior hub logístico) |
| `purchase_day_of_week` | Dia da semana do pedido |
| `purchase_hour` | Hora do pedido |
| `purchase_is_weekend` | Pedido feito no final de semana |
| `customer_state` | UF de destino (categórica) |
| `seller_state` | UF de origem (categórica) |
| `chuva_mm` | Precipitação prevista no destino (Open-Meteo) |

### Predictor (`predictor.py`)
- Singleton `predictor` carregado uma vez no startup via `predictor.carregar()`.
- Modelo serializado em `app/ml/artifacts/modelo_v2.joblib`.
- `predictor.prever(dados)` retorna `{probabilidade, nivel, modelo_versao, features_usadas}`.
- Níveis: `baixo` (< 0.40), `médio` (0.40–0.60), `alto` (≥ 0.60).
- Pode ser recarregado em produção sem reiniciar o servidor (`predictor.carregar(nova_versao)`).

### Treino (`train.py`)
- Pipeline XGBoost com `scale_pos_weight` para lidar com classes desbalanceadas (~8 % de atrasos).
- Treinado sobre `entregas_historico` (dados do Olist + entregas reais acumuladas).
- Salva o artefato em `artifacts/modelo_{versao}.joblib`.

---

## Jobs assíncronos (`app/job/`)

### `retreino_job.py` — disparado por evento
Chamado em `BackgroundTask` após cada `PATCH /entregas/{id}/finalizar`.
- Conta amostras reais novas desde o último retreino bem-sucedido.
- Retreina somente se `>= RETREINO_MIN_AMOSTRAS` (padrão: 100).
- Exporta entregas reais para `entregas_historico`, treina, substitui modelo em memória.

### `reavaliacao_job.py` — periódico (APScheduler)
Roda a cada 30 minutos via `BackgroundScheduler`.
- Entregas cujo prazo expirou → `status='atrasada'`, `data_prevista_revisada = agora + 3 dias úteis`.
- Demais → re-executa o modelo com nova consulta Open-Meteo (usando coordenadas da capital do estado destino); persiste nova `Previsao` apenas se o nível de risco mudou.

---

## Autenticação JWT (`app/core/auth.py`)

- **Hash de senha**: `bcrypt` diretamente (sem passlib).
- **Token**: JWT assinado com `SECRET_KEY` (algoritmo HS256), expiração configurável.
- **Dependências FastAPI**:
  - `get_usuario_logado` — decodifica token, carrega usuário do banco.
  - `requer_admin` — bloqueia se `role != admin`.
  - `requer_empresa` — bloqueia se `role` não for `empresa` nem `admin`.
- **Isolamento multi-tenant**: campo `cliente_id` em `Usuario` e `Entrega`; empresa vê somente as próprias entregas; admin vê tudo.

---

## Integrações externas

### OSRM (`app/integration/rota.py`)
- Consulta a API pública do OSRM para calcular distância e duração da rota entre origem e destino.
- Fallback automático para distância haversine se o OSRM não responder.
- Chamado apenas quando `distancia_km` não for fornecida e as coordenadas estiverem disponíveis.

### Open-Meteo (`app/integration/clima.py`)
- Consulta precipitação prevista (ou histórica) no destino para a data prevista de entrega.
- Usa endpoint `forecast` para datas futuras e `archive` para datas passadas.
- Retorna `None` silenciosamente se a API falhar (feature opcional no modelo).

---

## Decisões de projeto

| Decisão | Motivo |
|---|---|
| FastAPI + Pydantic v2 | Validação automática, docs OpenAPI geradas, tipagem forte |
| SQLAlchemy 2.x (ORM declarativo) | Queries type-safe, migrações simples com `create_all` |
| PostgreSQL | Suporte a `EXTRACT`, texto livre, índices; SQLite usado só nos testes |
| XGBoost | Tolerante a features ausentes (`NaN`), boa performance em dados tabulares desbalanceados |
| `BackgroundScheduler` (APScheduler) | Thread separada, sem bloquear o event loop do FastAPI |
| `StaticPool` nos testes | Garante que todas as sessões SQLite in-memory compartilhem a mesma conexão |
| Isolamento por `cliente_id` | Abordagem simples sem schemas separados; troca de tenant = filtro de query |
| bcrypt direto (sem passlib) | passlib 1.7.x é incompatível com bcrypt >= 4.x; uso direto elimina a dependência frágil |
