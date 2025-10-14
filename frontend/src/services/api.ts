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
        // Buscar token en localStorage o sessionStorage según la configuración
        const rememberMe = localStorage.getItem('remember_me') === 'true'
        const token = rememberMe 
          ? localStorage.getItem('access_token') 
          : sessionStorage.getItem('access_token')
          
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
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
        default:
          toast.error(data.message || 'Error desconocido')
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
