/**
 * Sufijo admin (carga masiva / revisión manual): _ + A|P + 4 dígitos
 * (mismo archivo vs otro préstamo en BD). Secuencial, no aleatorio.
 */

import {
  NUMERO_DOCUMENTO_MAX_LEN,
  normalizarNumeroDocumento,
} from './pagoExcelValidation'

export const SUFIJO_VISTO_ARCHIVO_RE = /_[AP]\d{4}$/i

export const TOKEN_SUFIJO_VISTO_ARCHIVO_RE = /_([AP]\d{4})$/i

/** Tokens A#### / P#### ya presentes al final de numero_documento. */
export function collectTokensSufijoVistoArchivoDesdeFilas(
  rows: { numero_documento?: string | null }[]
): Set<string> {
  const usados = new Set<string>()
  for (const r of rows) {
    const m = String(r.numero_documento ?? '').match(
      TOKEN_SUFIJO_VISTO_ARCHIVO_RE
    )
    if (m) usados.add(m[1].toUpperCase())
  }
  return usados
}

/** Genera token A#### o P#### únicos dentro de `usados` (secuencial). */
export function allocarTokenSufijoVistoArchivo(
  letter: 'A' | 'P',
  usados: Set<string>
): string {
  for (let n = 0; n < 10000; n++) {
    const tok = `${letter}${String(n).padStart(4, '0')}`
    if (!usados.has(tok)) {
      usados.add(tok)
      return tok
    }
  }
  const tok = `${letter}${String(Date.now() % 10000).padStart(4, '0')}`
  if (!usados.has(tok)) {
    usados.add(tok)
    return tok
  }
  return `${letter}9999`
}

/**
 * Añade _A#### o _P#### al comprobante si aún no tiene sufijo admin.
 * Respeta NUMERO_DOCUMENTO_MAX_LEN truncando la base si hace falta.
 */
export function aplicarSufijoVistoADocumento(
  numeroDocumentoRaw: string | null | undefined,
  letter: 'A' | 'P',
  usados: Set<string>
): string {
  const raw = String(numeroDocumentoRaw ?? '').trim()
  if (SUFIJO_VISTO_ARCHIVO_RE.test(raw)) return raw
  const token = allocarTokenSufijoVistoArchivo(letter, usados)
  const maxBase = NUMERO_DOCUMENTO_MAX_LEN - 1 - token.length
  let base = raw
  if (base.length > maxBase) base = base.slice(0, Math.max(0, maxBase))
  const joined = `${base}_${token}`
  return normalizarNumeroDocumento(joined) || joined
}

/** Heurística: mensaje de error 409 / detalle indica duplicado ligado a otro préstamo → sufijo P. */
export function letterSufijoVistoDesdeMensajeDuplicado(
  msg: string | undefined
): 'A' | 'P' {
  const m = (msg || '').toLowerCase()
  if (
    m.includes('otro prestamo') ||
    m.includes('otro préstamo') ||
    m.includes('otro credito') ||
    m.includes('otro crédito')
  ) {
    return 'P'
  }
  return 'A'
}
