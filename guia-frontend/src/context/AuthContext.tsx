import { createContext, useState, useEffect, useCallback } from "react"
import type { User } from "@/types"
import { apiLogin, apiMe } from "@/api/auth"

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (email: string, senha: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const savedUser = localStorage.getItem("guia_user")
    const savedToken = localStorage.getItem("guia_token")
    if (savedUser && savedToken) {
      try {
        setUser(JSON.parse(savedUser))
      } catch {
        localStorage.removeItem("guia_user")
        localStorage.removeItem("guia_token")
      }
    }
    setIsLoading(false)
  }, [])

  const login = useCallback(async (email: string, senha: string) => {
    const { access_token } = await apiLogin(email, senha)
    localStorage.setItem("guia_token", access_token)
    const me = await apiMe()
    localStorage.setItem("guia_user", JSON.stringify(me))
    setUser(me)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("guia_token")
    localStorage.removeItem("guia_user")
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
