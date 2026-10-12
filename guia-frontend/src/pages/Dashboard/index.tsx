import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import StatusBadge from "@/components/StatusBadge"
import { getEntregas } from "@/api/entregas"
import type { Entrega } from "@/types"
import { Package, Truck, AlertTriangle } from "lucide-react"

function fmtDate(iso?: string) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("pt-BR")
}

export default function DashboardHome() {
  const [entregas, setEntregas] = useState<Entrega[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    getEntregas({ limit: 100 })
      .then(setEntregas)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  const total = entregas.length
  const emTransito = entregas.filter((e) => e.status === "em_transito" || e.status === "pendente").length
  const atrasadas = entregas.filter((e) => e.status === "atrasada").length
  const recentes = entregas.slice(0, 10)

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Painel</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { title: "Total de entregas", value: total, icon: Package, color: "" },
          { title: "Em trânsito", value: emTransito, icon: Truck, color: "text-primary" },
          { title: "Atrasadas", value: atrasadas, icon: AlertTriangle, color: "text-destructive" },
        ].map(({ title, value, icon: Icon, color }) => (
          <Card key={title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${color}`}>
                {isLoading ? "—" : value}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-semibold">Entregas recentes</CardTitle>
          <Button size="sm" variant="outline" onClick={() => navigate("/dashboard/entregas")}>
            Ver todas
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 text-center text-sm text-muted-foreground">Carregando...</div>
          ) : recentes.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">Nenhuma entrega ainda.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Código</TableHead>
                  <TableHead>Destino</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Previsão</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentes.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell className="font-mono text-xs">{e.codigo_rastreio ?? `#${e.id}`}</TableCell>
                    <TableCell>{e.estado_destino ?? "—"}</TableCell>
                    <TableCell><StatusBadge status={e.status} /></TableCell>
                    <TableCell className="text-sm">{fmtDate(e.data_prevista_revisada ?? e.data_prevista)}</TableCell>
                    <TableCell>
                      <Button size="sm" variant="ghost" onClick={() => navigate(`/dashboard/entregas/${e.id}`)}>
                        Ver
                      </Button>
                    </TableCell>
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
