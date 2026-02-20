/**
 * Thin wrapper for Excel client bulk upload.
 * Delegates to ExcelUploaderUI which uses useExcelUpload hook.
 */

import { ExcelUploaderUI } from './ExcelUploaderUI'
import type { ExcelUploaderProps } from '../../hooks/useExcelUpload'

export function ExcelUploader(props: ExcelUploaderProps) {
  return <ExcelUploaderUI {...props} />
}
