import jsPDF from "jspdf"
import autoTable from "jspdf-autotable"
import type { Orcamento, ResultadoCotacao } from "@/types"

const CAPITAL_COORDS: Record<string, [number, number]> = {
  AC: [-9.9754, -67.8249], AL: [-9.6658, -35.735], AM: [-3.119, -60.0217],
  AP: [0.0349, -51.0694], BA: [-12.9714, -38.5014], CE: [-3.7172, -38.543],
  DF: [-15.7797, -47.9297], ES: [-20.3194, -40.3378], GO: [-16.6869, -49.2648],
  MA: [-2.5297, -44.3028], MG: [-19.9191, -43.9386], MS: [-20.4428, -54.6459],
  MT: [-15.5989, -56.0949], PA: [-1.4558, -48.5044], PB: [-7.1195, -34.845],
  PE: [-8.0584, -34.8848], PI: [-5.0892, -42.8019], PR: [-25.4195, -49.2647],
  RJ: [-22.9035, -43.1724], RN: [-5.7945, -35.211], RO: [-8.7612, -63.9004],
  RR: [2.8235, -60.6758], RS: [-30.0368, -51.209], SC: [-27.5954, -48.548],
  SE: [-10.9472, -37.0731], SP: [-23.5489, -46.6388], TO: [-10.2491, -48.3243],
}

async function fetchMapBase64(
  olat: number, olng: number, dlat: number, dlng: number
): Promise<string | null> {
  try {
    const clat = (olat + dlat) / 2
    const clng = (olng + dlng) / 2
    const url =
      `https://staticmap.openstreetmap.de/staticmap.php` +
      `?center=${clat},${clng}&zoom=5&size=600x300` +
      `&markers=${olat},${olng},red-pushpin` +
      `&markers=${dlat},${dlng},green-pushpin`
    const resp = await fetch(url)
    if (!resp.ok) return null
    const blob = await resp.blob()
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = () => resolve(null)
      reader.readAsDataURL(blob)
    })
  } catch {
    return null
  }
}

type Input = Orcamento | ResultadoCotacao

function isSaved(d: Input): d is Orcamento {
  return "codigo" in d
}

function fmtDate(iso?: string) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("pt-BR")
}

function fmtMoney(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}

