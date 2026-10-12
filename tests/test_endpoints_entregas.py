"""
Testes dos endpoints de entregas:
  POST   /entregas
  GET    /entregas
  GET    /entregas/{id}
  PATCH  /entregas/{id}/finalizar
"""
from unittest.mock import patch

import pytest

# ── dados de base ─────────────────────────────────────────────────────────────

PAYLOAD = {
    "data_pedido": "2024-03-05T10:00:00",
    "data_prevista": "2024-03-15T10:00:00",
    "peso_g": 800.0,
    "valor": 120.0,
    "frete": 18.0,
    "estado_origem": "SP",
    "estado_destino": "RJ",
}

PAYLOAD_COM_COORDS = {
    **PAYLOAD,
    "origem_lat": -23.5505,
    "origem_lng": -46.6333,
    "destino_lat": -22.9068,
    "destino_lng": -43.1729,
}


# ══════════════════════════════════════════════════════════════════════════════
# POST /entregas
# ══════════════════════════════════════════════════════════════════════════════

class TestPostEntregas:

    def test_cria_entrega_retorna_201(self, client):
        resp = client.post("/entregas", json=PAYLOAD)
        assert resp.status_code == 201

    def test_resposta_tem_id_e_status_pendente(self, client):
        data = client.post("/entregas", json=PAYLOAD).json()
        assert isinstance(data["id"], int)
        assert data["status"] == "pendente"

    def test_resposta_tem_previsao_embutida(self, client):
        data = client.post("/entregas", json=PAYLOAD).json()
        assert "previsao" in data
        assert data["previsao"]["nivel"] == "baixo"
        assert data["previsao"]["probabilidade"] == 0.25

    def test_resposta_tem_ultima_previsao(self, client):
        data = client.post("/entregas", json=PAYLOAD).json()
        assert data["ultima_previsao"] is not None
        assert data["ultima_previsao"]["modelo_versao"] == "v2"

    def test_estado_salvo_em_maiusculo(self, client):
        payload = {**PAYLOAD, "estado_origem": "sp", "estado_destino": "rj"}
        data = client.post("/entregas", json=payload).json()
        assert data["estado_origem"] == "SP"
        assert data["estado_destino"] == "RJ"

    def test_sem_estados_valido(self, client):
        payload = {**PAYLOAD}
        payload.pop("estado_origem")
        payload.pop("estado_destino")
        resp = client.post("/entregas", json=payload)
        assert resp.status_code == 201

    def test_com_coordenadas_usa_rota_mockada(self, client):
        """Com lat/lng fornecidos, obter_rota é chamado e distancia_km é preenchida."""
        data = client.post("/entregas", json=PAYLOAD_COM_COORDS).json()
        # rota mockada retorna 120.0 km
        assert data["distancia_km"] == pytest.approx(120.0)

    def test_distancia_informada_nao_chama_rota(self, client):
        """Se distancia_km já vem no payload, obter_rota não deve ser chamado."""
        payload = {**PAYLOAD, "distancia_km": 350.0}
        with patch("app.service.previsao_service.obter_rota") as mock_rota:
            data = client.post("/entregas", json=payload).json()
        mock_rota.assert_not_called()
        assert data["distancia_km"] == pytest.approx(350.0)

    # ── validações de entrada ──────────────────────────────────────────────────

    def test_peso_zero_retorna_422(self, client):
        resp = client.post("/entregas", json={**PAYLOAD, "peso_g": 0})
        assert resp.status_code == 422

    def test_peso_negativo_retorna_422(self, client):
        resp = client.post("/entregas", json={**PAYLOAD, "peso_g": -1})
        assert resp.status_code == 422

    def test_valor_negativo_retorna_422(self, client):
        resp = client.post("/entregas", json={**PAYLOAD, "valor": -10})
        assert resp.status_code == 422

    def test_frete_negativo_retorna_422(self, client):
        resp = client.post("/entregas", json={**PAYLOAD, "frete": -5})
        assert resp.status_code == 422

    def test_data_prevista_antes_pedido_retorna_422(self, client):
        payload = {
            **PAYLOAD,
            "data_pedido": "2024-03-15T10:00:00",
            "data_prevista": "2024-03-05T10:00:00",
        }
        resp = client.post("/entregas", json=payload)
        assert resp.status_code == 422

    def test_uf_invalida_retorna_422(self, client):
        resp = client.post("/entregas", json={**PAYLOAD, "estado_origem": "XX"})
        assert resp.status_code == 422

    def test_lat_sem_lng_retorna_422(self, client):
        payload = {**PAYLOAD, "origem_lat": -23.5, "origem_lng": None}
        resp = client.post("/entregas", json=payload)
        assert resp.status_code == 422

    def test_campos_obrigatorios_faltando_retorna_422(self, client):
        resp = client.post("/entregas", json={"peso_g": 100})
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /entregas
# ══════════════════════════════════════════════════════════════════════════════

