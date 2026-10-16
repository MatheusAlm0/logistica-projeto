import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Card, CardContent } from "@/components/ui/card"
import { toast } from "@/hooks/use-toast"
import { getErrorMessage } from "@/lib/errors"
import type { Veiculo } from "@/types"
import { getVeiculos, createVeiculo, updateVeiculo, deleteVeiculo } from "@/api/cotacao"
import { Plus, Pencil, Trash2, Truck } from "lucide-react"

const TIPOS = ["furgao", "van", "caminhao_leve", "caminhao_pesado", "carreta"] as const
const TIPO_LABEL: Record<string, string> = {
  furgao: "Furgão", van: "Van", caminhao_leve: "Caminhão leve",
  caminhao_pesado: "Caminhão pesado", carreta: "Carreta",
}

const emptyV = { nome: "", tipo: "van", peso_max_kg: "", comprimento_max_cm: "", largura_max_cm: "", altura_max_cm: "", preco_por_km: "" }

export default function FrotaPage() {
  const [veiculos, setVeiculos] = useState<Veiculo[]>([])
  const [vLoading, setVLoading] = useState(true)
  const [vOpen, setVOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [vForm, setVForm] = useState(emptyV)
  const [vSubmit, setVSubmit] = useState(false)

  useEffect(() => {
    getVeiculos().then(setVeiculos)
      .catch((err: unknown) => toast({ title: "Erro ao carregar veículos", description: getErrorMessage(err, "Tente novamente."), variant: "destructive" }))
      .finally(() => setVLoading(false))
  }, [])

  const sv = (k: string, v: string) => setVForm((f) => ({ ...f, [k]: v }))

  const openNew = () => { setEditId(null); setVForm(emptyV); setVOpen(true) }
  const openEdit = (v: Veiculo) => {
    setEditId(v.id)
    setVForm({
      nome: v.nome, tipo: v.tipo,
      peso_max_kg: v.peso_max_kg.toString(),
      comprimento_max_cm: v.comprimento_max_cm?.toString() ?? "",
      largura_max_cm: v.largura_max_cm?.toString() ?? "",
      altura_max_cm: v.altura_max_cm?.toString() ?? "",
      preco_por_km: v.preco_por_km?.toString() ?? "",
    })
    setVOpen(true)
  }

  const handleVSubmit = async () => {
    if (!vForm.nome || !vForm.tipo || !vForm.peso_max_kg) return alert("Preencha nome, tipo e peso máximo.")
    setVSubmit(true)
    try {
      const payload = {
        nome: vForm.nome,
        tipo: vForm.tipo as Veiculo["tipo"],
        peso_max_kg: Number(vForm.peso_max_kg),
        comprimento_max_cm: vForm.comprimento_max_cm ? Number(vForm.comprimento_max_cm) : undefined,
        largura_max_cm: vForm.largura_max_cm ? Number(vForm.largura_max_cm) : undefined,
        altura_max_cm: vForm.altura_max_cm ? Number(vForm.altura_max_cm) : undefined,
        preco_por_km: vForm.preco_por_km ? Number(vForm.preco_por_km) : undefined,
      }
      if (editId) {
        const updated = await updateVeiculo(editId, payload)
        setVeiculos((prev) => prev.map((v) => v.id === editId ? updated : v))
        toast({ title: "Veículo atualizado" })
      } else {
        const novo = await createVeiculo(payload)
        setVeiculos((prev) => [...prev, novo])
        toast({ title: "Veículo cadastrado" })
      }
      setVOpen(false)
    } catch (err: unknown) {
      toast({ title: "Erro ao salvar veículo", description: getErrorMessage(err, "Tente novamente."), variant: "destructive" })
    } finally { setVSubmit(false) }
  }

  const handleDesativar = async (id: number) => {
    try {
      await deleteVeiculo(id)
      setVeiculos((prev) => prev.filter((v) => v.id !== id))
      toast({ title: "Veículo desativado" })
    } catch (err: unknown) {
      toast({ title: "Erro ao desativar", description: getErrorMessage(err, "Tente novamente."), variant: "destructive" })
    }
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Minha Frota</h1>
        <Button onClick={openNew}><Plus size={16} />Novo veículo</Button>
      </div>

      {vLoading ? (
        <div className="text-center py-10 text-muted-foreground animate-pulse">Carregando...</div>
      ) : veiculos.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Truck className="mx-auto mb-2 opacity-30" size={36} />
          <p className="text-sm">Nenhum veículo cadastrado.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {veiculos.map((v) => (
            <Card key={v.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold">{v.nome}</p>
                    <p className="text-sm text-muted-foreground">{TIPO_LABEL[v.tipo] ?? v.tipo}</p>
                    <p className="text-xs text-muted-foreground mt-1">Capacidade: {v.peso_max_kg} kg</p>
                    {v.preco_por_km != null && (
                      <p className="text-xs text-muted-foreground">
                        {v.preco_por_km.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}/km
                      </p>
                    )}
                    {(v.comprimento_max_cm || v.largura_max_cm || v.altura_max_cm) && (
                      <p className="text-xs text-muted-foreground">
                        {[v.comprimento_max_cm, v.largura_max_cm, v.altura_max_cm]
                          .filter(Boolean).join(" × ")} cm
                      </p>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button size="icon" variant="ghost" onClick={() => openEdit(v)}><Pencil size={14} /></Button>
                    <Button size="icon" variant="ghost" onClick={() => handleDesativar(v.id)}><Trash2 size={14} /></Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Modal veículo */}
      <Dialog open={vOpen} onOpenChange={setVOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editId ? "Editar veículo" : "Novo veículo"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Nome *</Label>
                <Input placeholder="Furgão 01" value={vForm.nome} onChange={(e) => sv("nome", e.target.value)} />
              </div>
              <div>
                <Label>Tipo *</Label>
                <Select value={vForm.tipo} onValueChange={(v) => sv("tipo", v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{TIPOS.map((t) => <SelectItem key={t} value={t}>{TIPO_LABEL[t]}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Peso máximo (kg) *</Label>
                <Input type="number" placeholder="1000" value={vForm.peso_max_kg} onChange={(e) => sv("peso_max_kg", e.target.value)} />
              </div>
              <div>
                <Label>Preço por km (R$, opcional)</Label>
                <Input type="number" step="0.01" placeholder="Ex: 1.80" value={vForm.preco_por_km} onChange={(e) => sv("preco_por_km", e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>Comp. máx (cm)</Label>
                <Input type="number" placeholder="300" value={vForm.comprimento_max_cm} onChange={(e) => sv("comprimento_max_cm", e.target.value)} />
              </div>
              <div>
                <Label>Larg. máx (cm)</Label>
                <Input type="number" placeholder="200" value={vForm.largura_max_cm} onChange={(e) => sv("largura_max_cm", e.target.value)} />
              </div>
              <div>
                <Label>Alt. máx (cm)</Label>
                <Input type="number" placeholder="200" value={vForm.altura_max_cm} onChange={(e) => sv("altura_max_cm", e.target.value)} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVOpen(false)}>Cancelar</Button>
            <Button onClick={handleVSubmit} disabled={vSubmit}>
              {vSubmit ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
