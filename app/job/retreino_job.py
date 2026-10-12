"""
Job de retreino automático.

Fluxo:
  1. Verifica se há >= settings.retreino_min_amostras novas entregas finalizadas
     desde o último retreino bem-sucedido.
  2. Se sim, exporta os dados reais para entregas_historico e dispara o treino.
  3. Registra o resultado na tabela retreinos.
  4. Troca o modelo em memória sem reiniciar o servidor.
"""
import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.ml.predictor import predictor
from app.ml.train import treinar
from app.model.entrega import Retreino
from app.repository import (
    atualizar_retreino,
    contar_entregas_desde_ultimo_retreino,
    criar_retreino,
)

log = logging.getLogger(__name__)


def _exportar_entregas_reais(db) -> int:
    """
    Copia as entregas finalizadas para a tabela entregas_historico no formato
    esperado pelo train.py. Retorna o número de linhas inseridas.
    """
    sql = text("""
        INSERT INTO entregas_historico (
            order_id,
            order_purchase_timestamp,
            order_estimated_delivery_date,
            order_delivered_customer_date,
            customer_state,
            seller_state,
            distance_km,
            total_weight_g,
            total_price,
            total_freight,
            freight_ratio,
            estimated_delivery_days,
            same_state,
            is_sao_paulo_seller,
            purchase_day_of_week,
            purchase_hour,
            purchase_is_weekend,
            is_late,
            origem_dado
        )
        SELECT
            'entrega_' || e.id::text          AS order_id,
            e.data_pedido                     AS order_purchase_timestamp,
            e.data_prevista                   AS order_estimated_delivery_date,
            e.data_entregue                   AS order_delivered_customer_date,
            e.estado_destino                  AS customer_state,
            e.estado_origem                   AS seller_state,
            e.distancia_km                    AS distance_km,
            e.peso_g                          AS total_weight_g,
            e.valor                           AS total_price,
            e.frete                           AS total_freight,
            CASE WHEN e.valor > 0 THEN e.frete / e.valor ELSE NULL END AS freight_ratio,
            EXTRACT(EPOCH FROM (e.data_prevista - e.data_pedido)) / 86400
                                              AS estimated_delivery_days,
            CASE WHEN e.estado_origem = e.estado_destino THEN 1 ELSE 0 END AS same_state,
            CASE WHEN e.estado_origem = 'SP' THEN 1 ELSE 0 END            AS is_sao_paulo_seller,
            EXTRACT(DOW FROM e.data_pedido)   AS purchase_day_of_week,
            EXTRACT(HOUR FROM e.data_pedido)  AS purchase_hour,
            CASE WHEN EXTRACT(DOW FROM e.data_pedido) IN (0,6) THEN 1 ELSE 0 END AS purchase_is_weekend,
            CASE WHEN e.data_entregue > e.data_prevista THEN 1 ELSE 0 END AS is_late,
            'real'                            AS origem_dado
        FROM entregas e
        WHERE e.status = 'entregue'
          AND 'entrega_' || e.id::text NOT IN (
              SELECT order_id FROM entregas_historico WHERE origem_dado = 'real'
          )
    """)
    result = db.execute(sql)
    return result.rowcount


def verificar_e_retreinar() -> None:
    """
    Chamado em background após cada finalização.
    Só retreina se o mínimo de amostras novas for atingido.
    """
    db = SessionLocal()
    try:
        novas = contar_entregas_desde_ultimo_retreino(db)
        log.info("entregas finalizadas desde último retreino: %d (mínimo: %d)",
                 novas, settings.retreino_min_amostras)

        if novas < settings.retreino_min_amostras:
            return

        log.info("iniciando retreino automático (%d novas amostras)", novas)
        retreino = criar_retreino(db)
        db.commit()

        try:
            n_exportadas = _exportar_entregas_reais(db)
            db.commit()

            metricas = treinar("v2")   # reutiliza o train.py existente
            nova_versao = metricas["versao"]

            atualizar_retreino(db, retreino, nova_versao, n_exportadas, metricas, status="ok")
            db.commit()

            # troca o modelo em memória sem reiniciar
            predictor.carregar(nova_versao)
            log.info("modelo atualizado para %s | ROC-AUC=%.4f | PR-AUC=%.4f",
                     nova_versao, metricas["roc_auc"], metricas["pr_auc"])

        except Exception as exc:
            log.exception("retreino falhou")
            atualizar_retreino(db, retreino, versao=None, n_amostras=0,
                               metricas={}, status="erro", erro=str(exc))
            db.commit()

    finally:
        db.close()
