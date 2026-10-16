import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Data/hora local sem offset de fuso ("YYYY-MM-DDTHH:mm:ss").
 * O backend grava as datas da entrega como timestamp sem fuso (horário local),
 * então enviar `toISOString()` (UTC com "Z") deslocaria o horário em 3h.
 */
export function toLocalISOString(date: Date = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0")
  return (
    `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}` +
    `T${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}`
  )
}

/** Data local de hoje no formato "YYYY-MM-DD" (para inputs type="date"). */
export function todayLocal(): string {
  return toLocalISOString().split("T")[0]
}
