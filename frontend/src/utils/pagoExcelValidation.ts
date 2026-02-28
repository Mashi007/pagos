/**
 * Validación para carga masiva de pagos desde Excel.
 * Columnas: Cédula, Fecha de pago, Monto, Documento (Nº documento), ID Préstamo (opcional).
 * Regla general: no se aceptan duplicados en documentos (ni en archivo ni en el sistema).
 * Nº documento: cualquier formato; documentos numéricos 10-25 dígitos sin problemas.
 */

import { validateExcelFile, validateExcelData, sanitizeFileName } from './excelValidation'

/** Rango de dígitos admitido para documentos numéricos (sin restricción de formato; solo referencia). */
export const DOCUMENTO_DIGITS_MIN = 10
export const DOCUMENTO_DIGITS_MAX = 25

export interface PagoExcelRow {
  _rowIndex: number
  _validation: Record<string, { isValid: boolean; message?: string }>
  _hasErrors: boolean
  cedula: string
  fecha_pago: string
  monto_pagado: number
  numero_documento: string
  prestamo_id: number | null
  conciliado: boolean  // SÃ­/No - ConciliaciÃ³n
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
  // DD-MM-YY: yy < 50 -> 2000+yy (ej. 26->2026), yy >= 50 -> 1900+yy. Validacion 2020-2030 filtra anos fuera de rango.
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

/**
 * Extrae la cédula para búsqueda cuando la celda tiene prefijo (ej. "AUL V23107415" → "V23107415").
 * Si Excel guardó la cédula como número (ej. 23107415), normaliza a "V23107415" para que el batch y la auto-asignación de crédito funcionen.
 * Solo para lookup/batch; no cambia el valor mostrado en la tabla.
 */
export function cedulaParaLookup(val: unknown): string {
  if (val == null || val === '') return ''
  const s = String(val).trim()
  if (!s) return ''
  const sinGuion = s.replace(/-/g, '').replace(/\s+/g, '')
  if (LOOKS_LIKE_CEDULA.test(sinGuion)) return sinGuion
  const match = s.match(/[VEJZ]\d{6,11}/i)
  if (match) return match[0].replace(/-/g, '')
  // Excel a veces guarda cédula como número y se pierde la letra (V/E/J); normalizar para batch y auto-asignación
  if (/^\d{8}$/.test(sinGuion)) return 'V' + sinGuion
  return s
}

/**
 * Devuelve la cédula a usar para buscar préstamos en esta fila.
 * Si la columna "Cédula" tiene número largo (ej. 740087406572495) y "Documento" tiene V27020005,
 * usa el documento como cédula para lookup (evita que esas filas queden sin Crédito asignado).
 */
export function cedulaLookupParaFila(cedula: string, numero_documento: string): string {
  const fromC = cedulaParaLookup(cedula)
  const fromD = cedulaParaLookup(numero_documento)
  if (fromC && LOOKS_LIKE_CEDULA.test(fromC.replace(/-/g, ''))) return fromC
  if (fromD && LOOKS_LIKE_CEDULA.test(fromD.replace(/-/g, ''))) return fromD
  return fromC || fromD
}

/** True si el valor parece un Nº de documento (10-25 dígitos u otros formatos BNC/ZELLE/…) y no una cédula V/E/J/Z. */
export function looksLikeDocumentNotCedula(val: unknown): boolean {
  if (val == null || val === '') return false
  const s = String(val).trim()
  if (!s) return false
  if (LOOKS_LIKE_CEDULA.test(s.replace(/-/g, ''))) return false
  if (/^\d{10,}$/.test(s)) return true
  if (/^(BNC|ZELLE|BINANCE|VE\/|BS\.|REF\.?)\s*\/?/i.test(s) || /^[A-Z0-9\/\.\s\-]{10,}$/i.test(s)) return true
  return false
}

// Quita caracteres invisibles/control que Excel o copiar-pegar pueden incluir (evita que el mismo documento se vea como distinto)
function limpiarDocumento(s: string): string {
  return s.replace(/[\u200B-\u200D\uFEFF\r\n\t]/g, '').trim()
}

/**
 * Convierte CUALQUIER valor a string para uso como número de documento.
 * Reconocimiento genérico: BNC/, BINANCE, VE/, ZELLE/, numérico, BS. BNC / REF., etc.
 * Única regla: NO DUPLICADO (archivo o BD). No se valida formato; solo se normaliza para comparación.
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
    // Excel "número como texto" puede llegar como number; conservar todos los dígitos (evitar pérdida de precisión)
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
  // Notación científica → dígitos (mismo número = misma clave)
  if (/^\d+\.?\d*[eE][+-]?\d+$/.test(s)) {
    try {
      const n = parseFloat(s)
      if (!Number.isNaN(n) && isFinite(n))
        s = Math.abs(n) >= 1e15 ? BigInt(Math.round(n)).toString() : String(Math.round(n))
    } catch {
      /* mantener s */
    }
  }
  // Colapsar espacios internos (alineado con backend: misma ref con distinto espaciado = duplicado)
  s = s.replace(/\s+/g, ' ').trim()
  return s
}

