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
  ativo: boolean
}

export interface GalpaoCreate {
  nome: string
  cidade: string
  estado: string
  lat?: number
  lng?: number
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
