from fastapi import APIRouter, Depends

from app.core.auth import get_usuario_logado
from app.model.usuario import Usuario
from app.schema.previsao import PrevisaoRequest, PrevisaoResponse
from app.service import previsao_service

router = APIRouter(prefix="/previsoes", tags=["previsoes"])


@router.post("", response_model=PrevisaoResponse)
def prever(req: PrevisaoRequest, _: Usuario = Depends(get_usuario_logado)):
    return previsao_service.prever(req.model_dump())
