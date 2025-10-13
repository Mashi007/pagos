import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { Upload, FileSpreadsheet, Download, AlertCircle, CheckCircle, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'

interface UploadResult {
  success: boolean
  message: string
  data?: any
  errors?: string[]
}

export function CargaMasiva() {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Validar que sea un archivo Excel
      const validExtensions = ['.xlsx', '.xls', '.csv']
      const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
      
      if (!validExtensions.includes(fileExtension)) {
        setUploadResult({
          success: false,
          message: 'Formato de archivo no válido',
          errors: ['Solo se permiten archivos Excel (.xlsx, .xls) o CSV (.csv)']
        })
        return
      }

      // Validar tamaño (máximo 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setUploadResult({
          success: false,
          message: 'Archivo demasiado grande',
          errors: ['El archivo no puede superar los 10MB']
        })
        return
      }

      setSelectedFile(file)
      setUploadResult(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setIsUploading(true)
    setUploadProgress(0)
    setUploadResult(null)

    try {
      // Simular progreso de carga
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 200)

      // Crear FormData para enviar el archivo
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('type', 'clientes') // Tipo de datos a importar

      // Simular llamada a la API (por ahora)
      await new Promise(resolve => setTimeout(resolve, 2000))

      clearInterval(progressInterval)
      setUploadProgress(100)

      // Simular resultado exitoso
      setUploadResult({
        success: true,
        message: 'Archivo cargado exitosamente',
        data: {
          totalRecords: 150,
          processedRecords: 148,
          errors: 2,
          fileName: selectedFile.name
        }
      })

    } catch (error: any) {
      setUploadResult({
        success: false,
        message: 'Error al cargar el archivo',
        errors: [error.message || 'Error desconocido']
      })
    } finally {
      setIsUploading(false)
      setUploadProgress(0)
    }
  }

  const downloadTemplate = () => {
    // Crear un template Excel básico
    const templateData = [
      ['cedula', 'nombre', 'apellido', 'telefono', 'email', 'direccion', 'monto_prestamo', 'fecha_prestamo', 'estado'],
      ['12345678', 'Juan', 'Pérez', '3001234567', 'juan@email.com', 'Calle 123 #45-67', '500000', '2024-01-15', 'ACTIVO'],
      ['87654321', 'María', 'García', '3007654321', 'maria@email.com', 'Carrera 78 #12-34', '750000', '2024-01-20', 'ACTIVO']
    ]

    const csvContent = templateData.map(row => row.join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'template_clientes_rapicredit.csv'
    link.click()
  }

  return (
    <div className="p-6 space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Carga Masiva de Datos</h1>
          <p className="text-gray-600 mt-2">
            Importa datos desde archivos Excel para poblar la base de datos
          </p>
        </div>
        <Button
          onClick={downloadTemplate}
          variant="outline"
          className="flex items-center space-x-2"
        >
          <Download className="h-4 w-4" />
          <span>Descargar Template</span>
        </Button>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel de Carga */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Upload className="h-5 w-5" />
                <span>Cargar Archivo Excel</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                <FileSpreadsheet className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">
                  Arrastra tu archivo Excel aquí o haz clic para seleccionar
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                  disabled={isUploading}
                >
                  Seleccionar Archivo
                </Button>
              </div>

              {selectedFile && (
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <FileSpreadsheet className="h-5 w-5 text-blue-600" />
                      <div>
                        <p className="font-medium text-blue-900">{selectedFile.name}</p>
                        <p className="text-sm text-blue-700">
                          {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedFile(null)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}

              {isUploading && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Procesando archivo...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} className="w-full" />
                </div>
              )}

              <Button
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
                className="w-full"
                size="lg"
              >
                {isUploading ? 'Procesando...' : 'Cargar Datos'}
              </Button>
            </CardContent>
          </Card>
        </motion.div>

        {/* Panel de Resultados */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5" />
                <span>Resultados de la Carga</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {uploadResult ? (
                <div className="space-y-4">
                  <AlertWithIcon
                    variant={uploadResult.success ? 'success' : 'destructive'}
                    title={uploadResult.success ? 'Carga Exitosa' : 'Error en la Carga'}
                    description={uploadResult.message}
                  />

                  {uploadResult.success && uploadResult.data && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-green-50 p-3 rounded-lg">
                        <p className="text-sm text-green-700">Total Registros</p>
                        <p className="text-2xl font-bold text-green-900">
                          {uploadResult.data.totalRecords}
                        </p>
                      </div>
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <p className="text-sm text-blue-700">Procesados</p>
                        <p className="text-2xl font-bold text-blue-900">
                          {uploadResult.data.processedRecords}
                        </p>
                      </div>
                      <div className="bg-yellow-50 p-3 rounded-lg">
                        <p className="text-sm text-yellow-700">Con Errores</p>
                        <p className="text-2xl font-bold text-yellow-900">
                          {uploadResult.data.errors}
                        </p>
                      </div>
                      <div className="bg-purple-50 p-3 rounded-lg">
                        <p className="text-sm text-purple-700">Archivo</p>
                        <p className="text-sm font-medium text-purple-900 truncate">
                          {uploadResult.data.fileName}
                        </p>
                      </div>
                    </div>
                  )}

                  {uploadResult.errors && uploadResult.errors.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-medium text-red-700">Errores encontrados:</h4>
                      <ul className="space-y-1">
                        {uploadResult.errors.map((error, index) => (
                          <li key={index} className="text-sm text-red-600 flex items-center space-x-2">
                            <AlertCircle className="h-4 w-4" />
                            <span>{error}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">
                  <FileSpreadsheet className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Los resultados de la carga aparecerán aquí</p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Instrucciones */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>📋 Instrucciones para la Carga Masiva</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold text-gray-800 mb-3">Formato del Archivo:</h4>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• Archivos Excel (.xlsx, .xls) o CSV (.csv)</li>
                  <li>• Máximo 10MB de tamaño</li>
                  <li>• Primera fila debe contener los nombres de las columnas</li>
                  <li>• Usar el template proporcionado como referencia</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 mb-3">Columnas Requeridas:</h4>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• <strong>cedula:</strong> Número de cédula del cliente</li>
                  <li>• <strong>nombre:</strong> Nombre del cliente</li>
                  <li>• <strong>apellido:</strong> Apellido del cliente</li>
                  <li>• <strong>telefono:</strong> Número de teléfono</li>
                  <li>• <strong>email:</strong> Correo electrónico</li>
                  <li>• <strong>monto_prestamo:</strong> Monto del préstamo</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
