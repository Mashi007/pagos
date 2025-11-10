import { useState } from 'react'
import { Upload, X, FileSpreadsheet, Loader2, CheckCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { pagoService } from '@/services/pagoService'
import { toast } from 'sonner'

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
      // ✅ VALIDACIÓN DE SEGURIDAD: Validar archivo antes de aceptarlo
      const { validateExcelFile } = await import('@/utils/excelValidation')
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
    try {
      const result = await pagoService.uploadExcel(file)
      setResults(result)
      
      if (result.success > 0) {
        toast.success(`${result.success} pagos registrados exitosamente`)
      }
      
      if (result.errores > 0) {
        toast.warning(`${result.errores} errores encontrados`)
      }
      
      if (result.success > 0) {
        onSuccess()
      }
    } catch (error: any) {
      toast.error(error.message || 'Error al cargar archivo')
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
            {/* Instrucciones */}
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <h3 className="font-semibold text-lg">Formato del archivo Excel:</h3>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                    <li>Cédula de Identidad</li>
                    <li>Fecha de Pago</li>
                    <li>Monto Pagado</li>
                    <li>Número de Documento</li>
                  </ul>
                  <p className="text-xs text-gray-500 mt-2">
                    El archivo debe contener estas columnas exactamente como se muestra.
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
                      <span className="font-semibold">{results.success} pagos registrados</span>
                    </div>
                    {results.errores > 0 && (
                      <div className="text-red-600">
                        <span className="font-semibold">{results.errores} errores</span>
                      </div>
                    )}
                    {results.errores_detalle && results.errores_detalle.length > 0 && (
                      <div className="mt-3 max-h-40 overflow-y-auto">
                        {results.errores_detalle.map((error: string, index: number) => (
                          <p key={index} className="text-xs text-red-600">{error}</p>
                        ))}
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

