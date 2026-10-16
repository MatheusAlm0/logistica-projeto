import { useEffect, useState } from "react"
import { useGalpoes } from "@/hooks/useGalpoes"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Card, CardContent } from "@/components/ui/card"
import { UFS } from "@/constants"
import { Plus, MapPin, Warehouse, UserCheck } from "lucide-react"
import { toast } from "@/hooks/use-toast"

const TIPO_LABEL: Record<string, string> = {
  galpao: "Galpão",
  hub: "Hub Logístico",
  centro_logistico: "Centro Logístico",
  loja: "Loja",
  ponto_retirada: "Ponto de Retirada",
}

const empty = { nome: "", cidade: "", estado: "", rua: "", numero: "", bairro: "", cep: "", tipo: "galpao", permite_retirada: false }

export default function GalpoesPage() {
  const { galpoes, isLoading, fetch: recarregar, criar } = useGalpoes()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(empty)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { recarregar() }, []) // eslint-disable-line

  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async () => {
    if (!form.nome || !form.cidade || !form.estado || !form.rua) {
      return alert("Preencha nome, rua, cidade e estado.")
    }
    setSubmitting(true)
    try {
      const q = encodeURIComponent(
        `${form.rua}, ${form.numero}, ${form.bairro}, ${form.cep}, ${form.cidade}, ${form.estado}, Brasil`
      )
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${q}&countrycodes=br&limit=1`,
        { headers: { "Accept-Language": "pt-BR" } }
      )
      const results = await res.json()
      if (!results.length) {
        toast({ title: "Endereço não encontrado. Verifique os dados.", variant: "destructive" })
        return
      }
      const { lat, lon } = results[0]
      await criar({
        nome: form.nome,
        cidade: form.cidade,
        estado: form.estado,
        lat: Number(lat),
        lng: Number(lon),
        tipo: form.tipo,
        permite_retirada: form.permite_retirada,
      })
      setOpen(false)
      setForm(empty)
    } catch { /* handled by hook */ }
    finally { setSubmitting(false) }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">Unidades</h1>
        <Button onClick={() => setOpen(true)}>
          <Plus size={16} />
          Nova unidade
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground animate-pulse">Carregando...</div>
      ) : galpoes.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Warehouse className="mx-auto mb-3 opacity-30" size={40} />
          <p className="text-sm">Nenhuma unidade cadastrada ainda.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {galpoes.map((g) => (
            <Card key={g.id}>
              <CardContent className="p-5">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 p-2 rounded-lg bg-primary/10 text-primary shrink-0">
                    <Warehouse size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold truncate">{g.nome}</p>
                      {g.tipo && (
                        <Badge variant="secondary" className="text-xs shrink-0">
                          {TIPO_LABEL[g.tipo] ?? g.tipo}
                        </Badge>
                      )}
                      {g.permite_retirada && (
                        <span title="Permite retirada" className="text-primary shrink-0">
                          <UserCheck size={14} />
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">{g.cidade} / {g.estado}</p>
                    {g.lat != null && g.lng != null && (
                      <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                        <MapPin size={11} />
                        {g.lat.toFixed(4)}, {g.lng.toFixed(4)}
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nova unidade</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Nome *</Label>
              <Input placeholder="Galpão Central SP" value={form.nome} onChange={(e) => set("nome", e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Cidade *</Label>
                <Input placeholder="São Paulo" value={form.cidade} onChange={(e) => set("cidade", e.target.value)} />
              </div>
              <div>
                <Label>Estado *</Label>
                <Select value={form.estado} onValueChange={(v) => set("estado", v)}>
                  <SelectTrigger><SelectValue placeholder="UF" /></SelectTrigger>
                  <SelectContent>{UFS.map((uf) => <SelectItem key={uf} value={uf}>{uf}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Tipo de unidade</Label>
              <Select value={form.tipo} onValueChange={(v) => set("tipo", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="galpao">Galpão</SelectItem>
                  <SelectItem value="hub">Hub Logístico</SelectItem>
                  <SelectItem value="centro_logistico">Centro Logístico</SelectItem>
                  <SelectItem value="loja">Loja</SelectItem>
                  <SelectItem value="ponto_retirada">Ponto de Retirada</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-start gap-3 pt-1">
              <input
                id="permite_retirada"
                type="checkbox"
                checked={form.permite_retirada}
                onChange={(e) => set("permite_retirada", e.target.checked)}
                className="mt-0.5 accent-primary"
              />
              <div>
                <Label htmlFor="permite_retirada" className="cursor-pointer">Permite retirada pelo cliente</Label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Marque se clientes podem retirar encomendas nesta unidade
                </p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <Label>Rua *</Label>
                <Input placeholder="Av. Paulista" value={form.rua} onChange={(e) => set("rua", e.target.value)} />
              </div>
              <div>
                <Label>Número</Label>
                <Input placeholder="1000" value={form.numero} onChange={(e) => set("numero", e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Bairro</Label>
                <Input placeholder="Bela Vista" value={form.bairro} onChange={(e) => set("bairro", e.target.value)} />
              </div>
              <div>
                <Label>CEP</Label>
                <Input placeholder="01310-100" value={form.cep} onChange={(e) => set("cep", e.target.value)} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
