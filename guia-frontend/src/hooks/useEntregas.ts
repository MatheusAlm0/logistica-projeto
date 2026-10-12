import { useState, useCallback } from "react"
import { getEntregas, createEntrega, finalizarEntrega, createCheckpoint } from "@/api/entregas"
import type { Entrega, EntregaCreate } from "@/types"
import { toast } from "@/hooks/use-toast"

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
    } catch {
      setError("Erro ao carregar entregas")
    } finally {
      setIsLoading(false)
    }
  }, [])

  const criar = useCallback(async (payload: EntregaCreate, galpaoIds: number[] = []) => {
    setIsLoading(true)
    try {
      const entrega = await createEntrega(payload)
      for (const gid of galpaoIds) {
        try { await createCheckpoint(entrega.id, gid) } catch { /* best effort */ }
      }
      toast({ title: "Entrega criada", description: `Código: ${entrega.codigo_rastreio}` })
      setEntregas((prev) => [entrega, ...prev])
      return entrega
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Erro ao criar entrega"
      toast({ title: "Erro", description: msg, variant: "destructive" })
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
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Erro ao finalizar"
      toast({ title: "Erro", description: msg, variant: "destructive" })
      throw err
    }
  }, [])

  return { entregas, isLoading, error, fetchEntregas, criar, finalizar }
}
