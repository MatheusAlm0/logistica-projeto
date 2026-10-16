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

export interface Previsao {
  id: number
  nivel: string
  probabilidade: number
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

export interface Entrega {
  id: number
  peso_g: number
  valor_reais: number
  frete_reais: number
  estado_origem?: string
  estado_destino?: string
  data_pedido: string
  data_prevista: string
  data_entregue?: string
  data_prevista_revisada?: string
  status: StatusEntrega
  codigo_rastreio?: string
  cliente_id?: string
  ultima_previsao?: Previsao
}

export interface EntregaCreate {
  peso_g: number
  valor_reais: number
  frete_reais: number
  estado_origem?: string
  estado_destino?: string
  data_pedido: string
  data_prevista: string
  distancia_km?: number
  hubs_planejados?: number[]
}

export interface RastreioData {
  id: number
  codigo_rastreio?: string
  status: StatusEntrega
  estado_origem?: string
  estado_destino?: string
  data_pedido: string
  data_prevista: string
  data_entregue?: string
  data_prevista_revisada?: string
  ultima_previsao?: Previsao
  checkpoints: CheckpointResponse[]
}

export interface Retreino {
  id: number
  status: string
  iniciado_em: string
  finalizado_em?: string
  duracao_s?: number
  modelo_arquivo?: string
  roc_auc?: number
  pr_auc?: number
  amostras?: number
  erro?: string
}

export interface DispararRetreinoResponse {
  mensagem: string
  link: string
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
