import { useState, useEffect, KeyboardEvent } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { getRastreio } from "@/api/rastreio"
import type { RastreioData } from "@/types"
import StatusBadge from "@/components/StatusBadge"
import MapaRastreio from "@/components/MapaRastreio"
import Timeline from "@/components/Timeline"
import ThemeToggle from "@/components/ThemeToggle"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search } from "lucide-react"

function fmtDate(iso?: string) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("pt-BR")
}

export default function RastreioPage() {
  const { codigo } = useParams<{ codigo: string }>()
  const navigate = useNavigate()
  const [query, setQuery] = useState(codigo ?? "")
  const [data, setData] = useState<RastreioData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (codigo) search(codigo)
  }, [codigo])  // eslint-disable-line react-hooks/exhaustive-deps

  async function search(code: string) {
    const trimmed = code.trim().toUpperCase()
    if (!trimmed) return
    setIsLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await getRastreio(trimmed)
      setData(result)
      if (trimmed !== codigo) navigate(`/rastreio/${trimmed}`, { replace: true })
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status
      setError(status === 404 ? "Código de rastreio não encontrado." : "Erro ao buscar. Tente novamente.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") search(query)
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <a href="/rastreio" className="text-xl font-bold text-primary tracking-tight">guIA</a>
          <div className="flex items-center gap-2">
            <a href="/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Área restrita
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-10">
        {/* Search */}
        <div className="flex flex-col items-center gap-3 mb-10">
          <h2 className="text-2xl font-semibold">Rastrear entrega</h2>
          <p className="text-muted-foreground text-sm">Digite o código de rastreio da sua encomenda</p>
          <div className="flex gap-2 w-full max-w-md mt-2">
            <Input
              placeholder="Ex: TRK-A1B2C3D4"
              value={query}
              onChange={(e) => setQuery(e.target.value.toUpperCase())}
              onKeyDown={handleKey}
              className="font-mono uppercase"
            />
            <Button onClick={() => search(query)} disabled={isLoading}>
              <Search size={16} />
              {isLoading ? "..." : "Buscar"}
            </Button>
          </div>
          {error && (
            <p className="text-destructive text-sm">{error}</p>
          )}
        </div>

        {/* Results */}
        {data && (
          <div className="space-y-6">
            {/* Status card */}
            <div className="bg-card rounded-xl border p-6">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Código</p>
                  <p className="font-mono text-lg font-bold">{data.codigo_rastreio ?? "—"}</p>
                </div>
                <StatusBadge status={data.status} />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 text-sm">
                <div>
                  <p className="text-muted-foreground text-xs">Origem</p>
                  <p className="font-medium">{data.estado_origem ?? "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Destino</p>
                  <p className="font-medium">{data.estado_destino ?? "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Previsão</p>
                  <p className="font-medium">{fmtDate(data.data_prevista_revisada ?? data.data_prevista)}</p>
                </div>
                {data.data_entregue && (
                  <div>
                    <p className="text-muted-foreground text-xs">Entregue em</p>
                    <p className="font-medium">{fmtDate(data.data_entregue)}</p>
                  </div>
                )}
              </div>
              {data.ultima_previsao && (
                <p className="text-xs text-muted-foreground mt-3">
                  Risco de atraso: <span className="font-medium">{data.ultima_previsao.nivel}</span>{" "}
                  ({(data.ultima_previsao.probabilidade * 100).toFixed(0)}%)
                </p>
              )}
            </div>

            {/* Map */}
            {(data.checkpoints.length > 0 || data.estado_origem || data.estado_destino) && (
              <MapaRastreio rastreio={data} />
            )}

            {/* Timeline */}
            <Timeline checkpoints={data.checkpoints} />
          </div>
        )}
      </main>
    </div>
  )
}
