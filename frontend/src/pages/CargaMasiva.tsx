import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { 
  Upload, 
  FileSpreadsheet, 
  Download, 
  AlertCircle, 
  CheckCircle, 
  X, 
  AlertTriangle,
  Users,
  CreditCard,
  Edit3,
  Save,
  RefreshCw
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { cargaMasivaService } from '@/services/cargaMasivaService'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface UploadResult {
  success: boolean
  message: string
  data?: {
    totalRecords: number
    processedRecords: number
    errors: number
    fileName: string
    type: 'clientes' | 'pagos'
    erroresDetallados?: Array<{
      row: number
      cedula: string
      error: string
      data: any
      tipo: 'cliente' | 'pago'
    }>
  }
  errors?: string[]
}

interface ErrorRow {
  id: string
  row: number
  cedula: string
  error: string
  data: any
  tipo: 'cliente' | 'pago'
  isEditing?: boolean
  editedData?: any
}

export function CargaMasiva() {
  // Estados principales
  const [selectedFlow, setSelectedFlow] = useState<'clientes' | 'pagos'>('clientes')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [showErrorEditor, setShowErrorEditor] = useState(false)
  const [errorRows, setErrorRows] = useState<ErrorRow[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // Query client para invalidar cache
  const queryClient = useQueryClient()

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
      setShowErrorEditor(false)
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

      // Llamada real a la API
      const response = await cargaMasivaService.cargarArchivo({
        file: selectedFile,
        type: selectedFlow
      })

      clearInterval(progressInterval)
      setUploadProgress(100)

      // Procesar respuesta real
      setUploadResult({
        success: response.success,
        message: response.message,
        data: response.data ? {
          totalRecords: response.data.totalRecords,
          processedRecords: response.data.processedRecords,
          errors: response.data.errors,
          fileName: response.data.fileName,
          type: response.data.type as 'clientes' | 'pagos',
          erroresDetallados: response.erroresDetallados
        } : undefined,
        errors: response.errors
      })

      // Invalidar cache de clientes si la carga fue exitosa
      if (response.success && selectedFlow === 'clientes') {
        // Invalidar todas las queries relacionadas con clientes
        queryClient.invalidateQueries({ queryKey: ['clientes'] })
        queryClient.invalidateQueries({ queryKey: ['clientes-temp'] })
        
        // Mostrar notificación de éxito
        toast.success(`✅ ${response.data?.processedRecords || 0} clientes cargados exitosamente`)
        
        // Notificar que los datos se actualizarán en el módulo de clientes
        toast.success('📋 Los datos se reflejarán automáticamente en el módulo de clientes')
      } else if (response.success && selectedFlow === 'pagos') {
        // Invalidar queries de pagos y dashboard
        queryClient.invalidateQueries({ queryKey: ['pagos'] })
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
        
        // Mostrar notificación de éxito
        toast.success(`✅ ${response.data?.processedRecords || 0} pagos cargados exitosamente`)
        
        // Notificar que los datos se actualizarán en el dashboard
        toast.success('📊 Los datos se reflejarán automáticamente en el dashboard')
      }

      // Preparar errores para edición si existen
      if (response.erroresDetallados && response.erroresDetallados.length > 0) {
        const errors: ErrorRow[] = response.erroresDetallados.map((error: any, index: number) => ({
          id: `error-${index}`,
          row: error.row,
          cedula: error.cedula,
          error: error.error,
          data: error.data,
          tipo: error.tipo,
          isEditing: false,
          editedData: { ...error.data }
        }))
        setErrorRows(errors)
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

    if (selectedFlow === 'clientes') {
      templateData = [
        ['cedula', 'nombre', 'apellido', 'telefono', 'email', 'direccion'],
        ['V31566283', 'AARON ALEJANDRO', 'CRESPO ALVAREZ', '+5804127166660', 'aaroncrespo@gmail.com', 'Caracas, Venezuela'],
        ['V14929151', 'AARON DANIEL', 'PALENCIA GUZMAN', '+5804247505679', 'AARONWA7@GMAIL.COM', 'Valencia, Venezuela']
      ]
      filename = 'template_clientes_rapicredit.csv'
    } else {
      templateData = [
        ['cedula', 'fecha_pago', 'monto_pagado', 'numero_cuota', 'documento_pago', 'metodo_pago'],
        ['V22283249', '06/12/2024', '108.50', '1', '740087437485285', 'Transferencia'],
        ['V31566283', '07/12/2024', '250.00', '2', '740087437485286', 'Efectivo']
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

  const handleEditError = (errorId: string) => {
    setErrorRows(prev => prev.map(error => 
      error.id === errorId 
        ? { ...error, isEditing: !error.isEditing }
        : error
    ))
  }

  const handleSaveError = async (errorId: string) => {
    const errorToSave = errorRows.find(error => error.id === errorId)
    if (!errorToSave) return

    try {
      // Aquí iría la llamada a la API para guardar el error corregido
      await cargaMasivaService.corregirError({
        tipo: errorToSave.tipo,
        cedula: errorToSave.cedula,
        data: errorToSave.editedData
      })

      // Remover el error de la lista después de guardarlo exitosamente
      setErrorRows(prev => prev.filter(error => error.id !== errorId))
      
      // Actualizar estadísticas
      if (uploadResult?.data) {
        setUploadResult(prev => prev ? {
          ...prev,
          data: {
            ...prev.data!,
            errors: prev.data!.errors - 1,
            processedRecords: prev.data!.processedRecords + 1
          }
        } : null)
      }

      // Invalidar cache después de corregir error
      if (errorToSave.tipo === 'cliente') {
        queryClient.invalidateQueries({ queryKey: ['clientes'] })
        queryClient.invalidateQueries({ queryKey: ['clientes-temp'] })
        toast.success('✅ Cliente corregido y actualizado en el módulo de clientes')
      } else if (errorToSave.tipo === 'pago') {
        queryClient.invalidateQueries({ queryKey: ['pagos'] })
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
        toast.success('✅ Pago corregido y actualizado en el dashboard')
      }

    } catch (error) {
      console.error('Error al guardar corrección:', error)
      toast.error('❌ Error al corregir el registro')
    }
  }

  const handleUpdateErrorData = (errorId: string, field: string, value: string) => {
    setErrorRows(prev => prev.map(error => 
      error.id === errorId 
        ? { 
            ...error, 
            editedData: { 
              ...error.editedData, 
              [field]: value 
            } 
          }
        : error
    ))
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header con selector de flujo */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Carga Masiva</h1>
          <p className="text-gray-600 mt-2">
            Importa tus datos de clientes y pagos desde Excel al sistema RAPICREDIT
          </p>
        </div>
        <div className="flex space-x-2">
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

      {/* Selector de flujo */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Upload className="h-5 w-5" />
              <span>Seleccionar Tipo de Carga</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Button
                variant={selectedFlow === 'clientes' ? 'default' : 'outline'}
                className={`h-20 flex flex-col items-center justify-center space-y-2 ${
                  selectedFlow === 'clientes' ? 'bg-blue-600 hover:bg-blue-700' : ''
                }`}
                onClick={() => {
                  setSelectedFlow('clientes')
                  setUploadResult(null)
                  setSelectedFile(null)
                  setShowErrorEditor(false)
                }}
              >
                <Users className="h-8 w-8" />
                <span className="font-semibold">Cargar Clientes</span>
                <span className="text-sm opacity-80">Importar datos de clientes</span>
              </Button>

              <Button
                variant={selectedFlow === 'pagos' ? 'default' : 'outline'}
                className={`h-20 flex flex-col items-center justify-center space-y-2 ${
                  selectedFlow === 'pagos' ? 'bg-green-600 hover:bg-green-700' : ''
                }`}
                onClick={() => {
                  setSelectedFlow('pagos')
                  setUploadResult(null)
                  setSelectedFile(null)
                  setShowErrorEditor(false)
                }}
              >
                <CreditCard className="h-8 w-8" />
                <span className="font-semibold">Cargar Pagos</span>
                <span className="text-sm opacity-80">Importar datos de pagos</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel de Carga */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Upload className="h-5 w-5" />
                <span>
                  Cargar Archivo de {selectedFlow === 'clientes' ? 'Clientes' : 'Pagos'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                <FileSpreadsheet className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">
                  {selectedFlow === 'clientes' ? 
                    'Arrastra tu archivo de CLIENTES aquí (con columnas: cedula, nombre, apellido, telefono, email)' :
                    'Arrastra tu archivo de PAGOS aquí (con columnas: cedula, fecha_pago, monto_pagado, documento_pago)'
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
                {isUploading ? 'Procesando...' : 
                 `Cargar ${selectedFlow === 'clientes' ? 'Clientes' : 'Pagos'}`}
              </Button>
            </CardContent>
          </Card>
        </motion.div>

        {/* Panel de Resultados */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5" />
                <span>Dashboard de Resultados</span>
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
                    <div className="space-y-4">
                      {/* Estadísticas generales */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="bg-gradient-to-r from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-green-700">Total Registros</p>
                              <p className="text-3xl font-bold text-green-900 mt-1">
                                {uploadResult.data.totalRecords}
                              </p>
                            </div>
                            <div className="bg-green-500 rounded-full p-2">
                              <CheckCircle className="h-6 w-6 text-white" />
                            </div>
                          </div>
                        </div>
                        
                        <div className="bg-gradient-to-r from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-blue-700">Procesados</p>
                              <p className="text-3xl font-bold text-blue-900 mt-1">
                                {uploadResult.data.processedRecords}
                              </p>
                            </div>
                            <div className="bg-blue-500 rounded-full p-2">
                              <CheckCircle className="h-6 w-6 text-white" />
                            </div>
                          </div>
                        </div>
                        
                        <div className="bg-gradient-to-r from-red-50 to-red-100 p-4 rounded-lg border border-red-200">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-red-700">Con Errores</p>
                              <p className="text-3xl font-bold text-red-900 mt-1">
                                {uploadResult.data.errors}
                              </p>
                            </div>
                            <div className="bg-red-500 rounded-full p-2">
                              <AlertTriangle className="h-6 w-6 text-white" />
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Indicativo de errores */}
                      {uploadResult.data.errors > 0 && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <AlertTriangle className="h-6 w-6 text-red-600" />
                              <div>
                                <p className="font-medium text-red-900">
                                  {uploadResult.data.errors} errores encontrados
                                </p>
                                <p className="text-sm text-red-700">
                                  Revisa y corrige los errores de validación
                                </p>
                              </div>
                            </div>
                            <Button
                              onClick={() => setShowErrorEditor(!showErrorEditor)}
                              variant="outline"
                              className="border-red-300 text-red-700 hover:bg-red-50"
                            >
                              <Edit3 className="h-4 w-4 mr-2" />
                              {showErrorEditor ? 'Cerrar' : 'Abrir'}
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Información del archivo */}
                      <div className="bg-gradient-to-r from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <FileSpreadsheet className="h-5 w-5 text-purple-600" />
                            <div>
                              <p className="text-sm font-medium text-purple-700">Archivo Procesado</p>
                              <p className="text-lg font-semibold text-purple-900">
                                {uploadResult.data.fileName}
                              </p>
                            </div>
                          </div>
                          <Button
                            onClick={() => {
                              if (selectedFlow === 'clientes') {
                                queryClient.invalidateQueries({ queryKey: ['clientes'] })
                                queryClient.invalidateQueries({ queryKey: ['clientes-temp'] })
                                toast.success('🔄 Módulo de clientes actualizado')
                              } else {
                                queryClient.invalidateQueries({ queryKey: ['pagos'] })
                                queryClient.invalidateQueries({ queryKey: ['dashboard'] })
                                toast.success('🔄 Dashboard actualizado')
                              }
                            }}
                            variant="outline"
                            size="sm"
                            className="border-purple-300 text-purple-700 hover:bg-purple-50"
                          >
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Actualizar
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Editor de errores */}
                  {showErrorEditor && errorRows.length > 0 && (
                    <div className="mt-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold text-gray-900">Corrección de Errores</h4>
                        <Badge variant="destructive">
                          {errorRows.length} errores pendientes
                        </Badge>
                      </div>
                      
                      <div className="max-h-96 overflow-y-auto border border-gray-200 rounded-lg">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50 sticky top-0">
                            <tr>
                              <th className="px-3 py-2 text-left">Fila</th>
                              <th className="px-3 py-2 text-left">Cédula</th>
                              <th className="px-3 py-2 text-left">Error</th>
                              <th className="px-3 py-2 text-left">Datos</th>
                              <th className="px-3 py-2 text-left">Acciones</th>
                            </tr>
                          </thead>
                          <tbody>
                            {errorRows.map((error) => (
                              <tr key={error.id} className="border-b border-gray-100">
                                <td className="px-3 py-2">{error.row}</td>
                                <td className="px-3 py-2 font-mono text-xs">{error.cedula}</td>
                                <td className="px-3 py-2 text-red-600">{error.error}</td>
                                <td className="px-3 py-2">
                                  {error.isEditing ? (
                                    <div className="space-y-1">
                                      {Object.entries(error.editedData || {}).map(([key, value]) => (
                                        <input
                                          key={key}
                                          type="text"
                                          value={value as string}
                                          onChange={(e) => handleUpdateErrorData(error.id, key, e.target.value)}
                                          className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                                          placeholder={key}
                                        />
                                      ))}
                                    </div>
                                  ) : (
                                    <div className="text-xs text-gray-600">
                                      {Object.entries(error.data).map(([key, value]) => (
                                        <div key={key}>
                                          <span className="font-medium">{key}:</span> {value as string}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </td>
                                <td className="px-3 py-2">
                                  <div className="flex space-x-1">
                                    {error.isEditing ? (
                                      <Button
                                        size="sm"
                                        onClick={() => handleSaveError(error.id)}
                                        className="h-6 px-2 text-xs"
                                      >
                                        <Save className="h-3 w-3 mr-1" />
                                        Guardar
                                      </Button>
                                    ) : (
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleEditError(error.id)}
                                        className="h-6 px-2 text-xs"
                                      >
                                        <Edit3 className="h-3 w-3 mr-1" />
                                        Editar
                                      </Button>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
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
        transition={{ delay: 0.4 }}
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
                <h4 className="font-semibold text-gray-800 mb-3">
                  Columnas Requeridas - {selectedFlow === 'clientes' ? 'Clientes' : 'Pagos'}:
                </h4>
                <ul className="space-y-2 text-sm text-gray-600">
                  {selectedFlow === 'clientes' ? (
                    <>
                      <li>• <strong>cedula:</strong> Cédula venezolana (V/E/J + 7-10 dígitos)</li>
                      <li>• <strong>nombre:</strong> Nombre del cliente</li>
                      <li>• <strong>apellido:</strong> Apellido del cliente</li>
                      <li>• <strong>telefono:</strong> Teléfono (+58 + 10 dígitos)</li>
                      <li>• <strong>email:</strong> Correo electrónico válido</li>
                      <li>• <strong>direccion:</strong> Dirección del cliente</li>
                    </>
                  ) : (
                    <>
                      <li>• <strong>cedula:</strong> Cédula del cliente</li>
                      <li>• <strong>fecha_pago:</strong> Fecha de pago (dd/mm/yyyy)</li>
                      <li>• <strong>monto_pagado:</strong> Monto pagado</li>
                      <li>• <strong>numero_cuota:</strong> Número de cuota</li>
                      <li>• <strong>documento_pago:</strong> Número de documento</li>
                      <li>• <strong>metodo_pago:</strong> Método de pago</li>
                    </>
                  )}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}