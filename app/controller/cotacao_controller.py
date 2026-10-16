"""Cotação de frete: frota (veículos, tabela de preço) e orçamentos.

DDL para criar as tabelas (executar manualmente no banco):

CREATE TABLE veiculos (
    id SERIAL PRIMARY KEY,
    cliente_id VARCHAR(36) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    peso_max_kg FLOAT NOT NULL,
    comprimento_max_cm FLOAT,
    largura_max_cm FLOAT,
    altura_max_cm FLOAT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX ix_veiculos_cliente_id ON veiculos(cliente_id);

CREATE TABLE tabelas_preco (
    id SERIAL PRIMARY KEY,
    cliente_id VARCHAR(36) NOT NULL,
    modalidade VARCHAR(30) NOT NULL,
    preco_base_km FLOAT,
    multiplicador_expresso FLOAT NOT NULL DEFAULT 1.4,
    raio_galpao_km FLOAT NOT NULL DEFAULT 150.0,
    taxa_dimensao_extra FLOAT,
    limite_dimensao_cm FLOAT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX ix_tabelas_preco_cliente_id ON tabelas_preco(cliente_id);

CREATE TABLE faixas_preco (
    id SERIAL PRIMARY KEY,
    tabela_id INTEGER NOT NULL REFERENCES tabelas_preco(id) ON DELETE CASCADE,
    peso_min_kg FLOAT NOT NULL,
    peso_max_kg FLOAT,
    preco_por_km FLOAT NOT NULL
);

CREATE TABLE orcamentos (
    id SERIAL PRIMARY KEY,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    codigo VARCHAR(20) NOT NULL UNIQUE,
    cliente_id VARCHAR(36) NOT NULL,
    estado_origem VARCHAR(2) NOT NULL,
    estado_destino VARCHAR(2) NOT NULL,
    peso_kg FLOAT NOT NULL,
    comprimento_cm FLOAT NOT NULL,
    largura_cm FLOAT NOT NULL,
    altura_cm FLOAT NOT NULL,
    distancia_km FLOAT NOT NULL,
    duracao_min FLOAT,
    veiculo_id INTEGER REFERENCES veiculos(id),
    tipo_frete VARCHAR(20) NOT NULL,
    valor_frete FLOAT NOT NULL,
    prazo_dias INTEGER NOT NULL,
    galpoes_rota JSON,
    clima_resumo JSON,
    status VARCHAR(20) NOT NULL DEFAULT 'rascunho',
    validade_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_orcamentos_cliente_id ON orcamentos(cliente_id);
"""
import math
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import requer_empresa
from app.core.database import get_db
from app.integration.rota import haversine_km, obter_rota
from app.model.faixa_preco import FaixaPreco
from app.model.galpao import Galpao
from app.model.orcamento import Orcamento
from app.model.tabela_preco import TabelaPreco
from app.model.usuario import Usuario
from app.model.veiculo import Veiculo
from app.service import entrega_service

router = APIRouter(tags=["cotacao"])

# ── Coordenadas aproximadas das capitais estaduais ─────────────────────────

CAPITAL_COORDS: dict[str, tuple[float, float]] = {
    "AC": (-9.9754, -67.8249), "AL": (-9.6658, -35.7350), "AM": (-3.1190, -60.0217),
    "AP": (0.0349, -51.0694),  "BA": (-12.9714, -38.5014), "CE": (-3.7172, -38.5430),
    "DF": (-15.7797, -47.9297), "ES": (-20.3194, -40.3378), "GO": (-16.6869, -49.2648),
    "MA": (-2.5297, -44.3028), "MG": (-19.9191, -43.9386), "MS": (-20.4428, -54.6459),
    "MT": (-15.5989, -56.0949), "PA": (-1.4558, -48.5044), "PB": (-7.1195, -34.8450),
    "PE": (-8.0584, -34.8848), "PI": (-5.0892, -42.8019), "PR": (-25.4195, -49.2647),
    "RJ": (-22.9035, -43.1724), "RN": (-5.7945, -35.2110), "RO": (-8.7612, -63.9004),
    "RR": (2.8235, -60.6758),  "RS": (-30.0368, -51.2090), "SC": (-27.5954, -48.5480),
    "SE": (-10.9472, -37.0731), "SP": (-23.5489, -46.6388), "TO": (-10.2491, -48.3243),
}