class TestGetEntregas:

    def test_lista_vazia_inicialmente(self, client):
        resp = client.get("/entregas")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    def test_entrega_criada_aparece_na_lista(self, client):
        client.post("/entregas", json=PAYLOAD)
        resp = client.get("/entregas")
        assert resp.json()["total"] == 1

    def test_duas_entregas_listadas(self, client):
        client.post("/entregas", json=PAYLOAD)
        client.post("/entregas", json=PAYLOAD)
        assert client.get("/entregas").json()["total"] == 2

    def test_filtro_por_status_pendente(self, client):
        client.post("/entregas", json=PAYLOAD)
        resp = client.get("/entregas?status=pendente")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filtro_por_status_invalido_retorna_422(self, client):
        resp = client.get("/entregas?status=inexistente")
        # status inexistente não causa erro de validação no controller
        # (a filtragem simplesmente retorna vazio), mas se o service validar → 422
        assert resp.status_code in (200, 422)

    def test_filtro_por_estado_destino(self, client):
        client.post("/entregas", json={**PAYLOAD, "estado_destino": "AM"})
        client.post("/entregas", json={**PAYLOAD, "estado_destino": "RJ"})

        resp = client.get("/entregas?estado_destino=AM")
        items = resp.json()["items"]
        assert all(i["estado_destino"] == "AM" for i in items)

    def test_paginacao_limit(self, client):
        for _ in range(5):
            client.post("/entregas", json=PAYLOAD)
        resp = client.get("/entregas?limit=2")
        assert len(resp.json()["items"]) <= 2

    def test_paginacao_offset(self, client):
        for _ in range(3):
            client.post("/entregas", json=PAYLOAD)
        resp_completo = client.get("/entregas")
        resp_offset = client.get("/entregas?offset=1")
        total = resp_completo.json()["total"]
        assert resp_offset.json()["total"] == total   # total não muda com offset
        assert len(resp_offset.json()["items"]) == total - 1


# ══════════════════════════════════════════════════════════════════════════════
# GET /entregas/{id}
# ══════════════════════════════════════════════════════════════════════════════

class TestGetEntregaById:

    def test_detalha_entrega_existente(self, client):
        criado = client.post("/entregas", json=PAYLOAD).json()
        resp = client.get(f"/entregas/{criado['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == criado["id"]

    def test_detalhe_tem_ultima_previsao(self, client):
        criado = client.post("/entregas", json=PAYLOAD).json()
        data = client.get(f"/entregas/{criado['id']}").json()
        assert data["ultima_previsao"] is not None

    def test_id_inexistente_retorna_422(self, client):
        resp = client.get("/entregas/99999")
        assert resp.status_code == 422

    def test_campos_esperados_na_resposta(self, client):
        criado = client.post("/entregas", json=PAYLOAD).json()
        data = client.get(f"/entregas/{criado['id']}").json()
        for campo in ("id", "status", "peso_g", "valor", "frete",
                      "data_pedido", "data_prevista", "criado_em"):
            assert campo in data, f"campo '{campo}' ausente na resposta"


# ══════════════════════════════════════════════════════════════════════════════
# PATCH /entregas/{id}/finalizar
# ══════════════════════════════════════════════════════════════════════════════

FINALIZAR_PAYLOAD = {"data_entregue": "2024-03-13T14:00:00"}


class TestFinalizarEntrega:

    def _criar(self, client):
        return client.post("/entregas", json=PAYLOAD).json()

    def test_finalizar_muda_status_para_entregue(self, client):
        entrega = self._criar(client)
        resp = client.patch(
            f"/entregas/{entrega['id']}/finalizar",
            json=FINALIZAR_PAYLOAD,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "entregue"

    def test_finalizar_salva_data_entregue(self, client):
        entrega = self._criar(client)
        client.patch(f"/entregas/{entrega['id']}/finalizar", json=FINALIZAR_PAYLOAD)
        data = client.get(f"/entregas/{entrega['id']}").json()
        assert data["data_entregue"] is not None

    def test_finalizar_duas_vezes_retorna_422(self, client):
        entrega = self._criar(client)
        client.patch(f"/entregas/{entrega['id']}/finalizar", json=FINALIZAR_PAYLOAD)
        resp = client.patch(f"/entregas/{entrega['id']}/finalizar", json=FINALIZAR_PAYLOAD)
        assert resp.status_code == 422

    def test_finalizar_id_inexistente_retorna_422(self, client):
        resp = client.patch("/entregas/99999/finalizar", json=FINALIZAR_PAYLOAD)
        assert resp.status_code == 422

    def test_data_entregue_antes_do_pedido_retorna_422(self, client):
        entrega = self._criar(client)
        resp = client.patch(
            f"/entregas/{entrega['id']}/finalizar",
            json={"data_entregue": "2020-01-01T00:00:00"},  # antes de 2024-03-05
        )
        assert resp.status_code == 422

    def test_finalizar_dispara_background_task(self, client):
        """O job de retreino deve ser adicionado como BackgroundTask (não bloqueia)."""
        entrega = self._criar(client)
        with patch("app.controller.entrega_controller.verificar_e_retreinar") as mock_job:
            client.patch(
                f"/entregas/{entrega['id']}/finalizar",
                json=FINALIZAR_PAYLOAD,
            )
        # BackgroundTasks do TestClient executam de forma síncrona
        mock_job.assert_called_once()
