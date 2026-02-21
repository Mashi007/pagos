/**
 * Validación para carga masiva de préstamos desde Excel.
 * Columnas: Cédula, Total financiamiento, Modalidad pago, Fecha requerimiento, Producto,
 * Concesionario, Analista, Modelo vehículo, Número cuotas, Cuota período, Tasa interés, Observaciones.
 */

import { validateExcelFile, validateExcelData, sanitizeFileName } from './excelValidation'

export interface PrestamoExcelRow {
  _rowIndex: number
  _validation: Record<string, { isValid: boolean; message?: string }>
  _hasErrors: boolean
  cedula: string
  total_financiamiento: number
  modalidad_pago: string
  fecha_requerimiento: string
  producto: string
  concesionario: string
  analista: string
  modelo_vehiculo: string
  numero_cuotas: number
  cuota_periodo: number
  tasa_interes: number
  observaciones: string
}

const MODALIDADES = ['MENSUAL', 'QUINCENAL', 'SEMANAL']

export function convertirFechaExcelPrestamo(val: unknown): string {
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

export function convertirFechaParaBackendPrestamo(f: string): string {
  if (!f?.trim()) return ''
  const m = f.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  return m ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` : f.trim()
}

export function validatePrestamoField(
  field: string,
  value: string | number,
  _options?: { analistas?: string[]; concesionarios?: string[] }
): { isValid: boolean; message?: string } {
  const strVal = typeof value === 'number' ? String(value) : (value || '').toString().trim()

  switch (field) {
    case 'cedula':
      if (!strVal) return { isValid: false, message: 'Cédula requerida' }
      const c = strVal.replace(/[:$]/g, '')
      return /^[VEJZ]\d{6,11}$/i.test(c) ? { isValid: true } : { isValid: false, message: 'Formato E/V/J/Z + 6-11 dígitos' }

    case 'total_financiamiento': {
      const n = parseFloat(strVal)
      if (Number.isNaN(n) || n <= 0) return { isValid: false, message: 'Monto > 0 requerido' }
      return { isValid: true }
    }

    case 'modalidad_pago':
      if (!strVal) return { isValid: false, message: 'Modalidad requerida' }
      const mod = strVal.toUpperCase()
      return MODALIDADES.includes(mod) ? { isValid: true } : { isValid: false, message: `Uno de: ${MODALIDADES.join(', ')}` }

    case 'fecha_requerimiento':
      if (!strVal) return { isValid: false, message: 'Fecha requerida' }
      const fm = strVal.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
      if (!fm) return { isValid: false, message: 'Formato DD/MM/YYYY' }
      const dn = parseInt(fm[1], 10)
      const mn = parseInt(fm[2], 10)
      const yn = parseInt(fm[3], 10)
      if (dn < 1 || dn > 31) return { isValid: false, message: 'Día 1-31' }
      if (mn < 1 || mn > 12) return { isValid: false, message: 'Mes 1-12' }
      if (yn < 2020 || yn > 2030) return { isValid: false, message: 'Año 2020-2030' }
      return { isValid: true }

    case 'producto':
      return strVal.length >= 1 ? { isValid: true } : { isValid: false, message: 'Producto requerido' }

    case 'analista':
      return strVal.length >= 1 ? { isValid: true } : { isValid: false, message: 'Analista requerido' }

    case 'numero_cuotas': {
      const nc = parseInt(strVal, 10)
      if (Number.isNaN(nc) || nc < 1 || nc > 12) return { isValid: false, message: 'Entre 1 y 12' }
      return { isValid: true }
    }

    case 'cuota_periodo':
      if (!strVal) return { isValid: true }
      const cp = parseFloat(strVal)
      return Number.isNaN(cp) || cp < 0 ? { isValid: false, message: 'Número >= 0' } : { isValid: true }

    case 'tasa_interes':
      if (!strVal) return { isValid: true }
      const ti = parseFloat(strVal)
      return Number.isNaN(ti) || ti < 0 ? { isValid: false, message: 'Número >= 0' } : { isValid: true }

    case 'concesionario':
    case 'modelo_vehiculo':
    case 'observaciones':
      return { isValid: true }

    default:
      return { isValid: true }
  }
}

export { validateExcelFile, validateExcelData, sanitizeFileName }
