import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'

// Configuración base de Axios
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://pagos-f2qf.onrender.com'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
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
          // PRIMERO: Verificar localStorage (recordarme)
          const localToken = localStorage.getItem('access_token')
          const localUser = localStorage.getItem('user')
          
          // SEGUNDO: Si no hay en localStorage, verificar sessionStorage
          const sessionToken = sessionStorage.getItem('access_token')
          const sessionUser = sessionStorage.getItem('user')
          
          // DETERMINAR: Qué token usar basado en qué datos existen
          // PRIORIZAR: Si hay token en localStorage, usarlo (incluso si no hay user)
          const hasLocalToken = !!localToken
          const hasSessionToken = !!sessionToken
          
          let token, storageType
          
          if (hasLocalToken) {
            token = localToken
            storageType = 'localStorage'
            console.log('🔍 Interceptor: Usando token de localStorage (prioridad)')
          } else if (hasSessionToken) {
            token = sessionToken
            storageType = 'sessionStorage'
            console.log('🔍 Interceptor: Usando token de sessionStorage (fallback)')
          } else {
            token = null
            storageType = 'none'
            console.log('🔍 Interceptor: No hay tokens disponibles')
          }
            
          if (token && token.trim() !== '') {
            config.headers.Authorization = `Bearer ${token}`
            console.log('🔑 Token enviado en request:', config.url, token.substring(0, 20) + '...')
            console.log('🔍 Headers configurados:', {
              Authorization: config.headers.Authorization ? 'SET' : 'NOT_SET',
              ContentType: config.headers['Content-Type'],
              url: config.url
            })
          } else {
            console.warn('⚠️ No se encontró token para la request:', config.url)
            console.error('🚨 CRÍTICO: Request sin token - esto causará 403 Forbidden')
            console.log('🔍 Debug completo de storage MEJORADO:', {
              hasLocalToken,
              hasSessionToken,
              storageType,
              localStorage: {
                access_token: localStorage.getItem('access_token') ? 'EXISTS' : 'NOT_FOUND',
                refresh_token: localStorage.getItem('refresh_token') ? 'EXISTS' : 'NOT_FOUND',
                user: localStorage.getItem('user') ? 'EXISTS' : 'NOT_FOUND',
                remember_me: localStorage.getItem('remember_me')
              },
              sessionStorage: {
                access_token: sessionStorage.getItem('access_token') ? 'EXISTS' : 'NOT_FOUND',
                refresh_token: sessionStorage.getItem('refresh_token') ? 'EXISTS' : 'NOT_FOUND',
                user: sessionStorage.getItem('user') ? 'EXISTS' : 'NOT_FOUND'
              }
            })
            // Para endpoints que requieren autenticación, cancelar la request
            const protectedEndpoints = ['/api/v1/clientes', '/api/v1/concesionarios/activos', '/api/v1/asesores/activos', '/api/v1/dashboard', '/api/v1/configuracion', '/api/v1/validadores']
            const unprotectedEndpoints = ['/api/v1/clientes-temp/test-sin-auth', '/api/v1/health', '/api/v1/auth/login', '/api/v1/validadores/test-simple']
            
            // Usar startsWith para evitar coincidencias parciales
            const isProtectedEndpoint = protectedEndpoints.some(endpoint => config.url?.startsWith(endpoint))
            const isUnprotectedEndpoint = unprotectedEndpoints.some(endpoint => config.url?.includes(endpoint))
            
            if (isProtectedEndpoint && !isUnprotectedEndpoint) {
              console.error('🚫 Request protegida sin token, intentando continuar:', config.url)
              // En lugar de cancelar, intentar continuar y dejar que el backend responda con 401
              // Esto permitirá que el interceptor de respuesta maneje la renovación del token
              console.log('⚠️ Continuando request sin token - el backend manejará la autenticación')
            } else if (isUnprotectedEndpoint) {
              console.log('✅ Endpoint no protegido, continuando sin token:', config.url)
            } else {
              console.log('ℹ️ Endpoint no clasificado, continuando sin token:', config.url)
            }
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

        // Si el token expiró, intentar renovarlo
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          try {
            const rememberMe = localStorage.getItem('remember_me') === 'true'
            const refreshToken = rememberMe 
              ? localStorage.getItem('refresh_token') 
              : sessionStorage.getItem('refresh_token')
              
            if (refreshToken) {
              const response = await this.client.post('/api/v1/auth/refresh', {
                refresh_token: refreshToken,
              })

              const { access_token, refresh_token: newRefreshToken } = response.data
              
              // Guardar en el almacenamiento correspondiente
              if (rememberMe) {
                localStorage.setItem('access_token', access_token)
                localStorage.setItem('refresh_token', newRefreshToken)
              } else {
                sessionStorage.setItem('access_token', access_token)
                sessionStorage.setItem('refresh_token', newRefreshToken)
              }

              // Reintentar la petición original
              originalRequest.headers.Authorization = `Bearer ${access_token}`
              return this.client(originalRequest)
            }
          } catch (refreshError) {
            // Si no se puede renovar el token, limpiar datos y redirigir al login
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            localStorage.removeItem('remember_me')
            sessionStorage.removeItem('access_token')
            sessionStorage.removeItem('refresh_token')
            window.location.href = '/login'
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
      
      switch (status) {
        case 400:
          toast.error(data.message || 'Datos inválidos')
          break
        case 401:
          toast.error('No autorizado')
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
        case 503:
          toast.error('Servicio temporalmente no disponible. Intenta nuevamente.')
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
}

// Instancia singleton del cliente API
export const apiClient = new ApiClient()

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