# ── Helpers ────────────────────────────────────────────────────────────────

def _clima_3dias(lat: float, lng: float) -> list[dict]:
    hoje = date.today()
    try:
        r = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lng,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "start_date": hoje.isoformat(),
                "end_date": (hoje + timedelta(days=2)).isoformat(),
                "timezone": "America/Sao_Paulo",
            },
            timeout=5.0,
        )
        r.raise_for_status()
        d = r.json()["daily"]
        return [
            {
                "data": d["time"][i],
                "temp_max": d["temperature_2m_max"][i],
                "temp_min": d["temperature_2m_min"][i],
                "precipitacao_mm": d["precipitation_sum"][i],
            }
            for i in range(len(d["time"]))
        ]
    except Exception:
        return []


def _calcular_valor(
    tabela: TabelaPreco,
    peso_kg: float,
    distancia_km: float,
    tipo_frete: str,
    comprimento_cm: float,
    largura_cm: float,
    altura_cm: float,
    veiculo_preco_por_km: Optional[float] = None,
) -> float:
    if veiculo_preco_por_km:
        valor = distancia_km * veiculo_preco_por_km
    elif tabela.modalidade == "fixo_por_km":
        if not tabela.preco_base_km:
            raise HTTPException(422, "Tabela sem preço base por km configurado")
        valor = distancia_km * tabela.preco_base_km
    else:
        faixa = None
        for f in sorted(tabela.faixas, key=lambda x: x.peso_min_kg):
            if peso_kg >= f.peso_min_kg and (f.peso_max_kg is None or peso_kg < f.peso_max_kg):
                faixa = f
                break
        if not faixa:
            raise HTTPException(422, "Peso fora das faixas configuradas na tabela de preços")
        valor = distancia_km * faixa.preco_por_km

    if tipo_frete == "expresso":
        valor *= tabela.multiplicador_expresso

    if tabela.taxa_dimensao_extra and tabela.limite_dimensao_cm:
        if any(d > tabela.limite_dimensao_cm for d in [comprimento_cm, largura_cm, altura_cm]):
            valor += tabela.taxa_dimensao_extra

    return round(valor, 2)


def _veiculo_aceita(v: Veiculo, peso_kg: float, comp: float, larg: float, alt: float) -> bool:
    if peso_kg > v.peso_max_kg:
        return False
    if v.comprimento_max_cm and comp > v.comprimento_max_cm:
        return False
    if v.largura_max_cm and larg > v.largura_max_cm:
        return False
    if v.altura_max_cm and alt > v.altura_max_cm:
        return False
    return True


# ── Schemas ────────────────────────────────────────────────────────────────

class VeiculoCreate(BaseModel):
    nome: str
    tipo: str
    peso_max_kg: float
    comprimento_max_cm: Optional[float] = None
    largura_max_cm: Optional[float] = None
    altura_max_cm: Optional[float] = None
    preco_por_km: Optional[float] = None


class VeiculoUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
    peso_max_kg: Optional[float] = None
    comprimento_max_cm: Optional[float] = None
    largura_max_cm: Optional[float] = None
    altura_max_cm: Optional[float] = None
    preco_por_km: Optional[float] = None


class VeiculoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    peso_max_kg: float
    comprimento_max_cm: Optional[float] = None
    largura_max_cm: Optional[float] = None
    altura_max_cm: Optional[float] = None
    preco_por_km: Optional[float] = None
    ativo: bool
    model_config = {"from_attributes": True}


class FaixaCreate(BaseModel):
    peso_min_kg: float
    peso_max_kg: Optional[float] = None
    preco_por_km: float


class FaixaResponse(BaseModel):
    id: int
    peso_min_kg: float
    peso_max_kg: Optional[float] = None
    preco_por_km: float
    model_config = {"from_attributes": True}


