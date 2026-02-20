/**
 * Validation types and helpers for client bulk upload (Excel).
 * Extracted from ExcelUploader - used by useExcelUpload hook.
 */

export interface ValidationResult {
  isValid: boolean
  message?: string
  normalizedValue?: string
}

export interface ExcelData {
  cedula: string
  nombres: string
  telefono: string
  email: string
  direccion: string
  fecha_nacimiento: string
  ocupacion: string
  estado: string
  activo: string
  notas: string
}

export interface ExcelRow extends ExcelData {
  _rowIndex: number
  _validation: { [key: string]: ValidationResult }
  _hasErrors: boolean
}

/** Normalizer: if value is 'nn' (any case/spaces), convert to empty string */
export function blankIfNN(value: string | null | undefined): string {
  if (value == null) return ''
  const trimmed = value.toString().trim()
  return trimmed.toLowerCase() === 'nn' ? '' : trimmed
}

/** Format names: Title Case (first letter uppercase, rest lowercase per word) */
export function formatNombres(nombres: string): string {
  if (!nombres || !nombres.trim()) return nombres
  return nombres
    .split(/\s+/)
    .filter((word) => word.length > 0)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/** Convert Excel date value to DD/MM/YYYY */
export function convertirFechaExcel(value: unknown): string {
  if (value == null || value === '') return ''
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return ''
    const dia = String(value.getDate()).padStart(2, '0')
    const mes = String(value.getMonth() + 1).padStart(2, '0')
    const ano = value.getFullYear()
    return `${dia}/${mes}/${ano}`
  }
  const strValue = value.toString().trim()
  if (!strValue) return ''
  if (/^\d{4,}$/.test(strValue)) {
    try {
      const numeroSerie = parseInt(strValue, 10)
      const fechaBase = new Date(1900, 0, 1)
      fechaBase.setDate(fechaBase.getDate() + numeroSerie - 2)
      if (Number.isNaN(fechaBase.getTime())) return strValue
      const dia = String(fechaBase.getDate()).padStart(2, '0')
      const mes = String(fechaBase.getMonth() + 1).padStart(2, '0')
      const ano = String(fechaBase.getFullYear())
      return `${dia}/${mes}/${ano}`
    } catch {
      return strValue
    }
  }
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(strValue)) return strValue
  if (/^\d{4}-\d{2}-\d{2}$/.test(strValue)) {
    const [ano, mes, dia] = strValue.split('-')
    return `${dia}/${mes}/${ano}`
  }
  const matchDMY = strValue.match(/^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})$/)
  if (matchDMY) {
    const [, d, m, y] = matchDMY
    return `${(d as string).padStart(2, '0')}/${(m as string).padStart(2, '0')}/${y}`
  }
  const parsed = new Date(strValue)
  if (!Number.isNaN(parsed.getTime())) {
    const dia = String(parsed.getDate()).padStart(2, '0')
    const mes = String(parsed.getMonth() + 1).padStart(2, '0')
    const ano = parsed.getFullYear()
    return `${dia}/${mes}/${ano}`
  }
  return strValue
}

/** Convert DD/MM/YYYY to YYYY-MM-DD for backend */
export function convertirFechaParaBackend(fechaDDMMYYYY: string): string {
  if (!fechaDDMMYYYY || !fechaDDMMYYYY.trim()) return ''
  const trimmed = fechaDDMMYYYY.trim()
  const match = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (!match) return trimmed
  const [, d, m, y] = match
  return `${y}-${(d as string).padStart(2, '0')}-${(m as string).padStart(2, '0')}`
}

const DEFAULT_ESTADOS = ['ACTIVO', 'INACTIVO', 'FINALIZADO', 'LEGACY']

