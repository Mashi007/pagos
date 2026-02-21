/**
 * Wrapper para carga masiva de préstamos desde Excel.
 */

import { ExcelUploaderPrestamosUI } from './ExcelUploaderPrestamosUI'
import type { ExcelUploaderPrestamosProps } from '../../hooks/useExcelUploadPrestamos'

export function ExcelUploaderPrestamos(props: ExcelUploaderPrestamosProps) {
  return <ExcelUploaderPrestamosUI {...props} />
}
