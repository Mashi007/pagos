import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'
import { env } from '@/config/env'
import { 
  safeGetItem, 
  safeGetSessionItem,
  safeSetItem,
  safeSetSessionItem,
  safeRemoveItem,
  safeRemoveSessionItem,
  clearAuthStorage
} from '@/utils/storage'

const safeClear = () => {
  try {
    localStorage.clear()
    return true
  } catch {
    return false
  }
}

const safeClearSession = () => {
  try {
    sessionStorage.clear()
    return true
  } catch {
    return false
  }
}

// Constantes de configuración
const DEFAULT_TIMEOUT_MS = 30000

// Configuración base de Axios
const API_BASE_URL = env.API_URL

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: DEFAULT_TIMEOUT_MS,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor - agregar token de autenticación
    this.client.interceptors.request.use(
      (config) => {
        // NO agregar token a endpoints de autenticación
        const authEndpoints = ['/api/v1/auth/login', '/api/v1/auth/refresh']
        const isAuthEndpoint = authEndpoints.some(endpoint => config.url?.includes(endpoint))
        
        if (!isAuthEndpoint) {
          // Obtener token de forma segura
          const rememberMe = safeGetItem('remember_me', false)
          const token = rememberMe 
            ? safeGetItem('access_token', '') 
            : safeGetSessionItem('access_token', '')
          
          if (token) {
            config.headers.Authorization = `Bearer ${token}`
          }
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor - manejar errores globalmente
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config

        // Auto-refresh de tokens con protección contra loops infinitos
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          try {
            // No intentar refresh en endpoints de autenticación
            const authEndpoints = ['/api/v1/auth/login', '/api/v1/auth/refresh']
            const isAuthEndpoint = authEndpoints.some(endpoint => originalRequest.url?.includes(endpoint))
            
            if (isAuthEndpoint) {
              // En endpoints de auth, simplemente propagar el error sin intentar refresh
              this.handleError(error)
              return Promise.reject(error)
            }

            const rememberMe = safeGetItem('remember_me', false)
            const refreshToken = rememberMe 
              ? safeGetItem('refresh_token', '') 
              : safeGetSessionItem('refresh_token', '')
              
            if (refreshToken) {
              const response = await this.client.post('/api/v1/auth/refresh', {
                refresh_token: refreshToken,
              })
              
              const { access_token, refresh_token: newRefreshToken } = response.data
              
              // Guardar en el almacenamiento correspondiente usando funciones seguras
              if (rememberMe) {
                safeSetItem('access_token', access_token)
                safeSetItem('refresh_token', newRefreshToken)
              } else {
                safeSetSessionItem('access_token', access_token)
                safeSetSessionItem('refresh_token', newRefreshToken)
              }

              // Reintentar la petición original
              originalRequest.headers.Authorization = `Bearer ${access_token}`
              return this.client(originalRequest)
            } else {
              throw new Error('No refresh token available')
            }
          } catch (refreshError) {
            // Si no se puede renovar el token, limpiar datos y redirigir al login
            clearAuthStorage()
            
            // Evitar mostrar toasts durante el redirect
            const isAlreadyRedirecting = window.location.pathname === '/login'
            
            if (!isAlreadyRedirecting) {
              // Pequeño delay para asegurar que el storage se limpie
              setTimeout(() => {
                window.location.href = '/login'
              }, 100)
            }
            
            return Promise.reject(refreshError)
          }
        }

        // Manejar otros errores
        this.handleError(error)
        return Promise.reject(error)
      }
    )
  }

  private handleError(error: any) {
    if (error.response) {
      // Error del servidor
      const { status, data } = error.response
      
      // Evitar mostrar toast de 401 cuando está siendo manejado por el interceptor
      const isBeingHandledByInterceptor = error.config?._retry !== undefined
      
      switch (status) {
        case 400:
          toast.error(data.message || 'Datos inválidos')
          break
        case 401:
          // No mostrar toast si está siendo manejado por el interceptor de refresh
          if (!isBeingHandledByInterceptor) {
            toast.error('Sesión expirada. Redirigiendo al inicio de sesión...')
          }
          break
        case 403:
          toast.error('Sin permisos para esta acción')
          break
        case 404:
          toast.error('Recurso no encontrado')
          break
        case 422:
          // Errores de validación
          if (data.detail && Array.isArray(data.detail)) {
            data.detail.forEach((err: any) => {
              toast.error(`${err.loc?.join(' ')}: ${err.msg}`)
            })
          } else {
            toast.error(data.message || 'Error de validación')
          }
          break
        case 500:
          toast.error('Error interno del servidor')
          break
        case 409:
          toast.error(data?.message || 'Conflicto de datos. Verifica la información.')
          break
        case 400:
          // Error de validación o cliente duplicado (misma cédula y mismo nombre)
          if (typeof data?.detail === 'string') {
            toast.error(data.detail)
          } else {
            toast.error(data?.message || 'Error de validación')
          }
          break
        case 503:
          // NO mostrar toast genérico para errores 503 de duplicados
          // Permitir que el componente maneje el error específico
          if (data?.detail?.includes('duplicate key') || data?.detail?.includes('already exists') ||
              data?.detail?.includes('violates unique constraint') || data?.detail?.includes('cédula') ||
              data?.message?.includes('duplicate key') || data?.message?.includes('already exists')) {
            // No mostrar toast, dejar que el componente maneje el popup
            return Promise.reject(error) // ✅ CORRECCIÓN: Asegurar que se propague el error
          } else {
            toast.error('Servicio temporalmente no disponible. Intenta nuevamente.')
          }
          break
        default:
          if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
            toast.error('Tiempo de espera agotado. Verifica tu conexión.')
          } else if (error.message?.includes('Network Error') || error.code === 'ERR_NETWORK') {
            toast.error('Error de conexión. Verifica que el servidor esté funcionando.')
          } else {
            toast.error(data.message || 'Error desconocido')
          }
      }
    } else if (error.request) {
      // Error de red
      toast.error('Error de conexión. Verifique su conexión a internet.')
    } else {
      // Error de configuración
      toast.error('Error en la configuración de la petición')
    }
  }

  // Métodos HTTP
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.get(url, config)
    return response.data
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.post(url, data, config)
    return response.data
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.put(url, data, config)
    return response.data
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.patch(url, data, config)
    return response.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(url, config)
    return response.data
  }

  // Método para subir archivos
  async uploadFile<T>(
    url: string,
    file: File,
    onUploadProgress?: (progressEvent: any) => void
  ): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)

    const response: AxiosResponse<T> = await this.client.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    })

    return response.data
  }

  // Método para descargar archivos
  async downloadFile(url: string, filename: string): Promise<void> {
    const response = await this.client.get(url, {
      responseType: 'blob',
    })

    const blob = new Blob([response.data])
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  }

  // Obtener instancia de Axios para casos especiales
  getAxiosInstance(): AxiosInstance {
    return this.client
  }

  // FUNCIÓN DE EMERGENCIA: Limpiar completamente el storage
  emergencyClearStorage(): void {
    try {
      // Limpiar localStorage
      safeClear()
      // Limpiar sessionStorage  
      safeClearSession()
      // Limpiar específicamente tokens de auth
      clearAuthStorage()
    } catch (error) {
      // Error silencioso para evitar loops de logging
    }
  }
}

// Instancia singleton del cliente API
export const apiClient = new ApiClient()

// FUNCIÓN GLOBAL DE EMERGENCIA: Limpiar storage desde consola del navegador
// Uso: window.clearAuthStorage() en la consola del navegador
if (typeof window !== 'undefined') {
  (window as any).clearAuthStorage = () => {
    apiClient.emergencyClearStorage()
    window.location.reload()
  }
}

// Tipos para respuestas de API
export interface ApiResponse<T> {
  data: T
  message: string
  success: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// Funciones de utilidad para construir URLs con parámetros
export function buildUrl(baseUrl: string, params?: Record<string, any>): string {
  if (!params) return baseUrl

  const searchParams = new URLSearchParams()
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      if (Array.isArray(value)) {
        value.forEach(v => searchParams.append(key, String(v)))
      } else {
        searchParams.append(key, String(value))
      }
    }
  })

  const queryString = searchParams.toString()
  return queryString ? `${baseUrl}?${queryString}` : baseUrl
}

// Hook personalizado para manejar estados de carga
export function useApiState() {
  return {
    loading: false,
    error: null,
    success: false,
  }
}
