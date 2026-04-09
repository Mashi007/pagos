/**
 * Montos en Bs. (Venezuela): miles con punto, decimales con coma.
 * Evita tratar la coma solo como "decimal" cuando ya hay puntos de miles.
 */

export function parseMontoLatam(texto: string): number {
  const s = texto.trim().replace(/[\s\u00A0\u202F]/g, '')
  if (!s) return 0
  if (s === '.' || s === ',') return 0

  const lastComma = s.lastIndexOf(',')
  const lastDot = s.lastIndexOf('.')

  let normalized: string

  if (lastComma >= 0 && lastDot >= 0) {
    if (lastComma > lastDot) {
      normalized = s.replace(/\./g, '').replace(',', '.')
    } else {
      normalized = s.replace(/,/g, '')
    }
  } else if (lastComma >= 0) {
    const after = s.slice(lastComma + 1)
    if (after.length <= 2 && /^\d+$/.test(after)) {
      normalized = s.replace(',', '.')
    } else {
      normalized = s.replace(/,/g, '')
    }
  } else if (lastDot >= 0) {
    const parts = s.split('.')
    if (parts.length === 2) {
      const frac = parts[1]
      if (frac.length <= 2 && /^\d+$/.test(frac)) {
        normalized = s
      } else {
        normalized = parts[0] + parts[1]
      }
    } else if (parts.length > 2) {
      const last = parts[parts.length - 1]
      if (last.length <= 2 && /^\d+$/.test(last)) {
        normalized = parts.slice(0, -1).join('') + '.' + last
      } else {
        normalized = parts.join('')
      }
    } else {
      normalized = s
    }
  } else {
    normalized = s
  }

  const n = parseFloat(normalized)
  return Number.isFinite(n) ? n : 0
}

/** Formato visual Bs.: 1.234.567,89 (siempre 2 decimales). */
export function formatMontoBsVe(n: number): string {
  if (!Number.isFinite(n)) return ''
  const rounded = Math.round(n * 100) / 100
  const fixed = rounded.toFixed(2)
  const [intPart, decPart] = fixed.split('.')
  const neg = intPart.startsWith('-')
  const absInt = neg ? intPart.slice(1) : intPart
  const grouped = absInt.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return (neg ? '-' : '') + `${grouped},${decPart}`
}

/** Solo digitos, punto y coma; una sola coma (decimal Bs.). */
export function sanitizeMontoInputLatam(raw: string): string {
  let v = raw.replace(/[^\d.,]/g, '')
  const firstComma = v.indexOf(',')
  const lastComma = v.lastIndexOf(',')
  if (firstComma !== lastComma) {
    v = v.slice(0, lastComma).replace(/,/g, '') + v.slice(lastComma)
  }
  return v
}
