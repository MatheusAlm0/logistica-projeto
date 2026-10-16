import { useState, FormEvent } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import ThemeToggle from "@/components/ThemeToggle"
import { getErrorMessage, getErrorStatus } from "@/lib/errors"

export default function LoginPage() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState("")
  const [senha, setSenha] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  if (user) return <Navigate to={user.role === "admin" ? "/admin" : "/dashboard"} replace />

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)
    try {
      await login(email, senha)
      // redirect is handled by useEffect in AuthContext + ProtectedRoute
    } catch (err: unknown) {
      const status = getErrorStatus(err)
      if (status === 403) {
        setError("Conta aguardando aprovação do administrador.")
      } else if (status === 401) {
        setError("E-mail ou senha incorretos.")
      } else {
        setError(getErrorMessage(err, "Erro ao entrar. Tente novamente."))
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="flex justify-end p-4">
        <ThemeToggle />
      </div>

      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-primary tracking-tight">guIA</h1>
            <p className="text-muted-foreground text-sm mt-1">Sistema de logística inteligente</p>
          </div>

          <div className="bg-card border rounded-xl p-6 shadow-sm">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="email">E-mail</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="empresa@exemplo.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="senha">Senha</Label>
                <Input
                  id="senha"
                  type="password"
                  placeholder="••••••••"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  required
                />
              </div>

              {error && (
                <p className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">{error}</p>
              )}

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Entrando..." : "Entrar"}
              </Button>
            </form>
          </div>

          <p className="text-center text-xs text-muted-foreground mt-4">
            Para rastrear uma encomenda,{" "}
            <a href="/rastreio" className="text-primary underline underline-offset-2">clique aqui</a>
          </p>
        </div>
      </div>
    </div>
  )
}
