import { apiClient } from '../services/api'
import { pathApiComprobanteImagenDesdeHref } from './comprobanteImagenAuth'
import { archivoEsHeicHeif } from './normalizarComprobanteArchivo'

function archivoEsPdf(file: File): boolean {
  return (
    file.type === 'application/pdf' || /\.pdf$/i.test(file.name || '')
  )
}

/** ¿Conviene pedir al backend JPEG para vista (HEIC iPhone u octet-stream)? */
export function archivoNecesitaVistaWebBackend(file: File): boolean {
  if (archivoEsPdf(file)) return false
  if (archivoEsHeicHeif(file)) return true
  const mime = (file.type || '').split(';')[0].trim().toLowerCase()
  if (!mime || mime === 'application/octet-stream') return true
  return false
}

export function hrefComprobanteConDisplayWeb(href: string): string {
  const path = pathApiComprobanteImagenDesdeHref(href)
  if (!path) return href
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}display=web`
}

/** Convierte HEIC/local opaco a JPEG vía API (sin guardar en BD). */
export async function solicitarVistaWebDesdeArchivo(file: File): Promise<Blob> {
  const fd = new FormData()
  fd.append('file', file)
  return apiClient.postBlob('/api/v1/pagos/comprobante-imagen/vista-web', fd)
}

/**
 * Object URL listo para ``<img>`` (revocar al desmontar).
 * HEIC iPhone → JPEG en servidor; JPEG/PNG/WebP → blob local.
 */
export async function crearObjectUrlVistaComprobante(
  file: File
): Promise<string> {
  if (archivoEsPdf(file)) {
    return URL.createObjectURL(file)
  }
  if (!archivoNecesitaVistaWebBackend(file)) {
    return URL.createObjectURL(file)
  }
  const blob = await solicitarVistaWebDesdeArchivo(file)
  return URL.createObjectURL(blob)
}
