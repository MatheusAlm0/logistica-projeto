import { isAxiosError } from "axios"

interface ValidationIssue {
  loc?: (string | number)[]
  msg?: string
}

const SEM_CONEXAO = "Não foi possível conectar ao servidor"

function formatIssue(issue: unknown): string | null {
  if (typeof issue === "string") return issue
  if (!issue || typeof issue !== "object") return null
  const { loc, msg } = issue as ValidationIssue
  if (!msg) return null
  // loc vem como ["body", "campo", ...] — descarta a origem e mantém o caminho do campo
  const campo = Array.isArray(loc)
    ? loc.filter((p) => p !== "body" && p !== "query" && p !== "path").join(".")
    : ""
  return campo ? `${campo}: ${msg}` : msg
}

/** Extrai o `detail` de uma resposta de erro da API (string ou lista de validação do FastAPI). */
export function getErrorDetail(err: unknown): string | null {
  if (!isAxiosError(err)) return null
  const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    const msgs = detail.map(formatIssue).filter((m): m is string => !!m)
    return msgs.length ? msgs.join("; ") : null
  }
  return null
}

/** Converte qualquer erro em uma mensagem amigável (sempre uma string, segura para renderizar). */
export function getErrorMessage(err: unknown, fallback: string): string {
  if (isAxiosError(err) && !err.response) return SEM_CONEXAO
  return getErrorDetail(err) ?? fallback
}

/** Status HTTP da resposta de erro, se houver. */
export function getErrorStatus(err: unknown): number | undefined {
  return isAxiosError(err) ? err.response?.status : undefined
}