export async function gerarPdfOrcamento(data: Input): Promise<void> {
  const doc = new jsPDF({ unit: "mm", format: "a4" })
  const W = doc.internal.pageSize.getWidth()
  let y = 15

  const codigo = isSaved(data) ? data.codigo : "PRÉVIA"
  const validade = isSaved(data)
    ? fmtDate(data.validade_em)
    : fmtDate(new Date(Date.now() + 3 * 86400000).toISOString())
  const emissao = isSaved(data)
    ? fmtDate(data.criado_em)
    : fmtDate(new Date().toISOString())

  // ── Cabeçalho ──────────────────────────────────────────────────────────
  doc.setFontSize(26)
  doc.setTextColor(37, 99, 235)
  doc.setFont("helvetica", "bold")
  doc.text("guIA", 15, y)

  doc.setFontSize(9)
  doc.setTextColor(80, 80, 80)
  doc.setFont("helvetica", "normal")
  doc.text(`Código: ${codigo}`, W - 15, y - 5, { align: "right" })
  doc.text(`Emissão: ${emissao}`, W - 15, y, { align: "right" })
  doc.text(`Válido até: ${validade}`, W - 15, y + 5, { align: "right" })

  y += 12
  doc.setDrawColor(220, 220, 220)
  doc.line(15, y, W - 15, y)
  y += 8

  // ── Rota ───────────────────────────────────────────────────────────────
  doc.setFontSize(13)
  doc.setTextColor(30, 30, 30)
  doc.setFont("helvetica", "bold")
  doc.text("Rota", 15, y)
  y += 6

  doc.setFontSize(18)
  doc.setTextColor(37, 99, 235)
  doc.text(`${data.estado_origem}  →  ${data.estado_destino}`, 15, y)
  y += 7

  doc.setFontSize(9)
  doc.setTextColor(80, 80, 80)
  doc.setFont("helvetica", "normal")
  const dur = data.duracao_min
    ? `  ·  Duração estimada: ${Math.round(data.duracao_min / 60)}h`
    : ""
  doc.text(`Distância: ${data.distancia_km.toFixed(0)} km${dur}`, 15, y)
  y += 10

  // ── Mapa ───────────────────────────────────────────────────────────────
  const oCoords = CAPITAL_COORDS[data.estado_origem]
  const dCoords = CAPITAL_COORDS[data.estado_destino]
  if (oCoords && dCoords) {
    const mapB64 = await fetchMapBase64(oCoords[0], oCoords[1], dCoords[0], dCoords[1])
    if (mapB64) {
      const mapH = 45
      const mapW = W - 30
      doc.addImage(mapB64, "PNG", 15, y, mapW, mapH)
      y += mapH + 5
    }
  }

  // ── Paradas Intermediárias ─────────────────────────────────────────────
  const paradas = isSaved(data) ? (data.galpoes_rota ?? []) : data.paradas_intermediarias
  if (paradas.length > 0) {
    doc.setFontSize(11)
    doc.setFont("helvetica", "bold")
    doc.setTextColor(30, 30, 30)
    doc.text("Paradas Intermediárias", 15, y)
    y += 4
    autoTable(doc, {
      startY: y,
      head: [["Unidade", "Cidade", "Estado"]],
      body: paradas.map((g) => [g.nome, g.cidade, g.estado]),
      styles: { fontSize: 8 },
      headStyles: { fillColor: [37, 99, 235] },
      margin: { left: 15, right: 15 },
    })
    y = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 6
  }

  // ── Veículo sugerido ───────────────────────────────────────────────────
  const veiculos = "veiculos_elegiveis" in data ? data.veiculos_elegiveis : []
  if (veiculos.length > 0) {
    const v = veiculos[0]
    doc.setFontSize(11)
    doc.setFont("helvetica", "bold")
    doc.setTextColor(30, 30, 30)
    doc.text("Veículo Sugerido", 15, y)
    y += 4
    autoTable(doc, {
      startY: y,
      head: [["Nome", "Tipo", "Capacidade Máxima"]],
      body: [[v.nome, v.tipo.replace(/_/g, " "), `${v.peso_max_kg} kg`]],
      styles: { fontSize: 8 },
      headStyles: { fillColor: [37, 99, 235] },
      margin: { left: 15, right: 15 },
    })
    y = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 6
  }

  // ── Previsão do tempo ──────────────────────────────────────────────────
  const clima = data.clima_resumo ?? []
  if (clima.length > 0) {
    doc.setFontSize(11)
    doc.setFont("helvetica", "bold")
    doc.setTextColor(30, 30, 30)
    doc.text(`Previsão do Tempo — ${data.estado_destino}`, 15, y)
    y += 4
    autoTable(doc, {
      startY: y,
      head: [["Data", "Máx (°C)", "Mín (°C)", "Precipitação (mm)"]],
      body: clima.map((c) => [
        fmtDate(c.data),
        c.temp_max?.toFixed(1) ?? "—",
        c.temp_min?.toFixed(1) ?? "—",
        c.precipitacao_mm?.toFixed(1) ?? "—",
      ]),
      styles: { fontSize: 8 },
      headStyles: { fillColor: [37, 99, 235] },
      margin: { left: 15, right: 15 },
    })
    y = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 6
  }

  // ── Detalhamento do frete ──────────────────────────────────────────────
  doc.setFontSize(11)
  doc.setFont("helvetica", "bold")
  doc.setTextColor(30, 30, 30)
  doc.text("Detalhamento do Frete", 15, y)
  y += 4

  const rows: string[][] = [
    ["Distância", `${data.distancia_km.toFixed(0)} km`, ""],
    ["Tipo de frete", data.tipo_frete === "expresso" ? "Expresso" : "Padrão", ""],
    ["Prazo estimado", `${data.prazo_dias} dia(s) útil(eis)`, ""],
    ["Valor total", "", fmtMoney(data.valor_frete)],
  ]

  autoTable(doc, {
    startY: y,
    head: [["Item", "Detalhe", "Valor"]],
    body: rows,
    styles: { fontSize: 9 },
    headStyles: { fillColor: [37, 99, 235] },
    columnStyles: { 2: { halign: "right", fontStyle: "bold" } },
    margin: { left: 15, right: 15 },
  })
  y = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 8

  // Valor destacado
  doc.setFontSize(14)
  doc.setFont("helvetica", "bold")
  doc.setTextColor(37, 99, 235)
  doc.text(`Total: ${fmtMoney(data.valor_frete)}`, W - 15, y, { align: "right" })
  y += 6

  // ── Rodapé ─────────────────────────────────────────────────────────────
  const pageH = doc.internal.pageSize.getHeight()
  doc.setFontSize(7)
  doc.setTextColor(150, 150, 150)
  doc.setFont("helvetica", "normal")
  doc.text(`Orçamento válido até ${validade}`, 15, pageH - 10)
  doc.text("Documento gerado por guIA — sistema de logística inteligente", W / 2, pageH - 10, {
    align: "center",
  })

  const filename = isSaved(data) ? `orcamento-${data.codigo}.pdf` : "orcamento-previa.pdf"
  doc.save(filename)
}
