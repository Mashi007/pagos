/**
 * Bypass de bloqueos Cloudflare/edge en uploads multipart (HTML 403/502).
 * Preferir reintento JSON+base64 cuando el borde corta FormData.
 */

export function esErrorBloqueoBordeHtml(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const response = (err as { response?: { status?: number; data?: unknown; headers?: Record<string, unknown> } }).response
  const status = response?.status
  if (status !== 403 && status !== 502) return false
  const data = response?.data
  if (typeof data === 'string') {
    const lower = data.toLowerCase()
    if (
      lower.includes('<html') ||
      lower.includes('<!doctype') ||
      lower.includes('cloudflare')
    ) {
      return true
    }
  }
  const headers = response?.headers || {}
  const ct = String(
    headers['content-type'] ?? headers['Content-Type'] ?? ''
  ).toLowerCase()
  if (ct.includes('text/html')) return true
  const msg = err instanceof Error ? err.message.toLowerCase() : ''
  return (
    msg.includes('pagina html de error') ||
    msg.includes('página html de error') ||
    msg.includes('bloqueo en el borde') ||
    msg.includes('cloudflare')
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
