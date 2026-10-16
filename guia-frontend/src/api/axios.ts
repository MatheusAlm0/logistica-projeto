import axios from "axios"

const api = axios.create({
  baseURL: "http://localhost:8000",
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("guia_token")
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const url: string = error.config?.url ?? ""
    const isAuthRequest = url.startsWith("/auth/")
    const tokenEnviado = !!error.config?.headers?.Authorization
    // 401 em /auth/* (ex.: senha errada no login) é tratado pela própria tela.
    // Só encerra a sessão quando um token foi enviado e rejeitado (expirado/inválido).
    if (error.response?.status === 401 && !isAuthRequest && tokenEnviado) {
      localStorage.removeItem("guia_token")
      localStorage.removeItem("guia_user")
      if (window.location.pathname !== "/login") window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)

export default api
