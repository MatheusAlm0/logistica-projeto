import { useState, useCallback } from "react"
import { getGalpoes, createGalpao } from "@/api/galpoes"
import type { Galpao, GalpaoCreate } from "@/types"
import { toast } from "@/hooks/use-toast"

export function useGalpoes() {
  const [galpoes, setGalpoes] = useState<Galpao[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const fetch = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await getGalpoes()
      setGalpoes(data)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const criar = useCallback(async (payload: GalpaoCreate) => {
    try {
      const g = await createGalpao(payload)
      setGalpoes((prev) => [...prev, g])
      toast({ title: "Galpão criado", description: g.nome })
      return g
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Erro ao criar galpão"
      toast({ title: "Erro", description: msg, variant: "destructive" })
      throw err
    }
  }, [])

  return { galpoes, isLoading, fetch, criar }
}
