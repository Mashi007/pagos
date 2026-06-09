/**
 * HEIC/HEIF (iPhone): el backend normaliza con pillow-heif → JPEG antes de Gemini.
 * En navegadores (p. ej. Chrome en Windows) conviene convertir en cliente para el mismo
 * pipeline que JPG (recorte, contraste, OCR).
 */
export function archivoEsHeicHeif(file: File): boolean {
  const name = (file.name || '').toLowerCase()
  const ext = name.includes('.') ? name.slice(name.lastIndexOf('.')) : ''
  const mime = (file.type || '').split(';')[0].trim().toLowerCase()
  return (
    ext === '.heic' ||
    ext === '.heif' ||
    mime === 'image/heic' ||
    mime === 'image/heif'
  )
}

export async function normalizarComprobanteArchivoParaEscaneo(
  file: File
): Promise<File> {
  if (!archivoEsHeicHeif(file)) {
    return file
  }
  const mod = await import('heic2any')
  const heic2any = mod.default
  const out = await heic2any({
    blob: file,
    toType: 'image/jpeg',
    quality: 0.92,
  })
  const jpegBlob = Array.isArray(out) ? out[0] : out
  if (!(jpegBlob instanceof Blob)) {
    throw new Error('No se pudo convertir HEIC a JPEG.')
  }
  const base =
    file.name.replace(/\.(heic|heif)$/i, '').trim() || 'comprobante'
  return new File([jpegBlob], `${base}.jpg`, {
    type: 'image/jpeg',
    lastModified: file.lastModified,
  })
}
