import { NavLink, useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useAuth } from "@/hooks/useAuth"
import { Button } from "@/components/ui/button"
import { LayoutDashboard, Package, Warehouse, LogOut, Users, Calculator, Truck, DollarSign } from "lucide-react"

type Role = "empresa" | "admin"

const LINKS: Record<Role, { to: string; label: string; icon: React.ElementType; end?: boolean }[]> = {
  empresa: [
    { to: "/dashboard",         label: "Início",   icon: LayoutDashboard, end: true },
    { to: "/dashboard/entregas", label: "Entregas", icon: Package },
    { to: "/dashboard/galpoes",  label: "Unidades", icon: Warehouse },
    { to: "/dashboard/cotacao",    label: "Cotação",    icon: Calculator },
    { to: "/dashboard/financeiro", label: "Financeiro", icon: DollarSign },
    { to: "/dashboard/frota",      label: "Minha Frota", icon: Truck },
  ],
  admin: [
    { to: "/admin",          label: "Início",    icon: LayoutDashboard, end: true },
    { to: "/admin/empresas", label: "Empresas",  icon: Users },
  ],
}

export default function Sidebar({ role }: { role: Role }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const links = LINKS[role]

  return (
    <aside className="fixed left-0 top-0 h-full w-60 border-r bg-card flex flex-col z-10">
      <div className="px-6 py-5 border-b">
        <span className="text-xl font-bold text-primary tracking-tight">guIA</span>
      </div>
      <nav className="flex-1 p-3 space-y-0.5">
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-muted-foreground"
          onClick={() => { logout(); navigate("/login") }}
        >
          <LogOut size={17} />
          Sair
        </Button>
      </div>
    </aside>
  )
}
