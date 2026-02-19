import { useState, useMemo } from 'react'
import { Upload, X, FileSpreadsheet, Loader2, CheckCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '../../components/ui/button'
import { Card, CardContent } from '../../components/ui/card'
import { ErroresDetallados } from '../carga-masiva/ErroresDetallados'
import { pagoService } from '../../services/pagoService'
import { toast } from 'sonner'

interface ErrorDetalleBackend {
  fila: number
  cedula: string
  error: string
  datos: Record<string, unknown>
}

interface ExcelUploaderProps {
  onClose: () => void
  onSuccess: () => void
}

export function ExcelUploader({ onClose, onSuccess }: ExcelUploaderProps) {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [results, setResults] = useState<{
    registros_procesados?: number
    filas_omitidas?: number
    errores?: string[]
    errores_detalle?: ErrorDetalleBackend[]
    errores_total?: number
    errores_detalle_total?: number
    errores_truncados?: boolean
  } | null>(null)

  const erroresParaTabla = useMemo(() => {
    if (!results?.errores_detalle?.length) return []
    return results.errores_detalle.map((e: ErrorDetalleBackend) => {
      const d = e.datos ?? {}
      return {
        row: e.fila,
        cedula: String(e.cedula ?? ''),
        error: e.error,
        data: {
          ...d,
          fecha: d.fecha_pago,
          documento_pago: d.numero_documento,
        },
        tipo: 'pago' as const,
      }
    })
  }, [results?.errores_detalle])

  const handleDescargarErrores = () => {
    if (!results?.errores_detalle?.length) return
    const headers = ['fila', 'cedula', 'fecha_pago', 'monto_pagado', 'numero_documento', 'error']
    const rows = results.errores_detalle.map((e: ErrorDetalleBackend) => [
      e.fila,
      e.cedula,
      (e.datos?.fecha_pago ?? ''),
      (e.datos?.monto_pagado ?? ''),
      (e.datos?.numero_documento ?? ''),
      `"${(e.error ?? '').replace(/"/g, '""')}"`,
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'errores_pagos_carga_masiva.csv'
    a.click()
    URL.revokeObjectURL(a.href)
    toast.success('Archivo de errores descargado')
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      // âœ… VALIDACIÓN DE SEGURIDAD: Validar archivo antes de aceptarlo
      const { validateExcelFile } = await import('../../utils/excelValidation')
      const validation = validateExcelFile(selectedFile)

      if (!validation.isValid) {
        toast.error(validation.error || 'Archivo inválido')
        return
      }

      if (validation.warnings && validation.warnings.length > 0) {
        validation.warnings.forEach(warning => toast.warning(warning))
      }

      setFile(selectedFile)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      toast.error('Selecciona un archivo')
      return
    }

    setIsUploading(true)
    setResults(null)
    try {
      const result = await pagoService.uploadExcel(file)
      setResults(result)
      const registrados = result.registros_procesados ?? 0
      const filasOmitidas = result.filas_omitidas ?? 0
      const numErrores = result.errores_total ?? result.errores?.length ?? 0

      if (registrados > 0) {
        toast.success(`${registrados} pago(s) registrado(s) exitosamente`)
        onSuccess()
      }
      if (numErrores > 0) {
        toast.warning(`${numErrores} fila(s) con error`)
      }
      if (registrados === 0 && filasOmitidas > 0 && numErrores === 0) {
        toast.info(`${filasOmitidas} fila(s) omitida(s): cédula vacía o monto ≤ 0. Revisa el orden de columnas del Excel.`)
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || 'Error al cargar archivo')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95 }}
          className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
            <h2 className="text-xl font-bold">Carga Masiva de Pagos</h2>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Instrucciones alineadas con tabla pagos (cedula, prestamo_id, fecha_pago, monto_pagado, numero_documento) */}
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <h3 className="font-semibold text-lg">Formato del archivo Excel</h3>
                  <p className="text-sm text-gray-600">Primera fila: encabezados. Desde la segunda fila, una columna por campo (en este orden):</p>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
                    <li><strong>Cédula</strong> (obligatorio)</li>
                    <li><strong>ID Préstamo</strong> (obligatorio si la persona tiene más de un préstamo; número)</li>
                    <li><strong>Fecha de pago</strong> (fecha)</li>
                    <li><strong>Monto pagado</strong> (número, mayor a 0)</li>
                    <li><strong>Número de documento</strong> (referencia del pago)</li>
                  </ol>
                  <p className="text-xs text-amber-600 mt-2 font-medium">
                    Si una persona tiene varios préstamos, debe indicar el ID del préstamo al que aplica cada pago.
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Formatos aceptados: .xlsx o .xls. Las filas con cédula vacía o monto ≤ 0 se omiten.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* File Upload */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                className="hidden"
                id="excel-upload"
              />
              <label
                htmlFor="excel-upload"
                className="cursor-pointer inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Seleccionar Archivo
              </label>
              {file && (
                <p className="mt-2 text-sm text-gray-600">{file.name}</p>
              )}
            </div>

            {/* Resumen y errores detallados (misma interfaz que préstamos/clientes) */}
            {results && (
              <div className="space-y-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-semibold">{results.registros_procesados ?? 0} pago(s) registrado(s)</span>
                    </div>
                    {(results.filas_omitidas ?? 0) > 0 && (
                      <p className="text-sm text-amber-600 mt-1">
                        {results.filas_omitidas} fila(s) omitida(s) (cédula vacía o monto ≤ 0). Comprueba que la columna 1 sea Cédula y la 4 sea Monto &gt; 0.
                      </p>
                    )}
                    {(results.errores?.length ?? 0) > 0 && (
                      <p className="text-sm text-red-600 mt-1">
                        {(results.errores_total ?? results.errores?.length ?? 0)} fila(s) con error. Revisa la tabla inferior para ver fila, cédula y descripción.
                        {results.errores_truncados && (
                          <span className="block text-amber-600 mt-0.5">
                            Se muestran los primeros 50 errores y 100 detalles. Descarga el archivo para exportar los detalles mostrados.
                          </span>
                        )}
                      </p>
                    )}
                  </CardContent>
                </Card>
                {erroresParaTabla.length > 0 && (
                  <ErroresDetallados
                    errores={erroresParaTabla}
                    tipo="pagos"
                    onDescargarErrores={handleDescargarErrores}
                  />
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button variant="outline" onClick={onClose} disabled={isUploading}>
                Cancelar
              </Button>
              <Button onClick={handleUpload} disabled={!file || isUploading}>
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Cargando...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Cargar Pagos
                  </>
                )}
              </Button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

