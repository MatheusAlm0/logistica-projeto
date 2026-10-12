from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.controller import (
    admin_controller,
    auth_controller,
    checkpoint_controller,
    entrega_controller,
    galpao_controller,
    previsao_controller,
    rastreio_controller,
    retreino_controller,
)
from app.core.database import Base, engine
from app.core.exceptions import RegraDeNegocioError
from app.job.reavaliacao_job import reavaliar_entregas_pendentes
from app.ml.predictor import ModeloNaoEncontrado, predictor
import app.model  # noqa: F401 — registra todos os modelos no metadata do Base

scheduler = BackgroundScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    predictor.carregar()
    scheduler.add_job(reavaliar_entregas_pendentes, "interval", minutes=30, id="reavaliacao",
                      replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Previsor de Atrasos Logísticos", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_controller.router)
app.include_router(auth_controller.router)
app.include_router(previsao_controller.router)
app.include_router(entrega_controller.router)
app.include_router(checkpoint_controller.router)
app.include_router(galpao_controller.router)
app.include_router(retreino_controller.router)
app.include_router(rastreio_controller.router)


@app.exception_handler(RegraDeNegocioError)
async def regra_handler(request: Request, exc: RegraDeNegocioError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ModeloNaoEncontrado)
async def modelo_handler(request: Request, exc: ModeloNaoEncontrado):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok", "modelo": predictor.versao}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
