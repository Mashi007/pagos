import { apiClient } from '../services/api'
import { finiquitoGetBlob } from '../services/finiquitoService'

/**
 * Ruta `/api/v1/pagos/comprobante-imagen/{id}` extraída de una URL absoluta o relativa.
 * Sirve para GET con el mismo cliente Axios (Bearer) en lugar de abrir la URL en pestaña nueva.
 */
export function pathApiComprobanteImagenDesdeHref(href: string): string | null {
  const t = String(href ?? '').trim()
  if (!t) return null
  const m = /(\/api\/v1\/pagos\/comprobante-imagen\/[^/?#\s]+)/i.exec(t)
  return m ? m[1] : null
}

/** True si el enlace apunta al comprobante interno (requiere Authorization). */
export function esUrlComprobanteImagenConAuth(href: string): boolean {
  return pathApiComprobanteImagenDesdeHref(href) != null
}

/**
 * Abre el comprobante en una pestaña nueva. Si es comprobante-imagen, descarga con sesión
 * y muestra un object URL; si no, delega en `window.open` (p. ej. Drive).
 */
/** Descarga el comprobante interno (`/api/v1/pagos/comprobante-imagen/...`) con la sesión staff. */
export async function fetchStaffComprobanteBlobFromHref(
  href: string
): Promise<Blob> {
  const t = String(href ?? '').trim()
  const path = pathApiComprobanteImagenDesdeHref(t)
  if (!path) {
    throw new Error('El enlace no es un comprobante interno descargable con sesión.')
  }
  return apiClient.getBlob(path)
}

export async function abrirStaffComprobanteDesdeHref(href: string): Promise<void> {
  const t = String(href ?? '').trim()
  if (!t) return
  const path = pathApiComprobanteImagenDesdeHref(t)
  if (!path) {
    window.open(t, '_blank', 'noopener,noreferrer')
    return
  }
  const blob = await apiClient.getBlob(path)
  const url = URL.createObjectURL(blob)
  const w = window.open(url, '_blank', 'noopener,noreferrer')
  if (!w) {
    URL.revokeObjectURL(url)
    return
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
}

/** Misma lógica que staff pero con JWT del portal Finiquito (revisión de caso). */
export async function abrirFiniquitoComprobanteDesdeHref(
  href: string
): Promise<void> {
  const t = String(href ?? '').trim()
  if (!t) return
  const path = pathApiComprobanteImagenDesdeHref(t)
  if (!path) {
    window.open(t, '_blank', 'noopener,noreferrer')
    return
  }
  const blob = await finiquitoGetBlob(path)
  const url = URL.createObjectURL(blob)
  const w = window.open(url, '_blank', 'noopener,noreferrer')
  if (!w) {
    URL.revokeObjectURL(url)
    return
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
}

export async function abrirComprobanteDesdeHref(
  href: string,
  authMode: 'staff' | 'finiquito'
): Promise<void> {
  if (authMode === 'finiquito') {
    return abrirFiniquitoComprobanteDesdeHref(href)
  }
  return abrirStaffComprobanteDesdeHref(href)
}
