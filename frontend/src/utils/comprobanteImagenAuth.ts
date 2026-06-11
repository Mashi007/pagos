import { apiClient } from '../services/api'

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

function sniffHeicHeifFromHead(u: Uint8Array): 'image/heic' | 'image/heif' | null {
  if (u.length < 16) return null
  if (u[4] !== 0x66 || u[5] !== 0x74 || u[6] !== 0x79 || u[7] !== 0x70) {
    return null
  }
  const marca = String.fromCharCode(...u.slice(8, Math.min(48, u.length))).toLowerCase()
  if (/heic|heix|hevc|hevx/.test(marca)) return 'image/heic'
  if (/mif1|msf1/.test(marca)) return 'image/heif'
  return null
}

/** Primeros bytes del archivo para cuando `Blob.type` viene vacío u octet-stream. */
export function sniffComprobanteMimeFromHead(u: Uint8Array): string | null {
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
  return sniffHeicHeifFromHead(u)
}

function extensionDesdeMimeComprobante(mime: string): string {
  switch (mime) {
    case 'image/png':
      return 'png'
    case 'image/gif':
      return 'gif'
    case 'image/webp':
      return 'webp'
    case 'application/pdf':
      return 'pdf'
    case 'image/heic':
      return 'heic'
    case 'image/heif':
      return 'heif'
    default:
      return 'jpg'
  }
}

/**
 * Arma un `File` con MIME y extensión coherentes con el contenido real (OCR / escáner).
 * Evita enviar `application/octet-stream` o `.jpg` cuando el blob guardado es PDF/HEIC.
 */
export async function blobComprobanteAFileParaEscaneo(
  blob: Blob,
  contentTypeHint = ''
): Promise<File> {
  const buf = await blob.arrayBuffer()
  const head = new Uint8Array(buf.slice(0, Math.min(48, buf.byteLength)))
  const sniffed = sniffComprobanteMimeFromHead(head)
  let mime = (contentTypeHint || blob.type || '').split(';')[0].trim().toLowerCase()
  if (
    !mime ||
    mime === 'application/octet-stream' ||
    mime === 'binary/octet-stream'
  ) {
    mime = sniffed || ''
  } else if (sniffed && sniffed !== mime) {
    // BD o navegador pueden declarar image/jpeg sobre HEIC/PNG real; priorizar firma.
    mime = sniffed
  }
  if (!mime) {
    throw new Error(
      'No se pudo identificar el tipo del comprobante. Use «Elegir imagen» y vuelva a escanear.'
    )
  }
  if (mime === 'image/jpg') mime = 'image/jpeg'
  const ext = extensionDesdeMimeComprobante(mime)
  return new File([buf], `comprobante.${ext}`, { type: mime })
}

/**
 * Descarga comprobante interno y normaliza `Content-Type` para `<img>` / iframe en el panel de revisión.
 */
export async function fetchStaffComprobanteBlobWithDisplayMime(
  href: string
): Promise<{ blob: File; contentType: string }> {
  const raw = await fetchStaffComprobanteBlobFromHref(href)
  const file = await blobComprobanteAFileParaEscaneo(raw, raw.type)
  return { blob: file, contentType: file.type }
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

export async function abrirComprobanteDesdeHref(href: string): Promise<void> {
  return abrirStaffComprobanteDesdeHref(href)
}
