/**
 * Validación carga masiva de pagos (Excel).
 * ÚNICA REGLA: no se acepta documento duplicado (ni en el archivo ni en el sistema).
 */

import { validateExcelFile, validateExcelData, sanitizeFileName } from './excelValidation'

export interface PagoExcelRow {
  _rowIndex: number
  _validation: Record<string, { isValid: boolean; message?: string }>
  _hasErrors: boolean
  cedula: string
  fecha_pago: string
  monto_pagado: number
  numero_documento: string
  prestamo_id: number | null
  conciliado: boolean
}

export function convertirFechaExcelPago(val: unknown): string {
  if (val == null || val === '') return ''
  if (val instanceof Date) {
    if (Number.isNaN(val.getTime())) return ''
    return `${String(val.getDate()).padStart(2, '0')}/${String(val.getMonth() + 1).padStart(2, '0')}/${val.getFullYear()}`
  }
  const s = String(val).trim()
  if (!s) return ''
  if (/^\d{4,}$/.test(s)) {
    try {
      const d = new Date(1900, 0, 1)
      d.setDate(d.getDate() + parseInt(s, 10) - 2)
      return Number.isNaN(d.getTime())
        ? s
        : `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
    } catch {
      return s
    }
  }
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(s)) return s
  if (/^\d{2}-\d{2}-\d{2}$/.test(s)) {
    const [d, m, yy] = s.split('-')
    const y = parseInt(yy, 10) < 50 ? 2000 + parseInt(yy, 10) : 1900 + parseInt(yy, 10)
    return `${d}/${m}/${y}`
  }
  if (/^\d{2}-\d{2}-\d{4}$/.test(s)) {
    const [d, m, y] = s.split('-')
    return `${d}/${m}/${y}`
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const [y, m, d] = s.split('-')
    return `${d}/${m}/${y}`
  }
  const p = new Date(s)
  return !Number.isNaN(p.getTime())
    ? `${String(p.getDate()).padStart(2, '0')}/${String(p.getMonth() + 1).padStart(2, '0')}/${p.getFullYear()}`
    : s
}

export function convertirFechaParaBackendPago(f: string): string {
  if (!f?.trim()) return ''
  const m = f.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  return m ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` : f.trim()
}

const LOOKS_LIKE_CEDULA = /^[VEJZ]\d{6,11}$/i

export function cedulaParaLookup(val: unknown): string {
  if (val == null || val === '') return ''
  const s = String(val).trim()
  if (!s) return ''
  const sinGuion = s.replace(/-/g, '').replace(/\s+/g, '')
  if (LOOKS_LIKE_CEDULA.test(sinGuion)) return sinGuion
  const match = s.match(/[VEJZ]\d{6,11}/i)
  if (match) return match[0].replace(/-/g, '')
  if (/^\d{8}$/.test(sinGuion)) return 'V' + sinGuion
  return s
}

export function cedulaLookupParaFila(cedula: string, numero_documento: string): string {
  const fromC = cedulaParaLookup(cedula)
  const fromD = cedulaParaLookup(numero_documento)
  if (fromC && LOOKS_LIKE_CEDULA.test(fromC.replace(/-/g, ''))) return fromC
  if (fromD && LOOKS_LIKE_CEDULA.test(fromD.replace(/-/g, ''))) return fromD
  return fromC || fromD
}

/** True si el valor parece Nº documento (ej. 10+ dígitos, BNC/ZELLE) y no cédula V/E/J/Z. */
export function looksLikeDocumentNotCedula(val: unknown): boolean {
  if (val == null || val === '') return false
  const s = String(val).trim()
  if (!s) return false
  if (LOOKS_LIKE_CEDULA.test(s.replace(/-/g, ''))) return false
  if (/^\d{10,}$/.test(s)) return true
  if (/^(BNC|ZELLE|BINANCE|VE\/|BS\.|REF\.?)\s*\/?/i.test(s) || /^[A-Z0-9\/\.\s\-]{10,}$/i.test(s)) return true
  return false
}

function limpiarDocumento(s: string): string {
  return s.replace(/[\u200B-\u200D\uFEFF\r\n\t]/g, '').trim()
}

/**
 * Normaliza el valor a string para usar como clave de documento.
 * Acepta CUALQUIER formato: numérico, con € $ Bs, BNC/, ZELLE/, etc. No se quitan símbolos de moneda.
 * Misma clave = mismo documento (para detectar duplicados). Única regla: no duplicados.
 */
export function normalizarNumeroDocumento(val: unknown): string {
  if (val == null || val === '') return ''
  let s: string
  if (typeof val === 'object' && val !== null) {
    const rt = (val as { richText?: Array<{ text?: string }> }).richText
    if (Array.isArray(rt)) s = rt.map((x) => x?.text ?? '').join('')
    else if ((val as { text?: string }).text != null) s = String((val as { text?: string }).text)
    else return ''
  } else if (typeof val === 'number') {
    if (Number.isNaN(val)) return ''
    if (Math.abs(val) >= 1e12) {
      try {
        s = BigInt(Math.round(val)).toString()
      } catch {
        s = val.toFixed(0)
      }
    } else if (Math.abs(val) >= 1e11) {
      s = String(Math.round(val))
    } else {
      s = Math.round(val).toString()
    }
  } else {
    s = String(val)
  }
  s = s.trim()
  if (s.startsWith("'")) s = s.slice(1).trim()
  s = limpiarDocumento(s)
  if (!s || /^(nan|none|undefined|na|n\/a)$/i.test(s)) return ''
  if (/^\d+\.?\d*[eE][+-]?\d+$/.test(s)) {
    try {
      const n = parseFloat(s)
      if (!Number.isNaN(n) && isFinite(n))
        s = Math.abs(n) >= 1e15 ? BigInt(Math.round(n)).toString() : String(Math.round(n))
    } catch {
      /* mantener s */
    }
  }
  s = s.replace(/\s+/g, ' ').trim()
  return s
}

/** Única validación en carga masiva: documento duplicado = inválido. */
export function validatePagoField(
  field: string,
  value: string | number,
  options?: { documentosExistentes?: Set<string>; documentosEnArchivo?: Set<string> }
): { isValid: boolean; message?: string } {
  if (field !== 'numero_documento') return { isValid: true }

  const docNorm = (value === 'NaN' || value === 'nan' || value === 'undefined')
    ? ''
    : (normalizarNumeroDocumento(value) || String(value)).trim() || ''
  if (!docNorm) return { isValid: true }

  if (options?.documentosExistentes?.has(docNorm))
    return { isValid: false, message: 'Documento duplicado. No se aceptan duplicados.' }
  if (options?.documentosEnArchivo?.has(docNorm))
    return { isValid: false, message: 'Documento duplicado en este archivo. No se aceptan duplicados.' }
  return { isValid: true }
}

export { validateExcelFile, validateExcelData, sanitizeFileName }
