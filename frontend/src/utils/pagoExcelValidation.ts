/**
 * Validación para carga masiva de pagos desde Excel.
 * Columnas: Cédula, Fecha de pago, Monto, Documento (Nº documento), ID Préstamo (opcional).
 * La coincidencia se realiza por cédula. Sin columna Nombre.
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
  conciliado: boolean  // Sí/No - Conciliación
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
      return /^[VEJZ]\d{6,11}$/i.test(c) ? { isValid: true } : { isValid: false, message: 'Formato E/V/J/Z + 6-11 dígitos' }

    case 'fecha_pago':
      if (!strVal) return { isValid: false, message: 'Fecha de pago requerida' }
      const fm = strVal.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
      if (!fm) return { isValid: false, message: 'Formato DD/MM/YYYY' }
      const dn = parseInt(fm[1], 10)
      const mn = parseInt(fm[2], 10)
      const yn = parseInt(fm[3], 10)
      if (dn < 1 || dn > 31) return { isValid: false, message: 'Día 1-31' }
      if (mn < 1 || mn > 12) return { isValid: false, message: 'Mes 1-12' }
      if (yn < 2020 || yn > 2030) return { isValid: false, message: 'Año 2020-2030' }
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
      if (!strVal) return { isValid: false, message: 'Nº documento requerido' }
      if (_options?.documentosEnArchivo?.has(strVal)) return { isValid: false, message: 'Documento duplicado en archivo' }
      if (_options?.documentosExistentes?.has(strVal)) return { isValid: false, message: 'Documento ya existe en BD' }
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
