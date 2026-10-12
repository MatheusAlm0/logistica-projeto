import { useEffect, useState } from "react"
import { getEmpresasPendentes, aprovarEmpresa, bloquearEmpresa } from "@/api/admin"
import type { User } from "@/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "@/hooks/use-toast"
import { RefreshCw } from "lucide-react"

function fmtDate(iso?: string) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("pt-BR")
}

export default function EmpresasPage() {
  const [empresas, setEmpresas] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [actionId, setActionId] = useState<number | null>(null)

  async function load() {
    setIsLoading(true)
    try {
      const data = await getEmpresasPendentes()
      setEmpresas(data)
    } catch {
      toast({ title: "Erro ao carregar empresas", variant: "destructive" })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleAprovar(id: number) {
    setActionId(id)
    try {
      await aprovarEmpresa(id)
      toast({ title: "Empresa aprovada" })
      load()
    } catch {
      toast({ title: "Erro ao aprovar", variant: "destructive" })
    } finally {
      setActionId(null)
    }
  }

  async function handleBloquear(id: number) {
    setActionId(id)
    try {
      await bloquearEmpresa(id)
      toast({ title: "Empresa bloqueada" })
      load()
    } catch {
      toast({ title: "Erro ao bloquear", variant: "destructive" })
    } finally {
      setActionId(null)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Empresas pendentes</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Cadastros aguardando aprovação</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={isLoading}>
          <RefreshCw size={15} className={isLoading ? "animate-spin" : ""} />
          Atualizar
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground animate-pulse">Carregando...</div>
      ) : empresas.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-sm">Nenhuma empresa aguardando aprovação.</p>
          <p className="text-xs mt-1 opacity-60">Empresas aprovadas não aparecem nesta lista.</p>
        </div>
      ) : (
        <div className="border rounded-xl overflow-hidden bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>E-mail</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Cliente ID</TableHead>
                <TableHead>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {empresas.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="font-medium">{e.nome}</TableCell>
                  <TableCell className="text-sm">{e.email}</TableCell>
                  <TableCell>
                    <Badge variant={e.ativo ? "success" : "secondary"}>
                      {e.ativo ? "Ativa" : "Pendente"}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{e.cliente_id}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleAprovar(e.id)}
                        disabled={actionId === e.id}
                      >
                        Aprovar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleBloquear(e.id)}
                        disabled={actionId === e.id}
                      >
                        Bloquear
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
