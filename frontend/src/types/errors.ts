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
  if (typeof data === 'string' && data.trim()) {
    const s = data.trim()
    // Proxy Render/Cloudflare a veces devuelve HTML 502/503; no mostrar el markup.
    if (
      /<!doctype\s+html|<html[\s>]|<\/html>/i.test(s) ||
      (/502|bad gateway|503|service unavailable/i.test(s) &&
        /<html|<body|<title/i.test(s))
    ) {
      if (/502|bad gateway/i.test(s)) {
        return (
          'El servidor no respondió a tiempo (502). Espere unos segundos y reintente; ' +
          'si genera un Excel grande, el proxy puede cortar la petición.'
        )
      }
      if (/503|service unavailable/i.test(s)) {
        return 'Servicio temporalmente no disponible (503). Reintente en unos segundos.'
      }
      return 'Error del servidor (respuesta HTML del proxy). Reintente en unos momentos.'
    }
    return s
  }
  if (!data || typeof data !== 'object') return undefined
  // Blob de error con responseType: 'blob' (no se puede leer aquí de forma sync).
  if (typeof Blob !== 'undefined' && data instanceof Blob) {
    return undefined
  }
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
    const status = error.response?.status
    if (status === 502) {
      return (
        'El servidor no respondió a tiempo (502). Espere unos segundos y reintente; ' +
        'si genera un Excel grande, el proxy puede cortar la petición.'
      )
    }
    if (status === 503 || status === 504) {
      return `Servicio temporalmente no disponible (${status}). Reintente en unos segundos.`
    }
    const fromData = messageFromResponseData(error.response?.data)
    if (fromData) return fromData
    if (error.message) return error.message
    return 'Error de red'
  }

  if (isError(error)) {
    const msg = error.message || ''
    if (/<!doctype\s+html|<html[\s>]/i.test(msg)) {
      return 'Error del servidor (respuesta HTML). Reintente en unos momentos.'
    }
    return msg || 'Error desconocido'
  }

  if (typeof error === 'string') {
    if (/<!doctype\s+html|<html[\s>]/i.test(error)) {
      return 'Error del servidor (respuesta HTML). Reintente en unos momentos.'
    }
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

/** `detail` del 409 cuando el backend envía un objeto (duplicado → revisión). */
export function getErrorDetailRecord(
  error: unknown
): Record<string, unknown> | null {
  if (!isAxiosError(error)) return null
  const data = error.response?.data as { detail?: unknown } | undefined
  const d = data?.detail
  if (d && typeof d === 'object' && !Array.isArray(d)) {
    return d as Record<string, unknown>
  }
  return null
}

export function esDuplicadoEnviadoARevision(error: unknown): boolean {
  if (!isAxiosError(error) || error.response?.status !== 409) return false
  const rec = getErrorDetailRecord(error)
  if (rec?.resolver_en_revision_manual === true) return false
  const code = getErrorCode(error)
  if (
    code === 'SERIAL_DUPLICADO_EN_SITIO' ||
    code === 'HUELLA_DUPLICADA_EN_SITIO'
  ) {
    return false
  }
  if (rec?.revision_manual === true) return true
  return (
    code === 'BINANCE_SERIAL_DUPLICADO' ||
    code === 'SERIAL_DUPLICADO_REVISION' ||
    code === 'HUELLA_DUPLICADA_REVISION'
  )
}

/** 409: duplicado detectado en revisión manual; el humano debe resolverlo ahí (sin cola). */
export function esDuplicadoResolverEnSitio(error: unknown): boolean {
  if (!isAxiosError(error) || error.response?.status !== 409) return false
  const rec = getErrorDetailRecord(error)
  if (rec?.resolver_en_revision_manual === true) return true
  const code = getErrorCode(error)
  return (
    code === 'SERIAL_DUPLICADO_EN_SITIO' || code === 'HUELLA_DUPLICADA_EN_SITIO'
  )
}

export const MSG_PAGO_EN_PROCESO_NO_INGRESAR =
  'No puede ingresarse ese pago porque está siendo procesado.'

/** 409: el comprobante ya está en pagos o en la cola de reportados. */
export function esPagoEnProcesoBloqueado(error: unknown): boolean {
  if (!isAxiosError(error) || error.response?.status !== 409) return false
  if (getErrorCode(error) === 'PAGO_EN_PROCESO') return true
  const rec = getErrorDetailRecord(error)
  return rec?.codigo === 'PAGO_EN_PROCESO'
}

export function avisarPagoEnProceso(mensaje?: string): void {
  const texto =
    (mensaje && String(mensaje).trim()) || MSG_PAGO_EN_PROCESO_NO_INGRESAR
  window.alert(texto)
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
