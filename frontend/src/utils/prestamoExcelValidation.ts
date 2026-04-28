/**





 * Validación para carga masiva de préstamos desde Excel.





 * Layout por posición (sin fila de encabezados reconocible): Producto en col. E (índice 4),
 * fecha_aprobacion en col. M (índice 12), etc.
 *
 * Si la fila 1 tiene encabezados (cédula, total_financiar, fecha_aprobacion, producto, ...),
 * se detectan columnas por nombre y admite la plantilla con fecha_aprobacion antes de producto.





 */

import {
  validateExcelFile,
  validateExcelData,
  sanitizeFileName,
} from './excelValidation'

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

  fecha_aprobacion: string
}

export function normalizarEncabezadoPrestamoExcel(raw: unknown): string {
  return String(raw ?? '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
}

/**
 * ExcelJS puede dejar huecos en el array de celdas; sin densificar, cells[0] falla aunque la columna A exista.
 */
export function densificarFilaExcel(
  row: unknown[] | null | undefined
): unknown[] {
  if (!row) return []
  let maxIdx = -1
  for (const k of Object.keys(row)) {
    const i = Number(k)
    if (Number.isInteger(i) && i >= 0 && i > maxIdx) maxIdx = i
  }
  if (maxIdx < 0) {
    maxIdx = Math.max(0, row.length - 1)
  }
  const out: unknown[] = []
  for (let i = 0; i <= maxIdx; i++) {
    out[i] = row[i] ?? ''
  }
  return out
}

/**
 * Busca en las primeras filas una que tenga encabezados de plantilla de préstamo.
 * dataStartIndex: índice en jsonData de la primera fila de datos (después del encabezado).
 */
export function resolverEncabezadoYMapaPrestamo(jsonData: unknown[][]): {
  dataStartIndex: number
  colMap: Record<string, number> | null
} {
  const maxScan = Math.min(6, jsonData.length)
  for (let r = 0; r < maxScan; r++) {
    const dense = densificarFilaExcel(jsonData[r] as unknown[])
    const m = mapaColumnasPrestamoDesdeFilaEncabezado(dense)
    if (m) {
      return { dataStartIndex: r + 1, colMap: m }
    }
  }
  return { dataStartIndex: 1, colMap: null }
}

/**
 * Si la fila parece encabezados de préstamo, devuelve índice por campo.
 * Cubre plantillas con fecha_aprobacion en E y producto en F (10+ columnas).
 */
export function mapaColumnasPrestamoDesdeFilaEncabezado(
  headerRow: unknown[]
): Record<string, number> | null {
  const dense = densificarFilaExcel(headerRow)
  if (!dense.length) return null
  const cells = dense.map(c => normalizarEncabezadoPrestamoExcel(c))

  const findFirst = (pred: (norm: string) => boolean): number | undefined => {
    const i = cells.findIndex(pred)
    return i >= 0 ? i : undefined
  }

  const cedIdx = findFirst(
    n =>
      n.includes('cedula') ||
      n === 'ci' ||
      n === 'id_cliente' ||
      n === 'documento'
  )
  if (cedIdx === undefined) return null

  const m: Record<string, number> = {}
  m.cedula = cedIdx

  const totalIdx = findFirst(
    n =>
      (n.includes('total') && (n.includes('financ') || n.includes('finan'))) ||
      n === 'monto'
  )
  if (totalIdx !== undefined) m.total_financiamiento = totalIdx

  const modIdx = findFirst(n => n.includes('modalidad'))
  if (modIdx !== undefined) m.modalidad_pago = modIdx

  const reqIdx = findFirst(
    n => n.includes('requerim') || n === 'fecha_req' || n.endsWith('_req')
  )
  if (reqIdx !== undefined) m.fecha_requerimiento = reqIdx

  const aprobIdx = findFirst(
    n =>
      (n.includes('fecha') && n.includes('aprob')) ||
      n.includes('desembols') ||
      n === 'fecha_aprob'
  )
  if (aprobIdx !== undefined) m.fecha_aprobacion = aprobIdx

  const prodIdx = findFirst(n => n === 'producto')
  if (prodIdx !== undefined) m.producto = prodIdx

  const concIdx = findFirst(n => n.includes('concesion'))
  if (concIdx !== undefined) m.concesionario = concIdx

  const analIdx = findFirst(n => n.includes('analista'))
  if (analIdx !== undefined) m.analista = analIdx

  let modVehIdx = findFirst(
    n =>
      (n.includes('modelo') && (n.includes('veh') || n.includes('vehic'))) ||
      n === 'modelo_vehic'
  )
  if (modVehIdx === undefined)
    modVehIdx = findFirst(n => n === 'modelo' && !n.includes('veh'))
  if (modVehIdx !== undefined) m.modelo_vehiculo = modVehIdx

  let ncuIdx = findFirst(
    n =>
      (n.includes('numero') || n.includes('nro')) &&
      n.includes('cuota') &&
      !n.includes('periodo')
  )
  if (ncuIdx === undefined)
    ncuIdx = findFirst(
      n =>
        n === 'cuotas' ||
        (n.includes('cuota') && !n.includes('periodo') && !n.includes('monto'))
    )
  if (ncuIdx !== undefined) m.numero_cuotas = ncuIdx

  const cpIdx = findFirst(
    n => n.includes('cuota') && n.includes('period') && !n.includes('numero')
  )
  if (cpIdx !== undefined) m.cuota_periodo = cpIdx

  const tasaIdx = findFirst(
    n => n.includes('tasa') || n === 'interes' || n.includes('interes')
  )
  if (tasaIdx !== undefined) m.tasa_interes = tasaIdx

  const obsIdx = findFirst(n => n.includes('observ'))
  if (obsIdx !== undefined) m.observaciones = obsIdx

  const required = [
    'cedula',
    'total_financiamiento',
    'modalidad_pago',
    'fecha_aprobacion',
    'producto',
    'analista',
    'numero_cuotas',
  ] as const
  if (required.some(k => m[k] === undefined)) return null

  // Misma columna para requerimiento y aprobación (p. ej. encabezado ambiguo): el mapa es inválido;
  // forzar layout legacy + detección evita duplicar una fecha en ambos campos.
  if (m.fecha_requerimiento === m.fecha_aprobacion) return null

  return m
}

/** Monto tipo 1.344,00 o 1344 (Excel numérico). */
export function parseMontoPrestamoExcel(val: unknown): number {
  if (val == null || val === '') return 0
  if (typeof val === 'number' && !Number.isNaN(val)) return val
  let s = String(val)
    .trim()
    .replace(/\s/g, '')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
  if (!s) return 0
  // Miles con punto y decimal con coma (VE / ES)
  if (/^\d{1,3}(\.\d{3})*(,\d+)?$/.test(s)) {
    s = s.replace(/\./g, '').replace(',', '.')
  } else if (/^\d{1,3}(,\d{3})*(\.\d+)?$/.test(s)) {
    s = s.replace(/,/g, '')
  }
  const n = parseFloat(s)
  return Number.isNaN(n) ? 0 : n
}

const MODALIDADES = ['MENSUAL', 'QUINCENAL', 'SEMANAL']

export function convertirFechaExcelPrestamo(val: unknown): string {
  if (val == null || val === '') return ''

  if (val instanceof Date) {
    if (Number.isNaN(val.getTime())) return ''

    return `${String(val.getDate()).padStart(2, '0')}/${String(val.getMonth() + 1).padStart(2, '0')}/${val.getFullYear()}`
  }

  // Los seriales Excel (p. ej. 45991 → 30/11/2025) se normalizan en readExcelToJSON solo si numFmt es de fecha.
  // Aquí no interpretamos enteros/cadenas solo-dígitos como fecha: evita confundir Nº operación 45991 con una fecha.

  const s = String(val).trim()

  if (!s) return ''

  // Plantilla: 4-12-2026 o 04-12-2026 (día-mes-año con guión)
  const dmY = s.match(/^(\d{1,2})-(\d{1,2})-(\d{4})$/)
  if (dmY) {
    const d = parseInt(dmY[1], 10)
    const mo = parseInt(dmY[2], 10)
    const y = parseInt(dmY[3], 10)
    if (mo >= 1 && mo <= 12 && d >= 1 && d <= 31 && y >= 2000 && y <= 2100) {
      return `${String(d).padStart(2, '0')}/${String(mo).padStart(2, '0')}/${y}`
    }
  }

  if (/^\d{2}\/\d{2}\/\d{4}$/.test(s)) return s

  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const [y, m, d] = s.split('-')

    return `${d}/${m}/${y}`
  }

  // Solo dígitos (p. ej. "45991"): no usar new Date(s) ni serial; deja que la validación marque error si no es DD/MM/AAAA.
  if (/^\d+$/.test(s)) return s

  const p = new Date(s)

  return !Number.isNaN(p.getTime())
    ? `${String(p.getDate()).padStart(2, '0')}/${String(p.getMonth() + 1).padStart(2, '0')}/${p.getFullYear()}`
    : s
}

