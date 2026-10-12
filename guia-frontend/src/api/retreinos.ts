import api from "./axios"
import type { Retreino, DispararRetreinoResponse } from "@/types"

export interface RetreinesParams {
  status?: string
  limit?: number
  offset?: number
}

export async function getRetreinos(params?: RetreinesParams): Promise<Retreino[]> {
  const { data } = await api.get<Retreino[]>("/retreinos", { params })
  return data
}

export async function dispararRetreino(): Promise<DispararRetreinoResponse> {
  const { data } = await api.post<DispararRetreinoResponse>("/retreinos/disparar")
  return data
}

export async function getHealthCheck(): Promise<{ status: string; modelo: string }> {
  const { data } = await api.get<{ status: string; modelo: string }>("/health")
  return data
}
