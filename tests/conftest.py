"""
Fixtures compartilhadas entre todos os testes.

Problema resolvido:
  SQLite in-memory SEM StaticPool cria uma conexão nova por pool-checkout.
  Cada conexão nova = banco vazio → "no such table".
  Com StaticPool todas as operações compartilham a MESMA conexão → tabelas visíveis.

Estratégia:
- Engine SQLite criado UMA VEZ no nível de módulo com StaticPool.
- Tabelas criadas UMA VEZ (Base.metadata.create_all) antes de qualquer teste.
- db: yields uma session; ao final, deleta todas as linhas para isolar testes.
- client: substitui get_db, preditor e chamadas HTTP externas por mocks.
- Autenticação: get_usuario_logado retorna USUARIO_ADMIN_MOCK (role=admin).
"""
from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.model  # noqa: F401 — registra todos os modelos no Base
from app.core.database import Base, get_db
from app.model.usuario import Usuario

# ── Engine único compartilhado por toda a sessão de testes ────────────────────
# StaticPool: todas as operações usam a MESMA conexão → mesmo banco in-memory.

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_engine)           # cria tabelas uma vez
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

# ── Usuário admin para bypass de autenticação nos testes ─────────────────────

USUARIO_ADMIN_MOCK = Usuario(
    id=1,
    email="admin@test.com",
    senha_hash="",
    role="admin",
    nome="Admin Teste",
    cliente_id="test-cliente-id",
    ativo=True,
)


# ── Fixture de banco ──────────────────────────────────────────────────────────

@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Session isolada: ao final do teste limpa todas as linhas das tabelas."""
    session = _Session()
    yield session
    session.rollback()   # descarta qualquer transação aberta
    session.close()
    # Limpa linhas comprometidas para isolar testes entre si
    with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


# ── Mock padrão do predictor ──────────────────────────────────────────────────

PREVISAO_MOCK = {
    "probabilidade": 0.25,
    "nivel": "baixo",
    "modelo_versao": "v2",
    "features_usadas": {
        "distance_km": 120.0,
        "total_weight_g": 800.0,
        "total_price": 150.0,
        "total_freight": 18.0,
        "freight_ratio": 0.12,
        "estimated_delivery_days": 10.0,
        "same_state": 1,
        "is_sao_paulo_seller": 1,
        "purchase_day_of_week": 0,
        "purchase_hour": 10,
        "purchase_is_weekend": 0,
        "customer_state": "SP",
        "seller_state": "SP",
    },
    "contexto": {},
}

ROTA_MOCK = {"distancia_km": 120.0, "duracao_min": 90.0, "fonte": "osrm"}


@pytest.fixture()
def mock_predictor() -> MagicMock:
    m = MagicMock()
    m.versao = "v2"
    m.metricas = {
        "versao": "v2",
        "roc_auc": 0.83,
        "pr_auc": 0.31,
        "baseline_pr_auc": 0.08,
    }
    m.prever.return_value = {**PREVISAO_MOCK}
    return m


# ── Cliente FastAPI com tudo mockado ──────────────────────────────────────────

@pytest.fixture()
def client(db: Session, mock_predictor: MagicMock) -> Generator[TestClient, None, None]:
    """
    TestClient com:
    - get_db              → session SQLite do fixture db
    - create_all          → no-op no lifespan (tabelas já existem)
    - predictor           → mock em todos os módulos que o importam
    - obter_rota          → mock ROTA_MOCK (sem OSRM real)
    - obter_chuva_mm      → mock 2.5 mm (sem Open-Meteo real)
    - get_usuario_logado  → retorna USUARIO_ADMIN_MOCK (sem JWT real)
    """
    from app.core.auth import get_usuario_logado
    from app.main import app

    def override_get_db():
        yield db

    def override_get_usuario_logado():
        return USUARIO_ADMIN_MOCK

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_usuario_logado] = override_get_usuario_logado

    with (
        patch("app.main.Base.metadata.create_all"),           # evita conexão ao Postgres
        patch("app.main.scheduler.start"),                    # impede APScheduler de subir
        patch("app.main.scheduler.shutdown"),
        patch("app.main.predictor", mock_predictor),
        patch("app.service.previsao_service.predictor", mock_predictor),
        patch("app.service.retreino_service.predictor", mock_predictor),
        patch("app.ml.predictor.predictor", mock_predictor),
        patch("app.service.previsao_service.obter_rota", return_value=ROTA_MOCK),
        patch("app.service.previsao_service.obter_chuva_mm", return_value=2.5),
        # impede os jobs de conectar ao PostgreSQL real durante testes
        patch("app.controller.entrega_controller.verificar_e_retreinar"),
        patch("app.controller.retreino_controller.verificar_e_retreinar"),
    ):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
