/**
 * Bypass de bloqueos Cloudflare/edge en uploads multipart (HTML 403/502/520…).
 * Preferir reintento JSON+base64 cuando el borde corta FormData o el origen
 * responde vacío/malformado (Cloudflare 520).
 */

const STATUS_BORDE_REINTENTABLE = new Set([403, 502, 520, 521, 522, 523, 524])

function cuerpoPareceErrorBorde(data: unknown): boolean {
  if (typeof data === 'string') {
    const lower = data.toLowerCase()
    return (
      lower.includes('<html') ||
      lower.includes('<!doctype') ||
      lower.includes('cloudflare') ||
      lower.includes('could not parse') ||
      lower.includes('origin web server') ||
      lower.includes('bad gateway') ||
      lower.includes('web server is returning an unknown error')
    )
  }
  if (data && typeof data === 'object') {
    const d = data as { detail?: unknown; message?: unknown; error?: unknown }
    const parts = [d.detail, d.message, d.error]
      .map(x => (typeof x === 'string' ? x : ''))
      .join(' ')
      .toLowerCase()
    return (
      parts.includes('cloudflare') ||
      parts.includes('could not parse') ||
      parts.includes('origin web server') ||
      parts.includes('web server is returning an unknown error')
    )
  }
  return false
}

export function esErrorBloqueoBordeHtml(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const response = (
    err as {
      response?: {
        status?: number
        data?: unknown
        headers?: Record<string, unknown>
      }
    }
  ).response
  const status = response?.status
  if (typeof status === 'number' && STATUS_BORDE_REINTENTABLE.has(status)) {
    // 520–524 de Cloudflare: reintentar aunque el cuerpo no sea HTML.
    if (status >= 520 && status <= 524) return true
    if (status === 502 || status === 403) {
      if (cuerpoPareceErrorBorde(response?.data)) return true
      const headers = response?.headers || {}
      const ct = String(
        headers['content-type'] ?? headers['Content-Type'] ?? ''
      ).toLowerCase()
      if (ct.includes('text/html')) return true
    }
  }
  const msg = err instanceof Error ? err.message.toLowerCase() : ''
  return (
    msg.includes('pagina html de error') ||
    msg.includes('página html de error') ||
    msg.includes('bloqueo en el borde') ||
    msg.includes('cloudflare') ||
    msg.includes('could not parse') ||
    msg.includes('origin web server')
  )
}

export function bytesToBase64(bytes: Uint8Array): string {
  const chunk = 0x8000
  let binary = ''
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk))
  }
  return btoa(binary)
}

export async function fileToBase64Payload(file: File | Blob): Promise<{
  archivo_base64: string
  filename: string
  content_type: string
}> {
  const buf = new Uint8Array(await file.arrayBuffer())
  const filename =
    typeof File !== 'undefined' && file instanceof File && file.name
      ? file.name
      : 'comprobante.jpg'
  const content_type = (file.type || '').trim() || 'image/jpeg'
  return {
    archivo_base64: bytesToBase64(buf),
    filename,
    content_type,
  }
}
