/**
 * Alineado con backend `app.core.documento`: comprobante + código opcional → clave almacenada única.
 */
const SUFIJO = ' \u00a7CD:'
const MAX_DOC = 100
const MAX_CODIGO = 24

function normalizeCodigo(val: string | null | undefined): string | null {
  if (val == null) return null
  let s = String(val).trim()
  s = s.replace(/[\u200B-\u200D\uFEFF\r\n\t]/g, '').trim()
  if (
    !s ||
    ['NAN', 'NONE', 'UNDEFINED', 'NA', 'N/A'].includes(s.toUpperCase())
  ) {
    return null
  }
  if (s.includes('\u00a7CD:')) return null
  s = s.replace(/\s+/g, ' ').trim()
  if (!s) return null
  if (s.length > MAX_CODIGO) s = s.slice(0, MAX_CODIGO)
  return s
}

/**
 * `baseNorm` debe ser el resultado de normalizarNumeroDocumento (o equivalente) del comprobante.
 */
export function composeNumeroDocumentoAlmacenado(
  baseNorm: string | null | undefined,
  codigo: string | null | undefined
): string | null {
  const b = (baseNorm || '').trim()
  if (!b) return null
  const c = normalizeCodigo(codigo ?? undefined)
  if (!c) return b.length > MAX_DOC ? b.slice(0, MAX_DOC) : b
  const suf = SUFIJO + c
  const maxBase = MAX_DOC - suf.length
  if (maxBase < 1) return null
  const bn = b.length > maxBase ? b.slice(0, maxBase) : b
  const out = bn + suf
  return out.length > MAX_DOC ? out.slice(0, MAX_DOC) : out
}

export function splitNumeroDocumentoAlmacenado(
  stored: string | null | undefined
): { base: string; codigo: string } {
  const s = (stored || '').trim()
  if (!s) return { base: '', codigo: '' }
  if (s.includes(SUFIJO)) {
    const i = s.lastIndexOf(SUFIJO)
    const base = s.slice(0, i).trim()
    const codigo = s.slice(i + SUFIJO.length).trim()
    return { base, codigo }
  }
  return { base: s, codigo: '' }
}
