import api from "./axios"
import type { User, TokenResponse } from "@/types"

export async function apiLogin(email: string, senha: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", { email, senha })
  return data
}

export async function apiMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me")
  return data
}
