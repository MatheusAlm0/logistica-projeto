import api from "./axios"
import type { RastreioData } from "@/types"

export async function getRastreio(codigo: string): Promise<RastreioData> {
  const { data } = await api.get<RastreioData>(`/rastreio/${codigo}`)
  return data
}
