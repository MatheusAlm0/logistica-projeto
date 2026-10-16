import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider } from "@/context/AuthContext"
import { ThemeProvider } from "@/context/ThemeContext"
import { Toaster } from "@/components/ui/toaster"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import RastreioPage from "@/pages/Rastreio"
import LoginPage from "@/pages/Login"
import DashboardLayout from "@/pages/Dashboard/Layout"
import DashboardHome from "@/pages/Dashboard"
import EntregasPage from "@/pages/Dashboard/Entregas"
import EntregaDetalhePage from "@/pages/Dashboard/Entregas/Detalhe"
import GalpoesPage from "@/pages/Dashboard/Galpoes"
import FrotaPage from "@/pages/Dashboard/Frota"
import CotacaoPage from "@/pages/Dashboard/Cotacao"
import FinanceiroPage from "@/pages/Dashboard/Financeiro"
import AdminLayout from "@/pages/Admin/Layout"
import AdminHome from "@/pages/Admin"
import EmpresasPage from "@/pages/Admin/Empresas"

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/rastreio" replace />} />
            <Route path="/rastreio" element={<RastreioPage />} />
            <Route path="/rastreio/:codigo" element={<RastreioPage />} />
            <Route path="/login" element={<LoginPage />} />

            <Route element={<ProtectedRoute roles={["empresa"]} />}>
              <Route path="/dashboard" element={<DashboardLayout />}>
                <Route index element={<DashboardHome />} />
                <Route path="entregas" element={<EntregasPage />} />
                <Route path="entregas/:id" element={<EntregaDetalhePage />} />
                <Route path="galpoes" element={<GalpoesPage />} />
                <Route path="frota" element={<FrotaPage />} />
                <Route path="cotacao" element={<CotacaoPage />} />
                <Route path="financeiro" element={<FinanceiroPage />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute roles={["admin"]} />}>
              <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<AdminHome />} />
                <Route path="empresas" element={<EmpresasPage />} />
              </Route>
            </Route>
          </Routes>
          <Toaster />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