export function convertirFechaParaBackendPrestamo(f: string): string {
  if (!f?.trim()) return ''

  const m = f.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)

  return m
    ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`
    : f.trim()
}

export function validatePrestamoField(
  field: string,

  value: string | number,

  _options?: { analistas?: string[]; concesionarios?: string[] }
): { isValid: boolean; message?: string } {
  const strVal =
    typeof value === 'number' ? String(value) : (value || '').toString().trim()

  switch (field) {
    case 'cedula':
      if (!strVal) return { isValid: false, message: 'Cédula requerida' }

      const c = strVal.replace(/[:$]/g, '')

      return /^[VEJZ]\d{6,11}$/i.test(c)
        ? { isValid: true }
        : { isValid: false, message: 'Formato E/V/J/Z + 6-11 dígitos' }

    case 'total_financiamiento': {
      const n = parseFloat(strVal)

      if (Number.isNaN(n) || n <= 0)
        return { isValid: false, message: 'Monto > 0 requerido' }

      return { isValid: true }
    }

    case 'modalidad_pago':
      if (!strVal) return { isValid: false, message: 'Modalidad requerida' }

      const mod = strVal.toUpperCase()

      return MODALIDADES.includes(mod)
        ? { isValid: true }
        : { isValid: false, message: `Uno de: ${MODALIDADES.join(', ')}` }

    case 'fecha_requerimiento':
    case 'fecha_aprobacion':
      if (!strVal) return { isValid: false, message: 'Fecha requerida' }

      const fm = strVal.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)

      if (!fm) return { isValid: false, message: 'Formato DD/MM/YYYY' }

      const dn = parseInt(fm[1], 10)

      const mn = parseInt(fm[2], 10)

      const yn = parseInt(fm[3], 10)

      if (dn < 1 || dn > 31) return { isValid: false, message: 'Día 1-31' }

      if (mn < 1 || mn > 12) return { isValid: false, message: 'Mes 1-12' }

      if (yn < 2020 || yn > 2040)
        return { isValid: false, message: 'Año 2020-2040' }

      return { isValid: true }

    case 'producto':
      return strVal.length >= 1
        ? { isValid: true }
        : { isValid: false, message: 'Producto requerido' }

    case 'analista':
      return strVal.length >= 1
        ? { isValid: true }
        : { isValid: false, message: 'Analista requerido' }

    case 'numero_cuotas': {
      const nc = parseInt(strVal, 10)

      if (Number.isNaN(nc) || nc < 1 || nc > 50 || nc !== Number(strVal))
        return { isValid: false, message: 'Entero entre 1 y 50' }

      return { isValid: true }
    }

    case 'cuota_periodo':
      if (!strVal) return { isValid: true }

      const cp = parseFloat(strVal)

      return Number.isNaN(cp) || cp < 0
        ? { isValid: false, message: 'Número >= 0' }
        : { isValid: true }

    case 'tasa_interes': {
      if (!strVal || String(strVal).trim() === '') return { isValid: true }
      const ti = parseFloat(String(strVal).trim())
      if (Number.isNaN(ti) || Math.abs(ti) > 1e-9) {
        return {
          isValid: false,
          message: 'Debe ser 0 o vacío (producto sin interés)',
        }
      }
      return { isValid: true }
    }

    case 'concesionario':

    case 'modelo_vehiculo':

    case 'observaciones':
      return { isValid: true }

    default:
      return { isValid: true }
  }
}

/**
 * Revalida toda la fila antes de guardar (carga masiva).
 * Evita guardar si el estado UI quedó desincronizado respecto a las reglas de negocio.
 */
export function validarFilaPrestamoExcelParaGuardar(row: PrestamoExcelRow): {
  ok: boolean
  validation: PrestamoExcelRow['_validation']
  messages: string[]
} {
  const validation: PrestamoExcelRow['_validation'] = { ...row._validation }
  const messages: string[] = []

  const required = [
    'cedula',
    'total_financiamiento',
    'modalidad_pago',
    'fecha_requerimiento',
    'fecha_aprobacion',
    'producto',
    'analista',
    'numero_cuotas',
  ] as const

  let hasErrors = false

  for (const field of required) {
    const raw = row[field as keyof PrestamoExcelRow]
    const v = validatePrestamoField(
      field,
      field === 'numero_cuotas' || field === 'total_financiamiento'
        ? (raw as string | number)
        : (String(raw ?? '') as string | number)
    )
    validation[field] = v
    if (!v.isValid) {
      hasErrors = true
      if (v.message) messages.push(`${field}: ${v.message}`)
    }
  }

  const apB = convertirFechaParaBackendPrestamo(
    String(row.fecha_aprobacion ?? '')
  )

  if (!/^\d{4}-\d{2}-\d{2}$/.test(apB)) {
    validation.fecha_aprobacion = {
      isValid: false,
      message: 'fecha_aprobacion inválida o vacía',
    }
    hasErrors = true
    messages.push('fecha_aprobacion: inválida o vacía')
  }

  validation.cuota_periodo = validatePrestamoField(
    'cuota_periodo',
    row.cuota_periodo
  )
  if (!validation.cuota_periodo.isValid) {
    hasErrors = true
    if (validation.cuota_periodo.message)
      messages.push(`cuota_periodo: ${validation.cuota_periodo.message}`)
  }

  validation.tasa_interes = validatePrestamoField(
    'tasa_interes',
    row.tasa_interes
  )
  if (!validation.tasa_interes.isValid) {
    hasErrors = true
    if (validation.tasa_interes.message)
      messages.push(`tasa_interes: ${validation.tasa_interes.message}`)
  }

  validation.concesionario = { isValid: true }
  validation.modelo_vehiculo = { isValid: true }
  validation.observaciones = { isValid: true }

  return { ok: !hasErrors, validation, messages }
}

export { validateExcelFile, validateExcelData, sanitizeFileName }
