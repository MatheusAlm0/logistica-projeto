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
import { Badge } from "@/components/ui/badge"
import StatusBadge from "@/components/StatusBadge"
import { UFS } from "@/constants"
import { toast } from "@/hooks/use-toast"
import { deletarEntrega, editarEntrega, atualizarStatus } from "@/api/entregas"
import { getErrorMessage } from "@/lib/errors"
import { toLocalISOString, todayLocal } from "@/lib/utils"
import type { Entrega, EntregaEditar } from "@/types"
import { Plus, Pencil, RefreshCw, Trash2 } from "lucide-react"

const STATUS_OPTS = [
  { value: "", label: "Todos" },
  { value: "pendente", label: "Pendente" },
  { value: "em_transito", label: "Em trânsito" },
  { value: "entregue", label: "Entregue" },
  { value: "atrasada", label: "Atrasada" },
  { value: "cancelado", label: "Cancelado" },
]

const TRANSICOES: Record<string, string[]> = {
  pendente: ["em_transito", "cancelado"],
  em_transito: ["entregue", "cancelado"],
  atrasada: ["em_transito", "entregue", "cancelado"],
}

const STATUS_LABELS: Record<string, string> = {
  pendente: "Pendente",
  em_transito: "Em trânsito",
  entregue: "Entregue",
  cancelado: "Cancelado",
  atrasada: "Atrasada",
}

