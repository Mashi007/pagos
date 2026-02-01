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

