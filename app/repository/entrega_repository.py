"""Acesso ao banco para Entrega, Previsao e Retreino."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.entrega import Entrega, Previsao, Retreino


# ── Entrega ──────────────────────────────────────────────────────────────────

def criar_entrega(db: Session, dados: dict) -> Entrega:
    entrega = Entrega(**dados)
    db.add(entrega)
    db.flush()   # gera o id sem fechar a transação
    return entrega


def buscar_entrega(db: Session, entrega_id: int) -> Optional[Entrega]:
    return db.get(Entrega, entrega_id)


def buscar_entrega_por_codigo(db: Session, codigo_rastreio: str) -> Optional[Entrega]:
    return db.scalars(
        select(Entrega).where(Entrega.codigo_rastreio == codigo_rastreio)
    ).first()


def listar_entregas(
    db: Session,
    status: Optional[str] = None,
    estado_destino: Optional[str] = None,
    cliente_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Entrega]:
    q = select(Entrega)
    if status:
        q = q.where(Entrega.status == status)
    if estado_destino:
        q = q.where(Entrega.estado_destino == estado_destino)
    if cliente_id:
        q = q.where(Entrega.cliente_id == cliente_id)
    q = q.order_by(Entrega.criado_em.desc()).limit(limit).offset(offset)
    return list(db.scalars(q))


def contar_entregas(
    db: Session,
    status: Optional[str] = None,
    estado_destino: Optional[str] = None,
    cliente_id: Optional[str] = None,
) -> int:
    q = select(Entrega)
    if status:
        q = q.where(Entrega.status == status)
    if estado_destino:
        q = q.where(Entrega.estado_destino == estado_destino)
    if cliente_id:
        q = q.where(Entrega.cliente_id == cliente_id)
    return len(list(db.scalars(q)))


def finalizar_entrega(db: Session, entrega: Entrega, data_entregue: datetime) -> Entrega:
    entrega.status = "entregue"
    entrega.data_entregue = data_entregue
    db.flush()
    return entrega


# ── Previsao ──────────────────────────────────────────────────────────────────

def salvar_previsao(db: Session, entrega_id: int, resultado: dict, contexto: dict) -> Previsao:
    """Persiste o resultado do predictor junto com metadados de contexto."""
    rota = contexto.get("rota", {})
    previsao = Previsao(
        entrega_id=entrega_id,
        probabilidade=resultado["probabilidade"],
        nivel=resultado["nivel"],
        modelo_versao=resultado["modelo_versao"],
        features_json=resultado["features_usadas"],
        chuva_mm=contexto.get("chuva_mm"),
        rota_fonte=rota.get("fonte"),
    )
    db.add(previsao)
    db.flush()
    return previsao


# ── Retreino ──────────────────────────────────────────────────────────────────

def criar_retreino(db: Session) -> Retreino:
    retreino = Retreino(status="rodando")
    db.add(retreino)
    db.flush()
    return retreino


def atualizar_retreino(
    db: Session,
    retreino: Retreino,
    versao: str,
    n_amostras: int,
    metricas: dict,
    status: str = "ok",
    erro: Optional[str] = None,
) -> Retreino:
    from datetime import timezone
    retreino.concluido_em = datetime.now(tz=timezone.utc)
    retreino.versao = versao
    retreino.n_amostras = n_amostras
    retreino.roc_auc = metricas.get("roc_auc")
    retreino.pr_auc = metricas.get("pr_auc")
    retreino.status = status
    retreino.erro = erro
    db.flush()
    return retreino


def buscar_retreino(db: Session, retreino_id: int) -> Optional[Retreino]:
    return db.get(Retreino, retreino_id)


def listar_retreinos(
    db: Session,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Retreino]:
    q = select(Retreino)
    if status:
        q = q.where(Retreino.status == status)
    q = q.order_by(Retreino.iniciado_em.desc()).limit(limit).offset(offset)
    return list(db.scalars(q))


def buscar_ultimo_retreino_ok(db: Session) -> Optional[Retreino]:
    return db.scalars(
        select(Retreino)
        .where(Retreino.status == "ok")
        .order_by(Retreino.concluido_em.desc())
        .limit(1)
    ).first()


def contar_retreinos(db: Session, status: Optional[str] = None) -> int:
    q = select(Retreino)
    if status:
        q = q.where(Retreino.status == status)
    return len(list(db.scalars(q)))


def contar_entregas_desde_ultimo_retreino(db: Session) -> int:
    """Conta entregas finalizadas que ainda não foram exportadas ao histórico.

    Usa o mesmo critério de _exportar_entregas_reais: evita comparar data_entregue
    (data do negócio, pode ser retroativa) com concluido_em (timestamp do sistema).
    Faz fallback para contagem simples em ambientes sem entregas_historico (testes).
    """
    from sqlalchemy import text
    try:
        result = db.execute(text("""
            SELECT COUNT(*) FROM entregas e
            WHERE e.status = 'entregue'
              AND 'entrega_' || CAST(e.id AS TEXT) NOT IN (
                  SELECT order_id FROM entregas_historico WHERE origem_dado = 'real'
              )
        """))
        return result.scalar()
    except Exception:
        # Fallback para SQLite nos testes (entregas_historico não existe)
        db.rollback()
        return len(list(db.scalars(select(Entrega).where(Entrega.status == "entregue"))))