const empty = {
  peso_g: "", valor: "", frete: "",
  estado_origem: "", estado_destino: "", data_prevista: "",
  hubs_planejados: [] as number[],
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

  // Edit modal
  const [editOpen, setEditOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Entrega | null>(null)
  const [editForm, setEditForm] = useState({ data_prevista: "", peso_g: "", valor: "", frete: "" })
  const [editSubmitting, setEditSubmitting] = useState(false)

  // Status modal
  const [statusOpen, setStatusOpen] = useState(false)
  const [statusTarget, setStatusTarget] = useState<Entrega | null>(null)
  const [newStatus, setNewStatus] = useState("")
  const [statusSubmitting, setStatusSubmitting] = useState(false)

  useEffect(() => {
    fetchEntregas(filterStatus ? { status: filterStatus } : undefined)
  }, [filterStatus]) // eslint-disable-line

  useEffect(() => {
    fetchGalpoes()
  }, []) // eslint-disable-line

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const toggleHub = (id: number) => {
    setForm((f) => ({
      ...f,
      hubs_planejados: f.hubs_planejados.includes(id)
        ? f.hubs_planejados.filter((g) => g !== id)
        : [...f.hubs_planejados, id],
    }))
  }

  const today = todayLocal()

  const handleSubmit = async () => {
    if (!form.peso_g || !form.valor || !form.frete || !form.data_prevista) {
      return alert("Preencha todos os campos obrigatórios.")
    }
    setSubmitting(true)
    try {
      await criar(
        {
          peso_g: Number(form.peso_g),
          valor: Number(form.valor),
          frete: Number(form.frete),
          estado_origem: form.estado_origem || undefined,
          estado_destino: form.estado_destino || undefined,
          data_pedido: toLocalISOString(),
          data_prevista: `${form.data_prevista}T23:59:00`,
          hubs_planejados: form.hubs_planejados,
        },
        [] // backend handles hub checkpoints via hubs_planejados
      )
      setOpen(false)
      setForm(empty)
      fetchEntregas()
    } catch { /* handled by hook */ }
    finally { setSubmitting(false) }
  }

  const openEdit = (e: Entrega) => {
    setEditTarget(e)
    setEditForm({
      data_prevista: e.data_prevista ? e.data_prevista.split("T")[0] : "",
      peso_g: String(e.peso_g),
      valor: e.valor != null ? String(e.valor) : "",
      frete: e.frete != null ? String(e.frete) : "",
    })
    setEditOpen(true)
  }

  const handleEditSubmit = async () => {
    if (!editTarget) return
    // Envia só o que mudou (o backend rejeita data_prevista no passado,
    // então reenviar a data original de uma entrega atrasada falharia).
    const body: EntregaEditar = {}
    if (editForm.data_prevista && editForm.data_prevista !== editTarget.data_prevista.split("T")[0]) {
      if (editForm.data_prevista < today) {
        return toast({ title: "Data prevista não pode ser anterior a hoje", variant: "destructive" })
      }
      body.data_prevista = `${editForm.data_prevista}T23:59:00`
    }
    if (editForm.peso_g && Number(editForm.peso_g) !== editTarget.peso_g) body.peso_g = Number(editForm.peso_g)
    if (editForm.valor && Number(editForm.valor) !== editTarget.valor) body.valor = Number(editForm.valor)
    if (editForm.frete && Number(editForm.frete) !== editTarget.frete) body.frete = Number(editForm.frete)
    if (Object.keys(body).length === 0) {
      setEditOpen(false)
      return
    }
    setEditSubmitting(true)
    try {
      await editarEntrega(editTarget.id, body)
      setEditOpen(false)
      fetchEntregas(filterStatus ? { status: filterStatus } : undefined)
      toast({ title: "Entrega atualizada" })
    } catch (err: unknown) {
      const msg = getErrorMessage(err, "Erro ao atualizar")
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally { setEditSubmitting(false) }
  }

  const openStatus = (e: Entrega) => {
    setStatusTarget(e)
    setNewStatus("")
    setStatusOpen(true)
  }

  const handleStatusSubmit = async () => {
    if (!statusTarget || !newStatus) return
    setStatusSubmitting(true)
    try {
      await atualizarStatus(statusTarget.id, newStatus)
      setStatusOpen(false)
      fetchEntregas(filterStatus ? { status: filterStatus } : undefined)
      toast({ title: "Status atualizado" })
    } catch (err: unknown) {
      const msg = getErrorMessage(err, "Erro ao atualizar status")
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally { setStatusSubmitting(false) }
  }

  const handleDeletar = async (e: Entrega) => {
    const label = e.codigo_rastreio ?? `#${e.id}`
    if (!window.confirm(`Tem certeza que deseja excluir a entrega ${label}? Esta ação não pode ser desfeita.`)) return
    try {
      await deletarEntrega(e.id)
      fetchEntregas(filterStatus ? { status: filterStatus } : undefined)
      toast({ title: "Entrega excluída" })
    } catch (err: unknown) {
      const msg = getErrorMessage(err, "Erro ao excluir")
      toast({ title: "Erro", description: msg, variant: "destructive" })
    }
  }

  const hubsFiltrados = galpoes.filter((g) => g.tipo === "hub" || g.tipo === "centro_logistico")

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
                <TableHead>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entregas.map((e) => {
                const podeAtualizarStatus = !!TRANSICOES[e.status]
                const podeDeletar = e.status === "pendente" || e.status === "atrasada"
                return (
                  <TableRow key={e.id}>
                    <TableCell className="font-mono text-xs">{e.codigo_rastreio ?? `#${e.id}`}</TableCell>
                    <TableCell>{e.estado_origem ?? "—"}</TableCell>
                    <TableCell>{e.estado_destino ?? "—"}</TableCell>
                    <TableCell><StatusBadge status={e.status} /></TableCell>
                    <TableCell className="text-sm">{fmtDate(e.data_prevista)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button size="sm" variant="ghost" onClick={() => navigate(`/dashboard/entregas/${e.id}`)}>
                          Ver
                        </Button>
                        <Button size="icon" variant="ghost" title="Editar" onClick={() => openEdit(e)}>
                          <Pencil size={14} />
                        </Button>
                        {podeAtualizarStatus && (
                          <Button size="icon" variant="ghost" title="Atualizar status" onClick={() => openStatus(e)}>
                            <RefreshCw size={14} />
                          </Button>
                        )}
                        {podeDeletar && (
                          <Button size="icon" variant="ghost" title="Excluir" onClick={() => handleDeletar(e)}>
                            <Trash2 size={14} />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
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
                <Input type="number" min={0} step="0.01" placeholder="99.90" value={form.valor} onChange={(e) => set("valor", e.target.value)} />
              </div>
              <div>
                <Label>Frete (R$) *</Label>
                <Input type="number" min={0} step="0.01" placeholder="15.00" value={form.frete} onChange={(e) => set("frete", e.target.value)} />
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
            <div>
              <Label>Hubs planejados (opcional)</Label>
              {hubsFiltrados.length === 0 ? (
                <p className="text-sm text-muted-foreground mt-1">
                  Nenhum hub cadastrado. Adicione em Unidades.
                </p>
              ) : (
                <div className="mt-2 space-y-2 max-h-36 overflow-y-auto border rounded-lg p-3">
                  {hubsFiltrados.map((g) => (
                    <div key={g.id} className="flex items-center gap-2">
                      <Checkbox
                        id={`hub-${g.id}`}
                        checked={form.hubs_planejados.includes(g.id)}
                        onCheckedChange={() => toggleHub(g.id)}
                      />
                      <label htmlFor={`hub-${g.id}`} className="text-sm cursor-pointer">
                        {g.nome} — {g.cidade}/{g.estado}
                      </label>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Criando..." : "Criar entrega"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal de edição */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        {editTarget && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Editar entrega — {editTarget.codigo_rastreio ?? `#${editTarget.id}`}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div>
                <Label>Data prevista de entrega</Label>
                <Input
                  type="date"
                  min={today}
                  value={editForm.data_prevista}
                  onChange={(e) => setEditForm((f) => ({ ...f, data_prevista: e.target.value }))}
                />
              </div>
              <div>
                <Label>Peso (g)</Label>
                <Input
                  type="number"
                  min={1}
                  placeholder={String(editTarget.peso_g)}
                  value={editForm.peso_g}
                  onChange={(e) => setEditForm((f) => ({ ...f, peso_g: e.target.value }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Valor (R$)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="—"
                    value={editForm.valor}
                    onChange={(e) => setEditForm((f) => ({ ...f, valor: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>Frete (R$)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="—"
                    value={editForm.frete}
                    onChange={(e) => setEditForm((f) => ({ ...f, frete: e.target.value }))}
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditOpen(false)}>Cancelar</Button>
              <Button onClick={handleEditSubmit} disabled={editSubmitting}>
                {editSubmitting ? "Salvando..." : "Salvar"}
              </Button>
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>

      {/* Modal de atualização de status */}
      <Dialog open={statusOpen} onOpenChange={setStatusOpen}>
        {statusTarget && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Atualizar status — {statusTarget.codigo_rastreio ?? `#${statusTarget.id}`}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div>
                <Label>Novo status</Label>
                <Select value={newStatus} onValueChange={setNewStatus}>
                  <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                  <SelectContent>
                    {(TRANSICOES[statusTarget.status] ?? []).map((s) => (
                      <SelectItem key={s} value={s}>{STATUS_LABELS[s] ?? s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {newStatus === "entregue" && (
                <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-2">
                  <p className="text-sm text-amber-600 dark:text-amber-400">
                    Isso registrará a data de entrega como agora. Esta ação não pode ser desfeita.
                  </p>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Status atual:{" "}
                <Badge variant="secondary" className="text-xs">
                  {STATUS_LABELS[statusTarget.status] ?? statusTarget.status}
                </Badge>
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setStatusOpen(false)}>Cancelar</Button>
              <Button onClick={handleStatusSubmit} disabled={statusSubmitting || !newStatus}>
                {statusSubmitting ? "Confirmando..." : "Confirmar"}
              </Button>
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>
    </div>
  )
}
