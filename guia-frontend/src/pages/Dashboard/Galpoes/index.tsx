import { useEffect, useState } from "react"
import { useGalpoes } from "@/hooks/useGalpoes"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Card, CardContent } from "@/components/ui/card"
import { UFS } from "@/constants"
import { Plus, MapPin, Warehouse } from "lucide-react"

const empty = { nome: "", cidade: "", estado: "", lat: "", lng: "" }

export default function GalpoesPage() {
  const { galpoes, isLoading, fetch, criar } = useGalpoes()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(empty)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { fetch() }, []) // eslint-disable-line

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async () => {
    if (!form.nome || !form.cidade || !form.estado) {
      return alert("Preencha nome, cidade e estado.")
    }
    setSubmitting(true)
    try {
      await criar({
        nome: form.nome,
        cidade: form.cidade,
        estado: form.estado,
        lat: form.lat ? Number(form.lat) : undefined,
        lng: form.lng ? Number(form.lng) : undefined,
      })
      setOpen(false)
      setForm(empty)
    } catch { /* handled */ }
    finally { setSubmitting(false) }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">Galpões</h1>
        <Button onClick={() => setOpen(true)}>
          <Plus size={16} />
          Novo galpão
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground animate-pulse">Carregando...</div>
      ) : galpoes.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Warehouse className="mx-auto mb-3 opacity-30" size={40} />
          <p className="text-sm">Nenhum galpão cadastrado ainda.</p>
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
                    <p className="font-semibold truncate">{g.nome}</p>
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
            <DialogTitle>Novo galpão</DialogTitle>
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
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Latitude (opcional)</Label>
                <Input type="number" step="any" placeholder="-23.5489" value={form.lat} onChange={(e) => set("lat", e.target.value)} />
              </div>
              <div>
                <Label>Longitude (opcional)</Label>
                <Input type="number" step="any" placeholder="-46.6388" value={form.lng} onChange={(e) => set("lng", e.target.value)} />
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
