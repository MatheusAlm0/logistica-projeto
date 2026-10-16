import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "@/hooks/use-toast"
import type { ResultadoCotacao, Orcamento, Galpao, GalpaoRota } from "@/types"
import { calcularCotacao, salvarOrcamento, getOrcamentos, aprovarOrcamento, deletarOrcamento, getPontosRetirada } from "@/api/cotacao"
import { getGalpoes } from "@/api/galpoes"
import { gerarPdfOrcamento } from "@/lib/gerarPdfOrcamento"
import { UFS } from "@/constants"
import { FileDown, Check, Trash2 } from "lucide-react"

function fmtDate(iso?: string) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("pt-BR")
}

function fmtMoney(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}

const STATUS_BADGE: Record<string, "secondary" | "default" | "success" | "warning" | "destructive"> = {
  rascunho: "secondary",
  enviado: "default",
  aprovado: "success",
  expirado: "warning",
}

const emptyForm = {
  galpao_origem_id: "" as number | "",
  destino_tipo: "galpao" as "galpao" | "endereco" | "retirada",
  galpao_destino_id: "" as number | "",
  destino_rua: "",
  destino_numero: "",
  destino_bairro: "",
  destino_cep: "",
  destino_cidade: "",
  destino_estado: "",
  peso_kg: "",
  comprimento_cm: "",
  largura_cm: "",
  altura_cm: "",
  tipo_frete: "padrao" as "padrao" | "expresso",
}

