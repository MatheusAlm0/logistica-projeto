# Previsor de Atrasos Logísticos

Sistema acadêmico de **previsão de risco de atraso em entregas** combinando FastAPI, PostgreSQL, XGBoost e retreino automático contínuo. O modelo aprende com cada entrega finalizada e se atualiza em produção sem reiniciar o servidor.

---

## Sumário

- [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
- [Tecnologias](#tecnologias)
- [Banco de Dados](#banco-de-dados)
- [Endpoints da API](#endpoints-da-api)
- [Fluxo Completo de uma Entrega](#fluxo-completo-de-uma-entrega)
- [Modelo de Machine Learning](#modelo-de-machine-learning)
- [Integrações Externas](#integrações-externas)
- [Retreino Automático](#retreino-automático)
- [Como Rodar Localmente](#como-rodar-localmente)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Testes](#testes)

---

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        Cliente (HTTP)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST JSON
┌──────────────────────────▼──────────────────────────────────────┐
│                        FastAPI (app/)                           │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  /previsoes │  │  /entregas   │  │      /retreinos        │ │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬─────────────┘ │
│         │                │                     │               │
│  ┌──────▼────────────────▼─────────────────────▼─────────────┐ │
│  │                   Service Layer                            │ │
│  │  previsao_service  │  entrega_service  │  retreino_service │ │
│  └──────┬─────────────────────┬───────────────────────────────┘ │
│         │                     │                                 │
│  ┌──────▼──────┐    ┌─────────▼────────┐                       │
│  │  ML Module  │    │   Repository     │                       │
│  │             │    │                  │                       │
│  │  Predictor  │    │  entrega_repo    │                       │
│  │  XGBoost    │    │  (SQLAlchemy)    │                       │
│  │  features   │    └─────────┬────────┘                       │
│  └──────┬──────┘              │                                │
│         │              ┌──────▼──────────┐                     │
│  ┌──────▼──────┐        │   PostgreSQL    │                     │
│  │  .joblib    │        │                 │                     │
│  │  artefato   │        │  entregas       │                     │
│  └─────────────┘        │  previsoes      │                     │
│                         │  retreinos      │                     │
│  ┌──────────────────┐   │  entregas_      │                     │
│  │  Integrações     │   │  historico      │                     │
│  │                  │   └─────────────────┘                     │
│  │  OSRM (rota)     │                                           │
│  │  Open-Meteo      │                                           │
│  │  (chuva)         │                                           │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo Resumido

1. **Cadastro** — o cliente envia os dados da entrega (peso, valor, estados, coordenadas)
2. **Enriquecimento** — o sistema busca distância + duração via OSRM e chuva prevista via Open-Meteo
3. **Previsão** — o XGBoost calcula a probabilidade de atraso (nível `baixo / medio / alto`)
4. **Persistência** — entrega e previsão são salvas no PostgreSQL
5. **Finalização** — ao marcar como entregue, um job em background verifica se há dados suficientes para retreino
6. **Retreino** — quando o limiar é atingido, o modelo é retreinado com os dados reais e trocado em memória sem downtime

---

## Tecnologias

| Camada | Tecnologia | Versão |
|---|---|---|
| API | FastAPI | 0.115.5 |
| Servidor ASGI | Uvicorn | 0.32.1 |
| ORM | SQLAlchemy | 2.0.36 |
| Banco de dados | PostgreSQL | ≥ 14 |
| Validação | Pydantic v2 | 2.10.3 |
| ML | XGBoost | ≥ 2.1.3 |
| ML (pipeline) | scikit-learn | ≥ 1.5.2 |
| Manipulação de dados | pandas | ≥ 2.2.3 |
| HTTP client | httpx | 0.28.0 |
| Serialização de modelo | joblib | ≥ 1.4.2 |
| Roteamento | OSRM (público) | — |
| Meteorologia | Open-Meteo | — |

---

## Banco de Dados

### Tabelas de Operação (gerenciadas pelo SQLAlchemy)

#### `entregas`

Registra cada entrega cadastrada pelo sistema.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | Identificador autoincremental |
| `criado_em` | TIMESTAMPTZ | Data/hora de criação (automática) |
| `data_pedido` | TIMESTAMP | Momento do pedido |
| `data_prevista` | TIMESTAMP | Prazo de entrega prometido |
| `data_entregue` | TIMESTAMP | Data real de entrega (preenchida ao finalizar) |
| `peso_g` | FLOAT | Peso total em gramas |
| `valor` | FLOAT | Valor do pedido em R$ |
| `frete` | FLOAT | Valor do frete em R$ |
| `estado_origem` | VARCHAR(2) | UF de origem do vendedor |
| `estado_destino` | VARCHAR(2) | UF de destino do comprador |
| `distancia_km` | FLOAT | Distância calculada pela rota (km) |
| `status` | VARCHAR(20) | `pendente` \| `entregue` \| `cancelado` |

#### `previsoes`

Snapshot imutável de cada execução do modelo para uma entrega.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `entrega_id` | INTEGER FK | Referência à entrega |
| `criado_em` | TIMESTAMPTZ | Momento da previsão |
| `probabilidade` | FLOAT | Score do modelo (0–1) |
| `nivel` | VARCHAR(10) | `baixo` \| `medio` \| `alto` |
| `modelo_versao` | VARCHAR(20) | Versão do modelo usado (ex: `v2`) |
| `features_json` | JSON | Snapshot completo das features enviadas ao modelo |
| `chuva_mm` | FLOAT | Precipitação prevista no destino (mm) |
| `rota_fonte` | VARCHAR(20) | `osrm` ou `haversine` |

#### `retreinos`

Histórico de cada execução de retreino automático ou manual.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `iniciado_em` | TIMESTAMPTZ | Início do retreino |
| `concluido_em` | TIMESTAMPTZ | Fim do retreino |
| `versao` | VARCHAR(20) | Versão do modelo produzido |
| `n_amostras` | INTEGER | Quantidade de amostras novas exportadas |
| `roc_auc` | FLOAT | ROC-AUC no conjunto de teste |
| `pr_auc` | FLOAT | PR-AUC no conjunto de teste |
| `status` | VARCHAR(20) | `rodando` \| `ok` \| `erro` |
| `erro` | TEXT | Mensagem de erro, se houver |

### Tabela de Treinamento

#### `entregas_historico`

Tabela flat usada exclusivamente pelo pipeline de ML. Contém os dados do dataset Olist (96.470 linhas), os 5.000 registros sintéticos gerados pelo script e as entregas reais exportadas automaticamente pelo job de retreino.

Colunas relevantes para o modelo:

| Coluna | Origem |
|---|---|
| `order_purchase_timestamp` | Timestamp do pedido (usado para split temporal) |
| `distance_km` | Distância da rota em km |
| `duracao_min` | Duração da rota em minutos (OSRM) |
| `total_weight_g` | Peso total em gramas |
| `total_price` | Valor do pedido |
| `total_freight` | Valor do frete |
| `freight_ratio` | `frete / valor` |
| `estimated_delivery_days` | Dias entre pedido e prazo |
| `same_state` | 1 se origem == destino |
| `is_sao_paulo_seller` | 1 se vendedor é de SP |
| `purchase_day_of_week` | Dia da semana do pedido (0=seg) |
| `purchase_hour` | Hora do pedido |
| `purchase_is_weekend` | 1 se fim de semana |
| `chuva_mm` | Precipitação no destino no dia previsto (mm) |
| `customer_state` | UF do comprador (categórica) |
| `seller_state` | UF do vendedor (categórica) |
| `is_late` | **Alvo**: 1 se atrasou, 0 se não |
| `origem_dado` | `olist` \| `sintetico` \| `real` |

---

## Endpoints da API

A documentação interativa completa está disponível em `http://localhost:8000/docs` (Swagger UI) e `http://localhost:8000/redoc`.

---

### `GET /health`

Verifica se a API está no ar e qual versão do modelo está carregada.

**Response `200`:**
```json
{
  "status": "ok",
  "modelo": "v2"
}
```

---

### `POST /previsoes`

Calcula o risco de atraso para uma entrega **sem persistir** nada no banco. Útil para simulações e testes rápidos.

**Request body:**
```json
{
  "data_pedido":  "2024-03-10T09:00:00",
  "data_prevista": "2024-03-20T18:00:00",
  "peso_g": 1500,
  "valor": 250.00,
  "frete": 35.00,
  "estado_origem": "SP",
  "estado_destino": "AM",
  "origem_lat": -23.5505,
  "origem_lng": -46.6333,
  "destino_lat": -3.1019,
  "destino_lng": -60.0250
}
```

> **Campos opcionais:** `estado_origem`, `estado_destino`, `distancia_km`, `origem_lat`, `origem_lng`, `destino_lat`, `destino_lng`. Se as coordenadas forem informadas, a rota é calculada automaticamente via OSRM.

**Response `200`:**
```json
{
  "probabilidade": 0.7423,
  "nivel": "alto",
  "modelo_versao": "v2",
  "features_usadas": {
    "distance_km": 2712.4,
    "duracao_min": 1843.2,
    "total_weight_g": 1500,
    "total_price": 250.0,
    "total_freight": 35.0,
    "freight_ratio": 0.14,
    "estimated_delivery_days": 10.375,
    "same_state": 0,
    "is_sao_paulo_seller": 1,
    "purchase_day_of_week": 6,
    "purchase_hour": 9,
    "purchase_is_weekend": 1,
    "chuva_mm": 18.3,
    "customer_state": "AM",
    "seller_state": "SP"
  },
  "contexto": {
    "rota": {
      "distancia_km": 2712.4,
      "duracao_min": 1843.2,
      "fonte": "osrm"
    },
    "chuva_mm": 18.3
  }
}
```

**Níveis de risco:**

| Nível | Probabilidade |
|---|---|
| `baixo` | < 0.40 |
| `medio` | 0.40 – 0.60 |
| `alto` | ≥ 0.60 |

**Erros:**

| Código | Situação |
|---|---|
| `422` | Campo inválido (ex: `peso_g ≤ 0`, `data_prevista ≤ data_pedido`, UF inexistente) |
| `503` | Modelo não encontrado (arquivo `.joblib` ausente) |

---

### `POST /entregas`

Cadastra uma entrega, executa a previsão de risco e persiste tudo. A resposta inclui o resultado completo da previsão.

**Request body:** mesmo schema de `POST /previsoes`.

**Response `201`:**
```json
{
  "id": 42,
  "criado_em": "2024-03-10T09:01:15.234Z",
  "data_pedido":  "2024-03-10T09:00:00",
  "data_prevista": "2024-03-20T18:00:00",
  "data_entregue": null,
  "peso_g": 1500,
  "valor": 250.00,
  "frete": 35.00,
  "estado_origem": "SP",
  "estado_destino": "AM",
  "distancia_km": 2712.4,
  "status": "pendente",
  "ultima_previsao": {
    "id": 87,
    "probabilidade": 0.7423,
    "nivel": "alto",
    "modelo_versao": "v2",
    "chuva_mm": 18.3,
    "rota_fonte": "osrm",
    "criado_em": "2024-03-10T09:01:16.001Z"
  },
  "previsao": {
    "probabilidade": 0.7423,
    "nivel": "alto",
    "modelo_versao": "v2",
    "features_usadas": { "...": "..." },
    "contexto": { "...": "..." }
  }
}
```

---

### `GET /entregas`

Lista entregas com paginação e filtros opcionais.

**Query params:**

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `status` | string | — | `pendente` \| `entregue` \| `cancelado` |
| `estado_destino` | string | — | UF de destino (ex: `SP`) |
| `limit` | int | 50 | Máximo de itens (1–200) |
| `offset` | int | 0 | Deslocamento para paginação |

**Response `200`:**
```json
{
  "total": 312,
  "items": [
    {
      "id": 42,
      "status": "pendente",
      "estado_destino": "AM",
      "distancia_km": 2712.4,
      "ultima_previsao": { "nivel": "alto", "probabilidade": 0.7423, "..." : "..." }
    }
  ]
}
```

---

### `GET /entregas/{id}`

Detalha uma entrega e sua última previsão.

**Response `200`:** mesmo schema de `POST /entregas`, sem o campo `previsao`.

**Response `422`:** entrega não encontrada.

---

### `PATCH /entregas/{id}/finalizar`

Marca a entrega como entregue e agenda o job de retreino automático em background (não bloqueia a resposta).

**Request body:**
```json
{
  "data_entregue": "2024-03-22T14:30:00"
}
```

**Response `200`:** entrega atualizada com `status: "entregue"` e `data_entregue` preenchida.

**Erros:**

| Código | Situação |
|---|---|
| `422` | Entrega não encontrada, já finalizada, ou `data_entregue < data_pedido` |

---

### `GET /retreinos/status`

Visão geral do ciclo de aprendizado: modelo ativo, métricas, progresso até o próximo retreino.

**Response `200`:**
```json
{
  "modelo_ativo": "v2",
  "metricas_ativas": {
    "versao": "v2",
    "roc_auc": 0.5643,
    "pr_auc": 0.1489,
    "baseline_pr_auc": 0.1194
  },
  "ultimo_retreino": {
    "id": 3,
    "iniciado_em": "2024-03-10T10:00:00Z",
    "concluido_em": "2024-03-10T10:01:42Z",
    "versao": "v2",
    "n_amostras": 127,
    "roc_auc": 0.5643,
    "pr_auc": 0.1489,
    "status": "ok",
    "erro": null,
    "duracao_segundos": 102.1
  },
  "entregas_desde_ultimo_retreino": 47,
  "min_para_retreinar": 100,
  "pronto_para_retreinar": false
}
```

---

### `GET /retreinos`

Lista o histórico de retreinos com métricas de cada execução.

**Query params:** `status` (`rodando` | `ok` | `erro`), `limit` (padrão 20), `offset`.

**Response `200`:**
```json
{
  "total": 5,
  "pendentes": 0,
  "items": [
    {
      "id": 3,
      "status": "ok",
      "roc_auc": 0.5643,
      "pr_auc": 0.1489,
      "n_amostras": 127,
      "duracao_segundos": 102.1
    }
  ]
}
```

---

### `GET /retreinos/{id}`

Detalha um retreino específico pelo ID.

---

### `POST /retreinos/disparar`

Dispara um retreino manual em background, **independente do limiar** de amostras configurado.

**Response `202`:**
```json
{
  "mensagem": "retreino agendado em background",
  "acompanhe": "/retreinos/status"
}
```

---

## Fluxo Completo de uma Entrega

```
Cliente                 FastAPI              OSRM         Open-Meteo     PostgreSQL    XGBoost
  │                        │                  │               │              │             │
  │── POST /entregas ──────►│                  │               │              │             │
  │                        │                  │               │              │             │
  │                        │── GET /route ────►│               │              │             │
  │                        │◄── distancia_km ──│               │              │             │
  │                        │   duracao_min     │               │              │             │
  │                        │                  │               │              │             │
  │                        │── GET /archive ───────────────────►              │             │
  │                        │◄── chuva_mm (mm) ──────────────────              │             │
  │                        │                  │               │              │             │
  │                        │── predict(features) ──────────────────────────────────────────►│
  │                        │◄── probabilidade, nivel ──────────────────────────────────────│
  │                        │                  │               │              │             │
  │                        │── INSERT entregas ──────────────────────────────►│             │
  │                        │── INSERT previsoes ─────────────────────────────►│             │
  │                        │                  │               │              │             │
  │◄── 201 Created ─────────│                  │               │              │             │
  │                        │                  │               │              │             │
  │── PATCH /finalizar ────►│                  │               │              │             │
  │                        │── UPDATE entregas ──────────────────────────────►│             │
  │◄── 200 OK ──────────────│                  │               │              │             │
  │                        │                  │               │              │             │
  │                        │── [Background Task] verificar_e_retreinar        │             │
  │                        │       │           │               │              │             │
  │                        │       │── COUNT entregas finalizadas ────────────►│             │
  │                        │       │   (se < 100: encerra)                    │             │
  │                        │       │                                          │             │
  │                        │       │── INSERT retreinos (status=rodando) ─────►│             │
  │                        │       │── SELECT entregas → INSERT historico ────►│             │
  │                        │       │── treinar("v2") ──────────────────────────────────────►│
  │                        │       │◄── modelo_v2.joblib ──────────────────────────────────│
  │                        │       │── UPDATE retreinos (status=ok) ──────────►│             │
  │                        │       │── predictor.carregar("v2")               │             │
  │                        │       │   (hot-swap em memória)                  │             │
```

### Estados de uma Entrega

```
[criada] → pendente → entregue
                   → cancelado
```

---

## Modelo de Machine Learning

### Dataset de Treinamento

O modelo é treinado sobre três fontes de dados combinadas na tabela `entregas_historico`:

| Fonte | Linhas | Taxa de Atraso | Novas Features |
|---|---|---|---|
| Olist (HuggingFace) | 96.470 | 8,1% | — |
| Sintético (OSRM + Open-Meteo) | 5.000 | ~29% | `chuva_mm`, `duracao_min` |
| Real (entregas do sistema) | dinâmico | variável | `chuva_mm`, `duracao_min` |

**Total atual:** 101.480 linhas.

### Features do Modelo v2

O modelo usa exclusivamente informações **disponíveis no momento do cadastro** (sem vazamento de dados):

| Feature | Tipo | Origem | Descrição |
|---|---|---|---|
| `distance_km` | numérica | OSRM / informado | Distância da rota (km) |
| `duracao_min` | numérica | OSRM | Tempo de rota estimado (min) |
| `total_weight_g` | numérica | cadastro | Peso total do pedido (g) |
| `total_price` | numérica | cadastro | Valor do pedido (R$) |
| `total_freight` | numérica | cadastro | Valor do frete (R$) |
| `freight_ratio` | numérica | calculada | `frete / valor` |
| `estimated_delivery_days` | numérica | calculada | Dias entre pedido e prazo |
| `same_state` | binária | calculada | 1 se origem == destino |
| `is_sao_paulo_seller` | binária | calculada | 1 se vendedor em SP |
| `purchase_day_of_week` | numérica | calculada | Dia da semana (0=seg) |
| `purchase_hour` | numérica | calculada | Hora do pedido |
| `purchase_is_weekend` | binária | calculada | 1 se sáb/dom |
| `chuva_mm` | numérica | Open-Meteo | Precipitação no destino (mm) |
| `customer_state` | categórica | cadastro | UF do comprador |
| `seller_state` | categórica | cadastro | UF do vendedor |

**Features proibidas** (vazamento): `actual_delivery_days`, `order_delivered_customer_date`, `is_late`, `order_status`, etc.

### Algoritmo: XGBoost

```python
XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=(negativos / positivos),  # corrige desbalanceamento ~91% / 9%
    enable_categorical=True,                   # suporte nativo a categóricas
    tree_method="hist",
    eval_metric="aucpr",
    random_state=42,
)
```

### Divisão Temporal (sem vazamento)

```
┌────────────────────────────────────────────────────────────────────┐
│                entregas_historico ordenadas por data               │
├─────────────────────────────────────┬──────────────────────────────┤
│         80% mais antigos (treino)   │   20% mais recentes (teste)  │
│         Olist 2016-2018             │   Olist + Sintéticos 2023-24 │
└─────────────────────────────────────┴──────────────────────────────┘
```

A divisão por tempo — e não por shuffle aleatório — evita que o modelo "veja o futuro" durante o treinamento, simulando o comportamento real em produção.

### Tratamento de Valores Ausentes

O XGBoost lida com `NaN` nativamente. Dados do Olist não têm `chuva_mm` nem `duracao_min`; esses campos chegam como `NULL` no SQL e `NaN` no DataFrame. O modelo aprende a usar essas features quando disponíveis e a ignorá-las quando ausentes.

### Métricas (modelo atual)

| Métrica | Valor | Interpretação |
|---|---|---|
| **ROC-AUC** | 0.5643 | Discriminação entre atrasados e pontuais |
| **PR-AUC** | 0.1489 | Precisão/recall para a classe positiva (atrasado) |
| **Baseline PR-AUC** | 0.1194 | Taxa de atraso no conjunto de teste (naive) |

> O PR-AUC 25% acima do baseline confirma que o modelo adiciona valor preditivo real, especialmente para a classe minoritária.

### Artefato Salvo

O modelo treinado é salvo em `app/ml/artifacts/modelo_v2.joblib` com o seguinte conteúdo:

```python
{
    "versao": "v2",
    "modelo": XGBClassifier,          # modelo treinado
    "features": [...],                 # lista ordenada de features
    "categoricas": [...],              # nomes das features categóricas
    "categorias": {"customer_state": [...], "seller_state": [...]},  # categorias do treino
    "metricas": {"roc_auc": ..., "pr_auc": ..., "baseline_pr_auc": ...},
}
```

---

## Integrações Externas

### OSRM (Open Source Routing Machine)

Calcula a **rota real de caminhão** entre dois pontos.

- **URL:** `https://router.project-osrm.org/route/v1/driving/{lng},{lat};{lng},{lat}?overview=false`
- **Retorna:** `distancia_km` e `duracao_min`
- **Fallback:** se o OSRM falhar, usa a distância em linha reta (fórmula de Haversine); `duracao_min` fica `null`
- **Formato das coordenadas:** OSRM exige `longitude,latitude` (ao contrário do padrão lat/lng)

### Open-Meteo

Obtém a **precipitação prevista** (ou histórica) no destino da entrega.

- **Previsão (futuro):** `https://api.open-meteo.com/v1/forecast`
- **Histórico (passado):** `https://archive-api.open-meteo.com/v1/archive`
- **Parâmetro:** `precipitation_sum` diário (mm)
- **Fallback:** retorna `null` se a API falhar; o modelo trata como `NaN`

---

## Retreino Automático

O sistema implementa um ciclo de **aprendizado contínuo** sem intervenção manual:

```
PATCH /finalizar  ──►  BackgroundTask: verificar_e_retreinar()
                                │
                         COUNT novas entregas
                         desde último retreino ok
                                │
                    ┌── < min_amostras ──►  encerra (sem retreino)
                    │
                    └── >= min_amostras
                                │
                         INSERT retreinos (rodando)
                                │
                         SELECT entregas WHERE status='entregue'
                         INSERT INTO entregas_historico (origem_dado='real')
                                │
                         treinar("v2")
                         → gera modelo_v2.joblib
                                │
                         UPDATE retreinos (ok, roc_auc, pr_auc)
                                │
                         predictor.carregar("v2")
                         ← hot-swap em memória, zero downtime
```

**Configuração** (via `.env`):

```env
RETREINO_MIN_AMOSTRAS=100  # mínimo de novas entregas finalizadas para retreinar
```

**Retreino manual** via `POST /retreinos/disparar` ignora o limiar.

---

## Como Rodar Localmente

### Pré-requisitos

- Python 3.11+
- PostgreSQL 14+
- Git

### 1. Clone e ambiente virtual

```bash
git clone <url-do-repositório>
cd logistica-ia
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Banco de dados

```sql
-- No psql ou pgAdmin:
CREATE DATABASE logistica;
```

### 3. Variáveis de ambiente

```bash
cp .env.example .env
# Edite .env com as credenciais do seu PostgreSQL:
# DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/logistica
```

### 4. Carga dos dados históricos (Olist)

O arquivo `olist_analytical_novo.csv` deve estar em `scripts/`.

```bash
python scripts/carga_csv.py
# Esperado: "96470 linhas inseridas em entregas_historico"
```

### 5. Treinar o modelo

```bash
python -m app.ml.train v2
# Saída: modelo salvo em app/ml/artifacts/modelo_v2.joblib
# Métricas: ROC-AUC ~0.60, PR-AUC ~0.08
```

### 6. (Opcional) Gerar dados sintéticos e retreinar

Gera 5.000 entregas sintéticas com dados reais de rotas e clima:

```bash
python scripts/gerar_dados_sinteticos.py --n 5000 --seed 42
# Duração: ~5 minutos (OSRM + Open-Meteo)
# Ao final: modelo retreinado com 101.480 linhas
# Métricas: ROC-AUC ~0.56, PR-AUC ~0.15
```

### 7. Subir a API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Testar

```bash
# Health check
curl http://localhost:8000/health

# Previsão rápida
curl -X POST http://localhost:8000/previsoes \
  -H "Content-Type: application/json" \
  -d '{
    "data_pedido": "2024-03-10T09:00:00",
    "data_prevista": "2024-03-20T18:00:00",
    "peso_g": 1500,
    "valor": 250.00,
    "frete": 35.00,
    "estado_origem": "SP",
    "estado_destino": "AM",
    "origem_lat": -23.5505,
    "origem_lng": -46.6333,
    "destino_lat": -3.1019,
    "destino_lng": -60.0250
  }'

# Swagger UI
open http://localhost:8000/docs
```

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://postgres@localhost:5432/logistica` | URL do PostgreSQL |
| `ARTIFACTS_DIR` | `app/ml/artifacts` | Diretório dos artefatos do modelo |
| `RETREINO_MIN_AMOSTRAS` | `100` | Mínimo de novas entregas para retreinar |

---

## Estrutura de Pastas

```
logistica-ia/
│
├── app/                          # Pacote principal da aplicação
│   ├── main.py                   # Ponto de entrada FastAPI: lifespan, routers, handlers
│   │
│   ├── controller/               # Camada HTTP: recebe requests, devolve responses
│   │   ├── entrega_controller.py # POST /entregas, GET /entregas, PATCH /finalizar
│   │   ├── previsao_controller.py# POST /previsoes (sem persistência)
│   │   └── retreino_controller.py# GET /retreinos/*, POST /retreinos/disparar
│   │
│   ├── service/                  # Lógica de negócio (sem dependência HTTP)
│   │   ├── entrega_service.py    # Criar, finalizar, listar, detalhar entregas
│   │   ├── previsao_service.py   # Orquestra OSRM + Open-Meteo + predictor
│   │   └── retreino_service.py   # Status, histórico e métricas de retreinos
│   │
│   ├── repository/               # Acesso ao banco (SQLAlchemy queries)
│   │   └── entrega_repository.py # CRUD de entregas, previsoes e retreinos
│   │
│   ├── model/                    # Modelos SQLAlchemy (mapeamento ORM)
│   │   └── entrega.py            # Entrega, Previsao, Retreino
│   │
│   ├── schema/                   # Schemas Pydantic (validação e serialização)
│   │   ├── entrega.py            # EntregaCreate, EntregaResponse, FinalizarRequest
│   │   ├── previsao.py           # PrevisaoRequest, PrevisaoResponse
│   │   └── retreino.py           # RetreinoResponse, RetreinoStatusResponse
│   │
│   ├── ml/                       # Pipeline de Machine Learning
│   │   ├── features.py           # Definição das features v1/v2; montar_features_v2()
│   │   ├── predictor.py          # Predictor: carrega .joblib, prever(), hot-swap
│   │   ├── train.py              # treinar(): lê historico, treina XGBoost, salva artefato
│   │   └── artifacts/            # Modelos serializados (modelo_v2.joblib)
│   │
│   ├── integration/              # Clientes de APIs externas
│   │   ├── rota.py               # obter_rota(): OSRM + fallback Haversine
│   │   └── clima.py              # obter_chuva_mm(): Open-Meteo Forecast/Archive
│   │
│   ├── job/                      # Jobs assíncronos (BackgroundTasks)
│   │   └── retreino_job.py       # verificar_e_retreinar(): exporta + treina + hot-swap
│   │
│   └── core/                     # Infraestrutura transversal
│       ├── config.py             # Settings (pydantic-settings, lê .env)
│       ├── database.py           # engine, SessionLocal, get_db, Base
│       └── exceptions.py         # RegraDeNegocioError
│
├── scripts/                      # Utilitários de linha de comando
│   ├── carga_csv.py              # Carrega olist_analytical_novo.csv → entregas_historico
│   ├── extract.py                # Extrai e transforma o dataset Olist bruto
│   └── gerar_dados_sinteticos.py # Gera 5k registros sintéticos (OSRM + Open-Meteo)
│
├── tests/                        # Suite de testes (pytest)
│   ├── conftest.py               # Fixtures: DB SQLite em memória, mocks, TestClient
│   ├── test_endpoints_entregas.py# Testes dos endpoints de entregas (22 casos)
│   ├── test_endpoints_retreinos.py# Testes dos endpoints de retreinos (18 casos)
│   ├── test_features.py          # Testes unitários de montar_features_v2()
│   ├── test_validacao.py         # Testes das regras de negócio (peso, datas, UF)
│   ├── test_integracao_rota.py   # Testes de obter_rota() com mock HTTP
│   └── test_integracao_clima.py  # Testes de obter_chuva_mm() com mock HTTP
│
├── .env                          # Variáveis de ambiente (não versionado)
├── .env.example                  # Template das variáveis de ambiente
├── requirements.txt              # Dependências de produção
└── requirements-dev.txt          # Dependências de desenvolvimento (pytest, httpx[test])
```

---

## Testes

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Estratégia de Testes

| Aspecto | Abordagem |
|---|---|
| **Banco de dados** | SQLite em memória com `StaticPool` (mesma conexão em todas as threads) |
| **Modelo ML** | Mock via `unittest.mock.patch` — isola os testes de ML do endpoint |
| **OSRM / Open-Meteo** | Mocks HTTP com respostas fixas — sem chamadas reais de rede |
| **BackgroundTasks** | `verificar_e_retreinar` mockado — evita conexão PostgreSQL nos testes |
| **Isolamento** | Cada teste limpa todas as tabelas após execução (`table.delete()`) |

```
115 tests passed in 2.55s
```

### Cobertura de Cenários

- Criação de entrega com e sem coordenadas
- Estado salvo em maiúsculas, distância propagada da rota
- Previsão de chuva integrada às features do modelo
- Paginação com `total` real (sem limit/offset)
- Finalização com data inválida retorna 422
- Retreino manual via `POST /retreinos/disparar`
- Status do ciclo de aprendizado em `/retreinos/status`
- Regras de negócio: peso zero, frete negativo, UF inválida, data prevista anterior ao pedido

---

## Decisões de Projeto

### Por que XGBoost?

O problema tem dados tabulares heterogêneos (numéricas, categóricas, valores ausentes), desbalanceamento de classes (~9% de atrasos) e necessidade de retreino incremental rápido. O XGBoost trata todos esses casos nativamente (`enable_categorical`, `scale_pos_weight`, suporte a `NaN`) sem pré-processamento adicional.

### Por que divisão temporal e não aleatória?

Em problemas de logística, o padrão de atrasos muda ao longo do tempo (sazonalidade, crescimento da base de vendedores, eventos). Dividir por data simula fielmente o cenário de produção: o modelo é sempre avaliado em dados mais recentes do que os de treino.

### Por que PR-AUC como métrica principal?

Com apenas ~9% de entregas atrasadas, o ROC-AUC pode inflar artificialmente. A PR-AUC foca especificamente na precisão e revocação da classe positiva (atraso), que é o que importa operacionalmente — o custo de não alertar um atraso real é maior que o de um falso alarme.

### Por que hot-swap sem restart?

O `predictor` é um singleton em memória (`app/ml/predictor.py`). Ao final do retreino, `predictor.carregar(nova_versao)` substitui o objeto interno (`self._pacote`) atomicamente. Requisições em andamento terminam com o modelo antigo; as seguintes já usam o novo — sem downtime nem race condition.
