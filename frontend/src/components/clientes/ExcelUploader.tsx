import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload,
  FileSpreadsheet,
  X,
  CheckCircle,
  AlertTriangle,
  Eye,
  Save,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import * as XLSX from 'xlsx'

interface ExcelData {
  cedula: string
  nombres: string
  apellidos: string
  telefono: string
  email: string
  direccion: string
  fecha_nacimiento: string
  ocupacion: string
  modelo_vehiculo: string
  concesionario: string
  analista: string
  total_financiamiento: string
  cuota_inicial: string
  numero_amortizaciones: string
  modalidad_pago: string
  fecha_entrega: string
  estado: string
  activo: string
  notas: string
}

interface ValidationResult {
  isValid: boolean
  message?: string
}

interface ExcelRow extends ExcelData {
  _rowIndex: number
  _validation: { [key: string]: ValidationResult }
  _hasErrors: boolean
}

interface ExcelUploaderProps {
  onClose: () => void
  onDataProcessed?: (data: ExcelRow[]) => void
  onSuccess?: () => void
}

export function ExcelUploader({ onClose, onDataProcessed, onSuccess }: ExcelUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [excelData, setExcelData] = useState<ExcelRow[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)


  // 🔍 VALIDAR CAMPO INDIVIDUAL
  const validateField = async (field: string, value: string): Promise<ValidationResult> => {
    switch (field) {
      case 'cedula':
        if (!value.trim()) return { isValid: false, message: 'Cédula requerida' }
        const cedulaPattern = /^[VEJ]\d{7,10}$/
        if (!cedulaPattern.test(value.toUpperCase())) {
          return { isValid: false, message: 'Formato: V/E/J + 7-10 dígitos' }
        }
        return { isValid: true }

      case 'nombres':
        if (!value.trim()) return { isValid: false, message: 'Nombres requeridos' }
        if (value.trim().length < 2) return { isValid: false, message: 'Mínimo 2 caracteres' }
        return { isValid: true }

      case 'apellidos':
        if (!value.trim()) return { isValid: false, message: 'Apellidos requeridos' }
        if (value.trim().length < 2) return { isValid: false, message: 'Mínimo 2 caracteres' }
        return { isValid: true }

      case 'telefono':
        if (!value.trim()) return { isValid: false, message: 'Teléfono requerido' }
        const cleanPhone = value.replace(/\D/g, '')
        if (cleanPhone.length !== 10) return { isValid: false, message: 'Debe tener 10 dígitos' }
        return { isValid: true }

      case 'email':
        if (!value.trim()) return { isValid: false, message: 'Email requerido' }
        const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
        if (!emailPattern.test(value.toLowerCase())) {
          return { isValid: false, message: 'Formato de email inválido' }
        }
        return { isValid: true }

      case 'total_financiamiento':
        if (!value.trim()) return { isValid: false, message: 'Total requerido' }
        const total = parseFloat(value.replace(/[^\d.-]/g, ''))
        if (isNaN(total) || total <= 0) return { isValid: false, message: 'Debe ser un número positivo' }
        if (total < 1000 || total > 50000000) return { isValid: false, message: 'Entre $1,000 y $50,000,000' }
        return { isValid: true }

      case 'numero_amortizaciones':
        if (!value.trim()) return { isValid: false, message: 'Número requerido' }
        const amortizaciones = parseInt(value)
        if (isNaN(amortizaciones) || amortizaciones < 1 || amortizaciones > 60) {
          return { isValid: false, message: 'Entre 1 y 60 cuotas' }
        }
        return { isValid: true }

      case 'modalidad_pago':
        if (!value.trim()) return { isValid: false, message: 'Modalidad requerida' }
        const modalidades = ['SEMANAL', 'QUINCENAL', 'MENSUAL']
        if (!modalidades.includes(value.toUpperCase())) {
          return { isValid: false, message: 'Debe ser SEMANAL, QUINCENAL o MENSUAL' }
        }
        return { isValid: true }

      case 'fecha_entrega':
        if (!value.trim()) return { isValid: false, message: 'Fecha requerida' }
        const fecha = new Date(value)
        const hoy = new Date()
        hoy.setHours(0, 0, 0, 0)
        if (isNaN(fecha.getTime()) || fecha < hoy) {
          return { isValid: false, message: 'Debe ser una fecha futura válida' }
        }
        return { isValid: true }

      case 'estado':
        if (!value.trim()) return { isValid: false, message: 'Estado requerido' }
        const estados = ['ACTIVO', 'INACTIVO']
        if (!estados.includes(value.toUpperCase())) {
          return { isValid: false, message: 'Debe ser ACTIVO o INACTIVO' }
        }
        return { isValid: true }

      case 'activo':
        if (!value.trim()) return { isValid: false, message: 'Valor requerido' }
        const activos = ['true', 'false']
        if (!activos.includes(value.toLowerCase())) {
          return { isValid: false, message: 'Debe ser true o false' }
        }
        return { isValid: true }

      default:
        return { isValid: true }
    }
  }

  // 📊 PROCESAR ARCHIVO EXCEL
  const processExcelFile = async (file: File) => {
    setIsProcessing(true)
    try {
      console.log('📊 Procesando archivo Excel:', file.name)
      
      const data = await file.arrayBuffer()
      const workbook = XLSX.read(data, { type: 'array' })
      const sheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[sheetName]
      
      // Convertir a JSON
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })
      
      if (jsonData.length < 2) {
        throw new Error('El archivo debe tener al menos una fila de datos')
      }
      
      // Obtener encabezados (primera fila)
      const headers = jsonData[0] as string[]
      console.log('📋 Encabezados encontrados:', headers)
      
      // Procesar filas de datos
      const processedData: ExcelRow[] = []
      
      for (let i = 1; i < jsonData.length; i++) {
        const row = jsonData[i] as any[]
        if (!row || row.every(cell => !cell)) continue // Saltar filas vacías
        
        const rowData: ExcelRow = {
          _rowIndex: i + 1,
          _validation: {},
          _hasErrors: false,
          cedula: row[0]?.toString() || '',
          nombres: row[1]?.toString() || '',
          apellidos: row[2]?.toString() || '',
          telefono: row[3]?.toString() || '',
          email: row[4]?.toString() || '',
          direccion: row[5]?.toString() || '',
          fecha_nacimiento: row[6]?.toString() || '',
          ocupacion: row[7]?.toString() || '',
          modelo_vehiculo: row[8]?.toString() || '',
          concesionario: row[9]?.toString() || '',
          analista: row[10]?.toString() || '',
          total_financiamiento: row[11]?.toString() || '',
          cuota_inicial: row[12]?.toString() || '',
          numero_amortizaciones: row[13]?.toString() || '',
          modalidad_pago: row[14]?.toString() || '',
          fecha_entrega: row[15]?.toString() || '',
          estado: row[16]?.toString() || '',
          activo: row[17]?.toString() || '',
          notas: row[18]?.toString() || ''
        }
        
        // Validar campos requeridos
        const requiredFields = ['cedula', 'nombres', 'apellidos', 'telefono', 'email', 
                              'total_financiamiento', 'numero_amortizaciones', 'modalidad_pago', 
                              'fecha_entrega', 'estado', 'activo']
        
        let hasErrors = false
        for (const field of requiredFields) {
          const validation = await validateField(field, rowData[field as keyof ExcelData])
          rowData._validation[field] = validation
          if (!validation.isValid) hasErrors = true
        }
        
        rowData._hasErrors = hasErrors
        processedData.push(rowData)
      }
      
      console.log('✅ Datos procesados:', processedData.length, 'filas')
      setExcelData(processedData)
      setShowPreview(true)
      
    } catch (error) {
      console.error('❌ Error procesando Excel:', error)
      alert(`Error procesando el archivo: ${error instanceof Error ? error.message : 'Error desconocido'}`)
    } finally {
      setIsProcessing(false)
    }
  }

  // 🎯 MANEJAR DRAG & DROP
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    const excelFile = files.find(file => 
      file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    )
    
    if (excelFile) {
      setUploadedFile(excelFile)
      processExcelFile(excelFile)
    } else {
      alert('Por favor selecciona un archivo Excel (.xlsx o .xls)')
    }
  }

  // 📁 MANEJAR SELECCIÓN DE ARCHIVO
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
      processExcelFile(file)
    }
  }

  // 🔄 ACTUALIZAR VALOR EN PREVISUALIZACIÓN
  const updateCellValue = async (rowIndex: number, field: string, value: string) => {
    const newData = [...excelData]
    const row = newData[rowIndex]
    
    if (row) {
      row[field as keyof ExcelData] = value
      
      // Re-validar el campo
      const validation = await validateField(field, value)
      row._validation[field] = validation
      
      // Recalcular si tiene errores
      const hasErrors = Object.values(row._validation).some(v => !v.isValid)
      row._hasErrors = hasErrors
      
      setExcelData(newData)
    }
  }

  // 💾 GUARDAR DATOS VALIDADOS
  const handleSaveData = async () => {
    const validData = excelData.filter(row => !row._hasErrors)
    
    if (validData.length === 0) {
      alert('No hay datos válidos para guardar')
      return
    }
    
    console.log('💾 Guardando datos:', validData.length, 'clientes')
    onDataProcessed?.(validData)
    onSuccess?.()
    onClose()
  }

  const validRows = excelData.filter(row => !row._hasErrors).length
  const totalRows = excelData.length

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 text-white p-6 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileSpreadsheet className="h-6 w-6" />
              <h2 className="text-xl font-bold">CARGA MASIVA DE CLIENTES</h2>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                onClick={onClose}
                variant="ghost"
                size="sm"
                className="text-white hover:bg-white/20 p-2"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {!showPreview ? (
            /* ZONA DE SUBIDA */
            <Card>
              <CardContent className="pt-6">
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    isDragging 
                      ? 'border-green-500 bg-green-50' 
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-lg font-semibold mb-2">
                    {isDragging ? 'Suelta el archivo aquí' : 'Sube tu archivo Excel'}
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Arrastra y suelta tu archivo Excel o haz clic para seleccionar
                  </p>
                  
                  <Button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isProcessing}
                    className="mb-4"
                  >
                    <FileSpreadsheet className="mr-2 h-4 w-4" />
                    Seleccionar archivo
                  </Button>
                  
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  
                  {isProcessing && (
                    <div className="mt-4">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
                      <p className="text-sm text-gray-600 mt-2">Procesando archivo...</p>
                    </div>
                  )}
                  
                  {uploadedFile && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <FileSpreadsheet className="h-5 w-5 text-green-600" />
                        <span className="text-sm font-medium text-green-800">
                          {uploadedFile.name}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            /* PREVISUALIZACIÓN */
            <div className="space-y-4">
              {/* Estadísticas */}
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <Badge variant="outline" className="text-blue-700">
                        Total: {totalRows} filas
                      </Badge>
                      <Badge variant="outline" className="text-green-700">
                        Válidas: {validRows}
                      </Badge>
                      <Badge variant="outline" className="text-red-700">
                        Con errores: {totalRows - validRows}
                      </Badge>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        onClick={() => setShowPreview(false)}
                        variant="outline"
                        size="sm"
                      >
                        <X className="mr-2 h-4 w-4" />
                        Cambiar archivo
                      </Button>
                      <Button
                        onClick={handleSaveData}
                        disabled={validRows === 0}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <Save className="mr-2 h-4 w-4" />
                        Guardar ({validRows})
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Tabla de previsualización */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Eye className="mr-2 h-5 w-5" />
                    Previsualización de Datos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="border p-2 text-left text-xs font-medium text-gray-500">Fila</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500">Cédula</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500">Nombres</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500">Apellidos</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500">Teléfono</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500">Email</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500">Total Fin.</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500">Estado</th>
                        </tr>
                      </thead>
                      <tbody>
                        {excelData.map((row, index) => (
                          <tr key={index} className={row._hasErrors ? 'bg-red-50' : 'bg-green-50'}>
                            <td className="border p-2 text-xs">{row._rowIndex}</td>
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.cedula}
                                onChange={(e) => updateCellValue(index, 'cedula', e.target.value)}
                                className={`w-full text-xs p-1 border rounded ${
                                  row._validation.cedula?.isValid ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
                                }`}
                              />
                              {row._validation.cedula?.message && (
                                <p className="text-xs text-red-600 mt-1">{row._validation.cedula.message}</p>
                              )}
                            </td>
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.nombres}
                                onChange={(e) => updateCellValue(index, 'nombres', e.target.value)}
                                className={`w-full text-xs p-1 border rounded ${
                                  row._validation.nombres?.isValid ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
                                }`}
                              />
                            </td>
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.apellidos}
                                onChange={(e) => updateCellValue(index, 'apellidos', e.target.value)}
                                className={`w-full text-xs p-1 border rounded ${
                                  row._validation.apellidos?.isValid ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
                                }`}
                              />
                            </td>
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.telefono}
                                onChange={(e) => updateCellValue(index, 'telefono', e.target.value)}
                                className={`w-full text-xs p-1 border rounded ${
                                  row._validation.telefono?.isValid ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
                                }`}
                              />
                            </td>
                            <td className="border p-2">
                              <input
                                type="email"
                                value={row.email}
                                onChange={(e) => updateCellValue(index, 'email', e.target.value)}
                                className={`w-full text-xs p-1 border rounded ${
                                  row._validation.email?.isValid ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
                                }`}
                              />
                            </td>
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.total_financiamiento}
                                onChange={(e) => updateCellValue(index, 'total_financiamiento', e.target.value)}
                                className={`w-full text-xs p-1 border rounded ${
                                  row._validation.total_financiamiento?.isValid ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
                                }`}
                              />
                            </td>
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.estado}
                                onChange={(e) => updateCellValue(index, 'estado', e.target.value)}
                                className={`w-full text-xs p-1 border rounded ${
                                  row._validation.estado?.isValid ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
                                }`}
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}
