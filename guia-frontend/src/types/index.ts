export type UserRole = "admin" | "empresa" | "usuario_final"

export interface User {
  id: number
  email: string
  nome: string
  role: UserRole
  cliente_id: string
  ativo: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export type StatusEntrega = "pendente" | "em_transito" | "entregue" | "atrasada" | "cancelado"

// Espelha PrevisaoEmbutida (app/schema/entrega.py)
export interface Previsao {
  id: number
  nivel: string
  probabilidade: number
  modelo_versao: string
  chuva_mm?: number | null
  rota_fonte?: string | null
  criado_em: string
}

export interface Galpao {
  id: number
  nome: string
  cidade: string
  estado: string
  lat?: number
  lng?: number
  tipo?: string
  permite_retirada?: boolean
  ativo: boolean
}

export interface GalpaoCreate {
  nome: string
  cidade: string
  estado: string
  lat?: number
  lng?: number
  tipo?: string
  permite_retirada?: boolean
}

export interface CheckpointResponse {
  id: number
  entrega_id: number
  galpao: Galpao
  chegou_em: string
  observacao?: string
}

// Espelha EntregaResponse (app/schema/entrega.py)
export interface Entrega {
  id: number
  criado_em: string
  data_pedido: string
  data_prevista: string
  data_entregue?: string
  peso_g: number
  valor: number
  frete: number
  estado_origem?: string
  estado_destino?: string
  distancia_km?: number
  status: StatusEntrega
  codigo_rastreio?: string
  ultima_previsao?: Previsao
}

// Espelha EntregaCriadaResponse — resposta do POST /entregas
export interface EntregaCriada extends Entrega {
  previsao?: Record<string, unknown> | null
}

export interface EntregaListResponse {
  total: number
  items: Entrega[]
}

// Espelha EntregaCreate + hubs_planejados (EntregaCreateWithHubs no controller).
// Datas sem fuso: o backend grava timestamp sem timezone (horário local).
export interface EntregaCreate {
  data_pedido: string
  data_prevista: string
  peso_g: number
  valor: number
  frete: number
  estado_origem?: string
  estado_destino?: string
  distancia_km?: number
  origem_lat?: number
  origem_lng?: number
  destino_lat?: number
  destino_lng?: number
  hubs_planejados?: number[]
}

// Espelha EditarEntregaRequest (PATCH /entregas/{id}/editar)
export interface EntregaEditar {
  data_prevista?: string
  peso_g?: number
  valor?: number
  frete?: number
}

// Espelha CheckpointCreate (app/schema/checkpoint.py)
export interface CheckpointCreate {
  galpao_id: number
  chegou_em: string
  observacao?: string
}

// Espelha o schema público de rastreio (app/schema/rastreio.py): sem ids,
// observações, autor do registro nem dados do modelo — só o nível de risco.
// CheckpointResponse (rota autenticada) também é compatível com RastreioCheckpoint.
export interface RastreioGalpao {
  nome: string
  cidade: string
  estado: string
  lat?: number | null
  lng?: number | null
}

export interface RastreioCheckpoint {
  chegou_em: string
  galpao: RastreioGalpao | null
}

export interface RastreioData {
  codigo_rastreio?: string
  status: StatusEntrega
  estado_origem?: string | null
  estado_destino?: string | null
  data_prevista?: string | null
  data_prevista_revisada?: string | null
  data_entregue?: string | null
  nivel_risco?: string | null
  checkpoints: RastreioCheckpoint[]
}

// Espelha RetreinoResponse (app/schema/retreino.py)
export interface Retreino {
  id: number
  status: string           // rodando | ok | erro
  iniciado_em: string
  concluido_em?: string | null
  duracao_segundos?: number | null
  versao?: string | null
  roc_auc?: number | null
  pr_auc?: number | null
  n_amostras?: number | null
  erro?: string | null
}

// Espelha RetreinoListResponse
export interface RetreinoListResponse {
  total: number
  pendentes: number
  items: Retreino[]
}

// Resposta de POST /retreinos/disparar
export interface DispararRetreinoResponse {
  mensagem: string
  acompanhe: string
}

// Resposta de GET /health
export interface HealthCheck {
  status: string
  modelo: string
}

// ── Cotação ────────────────────────────────────────────────────────────────

export type TipoVeiculo = "furgao" | "van" | "caminhao_leve" | "caminhao_pesado" | "carreta"

export interface Veiculo {
  id: number
  nome: string
  tipo: TipoVeiculo
  peso_max_kg: number
  comprimento_max_cm?: number
  largura_max_cm?: number
  altura_max_cm?: number
  preco_por_km?: number
  ativo: boolean
}

export interface FaixaPreco {
  id?: number
  peso_min_kg: number
  peso_max_kg?: number
  preco_por_km: number
}

export interface TabelaPreco {
  id?: number
  modalidade: "fixo_por_km" | "faixa_peso_volume"
  preco_base_km?: number
  multiplicador_expresso: number
  raio_galpao_km: number
  taxa_dimensao_extra?: number
  limite_dimensao_cm?: number
  faixas: FaixaPreco[]
}

export interface ClimaDia {
  data: string
  temp_max?: number
  temp_min?: number
  precipitacao_mm?: number
}

export interface GalpaoRota {
  id: number
  nome: string
  cidade: string
  estado: string
}

export interface ResultadoCotacao {
  galpao_origem_id: number
  galpao_origem: GalpaoInfo
  destino_tipo: "galpao" | "endereco" | "retirada"
  destino_descricao: string
  estado_origem: string
  estado_destino: string
  peso_kg: number
  comprimento_cm: number
  largura_cm: number
  altura_cm: number
  tipo_frete: "padrao" | "expresso"
  distancia_km: number
  duracao_min?: number
  valor_frete: number
  prazo_dias: number
  veiculo_selecionado?: Veiculo
  veiculos_elegiveis: Veiculo[]
  paradas_intermediarias: GalpaoRota[]
  clima_resumo: ClimaDia[]
}

export interface GalpaoInfo {
  id: number
  nome: string
  cidade: string
  estado: string
}

export interface CotacaoRequest {
  galpao_origem_id: number
  destino_tipo: "galpao" | "endereco" | "retirada"
  galpao_destino_id?: number
  endereco_destino_lat?: number
  endereco_destino_lng?: number
  endereco_destino_cidade?: string
  endereco_destino_estado?: string
  peso_kg: number
  comprimento_cm: number
  largura_cm: number
  altura_cm: number
  tipo_frete: "padrao" | "expresso"
}

export interface Orcamento {
  id: number
  codigo: string
  galpao_origem_id?: number
  destino_tipo?: string
  destino_descricao?: string
  estado_origem: string
  estado_destino: string
  peso_kg: number
  comprimento_cm: number
  largura_cm: number
  altura_cm: number
  distancia_km: number
  duracao_min?: number
  tipo_frete: "padrao" | "expresso"
  valor_frete: number
  prazo_dias: number
  galpoes_rota?: GalpaoRota[]
  clima_resumo?: ClimaDia[]
  status: "rascunho" | "enviado" | "aprovado" | "expirado"
  validade_em: string
  criado_em: string
}
