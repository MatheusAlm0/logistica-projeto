"""
Testes de autenticação REAL (JWT) e isolamento entre clientes (tenant).

Diferente do resto da suíte, aqui NÃO usamos o override de get_usuario_logado:
os tokens são gerados com app.core.auth.criar_token e validados pela dependência
real. Cenário: duas empresas (A e B, cliente_id distintos) e um admin.

Cobre:
  - 401 sem token / token inválido / token expirado / empresa bloqueada
  - 403 de empresa em endpoints restritos a admin
  - empresa A não lê / finaliza / edita entregas nem checkpoints de B (404)
  - rastreio público sem dados internos
  - validação de registro/login (senha, e-mail case-insensitive)
  - finalizar com datetime com fuso e com status 'atrasada'
  - validador da SECRET_KEY
  - isolamento de veículos e orçamentos (cotação)
"""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.auth import criar_token, hash_senha
from app.model.entrega import Entrega
from app.model.galpao import Galpao
from app.model.orcamento import Orcamento
from app.model.usuario import Usuario
from app.model.veiculo import Veiculo

PAYLOAD_ENTREGA = {
    "data_pedido": "2024-03-05T10:00:00",
    "data_prevista": "2024-03-15T10:00:00",
    "peso_g": 800.0,
    "valor": 120.0,
    "frete": 18.0,
    "estado_origem": "SP",
    "estado_destino": "RJ",
}


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client_real(client):
    """TestClient do conftest, mas com a autenticação JWT real (sem override admin)."""
    from app.core.auth import get_usuario_logado
    from app.main import app

    app.dependency_overrides.pop(get_usuario_logado, None)
    return client


