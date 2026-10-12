import ThemeToggle from "./ThemeToggle"
import { useAuth } from "@/hooks/useAuth"

export default function Header() {
  const { user } = useAuth()
  return (
    <header className="h-14 border-b bg-card flex items-center justify-between px-6 shrink-0">
      <span className="text-sm text-muted-foreground truncate">{user?.nome}</span>
      <ThemeToggle />
    </header>
  )
}
