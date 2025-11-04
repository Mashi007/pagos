/**
 * Tipos comunes para manejo de errores
 * Evita el uso de 'any' en bloques catch
 */

import { AxiosError } from 'axios'

/**
 * Tipo para errores en bloques catch
 * Usar 'unknown' en lugar de 'any' para mayor seguridad
 */
export type ErrorLike = Error | AxiosError | unknown

/**
 * Verifica si un error es una instancia de Error
 */
export function isError(error: unknown): error is Error {
  return error instanceof Error
}

/**
 * Verifica si un error es un AxiosError
 */
export function isAxiosError(error: unknown): error is AxiosError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as { isAxiosError?: boolean }).isAxiosError === true
  )
}

/**
 * Obtiene el mensaje de error de forma segura
 */
export function getErrorMessage(error: unknown): string {
  if (isError(error)) {
    return error.message
  }
  if (isAxiosError(error)) {
    const responseData = error.response?.data as { detail?: string; message?: string } | undefined
    return (
      responseData?.detail ||
      responseData?.message ||
      error.message ||
      'Error de red'
    )
  }
  if (typeof error === 'string') {
    return error
  }
  return 'Error desconocido'
}

/**
 * Obtiene el detail del error de respuesta de forma segura
 */
export function getErrorDetail(error: unknown): string | undefined {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string } | undefined
    return typeof data?.detail === 'string' ? data.detail : undefined
  }
  return undefined
}

/**
 * Obtiene detalles adicionales del error (para logging)
 */
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

