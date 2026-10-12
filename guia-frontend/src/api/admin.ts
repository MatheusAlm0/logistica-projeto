import api from "./axios"
import type { User } from "@/types"

export async function getEmpresasPendentes(): Promise<User[]> {
  const { data } = await api.get<User[]>("/admin/empresas/pendentes")
  return data
}

export async function aprovarEmpresa(id: number): Promise<User> {
  const { data } = await api.patch<User>(`/admin/empresas/${id}/aprovar`)
  return data
}

export async function bloquearEmpresa(id: number): Promise<User> {
  const { data } = await api.patch<User>(`/admin/empresas/${id}/bloquear`)
  return data
}