/** Validate a single field. Returns ValidationResult. */
export function validateField(
  field: string,
  value: string,
  options?: { estadoOpciones?: string[] }
): ValidationResult {
  if (typeof value === 'string' && value.trim().toLowerCase() === 'nn') {
    return { isValid: true, message: 'Valor omitido por NN' }
  }
  const estadosValidos =
    (options?.estadoOpciones?.length ?? 0) > 0
      ? (options?.estadoOpciones ?? [])
      : DEFAULT_ESTADOS

  switch (field) {
    case 'cedula':
      if (!value.trim()) return { isValid: true }
      const cedulaLimpia = value.trim().replace(/:$/, '').replace(/:/g, '')
      const cedulaPattern = /^[VEJZ]\d{6,11}$/
      if (!cedulaPattern.test(cedulaLimpia.toUpperCase())) {
        return { isValid: false, message: 'Formato: E/V/J/Z + 6-11 dígitos (sin :)' }
      }
      return { isValid: true }

    case 'nombres':
      if (!value.trim()) return { isValid: false, message: 'Nombres requeridos' }
      const nombresWords = value.trim().split(/\s+/).filter((word) => word.length > 0)
      if (nombresWords.length < 2 || nombresWords.length > 7) {
        return { isValid: false, message: 'DEBE tener entre 2 y 7 palabras' }
      }
      return { isValid: true }

    case 'telefono':
      if (!value || !value.trim()) return { isValid: false, message: 'Teléfono requerido' }
      let digitsOnly = (value || '').replace(/\D/g, '')
      if (digitsOnly.startsWith('58') && digitsOnly.length >= 11) digitsOnly = digitsOnly.slice(2)
      if (digitsOnly.length > 10)
        return { isValid: true, message: 'Se usará 9999999999 por defecto (>10 dígitos)' }
      if (digitsOnly.length !== 10) {
        return { isValid: false, message: 'Formato: exactamente 10 dígitos (sin 0 inicial)' }
      }
      if (!/^[1-9]\d{9}$/.test(digitsOnly)) {
        return { isValid: false, message: 'Formato: 10 dígitos (sin 0 inicial)' }
      }
      return { isValid: true }

    case 'email':
      if (!value.trim()) return { isValid: false, message: 'Email requerido' }
      const emailTrimmed = value.trim()
      if (emailTrimmed.includes(' ')) {
        return { isValid: false, message: 'El email no puede contener espacios' }
      }
      if (emailTrimmed.includes(',')) {
        return { isValid: false, message: 'El email no puede contener comas' }
      }
      if (!emailTrimmed.includes('@')) {
        return { isValid: false, message: 'El email debe contener un @' }
      }
      if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(emailTrimmed.toLowerCase())) {
        return {
          isValid: false,
          message: 'El email debe tener una extensión válida (.com, .edu, .gob, etc.)',
        }
      }
      return { isValid: true }

    case 'direccion':
      if (!value.trim()) return { isValid: false, message: 'Dirección requerida' }
      if (value.trim().length < 5) return { isValid: false, message: 'Mínimo 5 caracteres' }
      return { isValid: true }

    case 'estado':
      if (!value.trim()) return { isValid: false, message: 'Estado requerido' }
      const estadoNormalizado = value.toUpperCase().trim()
      if (!estadosValidos.includes(estadoNormalizado)) {
        return { isValid: false, message: `Debe ser uno de: ${estadosValidos.join(', ')}` }
      }
      return { isValid: true }

    case 'activo':
      if (!value.trim()) return { isValid: false, message: 'Valor requerido' }
      if (!['true', 'false'].includes(value.toLowerCase())) {
        return { isValid: false, message: 'Debe ser true o false' }
      }
      return { isValid: true }

    case 'fecha_nacimiento':
      if (!value.trim()) return { isValid: false, message: 'Fecha requerida' }
      const fechaMatch = value.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
      if (!fechaMatch) {
        return { isValid: false, message: 'Formato: DD/MM/YYYY (ej: 01/01/2000 o 1/1/2000)' }
      }
      const [, diaStr, mesStr, anoStr] = fechaMatch
      const dia = (diaStr as string).padStart(2, '0')
      const mes = (mesStr as string).padStart(2, '0')
      const diaNum = parseInt(dia, 10)
      const mesNum = parseInt(mes, 10)
      const anoNum = parseInt(anoStr as string, 10)
      if (diaNum < 1 || diaNum > 31) return { isValid: false, message: 'Día inválido (1-31)' }
      if (mesNum < 1 || mesNum > 12) return { isValid: false, message: 'Mes inválido (1-12)' }
      if (anoNum < 1900 || anoNum > 2100) return { isValid: false, message: 'Año inválido (1900-2100)' }
      const fechaNac = new Date(anoNum, mesNum - 1, diaNum)
      if (
        fechaNac.getDate() !== diaNum ||
        fechaNac.getMonth() !== mesNum - 1 ||
        fechaNac.getFullYear() !== anoNum
      ) {
        return { isValid: false, message: 'Fecha inválida (ej: 31/02 no existe)' }
      }
      const hoy = new Date()
      hoy.setHours(0, 0, 0, 0)
      if (fechaNac >= hoy) {
        return { isValid: false, message: 'La fecha de nacimiento no puede ser futura o de hoy' }
      }
      const fecha18 = new Date(anoNum + 18, mesNum - 1, diaNum)
      if (fecha18 > hoy) {
        return { isValid: false, message: 'Debe tener al menos 18 años cumplidos' }
      }
      return { isValid: true }

    case 'ocupacion':
      if (!value.trim()) return { isValid: false, message: 'Ocupación requerida' }
      if (value.trim().length < 2) return { isValid: false, message: 'Mínimo 2 caracteres' }
      return { isValid: true }

    case 'notas':
      return { isValid: true }

    default:
      return { isValid: true }
  }
}
