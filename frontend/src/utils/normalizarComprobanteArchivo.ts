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
  // HEIC/HEIF: el backend (pillow-heif) convierte antes de OCR. Evitamos heic2any en el
  // navegador porque usa eval/Function y la CSP de producción (script-src 'self') lo bloquea.
  return file
}
