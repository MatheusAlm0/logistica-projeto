"""
Testes dos endpoints de administração e do fluxo de aprovação:
  POST  /auth/registro            → empresa nasce com ativo=False
  POST  /auth/login               → empresa inativa retorna 403
  GET   /admin/empresas/pendentes
  PATCH /admin/empresas/{id}/aprovar
  PATCH /admin/empresas/{id}/bloquear
"""
import pytest
from sqlalchemy.orm import Session

from app.model.usuario import Usuario


# ── helpers ───────────────────────────────────────────────────────────────────

def _empresa(db: Session, email: str, ativo: bool = False) -> Usuario:
    """Insere uma empresa diretamente no banco de testes (sem bcrypt — não testa login)."""
    u = Usuario(
        email=email,
        senha_hash="placeholder",
        role="empresa",
        nome="Empresa Teste",
        cliente_id="cli-test",
        ativo=ativo,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _empresa_com_senha(db: Session, email: str, senha: str, ativo: bool) -> Usuario:
    from app.core.auth import hash_senha
    u = Usuario(
        email=email,
        senha_hash=hash_senha(senha),
        role="empresa",
        nome="Empresa",
        cliente_id="cli-login",
        ativo=ativo,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/registro — conta nasce inativa
# ══════════════════════════════════════════════════════════════════════════════

class TestRegistroEmpresa:

    def test_registro_cria_conta_inativa(self, client):
        resp = client.post("/auth/registro", json={
            "email": "nova@empresa.com",
            "senha": "senha123",
            "nome": "Nova Empresa",
        })
        assert resp.status_code == 201
        assert resp.json()["ativo"] is False

    def test_registro_role_empresa(self, client):
        data = client.post("/auth/registro", json={
            "email": "outra@empresa.com",
            "senha": "senha123",
            "nome": "Outra Empresa",
        }).json()
        assert data["role"] == "empresa"

    def test_registro_retorna_campos_esperados(self, client):
        data = client.post("/auth/registro", json={
            "email": "campos@empresa.com",
            "senha": "senha123",
            "nome": "Campos Empresa",
        }).json()
        for campo in ("id", "email", "nome", "role", "cliente_id", "ativo"):
            assert campo in data, f"campo '{campo}' ausente"


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/login — verificação de aprovação
# ══════════════════════════════════════════════════════════════════════════════

class TestLoginAprovacao:

    def test_empresa_inativa_retorna_403(self, client, db):
        _empresa_com_senha(db, "inativa@empresa.com", "senha123", ativo=False)
        resp = client.post("/auth/login", json={
            "email": "inativa@empresa.com", "senha": "senha123",
        })
        assert resp.status_code == 403
        assert "aprovação" in resp.json()["detail"].lower()

    def test_empresa_ativa_retorna_token(self, client, db):
        _empresa_com_senha(db, "ativa@empresa.com", "senha123", ativo=True)
        resp = client.post("/auth/login", json={
            "email": "ativa@empresa.com", "senha": "senha123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_senha_errada_retorna_401(self, client, db):
        _empresa_com_senha(db, "cred@empresa.com", "certa", ativo=True)
        resp = client.post("/auth/login", json={
            "email": "cred@empresa.com", "senha": "errada",
        })
        assert resp.status_code == 401

    def test_email_inexistente_retorna_401(self, client):
        resp = client.post("/auth/login", json={
            "email": "naoexiste@empresa.com", "senha": "qualquer",
        })
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# GET /admin/empresas/pendentes
# ══════════════════════════════════════════════════════════════════════════════

class TestEmpresasPendentes:

    def test_lista_vazia_sem_pendentes(self, client):
        resp = client.get("/admin/empresas/pendentes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_empresa_pendente_aparece(self, client, db):
        _empresa(db, "pendente@empresa.com", ativo=False)
        itens = client.get("/admin/empresas/pendentes").json()
        assert len(itens) == 1
        assert itens[0]["email"] == "pendente@empresa.com"
        assert itens[0]["ativo"] is False

    def test_empresa_ativa_nao_aparece(self, client, db):
        _empresa(db, "ativa@empresa.com", ativo=True)
        assert client.get("/admin/empresas/pendentes").json() == []

    def test_multiplas_pendentes(self, client, db):
        _empresa(db, "p1@empresa.com", ativo=False)
        _empresa(db, "p2@empresa.com", ativo=False)
        assert len(client.get("/admin/empresas/pendentes").json()) == 2

    def test_misto_pendente_e_ativa(self, client, db):
        _empresa(db, "pend@empresa.com", ativo=False)
        _empresa(db, "ativ@empresa.com", ativo=True)
        itens = client.get("/admin/empresas/pendentes").json()
        assert len(itens) == 1
        assert itens[0]["email"] == "pend@empresa.com"

    def test_campos_retornados(self, client, db):
        _empresa(db, "campos@empresa.com", ativo=False)
        item = client.get("/admin/empresas/pendentes").json()[0]
        for campo in ("id", "email", "nome", "cliente_id", "ativo"):
            assert campo in item, f"campo '{campo}' ausente"


# ══════════════════════════════════════════════════════════════════════════════
# PATCH /admin/empresas/{id}/aprovar
# ══════════════════════════════════════════════════════════════════════════════

class TestAprovarEmpresa:

    def test_aprovar_seta_ativo_true(self, client, db):
        u = _empresa(db, "aprovar@empresa.com", ativo=False)
        resp = client.patch(f"/admin/empresas/{u.id}/aprovar")
        assert resp.status_code == 200
        assert resp.json()["ativo"] is True

    def test_aprovada_some_da_lista_pendentes(self, client, db):
        u = _empresa(db, "sum@empresa.com", ativo=False)
        client.patch(f"/admin/empresas/{u.id}/aprovar")
        assert client.get("/admin/empresas/pendentes").json() == []

    def test_aprovar_id_inexistente_retorna_404(self, client):
        resp = client.patch("/admin/empresas/99999/aprovar")
        assert resp.status_code == 404

    def test_aprovar_idempotente(self, client, db):
        u = _empresa(db, "idem@empresa.com", ativo=True)
        resp = client.patch(f"/admin/empresas/{u.id}/aprovar")
        assert resp.status_code == 200
        assert resp.json()["ativo"] is True


# ══════════════════════════════════════════════════════════════════════════════
# PATCH /admin/empresas/{id}/bloquear
# ══════════════════════════════════════════════════════════════════════════════

class TestBloquearEmpresa:

    def test_bloquear_seta_ativo_false(self, client, db):
        u = _empresa(db, "bloquear@empresa.com", ativo=True)
        resp = client.patch(f"/admin/empresas/{u.id}/bloquear")
        assert resp.status_code == 200
        assert resp.json()["ativo"] is False

    def test_bloqueada_aparece_na_lista_pendentes(self, client, db):
        u = _empresa(db, "bloq2@empresa.com", ativo=True)
        client.patch(f"/admin/empresas/{u.id}/bloquear")
        pendentes = client.get("/admin/empresas/pendentes").json()
        assert any(p["id"] == u.id for p in pendentes)

    def test_bloquear_id_inexistente_retorna_404(self, client):
        resp = client.patch("/admin/empresas/99999/bloquear")
        assert resp.status_code == 404

    def test_bloquear_empresa_ja_inativa_idempotente(self, client, db):
        u = _empresa(db, "jabl@empresa.com", ativo=False)
        resp = client.patch(f"/admin/empresas/{u.id}/bloquear")
        assert resp.status_code == 200
        assert resp.json()["ativo"] is False

    def test_aprovar_depois_bloquear(self, client, db):
        u = _empresa(db, "ciclo@empresa.com", ativo=False)
        client.patch(f"/admin/empresas/{u.id}/aprovar")
        resp = client.patch(f"/admin/empresas/{u.id}/bloquear")
        assert resp.json()["ativo"] is False