class TabelaCreate(BaseModel):
    modalidade: str
    preco_base_km: Optional[float] = None
    multiplicador_expresso: float = 1.4
    raio_galpao_km: float = 150.0
    taxa_dimensao_extra: Optional[float] = None
    limite_dimensao_cm: Optional[float] = None
    faixas: list[FaixaCreate] = []


class TabelaResponse(BaseModel):
    id: int
    modalidade: str
    preco_base_km: Optional[float] = None
    multiplicador_expresso: float
    raio_galpao_km: float
    taxa_dimensao_extra: Optional[float] = None
    limite_dimensao_cm: Optional[float] = None
    faixas: list[FaixaResponse] = []
    model_config = {"from_attributes": True}


class CotacaoRequest(BaseModel):
    galpao_origem_id: int
    destino_tipo: str  # "galpao" | "endereco"
    galpao_destino_id: Optional[int] = None
    endereco_destino_lat: Optional[float] = None
    endereco_destino_lng: Optional[float] = None
    endereco_destino_cidade: Optional[str] = None
    endereco_destino_estado: Optional[str] = None
    peso_kg: float
    comprimento_cm: float
    largura_cm: float
    altura_cm: float
    tipo_frete: str = "padrao"


class GalpaoRotaItem(BaseModel):
    id: int
    nome: str
    cidade: str
    estado: str


class ClimaDia(BaseModel):
    data: str
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None
    precipitacao_mm: Optional[float] = None


class ResultadoCotacao(BaseModel):
    galpao_origem_id: int
    galpao_origem: dict
    destino_tipo: str
    destino_descricao: str
    estado_origem: str
    estado_destino: str
    peso_kg: float
    comprimento_cm: float
    largura_cm: float
    altura_cm: float
    tipo_frete: str
    distancia_km: float
    duracao_min: Optional[float] = None
    valor_frete: float
    prazo_dias: int
    veiculo_selecionado: Optional[VeiculoResponse] = None
    veiculos_elegiveis: list[VeiculoResponse]
    paradas_intermediarias: list[GalpaoRotaItem]
    clima_resumo: list[ClimaDia]


class SalvarOrcamentoRequest(ResultadoCotacao):
    pass


class OrcamentoResponse(BaseModel):
    id: int
    codigo: str
    galpao_origem_id: Optional[int] = None
    destino_tipo: Optional[str] = None
    destino_descricao: Optional[str] = None
    estado_origem: str
    estado_destino: str
    peso_kg: float
    comprimento_cm: float
    largura_cm: float
    altura_cm: float
    distancia_km: float
    duracao_min: Optional[float] = None
    tipo_frete: str
    valor_frete: float
    prazo_dias: int
    galpoes_rota: Optional[list] = None
    clima_resumo: Optional[list] = None
    status: str
    validade_em: datetime
    criado_em: datetime
    model_config = {"from_attributes": True}


# ── Frota: veículos ────────────────────────────────────────────────────────

