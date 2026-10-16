import api from "./axios"
import type { RetreinoListResponse, DispararRetreinoResponse, HealthCheck } from "@/types"

export interface RetreinesParams {
  status?: string
  limit?: number
  offset?: number
}

export async function getRetreinos(params?: RetreinesParams): Promise<RetreinoListResponse> {
  const { data } = await api.get<RetreinoListResponse>("/retreinos", { params })
  return data
}

export async function dispararRetreino(): Promise<DispararRetreinoResponse> {
  const { data } = await api.post<DispararRetreinoResponse>("/retreinos/disparar")
  return data
}

export async function getHealthCheck(): Promise<HealthCheck> {
  const { data } = await api.get<HealthCheck>("/health")
  return data
}
