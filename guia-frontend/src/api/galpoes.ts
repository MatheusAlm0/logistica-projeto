import api from "./axios"
import type { Galpao, GalpaoCreate } from "@/types"

export async function getGalpoes(): Promise<Galpao[]> {
  const { data } = await api.get<Galpao[]>("/galpoes")
  return data
}

export async function createGalpao(payload: GalpaoCreate): Promise<Galpao> {
  const { data } = await api.post<Galpao>("/galpoes", payload)
  return data
}
