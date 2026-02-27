/**
 * ValidaciÃ³n para carga masiva de pagos desde Excel.
 * Columnas: CÃ©dula, Fecha de pago, Monto, Documento (NÂº documento), ID PrÃ©stamo (opcional).
 * La coincidencia se realiza por cÃ©dula. Sin columna Nombre.
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

/**
 * Normaliza el valor de la columna Documento para comparación y guardado.
 * ÚNICA REGLA DE NEGOCIO: no duplicados (el mismo valor no puede repetirse en el archivo ni en BD).
 * Se acepta CUALQUIER formato: números (15–16 dígitos), notación científica, zelle/XXX, BS./VZLA.REF..., B RECIBO/..., o cualquier texto (trim solo en extremos).
 */
export function normalizarNumeroDocumento(val: unknown): string {
  if (val == null || val === '') return ''
  // Celdas Excel con richText u otro objeto: extraer texto para no guardar "[object Object]"
  if (typeof val === 'object' && val !== null) {
    const rt = (val as { richText?: Array<{ text?: string }> }).richText
    if (Array.isArray(rt)) {
      let out = rt.map((x) => x?.text ?? '').join('').trim() || ''
      if (out.startsWith("'")) out = out.slice(1).trim()
      return out
    }
    const t = (val as { text?: string }).text
    if (t != null) {
      let out = String(t).trim()
      if (out.startsWith("'")) out = out.slice(1).trim()
      return out
    }
    return ''
  }
  if (typeof val === 'number') {
    if (Number.isNaN(val)) return ''
    // Números largos (12+ dígitos, incl. 16 dígitos tipo 3740087403067198): string completo sin notación científica
    if (Math.abs(val) >= 1e11) {
      try { return Math.abs(val) >= 1e15 ? BigInt(Math.round(val)).toString() : String(Math.round(val)) } catch { return val.toFixed(0) }
    }
    return Math.round(val).toString()
  }
  let s = String(val).trim()
  // Excel a veces guarda "número como texto" o texto con apóstrofo inicial; quitar solo el prefijo '
  if (s.startsWith("'")) s = s.slice(1).trim()
  if (!s || s === 'NaN' || s === 'nan' || s === 'undefined') return ''
  // Aceptar fielmente: solo dígitos (15 o 16 dígitos), notación científica, zelle/..., BS./VZLA.REF..., B RECIBO/..., etc.
  if (/^\d+$/.test(s)) return s
  if (/^\d+\.?\d*[eE][+-]?\d+$/.test(s)) {
    try {
      const n = parseFloat(s)
      if (Number.isNaN(n)) return s
      if (Math.abs(n) >= 1e15) {
        try { return BigInt(Math.round(n)).toString() } catch { return n.toFixed(0) }
      }
      return Math.round(n).toString()
    } catch {
      return s
    }
  }
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
      if (!strVal) return { isValid: false, message: 'CÃ©dula requerida' }
      const c = strVal.replace(/[:$]/g, '')
      return /^[VEJZ]\d{6,11}$/i.test(c) ? { isValid: true } : { isValid: false, message: 'Formato E/V/J/Z + 6-11 dÃ­gitos' }

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
      // ÚNICA REGLA: no duplicados (mismo valor no puede repetirse en archivo ni en BD). Cualquier formato aceptado.
      const docNorm = (strVal === 'NaN' || strVal === 'nan' || strVal === 'undefined') ? '' : (normalizarNumeroDocumento(value) || strVal).trim() || ''
      if (_options?.documentosExistentes?.has(docNorm)) return { isValid: false, message: 'Documento ya existe en BD. No se permiten duplicados.' }
      if (_options?.documentosEnArchivo?.has(docNorm)) return { isValid: false, message: 'Documento duplicado en este archivo. No se permiten duplicados.' }
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

