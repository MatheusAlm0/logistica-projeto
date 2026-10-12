import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { getEntrega, getCheckpoints, finalizarEntrega } from "@/api/entregas"
import type { Entrega, CheckpointResponse } from "@/types"
import StatusBadge from "@/components/StatusBadge"
import Timeline from "@/components/Timeline"
import MapaRastreio from "@/components/MapaRastreio"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "@/hooks/use-toast"
import { ArrowLeft, ExternalLink } from "lucide-react"

function fmtDate(iso?: string) {
  if (!iso) return "—"
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
}

export default function EntregaDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [entrega, setEntrega] = useState<Entrega | null>(null)
  const [checkpoints, setCheckpoints] = useState<CheckpointResponse[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [finalizando, setFinalizando] = useState(false)

  useEffect(() => {
    if (!id) return
    const idNum = parseInt(id)
    Promise.all([getEntrega(idNum), getCheckpoints(idNum)])
      .then(([e, cps]) => { setEntrega(e); setCheckpoints(cps) })
      .catch(() => toast({ title: "Erro ao carregar entrega", variant: "destructive" }))
      .finally(() => setIsLoading(false))
  }, [id])

  async function handleFinalizar() {
    if (!entrega) return
    setFinalizando(true)
    try {
      const updated = await finalizarEntrega(entrega.id, new Date().toISOString())
      setEntrega(updated)
      toast({ title: "Entrega finalizada" })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Erro ao finalizar"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally {
      setFinalizando(false)
    }
  }

  if (isLoading) {
    return <div className="text-center py-12 text-muted-foreground animate-pulse">Carregando...</div>
  }

  if (!entrega) {
    return <div className="text-center py-12 text-muted-foreground">Entrega não encontrada.</div>
  }

  const canFinalizar = ["pendente", "em_transito", "atrasada"].includes(entrega.status)
  const rastreioData = {
    ...entrega,
    checkpoints,
    codigo_rastreio: entrega.codigo_rastreio,
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate("/dashboard/entregas")}>
          <ArrowLeft size={18} />
        </Button>
        <h1 className="text-xl font-semibold">Detalhe da entrega</h1>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Código de rastreio</p>
            <p className="font-mono text-xl font-bold">{entrega.codigo_rastreio ?? `#${entrega.id}`}</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <StatusBadge status={entrega.status} />
            {entrega.codigo_rastreio && (
              <a href={`/rastreio/${entrega.codigo_rastreio}`} target="_blank" rel="noopener">
                <Button size="sm" variant="outline">
                  <ExternalLink size={14} />
                  Rastrear
                </Button>
              </a>
            )}
            {canFinalizar && (
              <Button size="sm" onClick={handleFinalizar} disabled={finalizando}>
                {finalizando ? "Finalizando..." : "Finalizar entrega"}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            {[
              ["Origem", entrega.estado_origem],
              ["Destino", entrega.estado_destino],
              ["Peso", entrega.peso_g ? `${entrega.peso_g} g` : undefined],
              ["Valor", entrega.valor_reais ? `R$ ${entrega.valor_reais.toFixed(2)}` : undefined],
              ["Frete", entrega.frete_reais ? `R$ ${entrega.frete_reais.toFixed(2)}` : undefined],
              ["Pedido em", fmtDate(entrega.data_pedido)],
              ["Previsão", fmtDate(entrega.data_prevista_revisada ?? entrega.data_prevista)],
              ...(entrega.data_entregue ? [["Entregue em", fmtDate(entrega.data_entregue)]] : []),
            ].map(([label, value]) => (
              <div key={String(label)}>
                <p className="text-muted-foreground text-xs">{label}</p>
                <p className="font-medium">{value ?? "—"}</p>
              </div>
            ))}
          </div>
          {entrega.ultima_previsao && (
            <div className="mt-4 p-3 bg-muted rounded-lg text-sm">
              <span className="text-muted-foreground">Risco de atraso (IA): </span>
              <span className="font-medium">{entrega.ultima_previsao.nivel}</span>
              {" "}({(entrega.ultima_previsao.probabilidade * 100).toFixed(0)}%)
            </div>
          )}
        </CardContent>
      </Card>

      {(checkpoints.length > 0 || entrega.estado_origem || entrega.estado_destino) && (
        <MapaRastreio rastreio={rastreioData} />
      )}

      <Timeline checkpoints={checkpoints} />
    </div>
  )
}
