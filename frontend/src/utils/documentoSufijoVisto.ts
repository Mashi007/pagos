/**
 * Sufijo admin (carga masiva / revisión manual): _ + A|P + 4 dígitos
 * (mismo archivo vs otro préstamo en BD). Se elige un código libre: primero
 * al azar (varios intentos), luego barrido secuencial 0000-9999 si hace falta.
 */

import {
  NUMERO_DOCUMENTO_MAX_LEN,
  normalizarNumeroDocumento,
} from './pagoExcelValidation'

export const SUFIJO_VISTO_ARCHIVO_RE = /_[AP]\d{4}$/i

export const TOKEN_SUFIJO_VISTO_ARCHIVO_RE = /_([AP]\d{4})$/i

export type AplicarSufijoVistoOptions = {
  /**
   * Si true (p. ej. revisión manual «Añadir sufijos» otra vez): quita un
   * _A####/_P#### final, lo marca como usado y asigna uno nuevo. Sin esto, un
   * documento que ya tiene sufijo no cambia y el duplicado en BD sigue igual.
   */
  reemplazarSufijoAdmin?: boolean
}

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

function randomCuatroDigitos(): string {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const buf = new Uint32Array(1)
    crypto.getRandomValues(buf)
    return String(buf[0] % 10000).padStart(4, '0')
  }
  return String(Math.floor(Math.random() * 10000)).padStart(4, '0')
}

/** Genera token A#### o P#### único dentro de `usados` (aleatorio, luego secuencial). */
export function allocarTokenSufijoVistoArchivo(
  letter: 'A' | 'P',
  usados: Set<string>
): string {
  const maxRandomAttempts = 64
  for (let i = 0; i < maxRandomAttempts; i++) {
    const tok = `${letter}${randomCuatroDigitos()}`
    if (!usados.has(tok)) {
      usados.add(tok)
      return tok
    }
  }
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
 * Con `reemplazarSufijoAdmin`, sustituye un sufijo admin ya presente.
 * Respeta NUMERO_DOCUMENTO_MAX_LEN truncando la base si hace falta.
 */
export function aplicarSufijoVistoADocumento(
  numeroDocumentoRaw: string | null | undefined,
  letter: 'A' | 'P',
  usados: Set<string>,
  options?: AplicarSufijoVistoOptions
): string {
  const raw = String(numeroDocumentoRaw ?? '').trim()
  const reemplazar = !!options?.reemplazarSufijoAdmin

  if (!reemplazar && SUFIJO_VISTO_ARCHIVO_RE.test(raw)) return raw

  let base = raw
  if (reemplazar) {
    const m = base.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
    if (m) {
      usados.add(m[1].toUpperCase())
      base = base.replace(SUFIJO_VISTO_ARCHIVO_RE, '').trim()
    }
  }

  const token = allocarTokenSufijoVistoArchivo(letter, usados)
  const maxBase = NUMERO_DOCUMENTO_MAX_LEN - 1 - token.length
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