export function validatePagoField(
  field: string,
  value: string | number,
  _options?: { documentosExistentes?: Set<string>; documentosEnArchivo?: Set<string> }
): { isValid: boolean; message?: string } {
  const strVal = typeof value === 'number' ? String(value) : (value || '').toString().trim()

  switch (field) {
    case 'cedula':
      if (!strVal) return { isValid: false, message: 'Cédula requerida' }
      const c = strVal.replace(/[:$]/g, '')
      if (/^[VEJZ]\d{6,11}$/i.test(c)) return { isValid: true }
      // Si parece Nº documento (10+ dígitos, BNC/, ZELLE/, etc.) orientar al usuario; 10-25 dígitos aceptados sin problemas en columna documento
      if (/^\d{10,}$/.test(c) || /^(BNC|ZELLE|BINANCE|VE|BS\.)\s*\/?/i.test(c))
        return { isValid: false, message: 'Parece un Nº de documento. Use la columna Cédula para V/E/J/Z + dígitos y la columna Nº documento para la referencia.' }
      return { isValid: false, message: 'Formato E/V/J/Z + 6-11 dígitos' }

    case 'fecha_pago':
      if (!strVal) return { isValid: false, message: 'Fecha de pago requerida' }
      const fm = strVal.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
      if (!fm) return { isValid: false, message: 'Formato DD/MM/YYYY' }
      const dn = parseInt(fm[1], 10)
      const mn = parseInt(fm[2], 10)
      const yn = parseInt(fm[3], 10)
      if (dn < 1 || dn > 31) return { isValid: false, message: 'DÃ­a 1-31' }
      if (mn < 1 || mn > 12) return { isValid: false, message: 'Mes 1-12' }
      if (yn < 2020 || yn > 2030) return { isValid: false, message: 'AÃ±o 2020-2030' }
      const fechaPago = new Date(yn, mn - 1, dn)
      const hoy = new Date()
      hoy.setHours(23, 59, 59, 999)
      if (fechaPago > hoy) return { isValid: false, message: 'La fecha no puede ser futura' }
      return { isValid: true }

    case 'monto_pagado': {
      const n = parseFloat(strVal)
      if (Number.isNaN(n) || n <= 0) return { isValid: false, message: 'Monto > 0 requerido' }
      if (n > 1000000) return { isValid: false, message: 'Monto muy alto. Verifique' }
      return { isValid: true }
    }

    case 'numero_documento': {
      // Cualquier formato aceptado; 10-25 dígitos numéricos sin problemas. ÚNICA regla: no duplicado.
      const docNorm = (strVal === 'NaN' || strVal === 'nan' || strVal === 'undefined') ? '' : (normalizarNumeroDocumento(value) || strVal).trim() || ''
      if (!docNorm) return { isValid: true } // Vacío permitido; no cuenta como duplicado
      if (_options?.documentosExistentes?.has(docNorm)) return { isValid: false, message: 'Este documento ya existe en el sistema. Regla general: no se aceptan duplicados en documentos.' }
      if (_options?.documentosEnArchivo?.has(docNorm)) return { isValid: false, message: 'Documento duplicado en este archivo. Regla general: no se aceptan duplicados en documentos.' }
      return { isValid: true }
    }

    case 'prestamo_id':
      return { isValid: true }

    case 'conciliado':
      return { isValid: true }

    default:
      return { isValid: true }
  }
}

export { validateExcelFile, validateExcelData, sanitizeFileName }

