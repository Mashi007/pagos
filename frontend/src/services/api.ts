import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosProgressEvent, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'
import { getErrorMessage, isAxiosError } from '../types/errors'
import { env, BASE_PATH } from '../config/env'
import {
  safeGetItem,
  safeGetSessionItem,
  safeSetItem,
  safeSetSessionItem,
  safeRemoveItem,
  safeRemoveSessionItem,
  clearAuthStorage
} from '../utils/storage'
import { isTokenExpired } from '../utils/token'

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
const SLOW_ENDPOINT_TIMEOUT_MS = 60000 // Para endpoints que pueden tardar más

// Configuración base de Axios
const API_BASE_URL = env.API_URL

// Ruta de login con base path (ej. /pagos/login cuando BASE_PATH es /pagos)
const LOGIN_PATH = `${BASE_PATH}/login`.replace(/\/+/g, '/')

class ApiClient {
  private client: AxiosInstance
  private isRefreshing = false
  private isRedirectingToLogin = false
  private refreshTokenExpired = false // ✅ Flag para evitar requests cuando el refresh token está expirado
  private failedQueue: Array<{
    resolve: (value?: any) => void
    reject: (reason?: any) => void
  }> = []
  private requestCancellers: Map<string, AbortController> = new Map() // ✅ Para cancelar requests pendientes

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: DEFAULT_TIMEOUT_MS,
      headers: {
        'Content-Type': 'application/json',
      },
      // Optimizaciones de rendimiento
      maxRedirects: 5,
      validateStatus: (status) => status < 500, // No lanzar error para 4xx
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor - agregar token de autenticación
    this.client.interceptors.request.use(
      (config) => {
        // ✅ Si el refresh token está expirado, cancelar el request inmediatamente
        if (this.refreshTokenExpired && !config.url?.includes('/auth/login')) {
          const error = new Error('Sesión expirada. Por favor, inicia sesión nuevamente.')
          ;(error as any).isCancelled = true
          return Promise.reject(error)
        }

        // NO agregar token a endpoints de autenticación ni olvido de contraseña
        const authEndpoints = ['/api/v1/auth/login', '/api/v1/auth/refresh', '/api/v1/auth/forgot-password']
        const isAuthEndpoint = authEndpoints.some(endpoint => config.url?.includes(endpoint))

        if (!isAuthEndpoint) {
          // Obtener token de forma segura
          const rememberMe = safeGetItem('remember_me', false)
          let token = rememberMe
            ? safeGetItem('access_token', '')
            : safeGetSessionItem('access_token', '')

          // ✅ Limpiar token: remover espacios, saltos de línea, y prefijo "Bearer " si existe
          if (token) {
            token = token.trim()
            // Remover prefijo "Bearer " si está presente
            if (token.startsWith('Bearer ')) {
              token = token.substring(7).trim()
            }

            // Verificar que el token tenga el formato correcto (3 segmentos separados por puntos)
            const parts = token.split('.')
            if (parts.length !== 3) {
              // Token malformado - limpiar y redirigir
              console.error('❌ Token malformado (no tiene 3 segmentos). Limpiando almacenamiento...')
              this.refreshTokenExpired = true
              this.cancelAllPendingRequests()
              clearAuthStorage()

              if (window.location.pathname !== LOGIN_PATH && !this.isRedirectingToLogin) {
                this.isRedirectingToLogin = true
                window.location.replace(LOGIN_PATH)
              }

              const error = new Error('Token inválido. Por favor, inicia sesión nuevamente.')
              ;(error as any).isCancelled = true
              return Promise.reject(error)
            }

            // ✅ Verificar si el token está expirado ANTES de enviar el request
            if (isTokenExpired(token)) {
              // Token expirado - marcar flag, cancelar requests pendientes y redirigir
              this.refreshTokenExpired = true
              this.cancelAllPendingRequests()
              clearAuthStorage()

              // Redirigir inmediatamente si no estamos ya en login
              if (window.location.pathname !== LOGIN_PATH && !this.isRedirectingToLogin) {
                this.isRedirectingToLogin = true
                window.location.replace(LOGIN_PATH)
              }

              const error = new Error('Token expirado. Redirigiendo al login...')
              ;(error as any).isCancelled = true
              return Promise.reject(error)
            }
            config.headers.Authorization = `Bearer ${token}`
          }
        }

        // ✅ Usar signal del caller (p. ej. React Query) si existe; si no, crear uno para rastreo
        if (!config.signal) {
          const controller = new AbortController()
          const requestId = `${config.method}-${config.url}-${Date.now()}`
          config.signal = controller.signal
          ;(config as any).__requestId = requestId
          this.requestCancellers.set(requestId, controller)
        }

        // ✅ Exportar reportes (morosidad, cartera, pagos) puede tardar >60s con mucho dato
        if (config.url?.includes('/exportar/') && (config.timeout == null || config.timeout < 180000)) {
          config.timeout = 180000 // 3 minutos
        }

        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor - manejar errores globalmente
    this.client.interceptors.response.use(
      (response) => {
        // ✅ Limpiar AbortController cuando el request completa exitosamente
        const requestId = (response.config as any).__requestId
        if (requestId) {
          this.requestCancellers.delete(requestId)
        }
        return response
      },
      async (error) => {
        const originalRequest = error.config

        // ✅ Limpiar AbortController cuando el request falla
        if (originalRequest) {
          const requestId = (originalRequest as any).__requestId
          if (requestId) {
            this.requestCancellers.delete(requestId)
          }
        }

        // Auto-refresh de tokens con protección contra loops infinitos y race conditions
        if (error.response?.status === 401 && !originalRequest?._retry) {
          // No intentar refresh en endpoints de autenticación
          const authEndpoints = ['/api/v1/auth/login', '/api/v1/auth/refresh']
          const isAuthEndpoint = authEndpoints.some(endpoint => originalRequest.url?.includes(endpoint))

          if (isAuthEndpoint) {
            // En endpoints de auth, simplemente propagar el error sin intentar refresh
            this.handleError(error)
            return Promise.reject(error)
          }

          // Si ya hay un refresh en progreso, encolar esta petición
          if (this.isRefreshing) {
            return new Promise<string>((resolve, reject) => {
              this.failedQueue.push({ resolve, reject })
            })
              .then((token) => {
                if (!token) {
                  throw new Error('Token no disponible después del refresh')
                }
                originalRequest.headers.Authorization = `Bearer ${token}`
                return this.client(originalRequest)
              })
              .catch((err) => {
                return Promise.reject(err)
              })
          }

          originalRequest._retry = true
          this.isRefreshing = true

          try {
            const rememberMe = safeGetItem('remember_me', false)
            const refreshToken = rememberMe
              ? safeGetItem('refresh_token', '')
              : safeGetSessionItem('refresh_token', '')

            if (!refreshToken) {
              throw new Error('No refresh token available')
            }

            // Hacer la petición de refresh con validación estricta (lanzar error para 4xx)
            let response
            try {
              // Crear una instancia temporal de axios sin el interceptor para evitar loops
              const refreshClient = axios.create({
                baseURL: API_BASE_URL,
                timeout: DEFAULT_TIMEOUT_MS,
                headers: {
                  'Content-Type': 'application/json',
                },
                validateStatus: (status) => status < 400, // Lanzar error para 4xx y 5xx
              })

              response = await refreshClient.post('/api/v1/auth/refresh', {
                refresh_token: refreshToken,
              })
            } catch (error: any) {
              // Si el refresh token está expirado o es inválido, el servidor devuelve 401
              if (error.response?.status === 401 || error.response?.status === 400) {
                throw new Error('Refresh token inválido o expirado')
              }
              // Para otros errores (red, timeout, etc.), propagar el error
              throw error
            }

            // Verificar si la respuesta es válida
            if (!response || !response.data || !response.data.access_token) {
              throw new Error('Refresh token inválido o expirado')
            }

            const { access_token, refresh_token: newRefreshToken } = response.data

            // Guardar en el almacenamiento correspondiente usando funciones seguras
            if (rememberMe) {
              safeSetItem('access_token', access_token)
              safeSetItem('refresh_token', newRefreshToken)
            } else {
              safeSetSessionItem('access_token', access_token)
              safeSetSessionItem('refresh_token', newRefreshToken)
            }

            // Procesar todas las peticiones en cola
            this.processQueue(null, access_token)

            // Reintentar la petición original
            originalRequest.headers.Authorization = `Bearer ${access_token}`
            return this.client(originalRequest)
          } catch (refreshError: any) {
            // ✅ Marcar que el refresh token está expirado para cancelar requests futuros
            this.refreshTokenExpired = true

            // ✅ Cancelar todos los requests pendientes
            this.cancelAllPendingRequests()

            // Si no se puede renovar el token, limpiar datos y redirigir al login
            this.processQueue(refreshError, null)
            clearAuthStorage()

            // Evitar mostrar toasts durante el redirect
            const isAlreadyRedirecting = window.location.pathname === LOGIN_PATH || this.isRedirectingToLogin

            if (!isAlreadyRedirecting) {
              this.isRedirectingToLogin = true

              // Log para debugging (solo en desarrollo)
              if (process.env.NODE_ENV === 'development') {
                console.warn('🔄 Refresh token falló. Redirigiendo al login...', refreshError)
              }

              // ✅ Redirigir inmediatamente sin delay para evitar más requests (respeta BASE_PATH)
              window.location.replace(LOGIN_PATH)
            }

            return Promise.reject(refreshError)
          } finally {
            this.isRefreshing = false
          }
        }

        // Manejar otros errores - pero no mostrar toast si estamos redirigiendo al login
        if (!this.isRedirectingToLogin) {
          this.handleError(error)
        }
        return Promise.reject(error)
      }
    )
  }

  private processQueue(error: any, token: string | null) {
    this.failedQueue.forEach((prom) => {
      if (error) {
        prom.reject(error)
      } else if (token) {
        prom.resolve(token)
      } else {
        prom.reject(new Error('Token no disponible después del refresh'))
      }
    })
    this.failedQueue = []
  }

  // ✅ Cancelar todos los requests pendientes cuando el refresh token expira
  private cancelAllPendingRequests() {
    this.requestCancellers.forEach((controller, url) => {
      try {
        controller.abort()
      } catch (error) {
        // Ignorar errores al cancelar
      }
    })
    this.requestCancellers.clear()
  }

  // ✅ Resetear el flag cuando el usuario hace login exitosamente
  resetRefreshTokenExpired() {
    this.refreshTokenExpired = false
    this.isRedirectingToLogin = false
  }

  private handleError(error: unknown) {
    if (!isAxiosError(error)) {
      toast.error(getErrorMessage(error))
      return
    }
    // No mostrar toast ni log para peticiones canceladas (p. ej. desmontaje o React Query)
    const code = (error as any).code
    const msg = error.message || ''
    if (code === 'ERR_CANCELED' || msg.includes('Request aborted') || (error as any).isCancelled) {
      return
    }

    if (error.response) {
      // Error del servidor
      const { status, data } = error.response
      const responseData = data as { detail?: string | Array<{ loc?: string[]; msg?: string }>; message?: string } | undefined

      // Evitar mostrar toast de 401 cuando está siendo manejado por el interceptor
      const isBeingHandledByInterceptor = (error.config as { _retry?: boolean } | undefined)?._retry !== undefined

      switch (status) {
        case 400:
          // Error de validación o cliente duplicado (misma cédula y mismo nombre)
          if (typeof responseData?.detail === 'string') {
            toast.error(responseData.detail)
          } else {
            toast.error(responseData?.message || 'Error de validación')
          }
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
        case 409:
          toast.error(responseData?.message || 'Conflicto de datos. Verifica la información.')
          break
        case 422:
          // Errores de validación
          if (responseData?.detail && Array.isArray(responseData.detail)) {
            responseData.detail.forEach((err: { loc?: string[]; msg?: string }) => {
              toast.error(`${err.loc?.join(' ') || 'Campo'}: ${err.msg || 'Error de validación'}`)
            })
          } else {
            toast.error(responseData?.message || 'Error de validación')
          }
          break
        case 500:
          // Mostrar el mensaje de error específico del backend si está disponible
          const errorDetail = typeof responseData?.detail === 'string'
            ? responseData.detail
            : responseData?.message || 'Error interno del servidor'

          // Logging detallado para diagnóstico
          console.error('❌ [ApiClient] Error 500 del servidor:', {
            detail: errorDetail,
            message: responseData?.message,
            url: error.config?.url,
            method: error.config?.method,
            status: error.response?.status,
            fullError: error
          })

          // Mostrar toast con el mensaje del backend (ahora más específico)
          toast.error(errorDetail, { duration: 10000 })
          break
        case 503:
          // NO mostrar toast genérico para errores 503 de duplicados
          // Permitir que el componente maneje el error específico
          const detailStr = typeof responseData?.detail === 'string' ? responseData.detail : ''
          const messageStr = responseData?.message || ''
          if (detailStr.includes('duplicate key') || detailStr.includes('already exists') ||
              detailStr.includes('violates unique constraint') || detailStr.includes('cédula') ||
              messageStr.includes('duplicate key') || messageStr.includes('already exists')) {
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
            toast.error(responseData?.message || 'Error desconocido')
          }
      }
    } else if (error.request) {
      // Error de red - puede ser que el servidor esté reiniciando
      const errorCode = (error as any).code || ''
      const errorMessage = error.message || ''
      if (errorCode === 'ERR_CANCELED' || errorMessage.includes('Request aborted')) {
        return
      }

      // Log detallado para diagnóstico
      console.error('❌ [ApiClient] Error de conexión:', {
        url: error.config?.url,
        method: error.config?.method,
        baseURL: API_BASE_URL,
        code: errorCode,
        message: errorMessage,
        requestId: (error.config as any)?.__requestId
      })

      // No mostrar toast para errores de conexión durante el inicio (servidor reiniciando)
      // Estos errores son temporales y se resuelven automáticamente
      if (
        errorCode === 'ERR_NETWORK' ||
        errorCode === 'ECONNREFUSED' ||
        errorMessage.includes('Connection refused') ||
        errorMessage.includes('NS_ERROR_CONNECTION_REFUSED')
      ) {
        // Solo loggear en consola, no mostrar toast (el usuario verá el error si persiste)
        console.warn('⚠️ Servidor no disponible temporalmente. Esto es normal durante reinicios.')
        console.warn('   Verifica que el backend esté funcionando en:', API_BASE_URL || 'NO CONFIGURADO')
        return
      }

      // Mensaje más descriptivo según el tipo de error
      let errorMsg = 'Error de conexión. Verifique su conexión a internet.'
      if (errorCode === 'ECONNABORTED' || errorMessage.includes('timeout')) {
        errorMsg = 'Tiempo de espera agotado. El servidor está tardando demasiado en responder.'
      } else if (errorCode === 'ERR_NETWORK') {
        errorMsg = 'Error de red. Verifique que el servidor esté funcionando y su conexión a internet.'
      }
      
      toast.error(errorMsg)
    } else {
      // Error de configuración
      toast.error('Error en la configuración de la petición')
    }
  }

  // Métodos HTTP
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    // Detectar endpoints lentos y usar timeout extendido (p. ej. Render tarda 3–5 s en frío)
    const isSlowEndpoint = url.includes('/dashboard/') ||
                          url.includes('/reportes/') ||
                          url.includes('/notificaciones-previas') ||
                          url.includes('/admin') ||
                          url.includes('/evolucion') ||
                          url.includes('/tendencia') ||
                          url.includes('/ml-impago/modelos') ||
                          url.includes('/ml-riesgo/modelos') ||
                          url.includes('/ai/training/') ||
                          url.includes('/cobranzas/') ||
                          url.includes('/pagos/kpis') ||
                          url.includes('/pagos/stats') ||
                          url.includes('/revision-manual/')  // Render cold start + consulta pesada

    // ✅ Timeout especial para revision-manual (Render cold start + BD)
    const isRevisionManual = url.includes('/revision-manual/')
    const revisionManualTimeout = 120000 // 120 segundos

    // ✅ Timeout especial para reportes (Render cold start + consultas BD pesadas)
    const isReportesDashboard = url.includes('/reportes/') && (url.includes('/dashboard/') || url.includes('/resumen'))
    const reportesDashboardTimeout = 120000 // 120 segundos

    // ✅ Timeout especial para clientes-atrasados que puede procesar muchos registros (2868+)
    const isClientesAtrasados = url.includes('/cobranzas/clientes-atrasados')
    const verySlowTimeout = 120000 // 120 segundos para endpoints muy pesados
    
    // ✅ Timeout extendido para tablas-campos que consulta toda la estructura de BD
    const isTablasCampos = url.includes('/tablas-campos')
    const tablasCamposTimeout = 90000 // 90 segundos para consulta de estructura completa de BD

    let defaultTimeout = DEFAULT_TIMEOUT_MS
    if (isRevisionManual) {
      defaultTimeout = revisionManualTimeout
    } else if (isReportesDashboard) {
      defaultTimeout = reportesDashboardTimeout
    } else if (isClientesAtrasados) {
      defaultTimeout = verySlowTimeout
    } else if (isTablasCampos) {
      defaultTimeout = tablasCamposTimeout
    } else if (isSlowEndpoint) {
      defaultTimeout = SLOW_ENDPOINT_TIMEOUT_MS
    }

    // ✅ Priorizar timeout explícito si se proporciona, sino usar el calculado
    const timeout = config?.timeout ?? defaultTimeout
    // ✅ Asegurar que el timeout se aplique correctamente
    // Axios respeta el timeout en la configuración del request sobre el del cliente
    const finalConfig = { 
      ...config, 
      timeout,
    }

    const response: AxiosResponse<T> = await this.client.get(url, finalConfig)
    return response.data
  }

  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    try {
      // Detectar endpoints lentos (entrenamiento ML, etc.) y usar timeout extendido
      const isSlowEndpoint = url.includes('/ml-riesgo/entrenar') ||
                            url.includes('/ml-impago/entrenar') ||
                            url.includes('/fine-tuning/iniciar') ||
                            url.includes('/rag/generar-embeddings') ||
                            url.includes('/configuracion/ai/chat') ||
                            url.includes('/prestamos/cedula/batch') // ✅ Batch carga masiva: muchas cédulas

      const defaultTimeout = isSlowEndpoint ? (url.includes('/prestamos/cedula/batch') ? 60000 : 300000) : DEFAULT_TIMEOUT_MS
      // Priorizar timeout explícito si se proporciona, sino usar el calculado
      const timeout = config?.timeout ?? defaultTimeout
      const finalConfig = { ...config, timeout }

      const response: AxiosResponse<T> = await this.client.post(url, data, finalConfig)

      // Verificar si la respuesta es un error 4xx (validateStatus permite 4xx pero debemos manejarlos)
      if (response.status >= 400 && response.status < 500) {
        // 401 en login/refresh es esperado (credenciales incorrectas); solo log en desarrollo para no saturar consola
        const isAuthFailure = response.status === 401 && (url.includes('/auth/login') || url.includes('/auth/refresh'))
        if (isAuthFailure && process.env.NODE_ENV === 'development') {
          console.warn('⚠️ [ApiClient] Login/refresh no autorizado (401):', url)
        } else if (!isAuthFailure) {
          const is409Pagos = response.status === 409 && url.includes('/pagos/')
          if (is409Pagos) {
            console.warn('⚠️ [ApiClient] POST 409 (documento duplicado, se reintenta con sufijo):', url)
          } else {
            console.error('❌ [ApiClient] POST recibió error 4xx:', { url, status: response.status, data: response.data })
          }
        }
        // Crear un error de Axios para que se maneje correctamente, preservando el mensaje del backend
        const backendMessage = (response.data as any)?.detail || (response.data as any)?.message || `Request failed with status ${response.status}`
        const error = new Error(backendMessage) as any
        error.response = response
        error.isAxiosError = true
        error.code = `ERR_HTTP_${response.status}`
        throw error
      }

      return response.data
    } catch (error: any) {
      const is409Pagos = error?.response?.status === 409 && url.includes('/pagos/')
      if (is409Pagos) {
        console.warn('⚠️ [ApiClient] POST 409 (documento duplicado):', url)
      } else {
        console.error('❌ [ApiClient] POST error:', { url, error })
      }
      throw error
    }
  }

  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    console.log('📤 [ApiClient] PUT request:', { url, data: data ? '***' : '(vacío)', config })
    try {
      const response: AxiosResponse<T> = await this.client.put(url, data, config)
      console.log('✅ [ApiClient] PUT response:', { url, status: response.status, data: response.data })

      // Verificar si la respuesta es un error 4xx (validateStatus permite 4xx pero debemos manejarlos)
      if (response.status >= 400 && response.status < 500) {
        console.error('❌ [ApiClient] PUT recibió error 4xx:', { url, status: response.status, data: response.data })
        // Crear un error de Axios para que se maneje correctamente
        const error = new Error(`Request failed with status ${response.status}`) as any
        error.response = response
        error.isAxiosError = true
        throw error
      }

      return response.data
    } catch (error) {
      console.error('❌ [ApiClient] PUT error:', { url, error })
      throw error
    }
  }

  async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.patch(url, data, config)
    return response.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(url, config)

    // Verificar si la respuesta es un error 4xx (validateStatus permite 4xx pero debemos manejarlos)
    if (response.status >= 400 && response.status < 500) {
      const backendMessage = (response.data as any)?.detail || (response.data as any)?.message || `Request failed with status ${response.status}`
      const error = new Error(backendMessage) as any
      error.response = response
      error.isAxiosError = true
      error.code = `ERR_HTTP_${response.status}`
      throw error
    }

    return response.data
  }

  // Método para subir archivos
  async uploadFile<T>(
    url: string,
    file: File,
    onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
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
export default apiClient

// FUNCIÓN GLOBAL DE EMERGENCIA: Limpiar storage desde consola del navegador
// Uso: window.clearAuthStorage() en la consola del navegador
if (typeof window !== 'undefined') {
  (window as Window & { clearAuthStorage?: () => void }).clearAuthStorage = () => {
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
