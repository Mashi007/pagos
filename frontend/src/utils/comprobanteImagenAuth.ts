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
    throw new Error(
      'El enlace no es un comprobante interno descargable con sesión.'
    )
  }
  return apiClient.getBlob(path)
}

/** Primeros bytes del archivo para cuando `Blob.type` viene vacío u octet-stream. */
function sniffComprobanteMimeFromHead(u: Uint8Array): string | null {
  if (u.length < 4) return null
  if (u[0] === 0xff && u[1] === 0xd8 && u[2] === 0xff) return 'image/jpeg'
  if (u[0] === 0x89 && u[1] === 0x50 && u[2] === 0x4e && u[3] === 0x47)
    return 'image/png'
  if (u[0] === 0x47 && u[1] === 0x49 && u[2] === 0x46 && u[3] === 0x38)
    return 'image/gif'
  if (u[0] === 0x25 && u[1] === 0x50 && u[2] === 0x44 && u[3] === 0x46)
    return 'application/pdf'
  if (
    u.length >= 12 &&
    u[0] === 0x52 &&
    u[1] === 0x49 &&
    u[2] === 0x46 &&
    u[3] === 0x46 &&
    u[8] === 0x57 &&
    u[9] === 0x45 &&
    u[10] === 0x42 &&
    u[11] === 0x50
  ) {
    return 'image/webp'
  }
  return null
}

/**
 * Descarga comprobante interno y normaliza `Content-Type` para `<img>` / iframe en el panel de revisión.
 */
export async function fetchStaffComprobanteBlobWithDisplayMime(
  href: string
): Promise<{ blob: Blob; contentType: string }> {
  const raw = await fetchStaffComprobanteBlobFromHref(href)
  let ct = (raw.type || '').trim()
  if (!ct || ct === 'application/octet-stream') {
    const head = new Uint8Array(await raw.slice(0, 24).arrayBuffer())
    const sniffed = sniffComprobanteMimeFromHead(head)
    if (sniffed) {
      const buf = await raw.arrayBuffer()
      return { blob: new Blob([buf], { type: sniffed }), contentType: sniffed }
    }
  }
  return {
    blob: raw,
    contentType: ct || 'application/octet-stream',
  }
}

export async function abrirStaffComprobanteDesdeHref(
  href: string
): Promise<void> {
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
