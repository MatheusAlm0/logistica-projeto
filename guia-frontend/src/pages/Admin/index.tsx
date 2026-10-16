import { useEffect, useState } from "react"
import { getRetreinos, dispararRetreino, getHealthCheck } from "@/api/retreinos"
import type { Retreino, HealthCheck, RetreinoListResponse } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "@/hooks/use-toast"
import { getErrorMessage } from "@/lib/errors"
import { Brain, CheckCircle, XCircle, Loader2 } from "lucide-react"

function fmtDate(iso?: string) {
  if (!iso) return "—"
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" })
}

function statusBadge(s: string) {
  if (s === "ok") return <Badge variant="success">OK</Badge>
  if (s === "rodando") return <Badge variant="default">Rodando</Badge>
  return <Badge variant="destructive">Erro</Badge>
}

export default function AdminHome() {
  const [retreinos, setRetreinos] = useState<Retreino[]>([])
  const [totalRetreinos, setTotalRetreinos] = useState<number | null>(null)
  const [health, setHealth] = useState<HealthCheck | null>(null)
  const [loadingRetreino, setLoadingRetreino] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  function aplicarRetreinos(res: RetreinoListResponse) {
    setRetreinos(res.items)
    setTotalRetreinos(res.total)
  }

  function carregarRetreinos() {
    return getRetreinos({ limit: 10 })
      .then(aplicarRetreinos)
      .catch((err: unknown) =>
        toast({ title: "Erro ao carregar retreinos", description: getErrorMessage(err, "Tente novamente."), variant: "destructive" })
      )
  }

  useEffect(() => {
    Promise.all([
      carregarRetreinos(),
      getHealthCheck().then(setHealth).catch(() => {}),
    ]).finally(() => setIsLoading(false))
  }, [])

  async function handleTreinar() {
    setLoadingRetreino(true)
    try {
      const res = await dispararRetreino()
      toast({ title: "Retreino iniciado", description: res.mensagem })
      setTimeout(carregarRetreinos, 1500)
    } catch (err: unknown) {
      const msg = getErrorMessage(err, "Erro ao disparar retreino")
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally {
      setLoadingRetreino(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Painel Admin</h1>

      {/* Health check */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Backend API</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2">
            {health ? (
              <><CheckCircle size={16} className="text-green-500" /><span className="text-sm font-medium">Online</span></>
            ) : isLoading ? (
              <><Loader2 size={16} className="animate-spin text-muted-foreground" /><span className="text-sm text-muted-foreground">Verificando...</span></>
            ) : (
              <><XCircle size={16} className="text-destructive" /><span className="text-sm font-medium">Offline</span></>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Modelo IA</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium font-mono truncate">{health?.modelo ?? "—"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Retreinos realizados</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{totalRetreinos ?? "—"}</p>
          </CardContent>
        </Card>
      </div>

      {/* Treinar modelo */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-semibold">Modelo de previsão</CardTitle>
          <Button onClick={handleTreinar} disabled={loadingRetreino}>
            <Brain size={16} />
            {loadingRetreino ? "Iniciando..." : "Treinar modelo"}
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 text-center text-sm text-muted-foreground animate-pulse">Carregando...</div>
          ) : retreinos.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">Nenhum retreino registrado.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>ROC-AUC</TableHead>
                  <TableHead>PR-AUC</TableHead>
                  <TableHead>Amostras</TableHead>
                  <TableHead>Iniciado</TableHead>
                  <TableHead>Duração</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {retreinos.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="text-muted-foreground text-xs">{r.id}</TableCell>
                    <TableCell>{statusBadge(r.status)}</TableCell>
                    <TableCell className="font-mono text-sm">{r.roc_auc?.toFixed(4) ?? "—"}</TableCell>
                    <TableCell className="font-mono text-sm">{r.pr_auc?.toFixed(4) ?? "—"}</TableCell>
                    <TableCell>{r.n_amostras ?? "—"}</TableCell>
                    <TableCell className="text-sm">{fmtDate(r.iniciado_em)}</TableCell>
                    <TableCell className="text-sm">{r.duracao_segundos != null ? `${r.duracao_segundos.toFixed(1)}s` : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