@router.post("/frota/veiculos", response_model=VeiculoResponse, status_code=201)
def criar_veiculo(
    body: VeiculoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    v = Veiculo(**body.model_dump(), cliente_id=usuario.cliente_id)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.get("/frota/veiculos", response_model=list[VeiculoResponse])
def listar_veiculos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    return list(db.scalars(
        select(Veiculo)
        .where(Veiculo.cliente_id == usuario.cliente_id, Veiculo.ativo == True)
        .order_by(Veiculo.nome)
    ))


@router.patch("/frota/veiculos/{veiculo_id}", response_model=VeiculoResponse)
def atualizar_veiculo(
    veiculo_id: int,
    body: VeiculoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    v = db.get(Veiculo, veiculo_id)
    if not v or v.cliente_id != usuario.cliente_id:
        raise HTTPException(404, "Veículo não encontrado")
    for k, val in body.model_dump(exclude_unset=True).items():
        setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return v


@router.delete("/frota/veiculos/{veiculo_id}", status_code=204)
def desativar_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    v = db.get(Veiculo, veiculo_id)
    if not v or v.cliente_id != usuario.cliente_id:
        raise HTTPException(404, "Veículo não encontrado")
    v.ativo = False
    db.commit()


# ── Frota: tabela de preços ────────────────────────────────────────────────

@router.post("/frota/tabela-preco", response_model=TabelaResponse, status_code=201)
def salvar_tabela(
    body: TabelaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    # Desativa tabela anterior
    db.execute(
        select(TabelaPreco)
        .where(TabelaPreco.cliente_id == usuario.cliente_id, TabelaPreco.ativo == True)
    )
    antigas = list(db.scalars(
        select(TabelaPreco)
        .where(TabelaPreco.cliente_id == usuario.cliente_id, TabelaPreco.ativo == True)
    ))
    for a in antigas:
        a.ativo = False

    tabela = TabelaPreco(
        cliente_id=usuario.cliente_id,
        modalidade=body.modalidade,
        preco_base_km=body.preco_base_km,
        multiplicador_expresso=body.multiplicador_expresso,
        raio_galpao_km=body.raio_galpao_km,
        taxa_dimensao_extra=body.taxa_dimensao_extra,
        limite_dimensao_cm=body.limite_dimensao_cm,
        ativo=True,
    )
    db.add(tabela)
    db.flush()

    for f in body.faixas:
        db.add(FaixaPreco(tabela_id=tabela.id, **f.model_dump()))

    db.commit()
    db.refresh(tabela)
    return tabela


@router.get("/frota/tabela-preco", response_model=TabelaResponse)
def get_tabela(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    tabela = db.scalars(
        select(TabelaPreco)
        .where(TabelaPreco.cliente_id == usuario.cliente_id, TabelaPreco.ativo == True)
    ).first()
    if not tabela:
        raise HTTPException(404, "Nenhuma tabela de preços configurada")
    return tabela


# ── Cotação ────────────────────────────────────────────────────────────────

@router.post("/cotacao/calcular", response_model=ResultadoCotacao)
def calcular_cotacao(
    body: CotacaoRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    # ── Galpão de origem ────────────────────────────────────────────────────
    galpao_o = db.get(Galpao, body.galpao_origem_id)
    if not galpao_o or not galpao_o.ativo:
        raise HTTPException(404, "Galpão de origem não encontrado")
    if galpao_o.lat is None or galpao_o.lng is None:
        raise HTTPException(422, "Galpão de origem sem coordenadas cadastradas")
    olat, olng = galpao_o.lat, galpao_o.lng
    estado_origem = galpao_o.estado

    # ── Destino ─────────────────────────────────────────────────────────────
    if body.destino_tipo == "galpao":
        if not body.galpao_destino_id:
            raise HTTPException(422, "galpao_destino_id obrigatório quando destino_tipo='galpao'")
        galpao_d = db.get(Galpao, body.galpao_destino_id)
        if not galpao_d or not galpao_d.ativo:
            raise HTTPException(404, "Galpão de destino não encontrado")
        if galpao_d.lat is None or galpao_d.lng is None:
            raise HTTPException(422, "Galpão de destino sem coordenadas cadastradas")
        dlat, dlng = galpao_d.lat, galpao_d.lng
        estado_destino = galpao_d.estado
        destino_descricao = f"{galpao_d.nome} — {galpao_d.cidade}/{galpao_d.estado}"
    elif body.destino_tipo == "retirada":
        if not body.galpao_destino_id:
            raise HTTPException(422, "galpao_destino_id obrigatório quando destino_tipo='retirada'")
        galpao_d = db.get(Galpao, body.galpao_destino_id)
        if not galpao_d or not galpao_d.ativo:
            raise HTTPException(404, "Ponto de retirada não encontrado")
        if not galpao_d.permite_retirada:
            raise HTTPException(422, "Esta unidade não permite retirada pelo cliente")
        if galpao_d.lat is None or galpao_d.lng is None:
            raise HTTPException(422, "Ponto de retirada sem coordenadas cadastradas")
        dlat, dlng = galpao_d.lat, galpao_d.lng
        estado_destino = galpao_d.estado
        destino_descricao = f"{galpao_d.nome} — Retirada pelo cliente"
    else:
        if body.endereco_destino_lat is None or body.endereco_destino_lng is None:
            raise HTTPException(422, "Coordenadas do endereço de destino são obrigatórias")
        dlat, dlng = body.endereco_destino_lat, body.endereco_destino_lng
        estado_destino = body.endereco_destino_estado or "??"
        partes = [p for p in [body.endereco_destino_cidade, body.endereco_destino_estado] if p]
        destino_descricao = " / ".join(partes) if partes else "Endereço do cliente"

    tabela = db.scalars(
        select(TabelaPreco)
        .where(TabelaPreco.cliente_id == usuario.cliente_id, TabelaPreco.ativo == True)
    ).first()
    if not tabela:
        raise HTTPException(422, "Configure uma tabela de preços antes de cotar")

    rota = obter_rota(olat, olng, dlat, dlng)
    distancia_km: float = rota["distancia_km"]
    duracao_min: Optional[float] = rota["duracao_min"]

    # Hubs/centros logísticos próximos ao ponto médio da rota
    todos_galpoes = list(db.scalars(select(Galpao).where(Galpao.ativo == True)))
    mid_lat = (olat + dlat) / 2
    mid_lng = (olng + dlng) / 2
    excluir_ids = {galpao_o.id}
    if body.destino_tipo in ("galpao", "retirada") and body.galpao_destino_id:
        excluir_ids.add(body.galpao_destino_id)
    paradas_intermediarias = [
        g for g in todos_galpoes
        if g.id not in excluir_ids
        and g.lat is not None and g.lng is not None
        and g.tipo in ("hub", "centro_logistico")
        and haversine_km(g.lat, g.lng, mid_lat, mid_lng) <= tabela.raio_galpao_km
    ]

    veiculos = list(db.scalars(
        select(Veiculo)
        .where(Veiculo.cliente_id == usuario.cliente_id, Veiculo.ativo == True)
    ))
    elegiveis = [
        v for v in veiculos
        if _veiculo_aceita(v, body.peso_kg, body.comprimento_cm, body.largura_cm, body.altura_cm)
    ]
    # Ordena por preco_por_km asc, nulls por último
    elegiveis_sorted = sorted(
        elegiveis,
        key=lambda v: (v.preco_por_km is None, v.preco_por_km or 0.0),
    )
    veiculo_calc = elegiveis_sorted[0] if elegiveis_sorted else None

    valor_frete = _calcular_valor(
        tabela, body.peso_kg, distancia_km, body.tipo_frete,
        body.comprimento_cm, body.largura_cm, body.altura_cm,
        veiculo_preco_por_km=veiculo_calc.preco_por_km if veiculo_calc else None,
    )

    prazo_dias = max(1, math.ceil((duracao_min or distancia_km * 1.5) / 60 / 8))
    prazo_dias += len(paradas_intermediarias)  # +1 dia útil por parada intermediária
    clima = _clima_3dias(dlat, dlng)

    return ResultadoCotacao(
        galpao_origem_id=galpao_o.id,
        galpao_origem={"id": galpao_o.id, "nome": galpao_o.nome, "cidade": galpao_o.cidade, "estado": galpao_o.estado},
        destino_tipo=body.destino_tipo,
        destino_descricao=destino_descricao,
        estado_origem=estado_origem,
        estado_destino=estado_destino,
        peso_kg=body.peso_kg,
        comprimento_cm=body.comprimento_cm,
        largura_cm=body.largura_cm,
        altura_cm=body.altura_cm,
        tipo_frete=body.tipo_frete,
        distancia_km=round(distancia_km, 2),
        duracao_min=round(duracao_min, 1) if duracao_min else None,
        valor_frete=valor_frete,
        prazo_dias=prazo_dias,
        veiculo_selecionado=VeiculoResponse.model_validate(veiculo_calc) if veiculo_calc else None,
        veiculos_elegiveis=[VeiculoResponse.model_validate(v) for v in elegiveis_sorted],
        paradas_intermediarias=[GalpaoRotaItem(id=g.id, nome=g.nome, cidade=g.cidade, estado=g.estado)
                                for g in paradas_intermediarias],
        clima_resumo=[ClimaDia(**c) for c in clima],
    )


@router.post("/cotacao/salvar", response_model=OrcamentoResponse, status_code=201)
def salvar_orcamento(
    body: SalvarOrcamentoRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    veiculo_id = body.veiculos_elegiveis[0].id if body.veiculos_elegiveis else None
    orcamento = Orcamento(
        codigo=f"ORC-{uuid.uuid4().hex[:8].upper()}",
        cliente_id=usuario.cliente_id,
        galpao_origem_id=body.galpao_origem_id,
        destino_tipo=body.destino_tipo,
        destino_descricao=body.destino_descricao,
        estado_origem=body.estado_origem,
        estado_destino=body.estado_destino,
        peso_kg=body.peso_kg,
        comprimento_cm=body.comprimento_cm,
        largura_cm=body.largura_cm,
        altura_cm=body.altura_cm,
        distancia_km=body.distancia_km,
        duracao_min=body.duracao_min,
        veiculo_id=veiculo_id,
        tipo_frete=body.tipo_frete,
        valor_frete=body.valor_frete,
        prazo_dias=body.prazo_dias,
        galpoes_rota=[g.model_dump() for g in body.paradas_intermediarias],
        clima_resumo=[c.model_dump() for c in body.clima_resumo],
        status="rascunho",
        validade_em=datetime.now(tz=timezone.utc) + timedelta(days=3),
    )
    db.add(orcamento)
    db.commit()
    db.refresh(orcamento)
    return orcamento


@router.get("/cotacao/pontos-retirada", response_model=list[GalpaoRotaItem])
def listar_pontos_retirada(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requer_empresa),
):
    galpoes = list(db.scalars(
        select(Galpao).where(Galpao.ativo == True, Galpao.permite_retirada == True)
    ))
    return [GalpaoRotaItem(id=g.id, nome=g.nome, cidade=g.cidade, estado=g.estado) for g in galpoes]


@router.delete("/cotacao/orcamentos/{orc_id}", status_code=204)
def deletar_orcamento(
    orc_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    orc = db.get(Orcamento, orc_id)
    if not orc or orc.cliente_id != usuario.cliente_id:
        raise HTTPException(404, "Orçamento não encontrado")
    if orc.status == "aprovado":
        raise HTTPException(422, "Orçamento aprovado não pode ser removido")
    if orc.status not in ("rascunho", "expirado"):
        raise HTTPException(422, f"Orçamento com status '{orc.status}' não pode ser removido")
    db.delete(orc)
    db.commit()


@router.get("/cotacao/orcamentos", response_model=list[OrcamentoResponse])
def listar_orcamentos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    return list(db.scalars(
        select(Orcamento)
        .where(Orcamento.cliente_id == usuario.cliente_id)
        .order_by(Orcamento.criado_em.desc())
    ))


@router.get("/cotacao/orcamentos/{orc_id}", response_model=OrcamentoResponse)
def detalhar_orcamento(
    orc_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    orc = db.get(Orcamento, orc_id)
    if not orc or orc.cliente_id != usuario.cliente_id:
        raise HTTPException(404, "Orçamento não encontrado")
    return orc


@router.patch("/cotacao/orcamentos/{orc_id}/aprovar", response_model=OrcamentoResponse)
def aprovar_orcamento(
    orc_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requer_empresa),
):
    orc = db.get(Orcamento, orc_id)
    if not orc or orc.cliente_id != usuario.cliente_id:
        raise HTTPException(404, "Orçamento não encontrado")
    if orc.status not in ("rascunho", "enviado"):
        raise HTTPException(422, f"Orçamento com status '{orc.status}' não pode ser aprovado")

    now = datetime.now(tz=timezone.utc)
    dados_entrega = {
        "data_pedido": now.isoformat(),
        "data_prevista": (now + timedelta(days=orc.prazo_dias)).isoformat(),
        "peso_g": orc.peso_kg * 1000,
        "valor": orc.valor_frete,
        "frete": orc.valor_frete,
        "estado_origem": orc.estado_origem,
        "estado_destino": orc.estado_destino,
        "distancia_km": orc.distancia_km,
    }
    entrega_service.criar(db, dados_entrega, cliente_id=usuario.cliente_id)

    orc.status = "aprovado"
    db.commit()
    db.refresh(orc)
    return orc