def _usuario(db: Session, email: str, role: str, cliente_id: str,
             ativo: bool = True, senha: str = "senha-forte-123") -> Usuario:
    u = Usuario(
        email=email,
        senha_hash=hash_senha(senha),
        role=role,
        nome=f"Usuário {email}",
        cliente_id=cliente_id,
        ativo=ativo,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _headers(usuario: Usuario, expires_delta: timedelta | None = None) -> dict[str, str]:
    token = criar_token(
        {"sub": str(usuario.id), "email": usuario.email, "role": usuario.role},
        expires_delta=expires_delta,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def empresa_a(db):
    return _usuario(db, "empresa-a@test.com", "empresa", "cliente-a")


@pytest.fixture()
def empresa_b(db):
    return _usuario(db, "empresa-b@test.com", "empresa", "cliente-b")


@pytest.fixture()
def admin(db):
    return _usuario(db, "admin-real@test.com", "admin", "cliente-admin")


@pytest.fixture()
def h_a(empresa_a):
    return _headers(empresa_a)


@pytest.fixture()
def h_b(empresa_b):
    return _headers(empresa_b)


@pytest.fixture()
def h_admin(admin):
    return _headers(admin)


@pytest.fixture()
def galpao(db):
    g = Galpao(nome="CD Campinas", cidade="Campinas", estado="SP", lat=-22.9, lng=-47.06, ativo=True)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@pytest.fixture()
def entrega_a(client_real, h_a):
    """Entrega pertencente à empresa A, criada pela API."""
    resp = client_real.post("/entregas", json=PAYLOAD_ENTREGA, headers=h_a)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# 401 — autenticação
# ══════════════════════════════════════════════════════════════════════════════

class TestAutenticacao:

    def test_sem_token_retorna_401(self, client_real):
        assert client_real.get("/entregas").status_code == 401

    def test_token_malformado_retorna_401(self, client_real):
        resp = client_real.get("/entregas", headers={"Authorization": "Bearer abc.def.ghi"})
        assert resp.status_code == 401

    def test_token_assinado_com_outra_chave_retorna_401(self, client_real, empresa_a):
        from jose import jwt
        token = jwt.encode(
            {"sub": str(empresa_a.id), "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1)},
            "outra-chave-qualquer-com-mais-de-32-caracteres",
            algorithm="HS256",
        )
        resp = client_real.get("/entregas", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_token_expirado_retorna_401(self, client_real, empresa_a):
        h = _headers(empresa_a, expires_delta=timedelta(minutes=-5))
        assert client_real.get("/auth/me", headers=h).status_code == 401

    def test_token_valido_retorna_200(self, client_real, empresa_a, h_a):
        resp = client_real.get("/auth/me", headers=h_a)
        assert resp.status_code == 200
        assert resp.json()["email"] == empresa_a.email

    def test_empresa_bloqueada_com_token_antigo_retorna_401(self, client_real, db, empresa_a, h_a):
        assert client_real.get("/auth/me", headers=h_a).status_code == 200
        empresa_a.ativo = False
        db.commit()
        assert client_real.get("/auth/me", headers=h_a).status_code == 401
        assert client_real.get("/entregas", headers=h_a).status_code == 401

    def test_token_de_usuario_inexistente_retorna_401(self, client_real):
        fantasma = Usuario(id=987654, email="x@x.com", role="empresa")
        assert client_real.get("/auth/me", headers=_headers(fantasma)).status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 403 — autorização por papel
# ══════════════════════════════════════════════════════════════════════════════

class TestAutorizacaoAdmin:

    @pytest.mark.parametrize("metodo,url", [
        ("get", "/admin/empresas/pendentes"),
        ("patch", "/admin/empresas/1/aprovar"),
        ("patch", "/admin/empresas/1/bloquear"),
        ("get", "/retreinos"),
        ("get", "/retreinos/status"),
        ("post", "/retreinos/disparar"),
    ])
    def test_empresa_em_endpoint_admin_retorna_403(self, client_real, h_a, metodo, url):
        resp = getattr(client_real, metodo)(url, headers=h_a)
        assert resp.status_code == 403

    def test_admin_acessa_endpoint_admin(self, client_real, h_admin):
        assert client_real.get("/admin/empresas/pendentes", headers=h_admin).status_code == 200

    def test_empresa_nao_aprova_a_si_mesma(self, client_real, db, empresa_a, h_a):
        resp = client_real.patch(f"/admin/empresas/{empresa_a.id}/aprovar", headers=h_a)
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Isolamento de entregas entre clientes
# ══════════════════════════════════════════════════════════════════════════════

class TestIsolamentoEntregas:

    def test_dono_detalha_a_propria_entrega(self, client_real, h_a, entrega_a):
        assert client_real.get(f"/entregas/{entrega_a['id']}", headers=h_a).status_code == 200

    def test_b_nao_detalha_entrega_de_a(self, client_real, h_b, entrega_a):
        assert client_real.get(f"/entregas/{entrega_a['id']}", headers=h_b).status_code == 404

    def test_b_nao_ve_entrega_de_a_na_lista(self, client_real, h_b, entrega_a):
        data = client_real.get("/entregas", headers=h_b).json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_b_nao_finaliza_entrega_de_a(self, client_real, h_a, h_b, entrega_a):
        resp = client_real.patch(
            f"/entregas/{entrega_a['id']}/finalizar",
            json={"data_entregue": "2024-03-13T14:00:00"},
            headers=h_b,
        )
        assert resp.status_code == 404
        # continua pendente para o dono
        assert client_real.get(f"/entregas/{entrega_a['id']}", headers=h_a).json()["status"] == "pendente"

    def test_b_nao_edita_entrega_de_a(self, client_real, h_b, entrega_a):
        resp = client_real.patch(f"/entregas/{entrega_a['id']}/editar", json={"peso_g": 1.0}, headers=h_b)
        assert resp.status_code == 404

    def test_b_nao_muda_status_de_entrega_de_a(self, client_real, h_b, entrega_a):
        resp = client_real.patch(
            f"/entregas/{entrega_a['id']}/status", json={"status": "cancelado"}, headers=h_b
        )
        assert resp.status_code == 404

    def test_b_nao_remove_entrega_de_a(self, client_real, h_a, h_b, entrega_a):
        assert client_real.delete(f"/entregas/{entrega_a['id']}", headers=h_b).status_code == 404
        assert client_real.get(f"/entregas/{entrega_a['id']}", headers=h_a).status_code == 200

    def test_admin_detalha_entrega_de_qualquer_cliente(self, client_real, h_admin, entrega_a):
        assert client_real.get(f"/entregas/{entrega_a['id']}", headers=h_admin).status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Checkpoints: autenticação + tenant
# ══════════════════════════════════════════════════════════════════════════════

class TestIsolamentoCheckpoints:

    def test_listar_sem_token_retorna_401(self, client_real, entrega_a):
        assert client_real.get(f"/entregas/{entrega_a['id']}/checkpoints").status_code == 401

    def test_dono_lista_checkpoints(self, client_real, h_a, entrega_a, galpao):
        criado = client_real.post(
            f"/entregas/{entrega_a['id']}/checkpoints",
            json={"galpao_id": galpao.id, "chegou_em": "2024-03-07T09:00:00"},
            headers=h_a,
        )
        assert criado.status_code == 201
        resp = client_real.get(f"/entregas/{entrega_a['id']}/checkpoints", headers=h_a)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_b_nao_lista_checkpoints_de_a(self, client_real, h_b, entrega_a):
        assert client_real.get(f"/entregas/{entrega_a['id']}/checkpoints", headers=h_b).status_code == 404

    def test_b_nao_registra_checkpoint_em_entrega_de_a(self, client_real, h_b, entrega_a, galpao):
        resp = client_real.post(
            f"/entregas/{entrega_a['id']}/checkpoints",
            json={"galpao_id": galpao.id, "chegou_em": "2024-03-07T09:00:00"},
            headers=h_b,
        )
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Rastreio público — sem dados internos
# ══════════════════════════════════════════════════════════════════════════════

class TestRastreioPublico:

    def _criar_com_checkpoint(self, client_real, h_a, galpao):
        resp = client_real.post(
            "/entregas",
            json={**PAYLOAD_ENTREGA, "hubs_planejados": [galpao.id]},   # gera checkpoint c/ observacao
            headers=h_a,
        )
        assert resp.status_code == 201
        return resp.json()

    def test_rastreio_sem_token_funciona(self, client_real, h_a, galpao):
        entrega = self._criar_com_checkpoint(client_real, h_a, galpao)
        resp = client_real.get(f"/rastreio/{entrega['codigo_rastreio']}")
        assert resp.status_code == 200

    def test_rastreio_nao_vaza_dados_internos(self, client_real, h_a, galpao):
        entrega = self._criar_com_checkpoint(client_real, h_a, galpao)
        resp = client_real.get(f"/rastreio/{entrega['codigo_rastreio']}")
        texto = resp.text
        for proibido in ("observacao", "registrado_por", "probabilidade", "modelo_versao",
                         "chuva_mm", "features", "ultima_previsao", "Hub planejado",
                         "entrega_id", "galpao_id", "cliente_id"):
            assert proibido not in texto, f"'{proibido}' exposto no rastreio público"

        data = resp.json()
        assert "id" not in data
        assert data["nivel_risco"] == "baixo"
        assert len(data["checkpoints"]) == 1
        cp = data["checkpoints"][0]
        assert set(cp) == {"chegou_em", "galpao"}
        assert set(cp["galpao"]) == {"nome", "cidade", "estado", "lat", "lng"}
        assert cp["galpao"]["nome"] == "CD Campinas"

    def test_rastreio_codigo_inexistente_404(self, client_real):
        assert client_real.get("/rastreio/TRK-NAOEXISTE").status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Registro / login — validação de entrada
# ══════════════════════════════════════════════════════════════════════════════

class TestValidacaoAuth:

    def _registro(self, client_real, **overrides):
        body = {"email": "nova@empresa.com", "senha": "senha-forte-123", "nome": "Nova"}
        body.update(overrides)
        return client_real.post("/auth/registro", json=body)

    def test_senha_curta_retorna_422(self, client_real):
        assert self._registro(client_real, senha="1234567").status_code == 422

    def test_senha_100_caracteres_retorna_422(self, client_real):
        assert self._registro(client_real, senha="a" * 100).status_code == 422

    def test_senha_acima_de_72_bytes_retorna_422(self, client_real):
        # 40 caracteres, mas 80 bytes em UTF-8 → bcrypt recusaria (500) sem a validação
        assert self._registro(client_real, senha="ã" * 40).status_code == 422

    def test_nome_vazio_retorna_422(self, client_real):
        assert self._registro(client_real, nome="   ").status_code == 422

    def test_nome_e_email_normalizados(self, client_real):
        resp = self._registro(client_real, email="Nova@Empresa.COM", nome="  Nova Ltda  ")
        assert resp.status_code == 201
        assert resp.json()["email"] == "nova@empresa.com"
        assert resp.json()["nome"] == "Nova Ltda"

    def test_email_duplicado_com_outra_caixa_retorna_400(self, client_real):
        assert self._registro(client_real, email="nova@empresa.com").status_code == 201
        assert self._registro(client_real, email="NOVA@EMPRESA.COM").status_code == 400

    def test_login_case_insensitive(self, client_real, db):
        assert self._registro(client_real, email="Fulano@Empresa.com").status_code == 201
        db.query(Usuario).filter(Usuario.email == "fulano@empresa.com").update({"ativo": True})
        db.commit()
        for email in ("fulano@empresa.com", "FULANO@EMPRESA.COM", "Fulano@Empresa.com"):
            resp = client_real.post("/auth/login", json={"email": email, "senha": "senha-forte-123"})
            assert resp.status_code == 200, email

    def test_login_usuario_antigo_com_email_maiusculo(self, client_real, db):
        # usuário gravado antes da normalização, com maiúsculas no banco
        _usuario(db, "Legado@Empresa.com", "empresa", "cliente-legado", senha="curta")
        resp = client_real.post("/auth/login", json={"email": "legado@empresa.com", "senha": "curta"})
        assert resp.status_code == 200

    def test_login_senha_longa_retorna_422_nao_500(self, client_real, empresa_a):
        resp = client_real.post("/auth/login", json={"email": empresa_a.email, "senha": "a" * 100})
        assert resp.status_code == 422

    def test_verificar_senha_acima_de_72_bytes_nao_levanta(self):
        from app.core.auth import verificar_senha
        assert verificar_senha("ã" * 40, hash_senha("qualquer")) is False


# ══════════════════════════════════════════════════════════════════════════════
# Finalizar: fuso horário e status atrasada
# ══════════════════════════════════════════════════════════════════════════════

class TestFinalizar:

    def test_finalizar_com_datetime_aware_retorna_200(self, client_real, h_a, entrega_a):
        resp = client_real.patch(
            f"/entregas/{entrega_a['id']}/finalizar",
            json={"data_entregue": "2024-03-13T14:00:00Z"},
            headers=h_a,
        )
        assert resp.status_code == 200, resp.text
        # 14:00 UTC = 11:00 em São Paulo (UTC-3), gravado sem fuso
        assert resp.json()["data_entregue"] == "2024-03-13T11:00:00"

    def test_finalizar_com_offset_explicito(self, client_real, h_a, entrega_a):
        resp = client_real.patch(
            f"/entregas/{entrega_a['id']}/finalizar",
            json={"data_entregue": "2024-03-13T14:00:00-03:00"},
            headers=h_a,
        )
        assert resp.status_code == 200
        assert resp.json()["data_entregue"] == "2024-03-13T14:00:00"

    def test_finalizar_entrega_atrasada_retorna_200(self, client_real, db, h_a, entrega_a):
        db.get(Entrega, entrega_a["id"]).status = "atrasada"
        db.commit()
        resp = client_real.patch(
            f"/entregas/{entrega_a['id']}/finalizar",
            json={"data_entregue": "2024-03-20T10:00:00"},
            headers=h_a,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "entregue"

    def test_finalizar_entrega_cancelada_continua_422(self, client_real, db, h_a, entrega_a):
        db.get(Entrega, entrega_a["id"]).status = "cancelado"
        db.commit()
        resp = client_real.patch(
            f"/entregas/{entrega_a['id']}/finalizar",
            json={"data_entregue": "2024-03-20T10:00:00"},
            headers=h_a,
        )
        assert resp.status_code == 422

    def test_criar_com_datetime_aware_persiste_horario_local(self, client_real, h_a):
        payload = {**PAYLOAD_ENTREGA,
                   "data_pedido": "2024-03-05T10:00:00Z",
                   "data_prevista": "2024-03-15T10:00:00+00:00"}
        resp = client_real.post("/entregas", json=payload, headers=h_a)
        assert resp.status_code == 201, resp.text
        assert resp.json()["data_pedido"] == "2024-03-05T07:00:00"
        assert resp.json()["data_prevista"] == "2024-03-15T07:00:00"


# ══════════════════════════════════════════════════════════════════════════════
# SECRET_KEY
# ══════════════════════════════════════════════════════════════════════════════

class TestSecretKey:

    @pytest.mark.parametrize("chave", [
        "troque-esta-chave-por-um-valor-aleatorio-longo-em-producao",   # .env.example
        "troque-esta-chave-em-producao",                                # antigo default
        "curta-demais",
        "x" * 31,
    ])
    def test_rejeita_chave_insegura(self, chave):
        from app.core.config import Settings
        with pytest.raises(ValidationError):
            Settings(_env_file=None, secret_key=chave)

    def test_rejeita_ausencia_de_chave(self, monkeypatch):
        from app.core.config import Settings
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_aceita_chave_forte(self):
        import secrets
        from app.core.config import Settings
        chave = secrets.token_urlsafe(48)
        assert Settings(_env_file=None, secret_key=chave).secret_key == chave


# ══════════════════════════════════════════════════════════════════════════════
# Cotação: veículos e orçamentos por cliente
# ══════════════════════════════════════════════════════════════════════════════

def _orcamento(db: Session, cliente_id: str, veiculo_id: int | None = None) -> Orcamento:
    o = Orcamento(
        codigo=f"ORC-{cliente_id[-1].upper()}0000001",
        cliente_id=cliente_id,
        estado_origem="SP",
        estado_destino="RJ",
        peso_kg=10.0,
        comprimento_cm=30.0,
        largura_cm=30.0,
        altura_cm=30.0,
        distancia_km=430.0,
        veiculo_id=veiculo_id,
        tipo_frete="padrao",
        valor_frete=250.0,
        prazo_dias=2,
        status="rascunho",
        validade_em=datetime.now(tz=timezone.utc) + timedelta(days=3),
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


class TestIsolamentoCotacao:

    @pytest.fixture()
    def veiculo_a(self, db, empresa_a):
        v = Veiculo(cliente_id=empresa_a.cliente_id, nome="Van A", tipo="van", peso_max_kg=1000, ativo=True)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v

    def test_b_nao_lista_veiculo_de_a(self, client_real, h_a, h_b, veiculo_a):
        assert len(client_real.get("/frota/veiculos", headers=h_a).json()) == 1
        assert client_real.get("/frota/veiculos", headers=h_b).json() == []

    def test_b_nao_edita_nem_remove_veiculo_de_a(self, client_real, h_b, veiculo_a):
        assert client_real.patch(f"/frota/veiculos/{veiculo_a.id}", json={"nome": "x"}, headers=h_b).status_code == 404
        assert client_real.delete(f"/frota/veiculos/{veiculo_a.id}", headers=h_b).status_code == 404

    def test_b_nao_le_nem_aprova_orcamento_de_a(self, client_real, db, empresa_a, h_a, h_b):
        orc = _orcamento(db, empresa_a.cliente_id)
        assert client_real.get(f"/cotacao/orcamentos/{orc.id}", headers=h_b).status_code == 404
        assert client_real.get("/cotacao/orcamentos", headers=h_b).json() == []
        assert client_real.patch(f"/cotacao/orcamentos/{orc.id}/aprovar", headers=h_b).status_code == 404
        assert client_real.delete(f"/cotacao/orcamentos/{orc.id}", headers=h_b).status_code == 404
        assert client_real.get(f"/cotacao/orcamentos/{orc.id}", headers=h_a).status_code == 200

    def test_dono_aprova_orcamento_e_gera_entrega(self, client_real, db, empresa_a, h_a):
        orc = _orcamento(db, empresa_a.cliente_id)
        resp = client_real.patch(f"/cotacao/orcamentos/{orc.id}/aprovar", headers=h_a)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "aprovado"
        entregas = client_real.get("/entregas", headers=h_a).json()
        assert entregas["total"] == 1

    def test_b_nao_vincula_veiculo_de_a_ao_salvar_orcamento(self, client_real, h_b, veiculo_a):
        body = {
            "galpao_origem_id": 1, "galpao_origem": {}, "destino_tipo": "endereco",
            "destino_descricao": "RJ", "estado_origem": "SP", "estado_destino": "RJ",
            "peso_kg": 10.0, "comprimento_cm": 30.0, "largura_cm": 30.0, "altura_cm": 30.0,
            "tipo_frete": "padrao", "distancia_km": 430.0, "valor_frete": 250.0, "prazo_dias": 2,
            "veiculos_elegiveis": [{
                "id": veiculo_a.id, "nome": "Van A", "tipo": "van", "peso_max_kg": 1000, "ativo": True,
            }],
            "paradas_intermediarias": [], "clima_resumo": [],
        }
        assert client_real.post("/cotacao/salvar", json=body, headers=h_b).status_code == 404
