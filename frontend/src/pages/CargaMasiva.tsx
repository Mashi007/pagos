import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { Upload, FileSpreadsheet, Download, AlertCircle, CheckCircle, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'
import { ErroresDetallados } from '@/components/carga-masiva/ErroresDetallados'
import { Progress } from '@/components/ui/progress'

interface UploadResult {
  success: boolean
  message: string
  data?: any
  errors?: string[]
  erroresDetallados?: Array<{
    row: number
    cedula: string
    error: string
    data: any
    tipo: 'cliente' | 'pago'
  }>
}

export function CargaMasiva() {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedType, setSelectedType] = useState<'clientes' | 'pagos'>('clientes')
  const [uploadStep, setUploadStep] = useState<'clientes' | 'pagos' | 'complete'>('clientes')
  const [clientesLoaded, setClientesLoaded] = useState(false)
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
      formData.append('type', selectedType) // Tipo de datos a importar

      // Simular llamada a la API (por ahora)
      await new Promise(resolve => setTimeout(resolve, 2000))

      clearInterval(progressInterval)
      setUploadProgress(100)

      // Simular resultado con errores detallados
      const erroresDetallados = selectedType === 'clientes' ? [
        {
          row: 3,
          cedula: 'V30325601',
          error: 'Datos marcados como "error" - móvil y email inválidos',
          data: { cedula: 'V30325601', nombre: 'AARON ALEJANDRO GONZALEZ CAYAMA', telefono: 'error', email: 'error' },
          tipo: 'cliente' as const
        },
        {
          row: 15,
          cedula: 'V12345678',
          error: 'Formato de cédula inválido - debe empezar con V',
          data: { cedula: '12345678', nombre: 'JUAN PEREZ', telefono: '+5804123456789', email: 'juan@email.com' },
          tipo: 'cliente' as const
        }
      ] : [
        {
          row: 5,
          cedula: 'V99999999',
          error: 'Cliente con cédula V99999999 no encontrado',
          data: { cedula: 'V99999999', fecha: '06/12/2024', monto_pagado: '150', documento_pago: '123456789' },
          tipo: 'pago' as const
        },
        {
          row: 8,
          cedula: 'V22283249',
          error: 'Formato de monto inválido - debe ser numérico',
          data: { cedula: 'V22283249', fecha: '06/12/2024', monto_pagado: 'abc', documento_pago: '740087437485285' },
          tipo: 'pago' as const
        }
      ]

      const result = {
        success: true,
        message: `${selectedType === 'clientes' ? 'Clientes' : 'Pagos'} procesados con ${erroresDetallados.length} errores`,
        data: {
          totalRecords: selectedType === 'clientes' ? 150 : 300,
          processedRecords: selectedType === 'clientes' ? 148 : 295,
          errors: erroresDetallados.length,
          fileName: selectedFile.name,
          type: selectedType
        },
        erroresDetallados
      }

      setUploadResult(result)

      // Si se cargaron clientes exitosamente (aunque haya errores), avanzar al siguiente paso
      if (selectedType === 'clientes' && result.success && result.data.processedRecords > 0) {
        setClientesLoaded(true)
        setUploadStep('pagos')
        setSelectedType('pagos')
        setSelectedFile(null)
      } else if (selectedType === 'pagos' && result.success && result.data.processedRecords > 0) {
        setUploadStep('complete')
      }

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
    let templateData: string[][]
    let filename: string

    if (selectedType === 'clientes') {
      templateData = [
        ['cedula', 'nombre', 'telefono', 'email'],
        ['V31566283', 'AARON ALEJANDRO CRESPO ALVAREZ', '+5804127166660', 'aaroncrespo@gmail.com'],
        ['V14929151', 'AARON DANIEL PALENCIA GUZMAN', '+5804247505679', 'AARONWA7@GMAIL.COM']
      ]
      filename = 'template_clientes_rapicredit.csv'
    } else {
      templateData = [
        ['cedula', 'fecha', 'monto_pagado', 'fecha_pago_cuota', 'documento_pago'],
        ['V22283249', '06/12/2024', '108', '05/12/2024', '740087437485285'],
        ['V31566283', '07/12/2024', '250', '06/12/2024', '740087437485286']
      ]
      filename = 'template_pagos_rapicredit.csv'
    }

    const csvContent = templateData.map(row => row.join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
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
          <h1 className="text-3xl font-bold text-gray-900">Migración desde Excel</h1>
          <p className="text-gray-600 mt-2">
            Importa tus datos de clientes y pagos desde Excel al sistema RAPICREDIT
          </p>
          <div className="mt-4 flex space-x-4">
            <div className={`px-4 py-2 rounded-lg ${uploadStep === 'clientes' ? 'bg-blue-100 text-blue-800' : clientesLoaded ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
              <span className="font-medium">Paso 1:</span> Cargar Clientes
            </div>
            <div className={`px-4 py-2 rounded-lg ${uploadStep === 'pagos' ? 'bg-blue-100 text-blue-800' : uploadStep === 'complete' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
              <span className="font-medium">Paso 2:</span> Cargar Pagos
            </div>
            <div className={`px-4 py-2 rounded-lg ${uploadStep === 'complete' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
              <span className="font-medium">Paso 3:</span> Articulación Completa
            </div>
          </div>
        </div>
        <div className="flex space-x-2">
          <select
            className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as 'clientes' | 'pagos')}
          >
            <option value="clientes">Template Clientes</option>
            <option value="pagos">Template Pagos</option>
          </select>
          <Button
            onClick={downloadTemplate}
            variant="outline"
            className="flex items-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Descargar Template</span>
          </Button>
        </div>
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
                <span>
                  {uploadStep === 'clientes' ? 'Cargar Archivo de Clientes' : 
                   uploadStep === 'pagos' ? 'Cargar Archivo de Pagos' : 
                   'Migración Completa'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                <FileSpreadsheet className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">
                  {uploadStep === 'clientes' ? 
                    'Arrastra tu archivo de CLIENTES aquí (con columnas: cedula, nombre, telefono, email)' :
                    uploadStep === 'pagos' ?
                    'Arrastra tu archivo de PAGOS aquí (con columnas: cedula, fecha, monto_pagado, documento_pago)' :
                    'Migración completada exitosamente'
                  }
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
                  disabled={isUploading || uploadStep === 'complete'}
                >
                  {uploadStep === 'complete' ? 'Migración Completa' : 'Seleccionar Archivo'}
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
                disabled={!selectedFile || isUploading || uploadStep === 'complete'}
                className="w-full"
                size="lg"
              >
                {isUploading ? 'Procesando...' : 
                 uploadStep === 'complete' ? 'Migración Completa' :
                 `Cargar ${selectedType === 'clientes' ? 'Clientes' : 'Pagos'}`}
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

                  {/* Mostrar errores detallados si existen */}
                  {uploadResult.erroresDetallados && uploadResult.erroresDetallados.length > 0 && (
                    <div className="mt-6">
                      <ErroresDetallados
                        errores={uploadResult.erroresDetallados}
                        tipo={uploadResult.data.type}
                        onDescargarErrores={() => {
                          // Generar archivo CSV con solo los errores
                          const erroresCSV = uploadResult.erroresDetallados!.map(error => [
                            error.row,
                            error.cedula,
                            error.error,
                            JSON.stringify(error.data)
                          ])
                          const csvContent = [
                            ['fila', 'cedula', 'error', 'datos'],
                            ...erroresCSV
                          ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
                          
                          const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
                          const link = document.createElement('a')
                          link.href = URL.createObjectURL(blob)
                          link.download = `errores_${uploadResult.data.type}_${new Date().toISOString().split('T')[0]}.csv`
                          link.click()
                        }}
                      />
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
