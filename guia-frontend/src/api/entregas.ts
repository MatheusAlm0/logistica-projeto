import api from "./axios"
import type { Entrega, EntregaCreate, CheckpointResponse } from "@/types"

export interface EntregasParams {
  status?: string
  estado_destino?: string
  limit?: number
  offset?: number
}

export async function getEntregas(params?: EntregasParams): Promise<Entrega[]> {
  const { data } = await api.get<{ total: number; items: Entrega[] }>("/entregas", { params })
  return Array.isArray(data) ? data : (data.items ?? [])
}

export async function getEntrega(id: number): Promise<Entrega> {
  const { data } = await api.get<Entrega>(`/entregas/${id}`)
  return data
}

export async function createEntrega(payload: EntregaCreate): Promise<Entrega> {
  const { data } = await api.post<Entrega>("/entregas", payload)
  return data
}

export async function finalizarEntrega(id: number, data_entregue: string): Promise<Entrega> {
  const { data } = await api.patch<Entrega>(`/entregas/${id}/finalizar`, { data_entregue })
  return data
}

export async function getCheckpoints(entregaId: number): Promise<CheckpointResponse[]> {
  const { data } = await api.get<CheckpointResponse[]>(`/entregas/${entregaId}/checkpoints`)
  return data
}

export async function createCheckpoint(
  entregaId: number,
  galpaoId: number,
  observacao?: string
): Promise<CheckpointResponse> {
  const { data } = await api.post<CheckpointResponse>(`/entregas/${entregaId}/checkpoints`, {
    galpao_id: galpaoId,
    observacao,
  })
  return data
}

export async function deletarEntrega(id: number): Promise<void> {
  await api.delete(`/entregas/${id}`)
}

export async function editarEntrega(
  id: number,
  body: { data_prevista?: string; peso_g?: number; valor?: number; frete?: number }
): Promise<Entrega> {
  const { data } = await api.patch<Entrega>(`/entregas/${id}/editar`, body)
  return data
}

export async function atualizarStatus(id: number, status: string): Promise<Entrega> {
  const { data } = await api.patch<Entrega>(`/entregas/${id}/status`, { status })
  return data
}
