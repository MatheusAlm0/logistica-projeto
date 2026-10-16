import { Component, type ErrorInfo, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { AlertTriangle } from "lucide-react"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

/** Captura erros de renderização e mostra uma tela amigável em vez da tela em branco. */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Erro não tratado na interface:", error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="w-full max-w-sm bg-card border rounded-xl p-6 shadow-sm text-center space-y-4">
          <AlertTriangle className="mx-auto text-destructive" size={36} />
          <div className="space-y-1">
            <h1 className="text-lg font-semibold">Algo deu errado</h1>
            <p className="text-sm text-muted-foreground">
              Ocorreu um erro inesperado ao exibir esta página. Recarregue para tentar novamente.
            </p>
          </div>
          <Button className="w-full" onClick={() => window.location.reload()}>
            Recarregar
          </Button>
        </div>
      </div>
    )
  }
}
