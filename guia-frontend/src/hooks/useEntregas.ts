import { useState, useCallback } from "react"
import { getEntregas, createEntrega, finalizarEntrega, createCheckpoint } from "@/api/entregas"
import type { Entrega, EntregaCreate } from "@/types"
import { toast } from "@/hooks/use-toast"
import { getErrorMessage } from "@/lib/errors"
import { toLocalISOString } from "@/lib/utils"

export function useEntregas() {
  const [entregas, setEntregas] = useState<Entrega[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchEntregas = useCallback(async (params?: { status?: string }) => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await getEntregas({ ...params, limit: 200 })
      setEntregas(data)
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erro ao carregar entregas"))
    } finally {
      setIsLoading(false)
    }
  }, [])

  /**
   * Cria a entrega e, opcionalmente, registra checkpoints adicionais (galpaoIds).
   * Os hubs planejados enviados em `payload.hubs_planejados` são registrados pelo backend.
   */
  const criar = useCallback(async (payload: EntregaCreate, galpaoIds: number[] = []) => {
    setIsLoading(true)
    try {
      const entrega = await createEntrega(payload)
      const falhas: string[] = []
      for (const gid of galpaoIds) {
        try {
          await createCheckpoint(entrega.id, { galpao_id: gid, chegou_em: toLocalISOString() })
        } catch (err: unknown) {
          falhas.push(getErrorMessage(err, `galpão ${gid}`))
        }
      }
      toast({ title: "Entrega criada", description: `Código: ${entrega.codigo_rastreio ?? `#${entrega.id}`}` })
      if (falhas.length) {
        toast({
          title: `Falha ao registrar ${falhas.length} checkpoint(s)`,
          description: falhas.join(" | "),
          variant: "destructive",
        })
      }
      setEntregas((prev) => [entrega, ...prev])
      return entrega
    } catch (err: unknown) {
      toast({ title: "Erro", description: getErrorMessage(err, "Erro ao criar entrega"), variant: "destructive" })
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const finalizar = useCallback(async (id: number, dataEntregue: string) => {
    try {
      const updated = await finalizarEntrega(id, dataEntregue)
      setEntregas((prev) => prev.map((e) => (e.id === id ? updated : e)))
      toast({ title: "Entrega finalizada com sucesso" })
      return updated
    } catch (err: unknown) {
      toast({ title: "Erro", description: getErrorMessage(err, "Erro ao finalizar"), variant: "destructive" })
      throw err
    }
  }, [])

  return { entregas, isLoading, error, fetchEntregas, criar, finalizar }
}
