import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosProgressEvent,
  AxiosResponse,
} from 'axios'

import toast from 'react-hot-toast'

import { getErrorMessage, getErrorCode, isAxiosError } from '../types/errors'

import { env, BASE_PATH, STAFF_LOGIN_SEARCH } from '../config/env'

import {
  safeGetItem,
  safeGetSessionItem,
  safeSetItem,
  safeSetSessionItem,
  safeRemoveItem,
  safeRemoveSessionItem,
  clearAuthStorage,
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

// Base URL de la API. CSP permite same-origin y orígenes Render; usar VITE_API_URL cuando front y back estén en servicios distintos.

function getEffectiveApiBaseUrl(): string {
  const url = env.API_URL

  if (typeof window === 'undefined') return url

  if (!url) return ''

  try {
    const parsed = new URL(url)
    // Browser: forzar same-origin (/api) cuando la URL configurada apunta
    // a otro origen. Evita CORS al saltarse el proxy del frontend.
    if (parsed.origin !== window.location.origin) {
      console.warn(
        `[api] API_URL cross-origin detectada (${parsed.origin}); usando /api same-origin.`
      )
      return ''
    }
    return parsed.toString().replace(/\/$/, '')
  } catch {
    return ''
  }
}

export const API_BASE_URL = getEffectiveApiBaseUrl()

function looksLikeHtmlErrorBody(text: string): boolean {
  const t = text.toLowerCase()
  return (
    t.includes('<html') ||
    t.includes('<!doctype html') ||
    t.includes('cloudflare') ||
    t.includes('bad request')
  )
}

function readBackend4xxErrorMessage(status: number, data: unknown): string {
  if (typeof data === 'string') {
    const s = data.trim()
    if (s && looksLikeHtmlErrorBody(s)) {
      return `El servidor devolvió una página HTML de error (HTTP ${status}). Suele indicar bloqueo en el proxy (p. ej. Cloudflare) o un fallo antes de llegar al API.`
    }
    if (s) return s
  }

  if (data && typeof data === 'object') {
    const anyData = data as { detail?: unknown; message?: unknown }
    if (typeof anyData.detail === 'string' && anyData.detail.trim()) {
      return anyData.detail
    }
    if (Array.isArray(anyData.detail)) {
      return anyData.detail
        .map((x: { msg?: string }) =>
          typeof x?.msg === 'string' ? x.msg : JSON.stringify(x)
        )
        .join('; ')
    }
    if (typeof anyData.message === 'string' && anyData.message.trim()) {
      return anyData.message
    }
  }

  return `Request failed with status ${status}`
}

function compactFor4xxLog(data: unknown): unknown {
  if (typeof data === 'string') {
    const s = data
    if (s.length > 400 || looksLikeHtmlErrorBody(s)) {
      const oneLine = s.replace(/\s+/g, ' ').trim()
      return {
        _type: 'non_json_error_body',
        preview: oneLine.slice(0, 240) + (oneLine.length > 240 ? '…' : ''),
      }
    }
    return s
  }
  return data
}

// Ruta de login con base path (ej. /pagos/login cuando BASE_PATH es /pagos)

const LOGIN_PATH = `${BASE_PATH}/login`.replace(/\/+/g, '/')

const LOGIN_REDIRECT_URL = `${LOGIN_PATH}${STAFF_LOGIN_SEARCH}`

class ApiClient {
  private client: AxiosInstance

  private isRefreshing = false

  private isRedirectingToLogin = false

  private refreshTokenExpired = false // ? Flag para evitar requests cuando el refresh token esté expirado

  private failedQueue: Array<{
    resolve: (value?: any) => void

    reject: (reason?: any) => void
  }> = []

  private requestCancellers: Map<string, AbortController> = new Map() // ? Para cancelar requests pendientes
  private inFlightGetRequests: Map<string, Promise<unknown>> = new Map()
  private last502ToastAt = 0
  private putQueueByGroup: Map<
    string,
    { active: number; queue: Array<() => void>; limit: number }
  > = new Map()

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,

      timeout: DEFAULT_TIMEOUT_MS,

      headers: {
        'Content-Type': 'application/json',
      },

      // Optimizaciones de rendimiento

      maxRedirects: 5,

      validateStatus: status => status < 500, // No lanzar error para 4xx
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor - agregar token de autenticación

    this.client.interceptors.request.use(
      config => {
        // ? Si el refresh token esté expirado, cancelar el request inmediatamente

        if (this.refreshTokenExpired && !config.url?.includes('/auth/login')) {
          const error = new Error(
            'Sesión expirada. Por favor, inicia sesión nuevamente.'
          )

          ;(error as any).isCancelled = true

          return Promise.reject(error)
        }

        // NO agregar token a endpoints de autenticación ni olvido de contraseña

        const authEndpoints = [
          '/api/v1/auth/login',
          '/api/v1/auth/refresh',
          '/api/v1/auth/forgot-password',
        ]

        const isAuthEndpoint = authEndpoints.some(endpoint =>
          config.url?.includes(endpoint)
        )

        if (!isAuthEndpoint) {
          // Obtener token de forma segura

          const rememberMe = safeGetItem('remember_me', false)

          let token = rememberMe
            ? safeGetItem('access_token', '')
            : safeGetSessionItem('access_token', '')

          // ? Limpiar token: remover espacios, saltos de línea, y prefijo "Bearer " si existe

          if (token) {
            token = token.trim()

            // Remover prefijo "Bearer " si esté presente

            if (token.startsWith('Bearer ')) {
              token = token.substring(7).trim()
            }

            // Verificar que el token tenga el formato correcto (3 segmentos separados por puntos)

            const parts = token.split('.')

            if (parts.length !== 3) {
              // Token malformado - limpiar y redirigir

              console.error(
                '? Token malformado (no tiene 3 segmentos). Limpiando almacenamiento...'
              )

              this.refreshTokenExpired = true

              this.cancelAllPendingRequests()

              clearAuthStorage()

              if (
                window.location.pathname !== LOGIN_PATH &&
                !this.isRedirectingToLogin
              ) {
                this.isRedirectingToLogin = true

                window.location.replace(LOGIN_REDIRECT_URL)
              }

              const error = new Error(
                'Token inválido. Por favor, inicia sesión nuevamente.'
              )

              ;(error as any).isCancelled = true

              return Promise.reject(error)
            }

            // ? Verificar si el token esté expirado ANTES de enviar el request

            if (isTokenExpired(token)) {
              // Token expirado - marcar flag, cancelar requests pendientes y redirigir

              this.refreshTokenExpired = true

              this.cancelAllPendingRequests()

              clearAuthStorage()

              // Redirigir inmediatamente si no estamos ya en login

              if (
                window.location.pathname !== LOGIN_PATH &&
                !this.isRedirectingToLogin
              ) {
                this.isRedirectingToLogin = true

                window.location.replace(LOGIN_REDIRECT_URL)
              }

              const error = new Error(
                'Token expirado. Redirigiendo al login...'
              )

              ;(error as any).isCancelled = true

              return Promise.reject(error)
            }

            config.headers.Authorization = `Bearer ${token}`
          }
        }

        // ? Usar signal del caller (p. ej. React Query) si existe; si no, crear uno para rastreo

        if (!config.signal) {
          const controller = new AbortController()

          const requestId = `${config.method}-${config.url}-${Date.now()}`

          config.signal = controller.signal
          ;(config as any).__requestId = requestId

          this.requestCancellers.set(requestId, controller)
        }

        // ? Exportar reportes (morosidad, cartera, pagos) puede tardar >60s con mucho dato

        if (
          config.url?.includes('/exportar/') &&
          (config.timeout == null || config.timeout < 180000)
        ) {
          config.timeout = 180000 // 3 minutos
        }

        // Cobros: listado+KPIs recorre la cola en servidor; con cola grande puede superar 60s en picos.
        if (
          config.method?.toLowerCase() === 'get' &&
          config.url?.includes('/cobros/pagos-reportados/listado-y-kpis') &&
          (config.timeout == null || config.timeout < 120000)
        ) {
          config.timeout = 120000
        }

        if (
          config.method?.toLowerCase() === 'get' &&
          config.url?.includes('/prestamos/candidatos-drive/snapshot') &&
          (config.timeout == null || config.timeout < 120000)
        ) {
          config.timeout = 120000
        }

        // Cobros: PATCH estado (aprobar/rechazar) puede tardar (cascada, correo, PDF).
        if (
          config.method?.toLowerCase() === 'patch' &&
          config.url &&
          /\/cobros\/pagos-reportados\/\d+\/estado(?:\?|#|$)/.test(
            config.url
          ) &&
          (config.timeout == null || config.timeout < 120000)
        ) {
          config.timeout = 120000
        }

        // FormData: no fijar Content-Type aquí; axios/navegador añaden multipart + boundary.
        // Si queda 'application/json' por defecto o 'multipart/form-data' sin boundary, el backend puede no leer el archivo.
        if (
          typeof FormData !== 'undefined' &&
          config.data instanceof FormData
        ) {
          const h = config.headers as unknown as {
            delete?: (name: string) => void
            'Content-Type'?: string
            'content-type'?: string
          }
          if (typeof h?.delete === 'function') {
            h.delete('Content-Type')
            h.delete('content-type')
          } else if (h) {
            delete h['Content-Type']
            delete h['content-type']
          }
        }

        return config
      },

      error => {
        return Promise.reject(error)
      }
    )

    // Response interceptor - manejar errores globalmente

    this.client.interceptors.response.use(
      response => {
        // ? Limpiar AbortController cuando el request completa exitosamente

        const requestId = (response.config as any).__requestId

        if (requestId) {
          this.requestCancellers.delete(requestId)
        }

        return response
      },

      async error => {
        // Auto-retry para errores 500 transitorios (conexión SSL, timeouts, etc.)

        const requestConfigForRetry = error.config

        const retryCount = (requestConfigForRetry as any)._retryCount || 0

        const st = error.response?.status
        const reqUrl = String(requestConfigForRetry?.url || '')
        const methodLc = String(
          requestConfigForRetry?.method || ''
        ).toLowerCase()
        const isScannerReadOnlyPost =
          methodLc === 'post' &&
          (reqUrl.includes('/cobros/escaner/extraer-comprobante') ||
            reqUrl.includes('/cobros/escaner/lote/drive-digitalizar'))
        /**
         * GET idempotentes donde 502/503 suele ser cold start o proxy (Render), no lógica de negocio.
         * Solo rutas de lectura explícitas; no ampliar a GET arbitrarios (riesgo de duplicar efectos si hubiera efectos colaterales).
         */
        const isSafeTransientRetryGet =
          methodLc === 'get' &&
          (reqUrl.includes('/api/v1/auth/me') ||
            reqUrl.includes('/concesionarios/activos') ||
            reqUrl.includes('/analistas/activos') ||
            reqUrl.includes('/modelos-vehiculos/activos') ||
            reqUrl.includes('/cobros/pagos-reportados/listado-y-kpis') ||
            reqUrl.includes('/prestamos/candidatos-drive/snapshot') ||
            reqUrl.includes('/pagos/gmail/status') ||
            reqUrl.includes('/admin/tasas-cambio/estado') ||
            reqUrl.includes('/admin/tasas-cambio/hoy') ||
            reqUrl.includes('/tasas-cambio/estado') ||
            reqUrl.includes('/tasas-cambio/hoy'))
        /**
         * Dyno API en Render: 502/503 pueden durar >15s (arranque Gunicorn + init BD).
         * 3 reintentos con 2+4+8s no alcanzan; aquí ampliamos solo GET seguros ante 502/503.
         */
        const isColdStartProxySafeGet =
          isSafeTransientRetryGet && (st === 502 || st === 503)
        const maxRetries = isColdStartProxySafeGet ? 6 : 3
        /**
         * PATCH cambio de estado (aprobar/rechazar flujo UI). 502 del proxy sin cuerpo JSON
         * suele ser TCP/deploy; el backend puede no haber aplicado el cambio.
         */
        const isCobrosPagoReportadoEstadoPatch =
          methodLc === 'patch' &&
          /\/cobros\/pagos-reportados\/\d+\/estado(?:\?|#|$)/.test(reqUrl)
        const canRetryBecauseStatus =
          st === 503 ||
          st === 504 ||
          (st === 500 && (methodLc !== 'get' || isSafeTransientRetryGet)) ||
          (st === 502 &&
            (isScannerReadOnlyPost ||
              isSafeTransientRetryGet ||
              isCobrosPagoReportadoEstadoPatch))
        const mayRetryThisRequest =
          methodLc !== 'get' || isSafeTransientRetryGet
        if (
          canRetryBecauseStatus &&
          retryCount < maxRetries &&
          mayRetryThisRequest
        ) {
          ;(requestConfigForRetry as any)._retryCount = retryCount + 1

          // 502/503 en Render: dar tiempo al dyno del API a despertar (reintentos más espaciados).
          const delayBase =
            st === 502 || st === 503
              ? isColdStartProxySafeGet
                ? 3500
                : 2000
              : 500
          const rawDelay = delayBase * Math.pow(2, retryCount)
          const delayMs = isColdStartProxySafeGet
            ? Math.min(14000, rawDelay)
            : rawDelay

          // console.info: no pasa por el parche de console.warn de pagos-bootstrap.js (evita confundir la línea 128 del bootstrap con el origen del log).
          console.info(
            `[ApiClient] Error ${error.response?.status} (intento ${retryCount + 1}/${maxRetries}), reintentando en ${delayMs}ms:`,
            {
              url: requestConfigForRetry.url,

              method: requestConfigForRetry.method,
            }
          )

          await new Promise(resolve => setTimeout(resolve, delayMs))

          return this.client(requestConfigForRetry)
        }

        const originalRequest = error.config

        // ? Limpiar AbortController cuando el request falla

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

          const isAuthEndpoint = authEndpoints.some(endpoint =>
            originalRequest.url?.includes(endpoint)
          )

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

              .then(token => {
                if (!token) {
                  throw new Error('Token no disponible después del refresh')
                }

                originalRequest.headers.Authorization = `Bearer ${token}`

                return this.client(originalRequest)
              })

              .catch(err => {
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

                validateStatus: status => status < 400, // Lanzar error para 4xx y 5xx
              })

              response = await refreshClient.post('/api/v1/auth/refresh', {
                refresh_token: refreshToken,
              })
            } catch (error: any) {
              // Si el refresh token esté expirado o es inválido, el servidor devuelve 401

              if (
                error.response?.status === 401 ||
                error.response?.status === 400
              ) {
                throw new Error('Refresh token inválido o expirado')
              }

              // Para otros errores (red, timeout, etc.), propagar el error

              throw error
            }

            // Verificar si la respuesta es válida

            if (!response || !response.data || !response.data.access_token) {
              throw new Error('Refresh token inválido o expirado')
            }

            const { access_token, refresh_token: newRefreshToken } =
              response.data

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
            // ? Marcar que el refresh token esté expirado para cancelar requests futuros

            this.refreshTokenExpired = true

            // ? Cancelar todos los requests pendientes

            this.cancelAllPendingRequests()

            // Si no se puede renovar el token, limpiar datos y redirigir al login

            this.processQueue(refreshError, null)

            clearAuthStorage()

            // Evitar mostrar toasts durante el redirect

            const isAlreadyRedirecting =
              window.location.pathname === LOGIN_PATH ||
              this.isRedirectingToLogin

            if (!isAlreadyRedirecting) {
              this.isRedirectingToLogin = true

              // Log para debugging (solo en desarrollo)

              if (process.env.NODE_ENV === 'development') {
                console.warn(
                  '? Refresh token falló. Redirigiendo al login...',
                  refreshError
                )
              }

              // ? Redirigir inmediatamente sin delay para evitar más requests (respeta BASE_PATH)

              window.location.replace(LOGIN_REDIRECT_URL)
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

  private shouldDeduplicateHeavyGet(url: string): boolean {
    return (
      url.includes('/api/v1/notificaciones/clientes-retrasados') ||
      url.includes('/api/v1/notificaciones/cuotas-pendiente-2-dias-antes') ||
      url.includes('/api/v1/notificaciones-prejudicial') ||
      url.includes('/api/v1/cobros/pagos-reportados/listado-y-kpis') ||
      url.includes('/api/v1/cobros/pagos-reportados/kpis') ||
      url.includes('/api/v1/prestamos/candidatos-drive/snapshot')
    )
  }

  private buildGetDedupKey(url: string, config?: AxiosRequestConfig): string {
    const params =
      config?.params && typeof config.params === 'object'
        ? JSON.stringify(config.params)
        : String(config?.params ?? '')
    return `${url}::${params}`
  }

  private getPutConcurrencyGroup(
    url: string
  ): { key: string; limit: number } | null {
    if (url.includes('/api/v1/revision-manual/clientes/')) {
      return { key: 'revision-manual-clientes', limit: 4 }
    }
    return null
  }

  private async runWithPutLimit<T>(
    groupKey: string,
    limit: number,
    task: () => Promise<T>
  ): Promise<T> {
    let group = this.putQueueByGroup.get(groupKey)
    if (!group) {
      group = { active: 0, queue: [], limit }
      this.putQueueByGroup.set(groupKey, group)
    }
    group.limit = limit

    await new Promise<void>(resolve => {
      const startOrQueue = () => {
        if (group && group.active < group.limit) {
          group.active += 1
          resolve()
          return
        }
        group?.queue.push(startOrQueue)
      }
      startOrQueue()
    })

    try {
      return await task()
    } finally {
      if (group) {
        group.active = Math.max(0, group.active - 1)
        const next = group.queue.shift()
        if (next) next()
      }
    }
  }

  private processQueue(error: any, token: string | null) {
    this.failedQueue.forEach(prom => {
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

  // ? Cancelar todos los requests pendientes cuando el refresh token expira

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

  // ? Resetear el flag cuando el usuario hace login exitosamente

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

    if (
      code === 'ERR_CANCELED' ||
      msg.includes('Request aborted') ||
      (error as any).isCancelled
    ) {
      return
    }

    if (error.response) {
      // Error del servidor

      const { status, data } = error.response

      const responseData = data as
        | {
            detail?: string | Array<{ loc?: string[]; msg?: string }>
            message?: string
          }
        | undefined

      // Evitar mostrar toast de 401 cuando está siendo manejado por el interceptor

      const isBeingHandledByInterceptor =
        (error.config as { _retry?: boolean } | undefined)?._retry !== undefined

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
          toast.error(
            responseData?.message ||
              'Conflicto de datos. Verifica la información.'
          )

          break

        case 422:
          // Errores de validación

          if (responseData?.detail && Array.isArray(responseData.detail)) {
            responseData.detail.forEach(
              (err: { loc?: string[]; msg?: string }) => {
                toast.error(
                  `${err.loc?.join(' ') || 'Campo'}: ${err.msg || 'Error de validación'}`
                )
              }
            )
          } else {
            toast.error(responseData?.message || 'Error de validación')
          }

          break

        case 500:
          // Mostrar el mensaje de error específico del backend si esté disponible

          const errorDetail =
            typeof responseData?.detail === 'string'
              ? responseData.detail
              : responseData?.message || 'Error interno del servidor'

          // Logging detallado para diagnóstico

          // console.info: el bootstrap parchea console.error y la consola atribuye el log a pagos-bootstrap.js.
          console.info('[ApiClient] Error 500 del servidor:', {
            detail: errorDetail,

            message: responseData?.message,

            url: error.config?.url,

            method: error.config?.method,

            status: error.response?.status,

            fullError: error,
          })

          // Mostrar toast con el mensaje del backend (ahora más específico)

          toast.error(errorDetail, { duration: 10000 })

          break

        case 503:
          // NO mostrar toast genérico para errores 503 de duplicados

          // Permitir que el componente maneje el error específico

          const detailStr =
            typeof responseData?.detail === 'string' ? responseData.detail : ''

          const messageStr = responseData?.message || ''

          if (
            detailStr.includes('duplicate key') ||
            detailStr.includes('already exists') ||
            detailStr.includes('violates unique constraint') ||
            detailStr.includes('cédula') ||
            messageStr.includes('duplicate key') ||
            messageStr.includes('already exists')
          ) {
            // No mostrar toast, dejar que el componente maneje el popup

            return Promise.reject(error) // ? CORRECCIÓN: Asegurar que se propague el error
          } else {
            toast.error(
              'Servicio temporalmente no disponible. Intenta nuevamente.'
            )
          }

          break

        case 502:
          // Evita tormenta de toasts cuando varios requests paralelos/reintentos chocan con el mismo 502 transitorio.
          if (Date.now() - this.last502ToastAt > 15000) {
            this.last502ToastAt = Date.now()
            toast.error(
              'El API no respondió (502). Suele ser arranque del servidor o proxy; espere unos segundos y reintente. Si persiste, revise el servicio API y API_BASE_URL/BACKEND_URL en el servicio Node del frontend (Render).',
              { duration: 10000 }
            )
          }
          break

        default:
          if (
            error.code === 'ECONNABORTED' ||
            error.message?.includes('timeout')
          ) {
            toast.error('Tiempo de espera agotado. Verifica tu conexión.')
          } else if (
            error.message?.includes('Network Error') ||
            error.code === 'ERR_NETWORK'
          ) {
            toast.error(
              'Error de conexión. Verifica que el servidor esté funcionando.'
            )
          } else {
            toast.error(responseData?.message || 'Error desconocido')
          }
      }
    } else if (error.request) {
      // Error de red - puede ser que el servidor esté reiniciando

      const errorCode = (error as any).code || ''

      const errorMessage = error.message || ''

      if (
        errorCode === 'ERR_CANCELED' ||
        errorMessage.includes('Request aborted')
      ) {
        return
      }

      // Log detallado para diagnóstico

      console.error('? [ApiClient] Error de conexión:', {
        url: error.config?.url,

        method: error.config?.method,

        baseURL: API_BASE_URL,

        code: errorCode,

        message: errorMessage,

        requestId: (error.config as any)?.__requestId,
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

        console.warn(
          '? Servidor no disponible temporalmente. Esto es normal durante reinicios.'
        )

        console.warn(
          '   Verifica que el backend esté funcionando en:',
          API_BASE_URL || 'NO CONFIGURADO'
        )

        return
      }

      // Mensaje más descriptivo según el tipo de error

      let errorMsg = 'Error de conexión. Verifique su conexión a internet.'

      if (errorCode === 'ECONNABORTED' || errorMessage.includes('timeout')) {
        errorMsg =
          'Tiempo de espera agotado. El servidor esté tardando demasiado en responder.'
      } else if (errorCode === 'ERR_NETWORK') {
        errorMsg =
          'Error de red. Verifique que el servidor esté funcionando y su conexión a internet.'
      }

      toast.error(errorMsg)
    } else {
      // Error de configuración

      toast.error('Error en la configuración de la petición')
    }
  }

  // Métodos HTTP

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    // Detectar endpoints lentos y usar timeout extendido (p. ej. Render tarda 3-5 s en frío)

    const isSlowEndpoint =
      url.includes('/dashboard/') ||
      url.includes('/reportes/') ||
      url.includes('/notificaciones-previas') ||
      url.includes('/admin') ||
      url.includes('/evolucion') ||
      url.includes('/tendencia') ||
      url.includes('/ml-impago/modelos') ||
      url.includes('/ml-riesgo/modelos') ||
      url.includes('/ai/training/') ||
      url.includes('/cobros/') ||
      url.includes('/cobranzas/') ||
      url.includes('/auditoria/prestamos/cartera') ||
      url.includes('/pagos/kpis') ||
      url.includes('/pagos/stats') ||
      url.includes('/revision-manual/') || // Render cold start + consulta pesada
      url.includes('/conciliacion-sheet/diagnostico') || // Ping Google + lecturas BD
      url.includes('listado-y-kpis') || // Cobros: listado + KPIs en un request (dos consultas BD)
      url.includes('/notificaciones/clientes-retrasados') ||
      url.includes('/notificaciones-prejudicial')

    // ? Timeout especial para revision-manual (Render cold start + BD)

    const isRevisionManual = url.includes('/revision-manual/')

    const revisionManualTimeout = 120000 // 120 segundos

    // ? Timeout especial para reportes (Render cold start + consultas BD pesadas)

    const isReportesDashboard =
      url.includes('/reportes/') &&
      (url.includes('/dashboard/') || url.includes('/resumen'))

    const reportesDashboardTimeout = 120000 // 120 segundos

    // ? Timeout especial para clientes-atrasados que puede procesar muchos registros (2868+)

    const isClientesAtrasados = url.includes('/cobranzas/clientes-atrasados')

    const verySlowTimeout = 120000 // 120 segundos para endpoints muy pesados

    // ? Timeout extendido para tablas-campos que consulta toda la estructura de BD

    const isTablasCampos = url.includes('/tablas-campos')

    const tablasCamposTimeout = 90000 // 90 segundos para consulta de estructura completa de BD

    const isDiagnosticoPaquetePrueba = url.includes(
      'diagnostico-paquete-prueba'
    )

    const diagnosticoPaqueteTimeout = 180000

    // Cobros listado+KPIs: muchas filas + validadores por lote pueden superar 60s en Render frío.
    const isListadoKpisPagosReportados = url.includes('listado-y-kpis')

    const listadoKpisPagosReportadosTimeout = 180000

    // Préstamos Drive: snapshot lee tabla cache + validaciones; en Render frío puede acercarse a 60s.
    const isCandidatosDriveSnapshot = url.includes(
      '/prestamos/candidatos-drive/snapshot'
    )

    const candidatosDriveSnapshotTimeout = 120000

    // Sesión al arranque: Render frío + CORS preflight puede dejar el GET por detrás de un timeout corto.
    const isAuthMe = url.includes('/auth/me')

    let defaultTimeout = DEFAULT_TIMEOUT_MS

    if (isAuthMe) {
      defaultTimeout = SLOW_ENDPOINT_TIMEOUT_MS
    } else if (isListadoKpisPagosReportados) {
      defaultTimeout = listadoKpisPagosReportadosTimeout
    } else if (isCandidatosDriveSnapshot) {
      defaultTimeout = candidatosDriveSnapshotTimeout
    } else if (isRevisionManual) {
      defaultTimeout = revisionManualTimeout
    } else if (isReportesDashboard) {
      defaultTimeout = reportesDashboardTimeout
    } else if (isClientesAtrasados) {
      defaultTimeout = verySlowTimeout
    } else if (isDiagnosticoPaquetePrueba) {
      defaultTimeout = diagnosticoPaqueteTimeout
    } else if (isTablasCampos) {
      defaultTimeout = tablasCamposTimeout
    } else if (isSlowEndpoint) {
      defaultTimeout = SLOW_ENDPOINT_TIMEOUT_MS
    }

    // ? Priorizar timeout explícito si se proporciona, sino usar el calculado

    const timeout = config?.timeout ?? defaultTimeout

    // ? Asegurar que el timeout se aplique correctamente

    // Axios respeta el timeout en la configuración del request sobre el del cliente

    const finalConfig = {
      ...config,

      timeout,
    }

    const dedupKey = this.shouldDeduplicateHeavyGet(url)
      ? this.buildGetDedupKey(url, finalConfig)
      : null
    if (dedupKey) {
      const pending = this.inFlightGetRequests.get(dedupKey) as
        | Promise<T>
        | undefined
      if (pending) {
        return await pending
      }
    }

    const requestPromise = this.client
      .get<T>(url, finalConfig)
      .then((response: AxiosResponse<T>) => {
        if (response.status >= 400 && response.status < 500) {
          const backendMessage =
            (response.data as any)?.detail ||
            (response.data as any)?.message ||
            `Request failed with status ${response.status}`

          const error = new Error(backendMessage) as any

          error.response = response

          error.isAxiosError = true

          error.code = `ERR_HTTP_${response.status}`

          throw error
        }
        return response.data
      })
      .finally(() => {
        if (dedupKey) this.inFlightGetRequests.delete(dedupKey)
      })

    if (dedupKey) this.inFlightGetRequests.set(dedupKey, requestPromise)

    return await requestPromise
  }

  /**
   * GET con respuesta binaria y la misma autenticación que el resto de la API.
   * Útil para `<img>` cuando la URL directa devolvería 401 (p. ej. comprobante-imagen).
   */
  async getBlob(url: string, config?: AxiosRequestConfig): Promise<Blob> {
    // Comprobantes / recibos pueden ser MB grandes + Render frío → 30s suele cortar con ECONNABORTED.
    const isCobrosPagoReportadoBlob =
      url.includes('/cobros/pagos-reportados/') &&
      (url.includes('/comprobante') || url.includes('/recibo.pdf'))
    const defaultBlobTimeout = isCobrosPagoReportadoBlob
      ? 120000
      : Math.max(DEFAULT_TIMEOUT_MS, 60000)
    const response = await this.client.get(url, {
      ...config,
      responseType: 'blob',
      timeout: config?.timeout ?? defaultBlobTimeout,
    })
    if (response.status >= 400 && response.status < 500) {
      let backendMessage = `Request failed with status ${response.status}`
      const blobErr = response.data as Blob
      if (blobErr && typeof blobErr.text === 'function') {
        try {
          const txt = await blobErr.text()
          try {
            const j = JSON.parse(txt) as {
              detail?: unknown
              message?: string
            }
            if (typeof j.detail === 'string') {
              backendMessage = j.detail
            } else if (Array.isArray(j.detail)) {
              backendMessage = j.detail
                .map((x: { msg?: string }) =>
                  typeof x?.msg === 'string' ? x.msg : JSON.stringify(x)
                )
                .join('; ')
            } else if (j.message) {
              backendMessage = j.message
            }
          } catch {
            if (txt && txt.length > 0 && txt.length < 500) {
              backendMessage = txt
            }
          }
        } catch {
          /* ignore */
        }
      }
      const error = new Error(backendMessage) as any
      error.response = response
      error.isAxiosError = true
      error.code = `ERR_HTTP_${response.status}`
      throw error
    }
    return response.data as Blob
  }

  async post<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    try {
      // Cobros: aprobar/rechazar/enviar recibo/re-analizar generan PDF, SMTP, import a pagos - en Render suele >30s.
      const isCobrosEscanerGemini = url.includes(
        '/cobros/escaner/extraer-comprobante'
      )

      const isCobrosPagosReportadosHeavyPost =
        (url.includes('/cobros/pagos-reportados/') &&
          (url.includes('/aprobar') ||
            url.includes('/rechazar') ||
            url.includes('/enviar-recibo') ||
            url.includes('/re-analizar-gemini'))) ||
        url.includes('/cobros/pagos-reportados/marcar-exportados')

      // Detectar endpoints lentos (entrenamiento ML, etc.) y usar timeout extendido

      const isSlowEndpoint =
        url.includes('/ml-riesgo/entrenar') ||
        url.includes('/ml-impago/entrenar') ||
        url.includes('/fine-tuning/iniciar') ||
        url.includes('/rag/generar-embeddings') ||
        url.includes('/configuracion/ai/chat') ||
        url.includes('/prestamos/cedula/batch') || // Batch carga masiva: muchas cédulas
        url.includes('/pagos/upload') || // Carga masiva pagos: puede tardar con muchas filas
        url.includes('/pagos/batch') || // POST batch pagos: muchas filas + validaciones
        url.includes('/aplicar-pagos-cuotas') || // Cascada por préstamo: muchos pagos/cuotas en Render
        url.includes('/pagos/gmail/run-now') ||
        url.includes('/clientes/check-emails') ||
        url.includes('/clientes/check-cedulas') || // Pipeline Gmail: puede tardar si el backend es síncrono (credenciales OAuth)
        url.includes('/conciliacion-sheet/sync-now') || // Sheets API + escritura snapshot BD
        url.includes('/prestamos/candidatos-drive/refrescar') || // Recorre drive + prestamos + reescribe snapshot
        url.includes('/prestamos/candidatos-drive/guardar-validados-100') || // Crear préstamos por cada fila válida
        url.includes('/prestamos/candidatos-drive/guardar-fila') || // Una fila + mismas validaciones que el lote
        url.includes('/prestamos/recalcular-fechas-amortizacion-lote') || // Hasta 80 préstamos × ~3s en Render
        url.includes('/clientes/drive-import/importar') || // Lote: un commit por fila; cientos de filas >30s en Render
        url.includes('/configuracion/email/probar') || // Prueba SMTP; Recibos puede generar PDF + envío >30s
        url.includes('/notificaciones/recibos/ejecutar') // Lote recibos: PDF/SMTP; en Render frío suele >30s

      // Auditoria cartera en Render: sincroniza decenas de miles de cuotas + cascadas masivas (siempre >30s).
      const isAuditoriaCarteraCorregir = url.includes(
        '/auditoria/prestamos/cartera/corregir'
      )
      const isAuditoriaCarteraEjecutar = url.includes(
        '/auditoria/prestamos/cartera/ejecutar'
      )
      const isAuditoriaCarteraSyncCuotas = url.includes(
        '/auditoria/prestamos/cartera/sincronizar-estados-cuotas'
      )

      let defaultTimeout = DEFAULT_TIMEOUT_MS
      if (isCobrosEscanerGemini) {
        defaultTimeout = 120000 // Gemini + lectura comprobante
      } else if (isCobrosPagosReportadosHeavyPost) {
        defaultTimeout = 180000 // 3 min: PDF + SMTP + import; PATCH detalle ya visto ~35s en producción
      } else if (isAuditoriaCarteraCorregir) {
        defaultTimeout = 300000 // 5 min
      } else if (isAuditoriaCarteraEjecutar) {
        defaultTimeout = 180000 // 3 min
      } else if (isAuditoriaCarteraSyncCuotas) {
        defaultTimeout = 120000 // alinear muchas cuotas
      } else if (isSlowEndpoint) {
        defaultTimeout = url.includes('/clientes/drive-import/importar')
          ? 600000 // 10 min: import parcial muchas filas (commit por fila + Render frío)
          : url.includes('/prestamos/cedula/batch')
            ? 60000
            : url.includes('/aplicar-pagos-cuotas')
              ? 120000 // 2 min: cascada por préstamo puede exceder 30s en producción
              : url.includes('/pagos/upload')
                ? 120000
                : url.includes('/pagos/batch')
                  ? 180000 // 3 min: Render frío + muchas filas
                  : url.includes('/pagos/gmail/run-now')
                    ? 90000 // 90s: cubre credenciales OAuth + margen para backend síncrono viejo
                    : url.includes('/clientes/check-emails') ||
                        url.includes('/clientes/check-cedulas')
                      ? 60000
                      : 300000
      }

      // Priorizar timeout explícito si se proporciona, sino usar el calculado

      const timeout = config?.timeout ?? defaultTimeout

      const finalConfig = { ...config, timeout }

      const response: AxiosResponse<T> = await this.client.post(
        url,
        data,
        finalConfig
      )

      // Verificar si la respuesta es un error 4xx (validateStatus permite 4xx pero debemos manejarlos)

      if (response.status >= 400 && response.status < 500) {
        // 401 en login/refresh es esperado (credenciales incorrectas); solo log en desarrollo para no saturar consola

        const isAuthFailure =
          response.status === 401 &&
          (url.includes('/auth/login') || url.includes('/auth/refresh'))

        if (isAuthFailure && process.env.NODE_ENV === 'development') {
          console.warn('? [ApiClient] Login/refresh no autorizado (401):', url)
        } else if (!isAuthFailure) {
          const is409Pagos = response.status === 409 && url.includes('/pagos')

          if (!is409Pagos) {
            console.info('[ApiClient] POST recibió error 4xx:', {
              url,
              status: response.status,
              data: compactFor4xxLog(response.data),
            })
          }

          // 409 en pagos: no loguear por cada fila (satura consola); la UI ya muestra toast/resumen
        }

        // Crear un error de Axios para que se maneje correctamente, preservando el mensaje del backend

        const backendMessage = readBackend4xxErrorMessage(
          response.status,
          response.data
        )

        const error = new Error(backendMessage) as any

        error.response = response

        error.isAxiosError = true

        error.code = `ERR_HTTP_${response.status}`

        throw error
      }

      return response.data
    } catch (error: any) {
      const is409Pagos =
        error?.response?.status === 409 && url.includes('/pagos')

      if (!is409Pagos) {
        const status = error?.response?.status

        const detail =
          typeof status === 'number'
            ? readBackend4xxErrorMessage(status, error?.response?.data)
            : undefined

        console.info('[ApiClient] POST error:', {
          url,
          status,
          detail: detail ?? error?.message,
        })
      }

      throw error
    }
  }

  async put<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const logPut = process.env.NODE_ENV === 'development'
    if (logPut) {
      console.log('? [ApiClient] PUT request:', {
        url,
        data: data ? '***' : '(vacío)',
        config,
      })
    }

    try {
      const aiConfigPut =
        url.includes('/configuracion/ai/configuracion') &&
        !url.includes('/prompt')

      const putTimeoutMs = aiConfigPut
        ? Math.max(config?.timeout ?? 0, 60000)
        : (config?.timeout ?? DEFAULT_TIMEOUT_MS)

      const executePut = async () =>
        await this.client.put<T>(url, data, {
          ...config,
          timeout: putTimeoutMs,
        })
      const putGroup = this.getPutConcurrencyGroup(url)
      const response: AxiosResponse<T> = putGroup
        ? await this.runWithPutLimit(putGroup.key, putGroup.limit, executePut)
        : await executePut()

      if (logPut) {
        console.log('? [ApiClient] PUT response:', {
          url,
          status: response.status,
          data: response.data,
        })
      }

      // Verificar si la respuesta es un error 4xx (validateStatus permite 4xx pero debemos manejarlos)

      if (response.status >= 400 && response.status < 500) {
        if (logPut) {
          console.error('? [ApiClient] PUT recibió error 4xx:', {
            url,
            status: response.status,
            data: response.data,
          })
        }

        const raw = response.data as any
        let backendMessage: string =
          raw?.message || `Request failed with status ${response.status}`
        const d = raw?.detail
        if (typeof d === 'string') {
          backendMessage = d
        } else if (Array.isArray(d)) {
          backendMessage = d
            .map((x: any) =>
              typeof x?.msg === 'string' ? x.msg : JSON.stringify(x)
            )
            .join('; ')
        } else if (d != null && typeof d === 'object') {
          backendMessage = JSON.stringify(d)
        }

        const error = new Error(backendMessage) as any

        error.response = response

        error.isAxiosError = true

        error.code = `ERR_HTTP_${response.status}`

        throw error
      }

      return response.data
    } catch (error) {
      if (logPut) {
        console.error('? [ApiClient] PUT error:', { url, error })
      }

      throw error
    }
  }

  async patch<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const isCobrosPagoReportadoPatch = url.includes('/cobros/pagos-reportados/')
    const patchTimeoutMs =
      config?.timeout ??
      (isCobrosPagoReportadoPatch ? 120000 : DEFAULT_TIMEOUT_MS)
    const response: AxiosResponse<T> = await this.client.patch(url, data, {
      ...config,
      timeout: patchTimeoutMs,
    })

    // validateStatus permite 4xx sin lanzar en axios; igual que delete(), fallar aquí
    if (response.status >= 400 && response.status < 500) {
      const raw = response.data as any
      let backendMessage: string =
        raw?.message || `Request failed with status ${response.status}`
      const d = raw?.detail
      if (typeof d === 'string') {
        backendMessage = d
      } else if (Array.isArray(d)) {
        backendMessage = d
          .map((x: any) =>
            typeof x?.msg === 'string' ? x.msg : JSON.stringify(x)
          )
          .join('; ')
      } else if (d != null && typeof d === 'object') {
        backendMessage = JSON.stringify(d)
      }

      const error = new Error(backendMessage) as any
      error.response = response
      error.isAxiosError = true
      error.code = `ERR_HTTP_${response.status}`
      throw error
    }

    return response.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const pathOnly = (url || '').split('?')[0]
    const isSlowPagosDelete =
      /\/pagos\/\d+$/.test(pathOnly) ||
      /\/pagos\/por-prestamo\/\d+\/todos$/.test(pathOnly)
    const timeoutMs =
      config?.timeout ?? (isSlowPagosDelete ? 180000 : DEFAULT_TIMEOUT_MS)

    const response: AxiosResponse<T> = await this.client.delete(url, {
      ...config,
      timeout: timeoutMs,
    })

    // Verificar si la respuesta es un error 4xx (validateStatus permite 4xx pero debemos manejarlos)

    if (response.status >= 400 && response.status < 500) {
      const backendMessage =
        (response.data as any)?.detail ||
        (response.data as any)?.message ||
        `Request failed with status ${response.status}`

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

  /** POST con cuerpo JSON; respuesta binaria (p. ej. xlsx). En 4xx intenta leer JSON desde el blob del error. */
  async postDownloadFile(
    url: string,
    data?: unknown,
    fallbackFilename: string = 'download.bin'
  ): Promise<void> {
    const response = await this.client.post(url, data ?? {}, {
      responseType: 'blob',
      timeout: Math.max(SLOW_ENDPOINT_TIMEOUT_MS, 120000),
    })

    if (response.status >= 400 && response.status < 500) {
      let backendMessage = `Request failed with status ${response.status}`
      const blobErr = response.data as Blob
      if (blobErr && typeof blobErr.text === 'function') {
        try {
          const txt = await blobErr.text()
          try {
            const j = JSON.parse(txt) as {
              detail?: unknown
              message?: string
            }
            if (typeof j.detail === 'string') {
              backendMessage = j.detail
            } else if (Array.isArray(j.detail)) {
              backendMessage = j.detail
                .map((x: { msg?: string }) =>
                  typeof x?.msg === 'string' ? x.msg : JSON.stringify(x)
                )
                .join('; ')
            } else if (j.message) {
              backendMessage = j.message
            }
          } catch {
            if (txt && txt.length > 0 && txt.length < 500) {
              backendMessage = txt
            }
          }
        } catch {
          /* ignore */
        }
      }
      const error = new Error(backendMessage) as any
      error.response = response
      error.isAxiosError = true
      error.code = `ERR_HTTP_${response.status}`
      throw error
    }

    const rawCd =
      (response.headers['content-disposition'] as string | undefined) ||
      (response.headers['Content-Disposition'] as string | undefined)
    let filename = fallbackFilename
    if (rawCd) {
      const mStar = /filename\*=UTF-8''([^;]+)/i.exec(rawCd)
      if (mStar?.[1]) {
        try {
          filename = decodeURIComponent(mStar[1].trim())
        } catch {
          filename = mStar[1].trim()
        }
      } else {
        const m =
          /filename="([^"]+)"/i.exec(rawCd) || /filename=([^;\s]+)/i.exec(rawCd)
        if (m?.[1]) {
          filename = m[1].replace(/"/g, '')
        }
      }
    }

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
  ;(window as Window & { clearAuthStorage?: () => void }).clearAuthStorage =
    () => {
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

export function buildUrl(
  baseUrl: string,
  params?: Record<string, any>
): string {
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
