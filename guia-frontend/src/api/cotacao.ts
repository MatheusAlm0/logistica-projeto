import api from "./axios"
import type { Veiculo, TabelaPreco, Orcamento, ResultadoCotacao, CotacaoRequest, GalpaoRota } from "@/types"

// ── Frota ──────────────────────────────────────────────────────────────────

export async function getVeiculos(): Promise<Veiculo[]> {
  const { data } = await api.get<Veiculo[]>("/frota/veiculos")
  return data
}

export async function createVeiculo(
  payload: Omit<Veiculo, "id" | "ativo">
): Promise<Veiculo> {
  const { data } = await api.post<Veiculo>("/frota/veiculos", payload)
  return data
}

export async function updateVeiculo(
  id: number,
  payload: Partial<Omit<Veiculo, "id" | "ativo">>
): Promise<Veiculo> {
  const { data } = await api.patch<Veiculo>(`/frota/veiculos/${id}`, payload)
  return data
}

export async function deleteVeiculo(id: number): Promise<void> {
  await api.delete(`/frota/veiculos/${id}`)
}

// ── Tabela de preço ────────────────────────────────────────────────────────

export async function getTabelaPreco(): Promise<TabelaPreco> {
  const { data } = await api.get<TabelaPreco>("/frota/tabela-preco")
  return data
}

export async function saveTabelaPreco(
  payload: Omit<TabelaPreco, "id">
): Promise<TabelaPreco> {
  const { data } = await api.post<TabelaPreco>("/frota/tabela-preco", payload)
  return data
}

// ── Cotação ────────────────────────────────────────────────────────────────

export async function calcularCotacao(
  payload: CotacaoRequest
): Promise<ResultadoCotacao> {
  const { data } = await api.post<ResultadoCotacao>("/cotacao/calcular", payload)
  return data
}

export async function salvarOrcamento(
  resultado: ResultadoCotacao
): Promise<Orcamento> {
  const { data } = await api.post<Orcamento>("/cotacao/salvar", resultado)
  return data
}

export async function getOrcamentos(): Promise<Orcamento[]> {
  const { data } = await api.get<Orcamento[]>("/cotacao/orcamentos")
  return data
}

export async function getOrcamento(id: number): Promise<Orcamento> {
  const { data } = await api.get<Orcamento>(`/cotacao/orcamentos/${id}`)
  return data
}

export async function aprovarOrcamento(id: number): Promise<Orcamento> {
  const { data } = await api.patch<Orcamento>(`/cotacao/orcamentos/${id}/aprovar`)
  return data
}

export async function deletarOrcamento(id: number): Promise<void> {
  await api.delete(`/cotacao/orcamentos/${id}`)
}

export async function getPontosRetirada(): Promise<GalpaoRota[]> {
  const { data } = await api.get<GalpaoRota[]>("/cotacao/pontos-retirada")
  return data
}