export default function CotacaoPage() {
  const [tab, setTab] = useState<"nova" | "salvos">("nova")

  const [galpoes, setGalpoes] = useState<Galpao[]>([])
  const [gLoading, setGLoading] = useState(true)
  const [pontosRetirada, setPontosRetirada] = useState<GalpaoRota[]>([])
  const [pLoading, setPLoading] = useState(false)

  const [form, setForm] = useState(emptyForm)
  const [resultado, setResultado] = useState<ResultadoCotacao | null>(null)
  const [calculando, setCalculando] = useState(false)
  const [salvando, setSalvando] = useState(false)

  const [orcamentos, setOrcamentos] = useState<Orcamento[]>([])
  const [oLoading, setOLoading] = useState(false)
  const [detalhes, setDetalhes] = useState<Orcamento | null>(null)

  const sf = (k: string, v: string | number) => setForm((f) => ({ ...f, [k]: v }))

  useEffect(() => {
    getGalpoes()
      .then(setGalpoes)
      .catch(() => toast({ title: "Erro ao carregar galpões", variant: "destructive" }))
      .finally(() => setGLoading(false))
  }, [])

  useEffect(() => {
    if (form.destino_tipo === "retirada" && pontosRetirada.length === 0 && !pLoading) {
      setPLoading(true)
      getPontosRetirada().then(setPontosRetirada).catch(() => {}).finally(() => setPLoading(false))
    }
  }, [form.destino_tipo]) // eslint-disable-line

  useEffect(() => {
    if (tab === "salvos") {
      setOLoading(true)
      getOrcamentos().then(setOrcamentos).catch(() => {}).finally(() => setOLoading(false))
    }
  }, [tab])

  const galpoesDestino = galpoes.filter((g) => g.id !== Number(form.galpao_origem_id))

  const handleCalcular = async () => {
    if (!form.galpao_origem_id) {
      return toast({ title: "Selecione um galpão de origem.", variant: "destructive" })
    }
    if ((form.destino_tipo === "galpao" || form.destino_tipo === "retirada") && !form.galpao_destino_id) {
      return toast({ title: form.destino_tipo === "retirada" ? "Selecione um ponto de retirada." : "Selecione um galpão de destino.", variant: "destructive" })
    }
    if (!form.peso_kg) {
      return toast({ title: "Informe o peso do pacote.", variant: "destructive" })
    }

    setCalculando(true)
    setResultado(null)

    try {
      let endereco_lat: number | undefined
      let endereco_lng: number | undefined

      if (form.destino_tipo === "endereco") {
        if (!form.destino_cidade || !form.destino_estado) {
          toast({ title: "Informe cidade e estado do destino.", variant: "destructive" })
          return
        }
        const q = encodeURIComponent(
          [form.destino_rua, form.destino_numero, form.destino_bairro, form.destino_cep, form.destino_cidade, form.destino_estado, "Brasil"]
            .filter(Boolean).join(", ")
        )
        const resp = await fetch(
          `https://nominatim.openstreetmap.org/search?format=json&q=${q}&countrycodes=br&limit=1`,
          { headers: { "Accept-Language": "pt-BR" } }
        )
        const hits: { lat: string; lon: string }[] = await resp.json()
        if (!hits.length) {
          toast({ title: "Endereço não encontrado. Verifique os dados.", variant: "destructive" })
          return
        }
        endereco_lat = Number(hits[0].lat)
        endereco_lng = Number(hits[0].lon)
      }

      const res = await calcularCotacao({
        galpao_origem_id: Number(form.galpao_origem_id),
        destino_tipo: form.destino_tipo,
        galpao_destino_id: (form.destino_tipo === "galpao" || form.destino_tipo === "retirada") && form.galpao_destino_id
          ? Number(form.galpao_destino_id) : undefined,
        endereco_destino_lat: endereco_lat,
        endereco_destino_lng: endereco_lng,
        endereco_destino_cidade: form.destino_tipo === "endereco" ? form.destino_cidade : undefined,
        endereco_destino_estado: form.destino_tipo === "endereco" ? form.destino_estado : undefined,
        peso_kg: Number(form.peso_kg),
        comprimento_cm: Number(form.comprimento_cm) || 0,
        largura_cm: Number(form.largura_cm) || 0,
        altura_cm: Number(form.altura_cm) || 0,
        tipo_frete: form.tipo_frete,
      })
      setResultado(res)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        ?? "Erro ao calcular. Verifique a tabela de preços e as coordenadas dos galpões."
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally {
      setCalculando(false)
    }
  }

  const handleSalvar = async () => {
    if (!resultado) return
    setSalvando(true)
    try {
      const orc = await salvarOrcamento(resultado)
      toast({ title: "Orçamento salvo", description: orc.codigo })
      setOrcamentos((prev) => [orc, ...prev])
    } catch {
      toast({ title: "Erro ao salvar", variant: "destructive" })
    } finally { setSalvando(false) }
  }

  const handleDeletar = async (id: number) => {
    if (!window.confirm("Remover este orçamento?")) return
    try {
      await deletarOrcamento(id)
      setOrcamentos((prev) => prev.filter((o) => o.id !== id))
      toast({ title: "Orçamento removido" })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Erro ao remover"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    }
  }

  const handleAprovar = async (id: number) => {
    try {
      const updated = await aprovarOrcamento(id)
      setOrcamentos((prev) => prev.map((o) => o.id === id ? updated : o))
      toast({ title: "Orçamento aprovado e entrega criada" })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Erro ao aprovar"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    }
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <h1 className="text-xl font-semibold">Cotação de Frete</h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["nova", "salvos"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "nova" ? "Nova Cotação" : "Orçamentos Salvos"}
          </button>
        ))}
      </div>

      {/* ── Aba Nova Cotação ── */}
      {tab === "nova" && (
        <div className="space-y-5">
          <Card>
            <CardHeader><CardTitle className="text-base">Dados do envio</CardTitle></CardHeader>
            <CardContent className="space-y-4">

              {/* Galpão origem */}
              <div>
                <Label>Galpão de origem *</Label>
                <Select
                  value={form.galpao_origem_id === "" ? "" : String(form.galpao_origem_id)}
                  onValueChange={(v) => { sf("galpao_origem_id", Number(v)); sf("galpao_destino_id", "") }}
                  disabled={gLoading}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={gLoading ? "Carregando..." : "Selecione"} />
                  </SelectTrigger>
                  <SelectContent>
                    {galpoes.filter((g) => g.ativo).map((g) => (
                      <SelectItem key={g.id} value={String(g.id)}>
                        {g.nome} — {g.cidade}/{g.estado}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Tipo de destino */}
              <div>
                <Label>Tipo de destino</Label>
                <div className="flex gap-4 mt-1 flex-wrap">
                  {(["galpao", "endereco", "retirada"] as const).map((t) => (
                    <label key={t} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="destino_tipo"
                        value={t}
                        checked={form.destino_tipo === t}
                        onChange={() => { sf("destino_tipo", t); sf("galpao_destino_id", "") }}
                        className="accent-primary"
                      />
                      <span className="text-sm">
                        {t === "galpao" ? "Galpão da empresa" : t === "endereco" ? "Endereço do cliente" : "Retirada pelo cliente"}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Destino: galpão */}
              {form.destino_tipo === "galpao" && (
                <div>
                  <Label>Galpão de destino *</Label>
                  <Select
                    value={form.galpao_destino_id === "" ? "" : String(form.galpao_destino_id)}
                    onValueChange={(v) => sf("galpao_destino_id", Number(v))}
                    disabled={gLoading || !form.galpao_origem_id}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={!form.galpao_origem_id ? "Selecione a origem primeiro" : "Selecione"} />
                    </SelectTrigger>
                    <SelectContent>
                      {galpoesDestino.filter((g) => g.ativo).map((g) => (
                        <SelectItem key={g.id} value={String(g.id)}>
                          {g.nome} — {g.cidade}/{g.estado}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Destino: retirada */}
              {form.destino_tipo === "retirada" && (
                <div>
                  <Label>Ponto de retirada *</Label>
                  {pLoading ? (
                    <p className="text-sm text-muted-foreground mt-1 animate-pulse">Carregando...</p>
                  ) : pontosRetirada.length === 0 ? (
                    <p className="text-sm text-muted-foreground mt-1">
                      Nenhuma unidade com retirada habilitada. Configure em Unidades.
                    </p>
                  ) : (
                    <>
                      <Select
                        value={form.galpao_destino_id === "" ? "" : String(form.galpao_destino_id)}
                        onValueChange={(v) => sf("galpao_destino_id", Number(v))}
                      >
                        <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                        <SelectContent>
                          {pontosRetirada.map((p) => (
                            <SelectItem key={p.id} value={String(p.id)}>
                              {p.nome} — {p.cidade}/{p.estado}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground mt-1">
                        O cliente poderá retirar a encomenda nesta unidade
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* Destino: endereço */}
              {form.destino_tipo === "endereco" && (
                <div className="space-y-3 p-3 border rounded-lg bg-muted/30">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2">
                      <Label>Rua</Label>
                      <Input placeholder="Av. Paulista" value={form.destino_rua} onChange={(e) => sf("destino_rua", e.target.value)} />
                    </div>
                    <div>
                      <Label>Número</Label>
                      <Input placeholder="1000" value={form.destino_numero} onChange={(e) => sf("destino_numero", e.target.value)} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>Bairro</Label>
                      <Input placeholder="Bela Vista" value={form.destino_bairro} onChange={(e) => sf("destino_bairro", e.target.value)} />
                    </div>
                    <div>
                      <Label>CEP</Label>
                      <Input placeholder="01310-100" value={form.destino_cep} onChange={(e) => sf("destino_cep", e.target.value)} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>Cidade *</Label>
                      <Input placeholder="São Paulo" value={form.destino_cidade} onChange={(e) => sf("destino_cidade", e.target.value)} />
                    </div>
                    <div>
                      <Label>Estado *</Label>
                      <Select value={form.destino_estado} onValueChange={(v) => sf("destino_estado", v)}>
                        <SelectTrigger><SelectValue placeholder="UF" /></SelectTrigger>
                        <SelectContent>{UFS.map((uf) => <SelectItem key={uf} value={uf}>{uf}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              )}

              {/* Peso e dimensões */}
              <div>
                <Label>Peso do pacote (kg) *</Label>
                <Input type="number" step="0.1" placeholder="10" value={form.peso_kg} onChange={(e) => sf("peso_kg", e.target.value)} />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label>Comprimento (cm)</Label>
                  <Input type="number" placeholder="50" value={form.comprimento_cm} onChange={(e) => sf("comprimento_cm", e.target.value)} />
                </div>
                <div>
                  <Label>Largura (cm)</Label>
                  <Input type="number" placeholder="30" value={form.largura_cm} onChange={(e) => sf("largura_cm", e.target.value)} />
                </div>
                <div>
                  <Label>Altura (cm)</Label>
                  <Input type="number" placeholder="20" value={form.altura_cm} onChange={(e) => sf("altura_cm", e.target.value)} />
                </div>
              </div>

              {/* Tipo de frete */}
              <div>
                <Label>Tipo de frete</Label>
                <div className="flex gap-3 mt-1">
                  {(["padrao", "expresso"] as const).map((t) => (
                    <label key={t} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="tipo_frete"
                        value={t}
                        checked={form.tipo_frete === t}
                        onChange={() => sf("tipo_frete", t)}
                        className="accent-primary"
                      />
                      <span className="text-sm">{t === "padrao" ? "Padrão" : "Expresso"}</span>
                    </label>
                  ))}
                </div>
              </div>

              <Button onClick={handleCalcular} disabled={calculando} className="w-full">
                {calculando ? "Calculando..." : "Calcular"}
              </Button>
            </CardContent>
          </Card>

          {resultado && (
            <Card className="border-primary/30">
              <CardHeader>
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Valor do frete</p>
                    <p className="text-3xl font-bold text-primary">{fmtMoney(resultado.valor_frete)}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Prazo estimado: <span className="font-medium">{resultado.prazo_dias} dia(s) útil(eis)</span>
                      {" · "}
                      {resultado.distancia_km.toFixed(0)} km
                    </p>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <Button size="sm" variant="outline" onClick={() => gerarPdfOrcamento(resultado)}>
                      <FileDown size={15} />PDF
                    </Button>
                    <Button size="sm" onClick={handleSalvar} disabled={salvando}>
                      {salvando ? "Salvando..." : "Salvar orçamento"}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs">De</p>
                    <p className="font-medium">{resultado.galpao_origem.nome}</p>
                    <p className="text-muted-foreground text-xs">{resultado.galpao_origem.cidade}/{resultado.galpao_origem.estado}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Para</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium">{resultado.destino_descricao}</p>
                      {resultado.destino_tipo === "retirada" && (
                        <Badge className="bg-blue-500 text-white text-xs">Retirada</Badge>
                      )}
                    </div>
                  </div>
                </div>

                {resultado.veiculos_elegiveis.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-1">Veículos elegíveis</p>
                    <div className="flex gap-2 flex-wrap">
                      {resultado.veiculos_elegiveis.map((v) => (
                        <Badge key={v.id} variant="secondary">{v.nome} — {v.peso_max_kg} kg</Badge>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <p className="text-sm font-medium mb-2">Paradas intermediárias na rota</p>
                  {resultado.paradas_intermediarias.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Rota direta — sem paradas intermediárias</p>
                  ) : (
                    <div className="space-y-1">
                      {resultado.paradas_intermediarias.map((g) => (
                        <div key={g.id} className="flex items-center justify-between text-sm border rounded-lg px-3 py-2">
                          <div>
                            <span className="font-medium">{g.nome}</span>
                            <span className="text-muted-foreground ml-2 text-xs">{g.cidade}/{g.estado}</span>
                          </div>
                          <Badge variant="secondary" className="text-xs">+1 dia útil</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {resultado.clima_resumo.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Previsão do tempo — {resultado.estado_destino}</p>
                    <div className="grid grid-cols-3 gap-2">
                      {resultado.clima_resumo.map((c) => (
                        <div key={c.data} className="border rounded-lg p-2 text-xs text-center">
                          <p className="font-medium">{fmtDate(c.data)}</p>
                          <p>{c.temp_max?.toFixed(0)}° / {c.temp_min?.toFixed(0)}°</p>
                          {c.precipitacao_mm != null && <p>{c.precipitacao_mm.toFixed(1)} mm</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Aba Orçamentos Salvos ── */}
      {tab === "salvos" && (
        <div className="space-y-3">
          {oLoading ? (
            <div className="text-center py-12 text-muted-foreground animate-pulse">Carregando...</div>
          ) : orcamentos.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground text-sm">Nenhum orçamento salvo.</div>
          ) : (
            <div className="border rounded-xl overflow-hidden bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Rota</TableHead>
                    <TableHead>Valor</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Validade</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {orcamentos.map((o) => (
                    <TableRow key={o.id}>
                      <TableCell className="font-mono text-xs">{o.codigo}</TableCell>
                      <TableCell className="text-sm">
                        {o.estado_origem} → {o.destino_descricao || o.estado_destino}
                      </TableCell>
                      <TableCell className="font-medium">{fmtMoney(o.valor_frete)}</TableCell>
                      <TableCell>
                        <Badge variant={STATUS_BADGE[o.status] ?? "secondary"}>{o.status}</Badge>
                      </TableCell>
                      <TableCell className="text-sm">{fmtDate(o.validade_em)}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => setDetalhes(o)}>Ver</Button>
                          <Button size="sm" variant="ghost" onClick={() => gerarPdfOrcamento(o)}>
                            <FileDown size={14} />
                          </Button>
                          {(o.status === "rascunho" || o.status === "enviado") && (
                            <Button size="sm" variant="ghost" onClick={() => handleAprovar(o.id)}>
                              <Check size={14} />
                            </Button>
                          )}
                          {(o.status === "rascunho" || o.status === "expirado") && (
                            <Button size="sm" variant="ghost" onClick={() => handleDeletar(o.id)}>
                              <Trash2 size={14} />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}

      {/* Modal detalhes orçamento */}
      <Dialog open={!!detalhes} onOpenChange={() => setDetalhes(null)}>
        {detalhes && (
          <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{detalhes.codigo}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                {[
                  ["Origem", detalhes.estado_origem],
                  ["Destino", detalhes.destino_descricao || detalhes.estado_destino],
                  ["Distância", `${detalhes.distancia_km.toFixed(0)} km`],
                  ["Peso", `${detalhes.peso_kg} kg`],
                  ["Dimensões", `${detalhes.comprimento_cm}×${detalhes.largura_cm}×${detalhes.altura_cm} cm`],
                  ["Tipo", detalhes.tipo_frete === "expresso" ? "Expresso" : "Padrão"],
                  ["Prazo", `${detalhes.prazo_dias} dia(s)`],
                  ["Valor", fmtMoney(detalhes.valor_frete)],
                  ["Validade", fmtDate(detalhes.validade_em)],
                  ["Criado em", fmtDate(detalhes.criado_em)],
                ].map(([k, v]) => (
                  <div key={k}>
                    <p className="text-muted-foreground text-xs">{k}</p>
                    <p className="font-medium">{v}</p>
                  </div>
                ))}
              </div>
              {detalhes.galpoes_rota && detalhes.galpoes_rota.length > 0 && (
                <div>
                  <p className="text-muted-foreground text-xs mb-1">Paradas intermediárias</p>
                  {detalhes.galpoes_rota.map((g) => (
                    <p key={g.id} className="text-sm">{g.nome} — {g.cidade}/{g.estado}</p>
                  ))}
                </div>
              )}
              <div className="flex gap-2 pt-2">
                <Button size="sm" variant="outline" onClick={() => gerarPdfOrcamento(detalhes)}>
                  <FileDown size={14} />Gerar PDF
                </Button>
                {(detalhes.status === "rascunho" || detalhes.status === "enviado") && (
                  <Button size="sm" onClick={() => { handleAprovar(detalhes.id); setDetalhes(null) }}>
                    Aprovar
                  </Button>
                )}
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  )
}
