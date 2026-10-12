import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useEntregas } from "@/hooks/useEntregas"
import { useGalpoes } from "@/hooks/useGalpoes"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import StatusBadge from "@/components/StatusBadge"
import { UFS } from "@/constants"
import { Plus } from "lucide-react"

const STATUS_OPTS = [
  { value: "", label: "Todos" },
  { value: "pendente", label: "Pendente" },
  { value: "em_transito", label: "Em trânsito" },
  { value: "entregue", label: "Entregue" },
  { value: "atrasada", label: "Atrasada" },
  { value: "cancelado", label: "Cancelado" },
]

const empty = {
  peso_g: "", valor_reais: "", frete_reais: "",
  estado_origem: "", estado_destino: "", data_prevista: "",
  galpao_ids: [] as number[],
}

function fmtDate(iso?: string) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("pt-BR")
}

export default function EntregasPage() {
  const navigate = useNavigate()
  const { entregas, isLoading, error, fetchEntregas, criar } = useEntregas()
  const { galpoes, fetch: fetchGalpoes } = useGalpoes()
  const [filterStatus, setFilterStatus] = useState("")
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(empty)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchEntregas(filterStatus ? { status: filterStatus } : undefined)
  }, [filterStatus]) // eslint-disable-line

  useEffect(() => {
    fetchGalpoes()
  }, []) // eslint-disable-line

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const toggleGalpao = (id: number) => {
    setForm((f) => ({
      ...f,
      galpao_ids: f.galpao_ids.includes(id) ? f.galpao_ids.filter((g) => g !== id) : [...f.galpao_ids, id],
    }))
  }

  const handleSubmit = async () => {
    if (!form.peso_g || !form.valor_reais || !form.frete_reais || !form.data_prevista) {
      return alert("Preencha todos os campos obrigatórios.")
    }
    setSubmitting(true)
    try {
      await criar(
        {
          peso_g: Number(form.peso_g),
          valor_reais: Number(form.valor_reais),
          frete_reais: Number(form.frete_reais),
          estado_origem: form.estado_origem || undefined,
          estado_destino: form.estado_destino || undefined,
          data_pedido: new Date().toISOString(),
          data_prevista: `${form.data_prevista}T23:59:00`,
        },
        form.galpao_ids
      )
      setOpen(false)
      setForm(empty)
      fetchEntregas()
    } catch { /* handled by hook */ }
    finally { setSubmitting(false) }
  }

  const today = new Date().toISOString().split("T")[0]

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-xl font-semibold">Entregas</h1>
        <Button onClick={() => setOpen(true)}>
          <Plus size={16} />
          Nova entrega
        </Button>
      </div>

      <div className="flex gap-3 items-center flex-wrap">
        <div className="w-44">
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger><SelectValue placeholder="Filtrar status" /></SelectTrigger>
            <SelectContent>
              {STATUS_OPTS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground animate-pulse">Carregando...</div>
      ) : entregas.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground text-sm">Nenhuma entrega encontrada.</div>
      ) : (
        <div className="border rounded-xl overflow-hidden bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Origem</TableHead>
                <TableHead>Destino</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Previsão</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {entregas.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="font-mono text-xs">{e.codigo_rastreio ?? `#${e.id}`}</TableCell>
                  <TableCell>{e.estado_origem ?? "—"}</TableCell>
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
        </div>
      )}

      {/* Nova entrega dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nova entrega</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>Peso (g) *</Label>
                <Input type="number" min={1} placeholder="1000" value={form.peso_g} onChange={(e) => set("peso_g", e.target.value)} />
              </div>
              <div>
                <Label>Valor (R$) *</Label>
                <Input type="number" min={0} step="0.01" placeholder="99.90" value={form.valor_reais} onChange={(e) => set("valor_reais", e.target.value)} />
              </div>
              <div>
                <Label>Frete (R$) *</Label>
                <Input type="number" min={0} step="0.01" placeholder="15.00" value={form.frete_reais} onChange={(e) => set("frete_reais", e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Estado de origem</Label>
                <Select value={form.estado_origem} onValueChange={(v) => set("estado_origem", v)}>
                  <SelectTrigger><SelectValue placeholder="UF" /></SelectTrigger>
                  <SelectContent>{UFS.map((uf) => <SelectItem key={uf} value={uf}>{uf}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label>Estado de destino</Label>
                <Select value={form.estado_destino} onValueChange={(v) => set("estado_destino", v)}>
                  <SelectTrigger><SelectValue placeholder="UF" /></SelectTrigger>
                  <SelectContent>{UFS.map((uf) => <SelectItem key={uf} value={uf}>{uf}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Data prevista de entrega *</Label>
              <Input type="date" min={today} value={form.data_prevista} onChange={(e) => set("data_prevista", e.target.value)} />
            </div>
            {galpoes.length > 0 && (
              <div>
                <Label>Checkpoint inicial (galpão)</Label>
                <div className="mt-2 space-y-2 max-h-36 overflow-y-auto border rounded-lg p-3">
                  {galpoes.map((g) => (
                    <div key={g.id} className="flex items-center gap-2">
                      <Checkbox
                        id={`g-${g.id}`}
                        checked={form.galpao_ids.includes(g.id)}
                        onCheckedChange={() => toggleGalpao(g.id)}
                      />
                      <label htmlFor={`g-${g.id}`} className="text-sm cursor-pointer">
                        {g.nome} — {g.cidade}/{g.estado}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Criando..." : "Criar entrega"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
