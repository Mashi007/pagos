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

/**
 * Normaliza el valor de la columna Documento al subir el Excel.
 * Acondiciona "comillas" automáticamente: documentos con formato solo números
 * (ej. 740087464410397) se convierten a texto completo para evitar notación científica.
 * - Si viene como número (Excel sin comillas): se pasa a string de dígitos completos.
 * - Si viene como string en notación científica (7.4E+14): se expande a dígitos.
 * - Si viene como string solo dígitos: se devuelve tal cual (respeta ceros a la izquierda).
 */
export function normalizarNumeroDocumento(val: unknown): string {
  if (val == null || val === '') return ''
  if (typeof val === 'number') {
    if (Number.isNaN(val)) return ''
    // Números largos: siempre a string de dígitos (equivalente a "comillas" en Excel)
    if (Math.abs(val) >= 1e15) {
      try { return BigInt(Math.round(val)).toString() } catch { return val.toFixed(0) }
    }
    return Math.round(val).toString()
  }
  const s = String(val).trim().replace(/\s+/g, '')
  if (!s || s === 'NaN' || s === 'nan' || s === 'undefined') return ''
  // Solo dígitos (formato documento): devolver tal cual
  if (/^\d+$/.test(s)) return s
  // Notación científica: expandir a dígitos completos
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

    case 'numero_documento':
      // Aceptar CUALQUIER formato; normalizar para reconocer números largos y notación científica (evita "no reconoce documento").
      const docNorm = (strVal === 'NaN' || strVal === 'nan' || strVal === 'undefined') ? '' : (normalizarNumeroDocumento(value) || strVal).trim() || ''
      if (docNorm && _options?.documentosExistentes?.has(docNorm)) return { isValid: false, message: 'Documento ya existe en BD' }
      return { isValid: true }

    case 'prestamo_id':
      return { isValid: true }

    case 'conciliado':
      return { isValid: true }

    default:
      return { isValid: true }
  }
}

export { validateExcelFile, validateExcelData, sanitizeFileName }

