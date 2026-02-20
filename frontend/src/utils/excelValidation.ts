/**
 * Utilidades de validación para archivos Excel
 * Validaciones de seguridad para archivos Excel procesados con ExcelJS
 */

// Límites de seguridad
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB
const MAX_ROWS = 10000 // Máximo 10,000 filas
const MAX_COLUMNS = 100 // Máximo 100 columnas
const ALLOWED_EXTENSIONS = ['.xlsx', '.xls']
const ALLOWED_MIME_TYPES = [
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
  'application/vnd.ms-excel', // .xls
  'application/excel',
  'application/x-excel',
  'application/x-msexcel'
]

export interface ExcelValidationResult {
  isValid: boolean
  error?: string
  warnings?: string[]
}

/**
 * Valida el archivo antes de procesarlo
 */
export function validateExcelFile(file: File): ExcelValidationResult {
  const warnings: string[] = []

  // 1. Validar extensión del archivo
  const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
  if (!ALLOWED_EXTENSIONS.includes(fileExtension)) {
    return {
      isValid: false,
      error: `Extensión de archivo no permitida. Solo se permiten: ${ALLOWED_EXTENSIONS.join(', ')}`
    }
  }

  // 2. Validar tipo MIME (si está disponible)
  if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
    warnings.push(`Tipo MIME inesperado: ${file.type}. Continuando con validación de extensión.`)
  }

  // 3. Validar tamaño del archivo
  if (file.size > MAX_FILE_SIZE) {
    return {
      isValid: false,
      error: `El archivo es demasiado grande. Tamaño máximo: ${(MAX_FILE_SIZE / 1024 / 1024).toFixed(0)} MB. Tamaño actual: ${(file.size / 1024 / 1024).toFixed(2)} MB`
    }
  }

  // 4. Validar que el archivo no esté vacío
  if (file.size === 0) {
    return {
      isValid: false,
      error: 'El archivo está vacío'
    }
  }

  // 5. Validar nombre del archivo (prevenir caracteres peligrosos)
  const dangerousChars = /[<>:"|?*\x00-\x1F]/
  if (dangerousChars.test(file.name)) {
    warnings.push('El nombre del archivo contiene caracteres no recomendados')
  }

  return {
    isValid: true,
    warnings: warnings.length > 0 ? warnings : undefined
  }
}

/**
 * Valida la estructura del workbook después de leerlo
 */
export function validateWorkbookStructure(workbook: any): ExcelValidationResult {
  const warnings: string[] = []

  // 1. Validar que tenga al menos una hoja
  if (!workbook.SheetNames || workbook.SheetNames.length === 0) {
    return {
      isValid: false,
      error: 'El archivo Excel no contiene hojas de cálculo'
    }
  }

  // 2. Validar número de hojas (limitar a 10)
  if (workbook.SheetNames.length > 10) {
    warnings.push(`El archivo tiene ${workbook.SheetNames.length} hojas. Solo se procesará la primera.`)
  }

  // 3. Validar la primera hoja
  const firstSheetName = workbook.SheetNames[0]
  const worksheet = workbook.Sheets[firstSheetName]

  if (!worksheet) {
    return {
      isValid: false,
      error: 'No se pudo leer la primera hoja del archivo'
    }
  }

  // 4. Validar rango de celdas (prevenir archivos extremadamente grandes)
  const range = worksheet['!ref']
  if (range) {
    const [startCell, endCell] = range.split(':')
    if (startCell && endCell) {
      // Extraer número de fila y columna
      const startRow = parseInt(startCell.match(/\d+/)?.[0] || '0')
      const endRow = parseInt(endCell.match(/\d+/)?.[0] || '0')
      const startCol = startCell.match(/[A-Z]+/)?.[0] || ''
      const endCol = endCell.match(/[A-Z]+/)?.[0] || ''

      // Convertir columnas a números (A=1, B=2, ..., Z=26, AA=27, etc.)
      const colToNumber = (col: string): number => {
        let num = 0
        for (let i = 0; i < col.length; i++) {
          num = num * 26 + (col.charCodeAt(i) - 64)
        }
        return num
      }

      const numRows = endRow - startRow + 1
      const numCols = colToNumber(endCol) - colToNumber(startCol) + 1

      if (numRows > MAX_ROWS) {
        return {
          isValid: false,
          error: `El archivo tiene demasiadas filas (${numRows}). Máximo permitido: ${MAX_ROWS}`
        }
      }

      if (numCols > MAX_COLUMNS) {
        return {
          isValid: false,
          error: `El archivo tiene demasiadas columnas (${numCols}). Máximo permitido: ${MAX_COLUMNS}`
        }
      }

      if (numRows === 0) {
        return {
          isValid: false,
          error: 'El archivo no contiene datos'
        }
      }
    }
  }

  return {
    isValid: true,
    warnings: warnings.length > 0 ? warnings : undefined
  }
}

