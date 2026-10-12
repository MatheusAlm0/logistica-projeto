import { Badge } from "@/components/ui/badge"
import type { StatusEntrega } from "@/types"

type Variant = "default" | "secondary" | "destructive" | "outline" | "success" | "warning"

const STATUS_MAP: Record<StatusEntrega, { label: string; variant: Variant }> = {
  pendente:    { label: "Pendente",    variant: "secondary" },
  em_transito: { label: "Em trânsito", variant: "default" },
  entregue:    { label: "Entregue",    variant: "success" },
  atrasada:    { label: "Atrasada",    variant: "destructive" },
  cancelado:   { label: "Cancelado",   variant: "warning" },
}

export default function StatusBadge({ status }: { status: StatusEntrega }) {
  const cfg = STATUS_MAP[status] ?? { label: status, variant: "secondary" as Variant }
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>
}
