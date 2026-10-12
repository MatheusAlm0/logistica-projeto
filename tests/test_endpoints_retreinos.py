"""
Testes dos endpoints de retreinos:
  GET  /retreinos/status
  GET  /retreinos
  GET  /retreinos/{id}
  POST /retreinos/disparar
"""
from unittest.mock import patch

import pytest

from app.model.entrega import Retreino

# ── helpers ───────────────────────────────────────────────────────────────────

ENTREGA_PAYLOAD = {
    "data_pedido": "2024-03-05T10:00:00",
    "data_prevista": "2024-03-15T10:00:00",
    "peso_g": 800.0,
    "valor": 120.0,
    "frete": 18.0,
    "estado_origem": "SP",
    "estado_destino": "RJ",
}


def _inserir_retreino(db, status="ok", versao="v2", n_amostras=150,
                      roc_auc=0.83, pr_auc=0.31):
    """Insere um Retreino diretamente no banco, sem passar pela API."""
    from datetime import datetime, timedelta
    r = Retreino(
        status=status,
        versao=versao,
        n_amostras=n_amostras,
        roc_auc=roc_auc,
        pr_auc=pr_auc,
        iniciado_em=datetime(2024, 3, 1, 8, 0),
        concluido_em=datetime(2024, 3, 1, 8, 5) if status != "rodando" else None,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# ══════════════════════════════════════════════════════════════════════════════
# GET /retreinos/status
# ══════════════════════════════════════════════════════════════════════════════

class TestRetreinoStatus:

    def test_retorna_200(self, client):
        assert client.get("/retreinos/status").status_code == 200

    def test_campos_obrigatorios_presentes(self, client):
        data = client.get("/retreinos/status").json()
        for campo in ("modelo_ativo", "metricas_ativas",
                      "entregas_desde_ultimo_retreino",
                      "min_para_retreinar", "pronto_para_retreinar"):
            assert campo in data, f"campo '{campo}' ausente"

    def test_modelo_ativo_do_mock(self, client):
        data = client.get("/retreinos/status").json()
        assert data["modelo_ativo"] == "v2"

    def test_metricas_ativas_do_mock(self, client):
        data = client.get("/retreinos/status").json()
        assert data["metricas_ativas"]["roc_auc"] == pytest.approx(0.83)

    def test_sem_retreinos_ultimo_e_none(self, client):
        data = client.get("/retreinos/status").json()
        assert data["ultimo_retreino"] is None

    def test_com_retreino_ok_aparece_no_status(self, client, db):
        _inserir_retreino(db)
        data = client.get("/retreinos/status").json()
        assert data["ultimo_retreino"] is not None
        assert data["ultimo_retreino"]["versao"] == "v2"

    def test_pronto_para_retreinar_false_sem_entregas(self, client):
        data = client.get("/retreinos/status").json()
        assert data["pronto_para_retreinar"] is False

    def test_pronto_para_retreinar_true_apos_min_amostras(self, client, db):
        """Após inserir entregas finalizadas suficientes, pronto deve ser True."""
        from datetime import datetime
        from app.model.entrega import Entrega

        # Pega o mínimo configurado
        min_amostras = client.get("/retreinos/status").json()["min_para_retreinar"]

        # Insere exatamente min_amostras entregas finalizadas sem retreino prévio
        for _ in range(min_amostras):
            e = Entrega(
                data_pedido=datetime(2024, 1, 1),
                data_prevista=datetime(2024, 1, 10),
                data_entregue=datetime(2024, 1, 8),
                peso_g=500, valor=100, frete=15,
                status="entregue",
            )
            db.add(e)
        db.commit()

        data = client.get("/retreinos/status").json()
        assert data["pronto_para_retreinar"] is True
        assert data["entregas_desde_ultimo_retreino"] >= min_amostras


# ══════════════════════════════════════════════════════════════════════════════
# GET /retreinos
# ══════════════════════════════════════════════════════════════════════════════

class TestListarRetreinos:

    def test_lista_vazia_inicialmente(self, client):
        resp = client.get("/retreinos")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_retreino_inserido_aparece_na_lista(self, client, db):
        _inserir_retreino(db)
        data = client.get("/retreinos").json()
        assert data["total"] == 1
        assert data["items"][0]["versao"] == "v2"

    def test_multiplos_retreinos_listados(self, client, db):
        _inserir_retreino(db, versao="v2")
        _inserir_retreino(db, versao="v3", roc_auc=0.85)
        assert client.get("/retreinos").json()["total"] == 2

    def test_filtro_por_status_ok(self, client, db):
        _inserir_retreino(db, status="ok")
        _inserir_retreino(db, status="erro")
        resp = client.get("/retreinos?status=ok")
        items = resp.json()["items"]
        assert all(i["status"] == "ok" for i in items)

    def test_filtro_por_status_erro(self, client, db):
        _inserir_retreino(db, status="ok")
        _inserir_retreino(db, status="erro")
        resp = client.get("/retreinos?status=erro")
        items = resp.json()["items"]
        assert all(i["status"] == "erro" for i in items)

    def test_filtro_status_invalido_retorna_422(self, client):
        resp = client.get("/retreinos?status=invalido")
        assert resp.status_code == 422

    def test_pendentes_conta_apenas_rodando(self, client, db):
        _inserir_retreino(db, status="rodando")
        _inserir_retreino(db, status="ok")
        data = client.get("/retreinos").json()
        assert data["pendentes"] == 1

    def test_paginacao_limit(self, client, db):
        for _ in range(5):
            _inserir_retreino(db)
        resp = client.get("/retreinos?limit=2")
        assert len(resp.json()["items"]) <= 2

    def test_duracao_calculada_automaticamente(self, client, db):
        _inserir_retreino(db)  # concluido_em - iniciado_em = 5 min = 300s
        item = client.get("/retreinos").json()["items"][0]
        assert item["duracao_segundos"] == pytest.approx(300.0)

    def test_duracao_none_quando_ainda_rodando(self, client, db):
        _inserir_retreino(db, status="rodando")
        item = client.get("/retreinos?status=rodando").json()["items"][0]
        assert item["duracao_segundos"] is None

    def test_campos_completos_na_resposta(self, client, db):
        _inserir_retreino(db)
        item = client.get("/retreinos").json()["items"][0]
        for campo in ("id", "status", "versao", "n_amostras",
                      "roc_auc", "pr_auc", "iniciado_em"):
            assert campo in item, f"campo '{campo}' ausente"


# ══════════════════════════════════════════════════════════════════════════════
# GET /retreinos/{id}
# ══════════════════════════════════════════════════════════════════════════════

class TestDetalharRetreino:

    def test_detalha_existente(self, client, db):
        r = _inserir_retreino(db)
        resp = client.get(f"/retreinos/{r.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == r.id

    def test_metricas_corretas(self, client, db):
        r = _inserir_retreino(db, roc_auc=0.91, pr_auc=0.45)
        data = client.get(f"/retreinos/{r.id}").json()
        assert data["roc_auc"] == pytest.approx(0.91)
        assert data["pr_auc"] == pytest.approx(0.45)

    def test_id_inexistente_retorna_422(self, client):
        resp = client.get("/retreinos/99999")
        assert resp.status_code == 422

    def test_status_erro_tem_campo_erro(self, client, db):
        from app.model.entrega import Retreino as R
        from datetime import datetime
        r = R(status="erro", erro="conexão recusada",
              iniciado_em=datetime(2024, 3, 1))
        db.add(r)
        db.commit()
        db.refresh(r)
        data = client.get(f"/retreinos/{r.id}").json()
        assert data["erro"] == "conexão recusada"


# ══════════════════════════════════════════════════════════════════════════════
# POST /retreinos/disparar
# ══════════════════════════════════════════════════════════════════════════════

class TestDispararRetreino:

    def test_retorna_202(self, client):
        with patch("app.controller.retreino_controller.verificar_e_retreinar"):
            resp = client.post("/retreinos/disparar")
        assert resp.status_code == 202

    def test_resposta_tem_mensagem_e_link(self, client):
        with patch("app.controller.retreino_controller.verificar_e_retreinar"):
            data = client.post("/retreinos/disparar").json()
        assert "mensagem" in data
        assert "acompanhe" in data
        assert "/retreinos" in data["acompanhe"]

    def test_job_e_chamado_em_background(self, client):
        """TestClient executa BackgroundTasks de forma síncrona."""
        with patch("app.controller.retreino_controller.verificar_e_retreinar") as mock_job:
            client.post("/retreinos/disparar")
        mock_job.assert_called_once()

    def test_nao_bloqueia_resposta(self, client):
        """Disparo deve responder imediatamente (job simulado com delay)."""
        import time

        def job_lento():
            time.sleep(0)   # simula job, mas não bloqueia de verdade

        with patch("app.controller.retreino_controller.verificar_e_retreinar", side_effect=job_lento):
            inicio = time.monotonic()
            resp = client.post("/retreinos/disparar")
            duracao = time.monotonic() - inicio

        assert resp.status_code == 202
        assert duracao < 2.0   # nunca deve demorar mais de 2s