/**
 * Valida los datos extraídos antes de procesarlos
 */
export function validateExcelData(data: any[]): ExcelValidationResult {
  const warnings: string[] = []

  // 1. Validar que haya datos
  if (!data || data.length === 0) {
    return {
      isValid: false,
      error: 'No se encontraron datos en el archivo'
    }
  }

  // 2. Validar número de filas
  if (data.length > MAX_ROWS) {
    return {
      isValid: false,
      error: `El archivo contiene demasiadas filas de datos (${data.length}). Máximo permitido: ${MAX_ROWS}`
    }
  }

  // 3. Validar que no haya filas excesivamente largas
  const maxRowLength = Math.max(...data.map((row: any) => Array.isArray(row) ? row.length : Object.keys(row).length))
  if (maxRowLength > MAX_COLUMNS) {
    warnings.push(`Algunas filas tienen más de ${MAX_COLUMNS} columnas. Solo se procesarán las primeras ${MAX_COLUMNS}.`)
  }

  return {
    isValid: true,
    warnings: warnings.length > 0 ? warnings : undefined
  }
}

/**
 * Sanitiza el nombre del archivo para prevenir problemas de seguridad
 */
export function sanitizeFileName(fileName: string): string {
  // Remover caracteres peligrosos
  return fileName
    .replace(/[<>:"|?*\x00-\x1F]/g, '')
    .replace(/\.\./g, '.')
    .trim()
}

/**
 * Valida y sanitiza datos de una celda
 */
export function sanitizeCellValue(value: any): string {
  if (value === null || value === undefined) {
    return ''
  }

  // Convertir a string
  let str = String(value)

  // Limitar longitud para prevenir DoS
  if (str.length > 10000) {
    str = str.substring(0, 10000)
  }

  // Remover caracteres de control (excepto saltos de línea y tabs)
  str = str.replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '')

  return str.trim()
}


export interface ExcelData { cedula: string; nombres: string; telefono: string; email: string; direccion: string; fecha_nacimiento: string; ocupacion: string; estado: string; activo: string; notas: string }
export interface ValidationResult { isValid: boolean; message?: string; normalizedValue?: string }
export interface ExcelRow extends ExcelData { _rowIndex: number; _validation: Record<string, ValidationResult>; _hasErrors: boolean }
export interface ValidateFieldOptions { estadoOpciones?: string[] }
export function blankIfNN(v: string | null | undefined): string { if (v == null) return ''; const t = v.toString().trim(); return t.toLowerCase() === 'nn' ? '' : t }
export function formatNombres(n: string): string { if (!n?.trim()) return n; return n.split(/\s+/).filter(w=>w.length).map(w=>w[0].toUpperCase()+w.slice(1).toLowerCase()).join(' ') }
export function convertirFechaExcel(val: unknown): string {
  if (val == null || val === '') return ''
  if (val instanceof Date) { if (Number.isNaN(val.getTime())) return ''; return `${String(val.getDate()).padStart(2,'0')}/${String(val.getMonth()+1).padStart(2,'0')}/${val.getFullYear()}` }
  const s = val.toString().trim(); if (!s) return ''
  if (/^\d{4,}$/.test(s)) { try { const d=new Date(1900,0,1); d.setDate(d.getDate()+parseInt(s,10)-2); return Number.isNaN(d.getTime())?s:`${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}` } catch { return s } }
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(s)) return s
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) { const [y,m,d]=s.split('-'); return `${d}/${m}/${y}` }
  const m = s.match(/^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})$/); if (m) return `//`
  const p = new Date(s); return !Number.isNaN(p.getTime()) ? `${String(p.getDate()).padStart(2,'0')}/${String(p.getMonth()+1).padStart(2,'0')}/${p.getFullYear()}` : s
}
export function convertirFechaParaBackend(f: string): string { if (!f?.trim()) return ''; const m = f.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/); return m ? `${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}` : f.trim() }
export function validateField(field: string, value: string, options?: ValidateFieldOptions): ValidationResult {
  if (typeof value==='string'&&value.trim().toLowerCase()==='nn') return { isValid: true, message: 'Valor omitido por NN' }
  const opts = options?.estadoOpciones ?? []
  switch (field) {
    case 'cedula': if (!value.trim()) return { isValid: true }; const c = value.trim().replace(/:$/, '').replace(/:/g, ''); return /^[VEJZ]\d{6,11}$/.test(c.toUpperCase()) ? { isValid: true } : { isValid: false, message: 'Formato E/V/J/Z + 6-11 dígitos' }
    case 'nombres': if (!value.trim()) return { isValid: false, message: 'Nombres requeridos' }; const w = value.trim().split(/\s+/).filter(x=>x.length); return w.length>=2&&w.length<=7 ? { isValid: true } : { isValid: false, message: 'Entre 2 y 7 palabras' }
    case 'telefono': if (!value?.trim()) return { isValid: false, message: 'Teléfono requerido' }; let d=(value||'').replace(/\D/g,''); if (d.startsWith('58')&&d.length>=11) d=d.slice(2); if (d.length>10) return { isValid: true }; if (d.length!==10) return { isValid: false, message: '10 dígitos' }; return /^[1-9]\d{9}$/.test(d) ? { isValid: true } : { isValid: false, message: '10 dígitos sin 0 inicial' }
    case 'email': if (!value.trim()) return { isValid: false, message: 'Email requerido' }; const t=value.trim(); if (t.includes(' ')) return { isValid: false, message: 'Sin espacios' }; if (t.includes(',')) return { isValid: false, message: 'Sin comas' }; if (!t.includes('@')) return { isValid: false, message: 'Debe tener @' }; return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(t.toLowerCase()) ? { isValid: true } : { isValid: false, message: 'Extensión válida' }
    case 'direccion': if (!value.trim()) return { isValid: false, message: 'Dirección requerida' }; return value.trim().length>=5 ? { isValid: true } : { isValid: false, message: 'Mínimo 5 caracteres' }
    case 'estado': if (!value.trim()) return { isValid: false, message: 'Estado requerido' }; const valid = opts.length ? opts : ['ACTIVO','INACTIVO','FINALIZADO','LEGACY']; return valid.includes(value.toUpperCase().trim()) ? { isValid: true } : { isValid: false, message: `Uno de: ${valid.join(', ')}` }
    case 'activo': if (!value.trim()) return { isValid: false, message: 'Valor requerido' }; return ['true','false'].includes(value.toLowerCase()) ? { isValid: true } : { isValid: false, message: 'true o false' }
    case 'fecha_nacimiento': if (!value.trim()) return { isValid: false, message: 'Fecha requerida' }; const fm = value.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/); if (!fm) return { isValid: false, message: 'Formato DD/MM/YYYY' }; const dn=parseInt(fm[1],10), mnn=parseInt(fm[2],10), yn=parseInt(fm[3],10); if (dn<1||dn>31) return { isValid: false, message: 'Día 1-31' }; if (mnn<1||mnn>12) return { isValid: false, message: 'Mes 1-12' }; if (yn<1900||yn>2100) return { isValid: false, message: 'Año 1900-2100' }; const fd = new Date(yn, mnn-1, dn); if (fd.getDate()!==dn||fd.getMonth()!==mnn-1||fd.getFullYear()!==yn) return { isValid: false, message: 'Fecha inválida' }; const hoy = new Date(); hoy.setHours(0,0,0,0); if (fd>=hoy) return { isValid: false, message: 'No futura' }; if (new Date(yn+18, mnn-1, dn) > hoy) return { isValid: false, message: 'Mínimo 18 años' }; return { isValid: true }
    case 'ocupacion': if (!value.trim()) return { isValid: false, message: 'Ocupación requerida' }; return value.trim().length>=2 ? { isValid: true } : { isValid: false, message: 'Mínimo 2 caracteres' }
    case 'notas': return { isValid: true }
    default: return { isValid: true }
  }
}
