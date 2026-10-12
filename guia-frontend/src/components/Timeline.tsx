import { MapPin, CheckCircle } from "lucide-react"
import type { CheckpointResponse } from "@/types"

interface TimelineProps {
  checkpoints: CheckpointResponse[]
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
}

export default function Timeline({ checkpoints }: TimelineProps) {
  if (checkpoints.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <h3 className="font-semibold mb-2">Histórico de movimentação</h3>
        <p className="text-sm text-muted-foreground">Nenhum checkpoint registrado ainda.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="font-semibold mb-5">Histórico de movimentação</h3>
      <div>
        {checkpoints.map((cp, i) => {
          const isLast = i === checkpoints.length - 1
          return (
            <div key={cp.id} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full shrink-0",
                  isLast ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                )}>
                  {isLast ? <CheckCircle size={15} /> : <MapPin size={15} />}
                </div>
                {!isLast && <div className="flex-1 w-px bg-border mt-1 mb-1 min-h-[20px]" />}
              </div>
              <div className="pb-5 flex-1">
                <p className="font-medium text-sm leading-tight">{cp.galpao.nome}</p>
                <p className="text-xs text-muted-foreground">{cp.galpao.cidade} / {cp.galpao.estado}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{fmtDate(cp.chegou_em)}</p>
                {cp.observacao && <p className="text-xs text-muted-foreground italic mt-0.5">"{cp.observacao}"</p>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ")
}
