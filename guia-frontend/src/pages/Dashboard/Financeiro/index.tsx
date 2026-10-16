import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "@/hooks/use-toast"
import { getErrorMessage } from "@/lib/errors"
import type { Veiculo, FaixaPreco } from "@/types"
import { getVeiculos, updateVeiculo, getTabelaPreco, saveTabelaPreco } from "@/api/cotacao"
import { Plus, Pencil, Trash2 } from "lucide-react"

const TIPO_LABEL: Record<string, string> = {
  furgao: "Furgão", van: "Van", caminhao_leve: "Caminhão leve",
  caminhao_pesado: "Caminhão pesado", carreta: "Carreta",
}

interface FaixaRow extends FaixaPreco { _key: number }

export default function FinanceiroPage() {
  // Tabela de preços state
  const [tModalidade, setTModalidade] = useState<"fixo_por_km" | "faixa_peso_volume">("fixo_por_km")
  const [tPrecoKm, setTPrecoKm] = useState("")
  const [tMulti, setTMulti] = useState("1.4")
  const [tRaio, setTRaio] = useState("150")
  const [tTaxa, setTTaxa] = useState("")
  const [tLimite, setTLimite] = useState("")
  const [faixas, setFaixas] = useState<FaixaRow[]>([])
  const [tSaving, setTSaving] = useState(false)
  const [tLoaded, setTLoaded] = useState(false)

  // Veículos state
  const [veiculos, setVeiculos] = useState<Veiculo[]>([])
  const [vLoading, setVLoading] = useState(true)
  const [editVeiculo, setEditVeiculo] = useState<Veiculo | null>(null)
  const [precoForm, setPrecoForm] = useState("")
  const [pSaving, setPSaving] = useState(false)

  useEffect(() => {
    getTabelaPreco()
      .then((t) => {
        setTModalidade(t.modalidade as "fixo_por_km" | "faixa_peso_volume")
        setTPrecoKm(t.preco_base_km?.toString() ?? "")
        setTMulti(t.multiplicador_expresso.toString())
        setTRaio(t.raio_galpao_km.toString())
        setTTaxa(t.taxa_dimensao_extra?.toString() ?? "")
        setTLimite(t.limite_dimensao_cm?.toString() ?? "")
        setFaixas(t.faixas.map((f, i) => ({ ...f, _key: i })))
        setTLoaded(true)
      })
      .catch(() => setTLoaded(true))
    getVeiculos().then(setVeiculos)
      .catch((err: unknown) => toast({ title: "Erro ao carregar veículos", description: getErrorMessage(err, "Tente novamente."), variant: "destructive" }))
      .finally(() => setVLoading(false))
  }, [])

  const addFaixa = () => setFaixas((f) => [...f, { _key: Date.now(), peso_min_kg: 0, preco_por_km: 0 }])
  const removeFaixa = (key: number) => setFaixas((f) => f.filter((r) => r._key !== key))
  const setFaixa = (key: number, field: string, val: string) =>
    setFaixas((f) => f.map((r) => r._key === key ? { ...r, [field]: val === "" ? undefined : Number(val) } : r))

  const handleSaveTabela = async () => {
    setTSaving(true)
    try {
      await saveTabelaPreco({
        modalidade: tModalidade,
        preco_base_km: tPrecoKm ? Number(tPrecoKm) : undefined,
        multiplicador_expresso: Number(tMulti) || 1.4,
        raio_galpao_km: Number(tRaio) || 150,
        taxa_dimensao_extra: tTaxa ? Number(tTaxa) : undefined,
        limite_dimensao_cm: tLimite ? Number(tLimite) : undefined,
        faixas: faixas.map(({ _key: _, ...f }) => f),
      })
      toast({ title: "Tabela de preços salva" })
    } catch (err: unknown) {
      toast({ title: "Erro ao salvar tabela", description: getErrorMessage(err, "Tente novamente."), variant: "destructive" })
    } finally { setTSaving(false) }
  }

  const openEditPreco = (v: Veiculo) => {
    setEditVeiculo(v)
    setPrecoForm(v.preco_por_km?.toString() ?? "")
  }

  const handleSavePreco = async () => {
    if (!editVeiculo) return
    setPSaving(true)
    try {
      const updated = await updateVeiculo(editVeiculo.id, {
        preco_por_km: precoForm ? Number(precoForm) : undefined,
      })
      setVeiculos((prev) => prev.map((v) => v.id === editVeiculo.id ? updated : v))
      toast({ title: "Preço atualizado" })
      setEditVeiculo(null)
    } catch (err: unknown) {
      toast({ title: "Erro ao salvar preço", description: getErrorMessage(err, "Tente novamente."), variant: "destructive" })
    } finally { setPSaving(false) }
  }

  const handleLimparPreco = async () => {
    if (!editVeiculo) return
    setPSaving(true)
    try {
      // null clears the per-vehicle price; backend uses exclude_unset so null is applied
      const updated = await updateVeiculo(
        editVeiculo.id,
        { preco_por_km: null } as unknown as Partial<Omit<Veiculo, "id" | "ativo">>
      )
      setVeiculos((prev) => prev.map((v) => v.id === editVeiculo.id ? updated : v))
      toast({ title: "Preço próprio removido — veículo usará tabela global" })
      setEditVeiculo(null)
    } catch (err: unknown) {
      toast({ title: "Erro ao limpar preço", description: getErrorMessage(err, "Tente novamente."), variant: "destructive" })
    } finally { setPSaving(false) }
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <h1 className="text-xl font-semibold">Financeiro</h1>

      {/* Tabela de Preços Global */}
      {tLoaded && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tabela de Preços Global</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Define o preço base por km usado quando o veículo não tem preço próprio configurado.
            </p>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Modalidade</Label>
                <Select value={tModalidade} onValueChange={(v) => setTModalidade(v as typeof tModalidade)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fixo_por_km">Fixo por km</SelectItem>
                    <SelectItem value="faixa_peso_volume">Por faixa de peso</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {tModalidade === "fixo_por_km" && (
                <div>
                  <Label>Preço por km (R$)</Label>
                  <Input type="number" step="0.01" placeholder="2.50" value={tPrecoKm} onChange={(e) => setTPrecoKm(e.target.value)} />
                </div>
              )}
            </div>

            {tModalidade === "faixa_peso_volume" && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Faixas de peso</Label>
                  <Button size="sm" variant="outline" onClick={addFaixa}><Plus size={14} />Adicionar</Button>
                </div>
                <div className="space-y-2">
                  {faixas.map((f) => (
                    <div key={f._key} className="grid grid-cols-4 gap-2 items-center">
                      <Input type="number" placeholder="Peso mín (kg)" value={f.peso_min_kg ?? ""} onChange={(e) => setFaixa(f._key, "peso_min_kg", e.target.value)} />
                      <Input type="number" placeholder="Peso máx (kg)" value={f.peso_max_kg ?? ""} onChange={(e) => setFaixa(f._key, "peso_max_kg", e.target.value)} />
                      <Input type="number" step="0.01" placeholder="R$/km" value={f.preco_por_km ?? ""} onChange={(e) => setFaixa(f._key, "preco_por_km", e.target.value)} />
                      <Button size="icon" variant="ghost" onClick={() => removeFaixa(f._key)}><Trash2 size={14} /></Button>
                    </div>
                  ))}
                  {faixas.length === 0 && <p className="text-sm text-muted-foreground">Nenhuma faixa configurada.</p>}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Multiplicador expresso</Label>
                <Input type="number" step="0.1" placeholder="1.4" value={tMulti} onChange={(e) => setTMulti(e.target.value)} />
              </div>
              <div>
                <Label>Raio galpão próximo (km)</Label>
                <Input type="number" placeholder="150" value={tRaio} onChange={(e) => setTRaio(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Taxa dimensão extra (R$, opcional)</Label>
                <Input type="number" step="0.01" placeholder="50.00" value={tTaxa} onChange={(e) => setTTaxa(e.target.value)} />
              </div>
              <div>
                <Label>Limite dimensão (cm, opcional)</Label>
                <Input type="number" placeholder="200" value={tLimite} onChange={(e) => setTLimite(e.target.value)} />
              </div>
            </div>

            <Button onClick={handleSaveTabela} disabled={tSaving}>
              {tSaving ? "Salvando..." : "Salvar configurações"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Preços por Veículo */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Preços por Veículo</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Veículos com preço próprio substituem a tabela global no cálculo de frete.
          </p>
        </CardHeader>
        <CardContent>
          {vLoading ? (
            <div className="text-center py-8 text-muted-foreground animate-pulse text-sm">Carregando...</div>
          ) : veiculos.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">Nenhum veículo cadastrado.</div>
          ) : (
            <div className="border rounded-xl overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Veículo</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Capacidade</TableHead>
                    <TableHead>Preço/km próprio</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {veiculos.map((v) => (
                    <TableRow key={v.id}>
                      <TableCell className="font-medium">{v.nome}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{TIPO_LABEL[v.tipo] ?? v.tipo}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{v.peso_max_kg} kg</TableCell>
                      <TableCell>
                        {v.preco_por_km != null ? (
                          <span className="font-medium text-sm">
                            {v.preco_por_km.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}/km
                          </span>
                        ) : (
                          <Badge variant="secondary" className="text-xs">Usa tabela global</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button size="sm" variant="ghost" onClick={() => openEditPreco(v)}>
                          <Pencil size={13} className="mr-1" />Editar preço
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal editar preço */}
      <Dialog open={!!editVeiculo} onOpenChange={() => setEditVeiculo(null)}>
        {editVeiculo && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Preço por km — {editVeiculo.nome}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div>
                <Label>Preço por km (R$)</Label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="Ex: 1.80 (deixe vazio para usar tabela global)"
                  value={precoForm}
                  onChange={(e) => setPrecoForm(e.target.value)}
                  autoFocus
                />
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="ghost" onClick={handleLimparPreco} disabled={pSaving}>
                Usar tabela global
              </Button>
              <Button onClick={handleSavePreco} disabled={pSaving}>
                {pSaving ? "Salvando..." : "Salvar"}
              </Button>
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>
    </div>
  )
}
