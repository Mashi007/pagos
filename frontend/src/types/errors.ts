/**
 * Tipos comunes para manejo de errores.
 * Evita el uso de 'any' en bloques catch.
 */

import { AxiosError } from 'axios'

/** Tipo para errores en bloques catch. Usar 'unknown' en lugar de 'any'. */
export type ErrorLike = Error | AxiosError | unknown

/** Verifica si un error es una instancia de Error. */
export function isError(error: unknown): error is Error {
  return error instanceof Error
}

/** Verifica si un error es un AxiosError (incluye los que ApiClient crea con isAxiosError). */
export function isAxiosError(error: unknown): error is AxiosError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as { isAxiosError?: boolean }).isAxiosError === true
  )
}

/** Timeout de Axios en peticiones largas (p. ej. envío masivo de correos). */
export function isAxiosTimeoutError(error: unknown): boolean {
  if (!isAxiosError(error)) return false
  const msg = (error.message || '').toLowerCase()
  return (
    error.code === 'ECONNABORTED' ||
    msg.includes('timeout') ||
    msg.includes('exceeded')
  )
}

/** Sin respuesta HTTP (timeout, proxy 502, red caída). No confundir con validación inválida. */
export function isNetworkOrTimeoutError(error: unknown): boolean {
  if (isAxiosTimeoutError(error)) return true
  if (isAxiosError(error) && error.response == null) return true
  const msg = getErrorMessage(error).toLowerCase()
  return /timeout|network|econnaborted|502|503|504|failed to fetch|ns_binding_aborted|load failed/i.test(
    msg
  )
}

/** Extrae mensaje legible de `response.data` (string, array FastAPI o `{ detail: { message } }`). */
function messageFromResponseData(data: unknown): string | undefined {
  if (typeof data === 'string' && data.trim()) return data.trim()
  if (!data || typeof data !== 'object') return undefined
  const responseData = data as {
    detail?: string | unknown
    message?: string
  }
  const d = responseData.detail
  if (typeof d === 'string' && d.trim()) return d.trim()
  if (Array.isArray(d)) {
    const joined = d
      .map((e: { msg?: string; message?: string }) => e?.msg || e?.message)
      .filter(Boolean)
      .join('; ')
    if (joined) return joined
  }
  if (d != null && typeof d === 'object') {
    const obj = d as { message?: unknown; msg?: unknown }
    if (typeof obj.message === 'string' && obj.message.trim()) {
      return obj.message.trim()
    }
    if (typeof obj.msg === 'string' && obj.msg.trim()) {
      return obj.msg.trim()
    }
  }
  if (typeof responseData.message === 'string' && responseData.message.trim()) {
    return responseData.message.trim()
  }
  return undefined
}

/** Obtiene el mensaje de error de forma segura. */
export function getErrorMessage(error: unknown): string {
  // AxiosError también es Error: preferir el body del backend.
  if (isAxiosError(error)) {
    const fromData = messageFromResponseData(error.response?.data)
    if (fromData) return fromData
    if (error.message) return error.message
    return 'Error de red'
  }

  if (isError(error)) {
    return error.message
  }

  if (typeof error === 'string') {
    return error
  }

  return 'Error desconocido'
}

/** Obtiene el detail del error de respuesta de forma segura. */
export function getErrorDetail(error: unknown): string | undefined {
  if (isAxiosError(error)) {
    return messageFromResponseData(error.response?.data)
  }
  return undefined
}

/** Código de error del backend (`code` o `detail.codigo`). */
export function getErrorCode(error: unknown): string | undefined {
  if (isAxiosError(error)) {
    const data = error.response?.data as
      | { code?: string; detail?: { codigo?: string; code?: string } }
      | undefined
    if (typeof data?.code === 'string') return data.code
    const d = data?.detail
    if (d && typeof d === 'object') {
      const obj = d as { codigo?: string; code?: string }
      if (typeof obj.codigo === 'string') return obj.codigo
      if (typeof obj.code === 'string') return obj.code
    }
    return undefined
  }
  return undefined
}

/** Detalles adicionales del error (para logging). */
export function getErrorDetails(error: unknown): Record<string, unknown> {
  if (isAxiosError(error)) {
    return {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      url: error.config?.url,
    }
  }

  if (isError(error)) {
    return {
      name: error.name,
      stack: error.stack,
    }
  }

  return {}
}
