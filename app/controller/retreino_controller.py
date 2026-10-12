"""Endpoints REST para retreinos."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import requer_admin
from app.core.database import get_db
from app.job.retreino_job import verificar_e_retreinar
from app.model.usuario import Usuario
from app.schema.retreino import (
    RetreinoListResponse,
    RetreinoResponse,
    RetreinoStatusResponse,
)
from app.service import retreino_service

router = APIRouter(prefix="/retreinos", tags=["retreinos"])


@router.get("/status", response_model=RetreinoStatusResponse)
def status_retreino(db: Session = Depends(get_db), _: Usuario = Depends(requer_admin)):
    """
    Visão geral do ciclo de aprendizado:

    - Modelo atualmente em memória e suas métricas.
    - Quantas entregas foram finalizadas desde o último retreino.
    - Se o mínimo para disparar um novo retreino já foi atingido.
    """
    resultado = retreino_service.status_geral(db)
    ultimo = resultado["ultimo_retreino"]
    return RetreinoStatusResponse(
        modelo_ativo=resultado["modelo_ativo"],
        metricas_ativas=resultado["metricas_ativas"],
        ultimo_retreino=RetreinoResponse.model_validate(ultimo) if ultimo else None,
        entregas_desde_ultimo_retreino=resultado["entregas_desde_ultimo_retreino"],
        min_para_retreinar=resultado["min_para_retreinar"],
        pronto_para_retreinar=resultado["pronto_para_retreinar"],
    )


@router.get("", response_model=RetreinoListResponse)
def listar_retreinos(
    status: Optional[str] = Query(
        None,
        description="Filtrar por status: rodando | ok | erro",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Usuario = Depends(requer_admin),
):
    """
    Lista o histórico de retreinos com métricas de cada execução.

    Útil para acompanhar a evolução do modelo ao longo do tempo.
    """
    resultado = retreino_service.listar(db, status=status, limit=limit, offset=offset)
    return RetreinoListResponse(
        total=resultado["total"],
        pendentes=resultado["pendentes"],
        items=[RetreinoResponse.model_validate(r) for r in resultado["items"]],
    )


@router.get("/{retreino_id}", response_model=RetreinoResponse)
def detalhar_retreino(retreino_id: int, db: Session = Depends(get_db), _: Usuario = Depends(requer_admin)):
    """Detalha um retreino específico pelo ID."""
    retreino = retreino_service.detalhar(db, retreino_id)
    return RetreinoResponse.model_validate(retreino)


@router.post("/disparar", status_code=202)
def disparar_retreino(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requer_admin),
):
    """
    Dispara um retreino manual em background, independente do mínimo de amostras.

    Retorna imediatamente com HTTP 202 (Accepted). Acompanhe o progresso
    em `GET /retreinos` ou `GET /retreinos/status`.
    """
    background_tasks.add_task(verificar_e_retreinar)
    return {
        "mensagem": "retreino agendado em background",
        "acompanhe": "/retreinos/status",
    }
