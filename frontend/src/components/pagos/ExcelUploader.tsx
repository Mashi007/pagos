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
  const [results, setResults] = useState<any>(null)

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
      const listaErrores = result.errores ?? []
      const numErrores = listaErrores.length

      if (registrados > 0) {
        toast.success(`${registrados} pago(s) registrado(s) exitosamente`)
        onSuccess()
      }
      if (numErrores > 0) {
        toast.warning(`${numErrores} fila(s) con error`)
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
          className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
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
                    <li><strong>ID Préstamo</strong> (opcional, número)</li>
                    <li><strong>Fecha de pago</strong> (fecha)</li>
                    <li><strong>Monto pagado</strong> (número, mayor a 0)</li>
                    <li><strong>Número de documento</strong> (referencia del pago)</li>
                  </ol>
                  <p className="text-xs text-gray-500 mt-2">
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

            {/* Results */}
            {results && (
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-semibold">{results.registros_procesados ?? 0} pago(s) registrado(s)</span>
                    </div>
                    {(results.errores?.length ?? 0) > 0 && (
                      <div className="text-red-600">
                        <span className="font-semibold">{results.errores.length} fila(s) con error</span>
                      </div>
                    )}
                    {results.errores && results.errores.length > 0 && (
                      <div className="mt-3 max-h-40 overflow-y-auto">
                        {results.errores.slice(0, 50).map((error: string, index: number) => (
                          <p key={index} className="text-xs text-red-600">{error}</p>
                        ))}
                        {results.errores.length > 50 && (
                          <p className="text-xs text-gray-500 mt-1">… y {results.errores.length - 50} más</p>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
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

