import { useState, useRef, useEffect } from 'react'
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
import { SearchableSelect } from '@/components/ui/searchable-select'
import * as XLSX from 'xlsx'
import { concesionarioService, type Concesionario } from '@/services/concesionarioService'
import { analistaService, type Analista } from '@/services/analistaService'
import { modeloVehiculoService, type ModeloVehiculo } from '@/services/modeloVehiculoService'
import { clienteService } from '@/services/clienteService'

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
  const [isSaving, setIsSaving] = useState(false)
  const [showValidationModal, setShowValidationModal] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Estados para listas desplegables
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [analistas, setAnalistas] = useState<Analista[]>([])
  const [modelosVehiculos, setModelosVehiculos] = useState<ModeloVehiculo[]>([])

  // Estado para tracking de errores en dropdowns
  const [dropdownErrors, setDropdownErrors] = useState<{[key: string]: boolean}>({})

  // Cargar datos de configuración
  useEffect(() => {
    const cargarDatosConfiguracion = async () => {
      try {
        console.log('🔄 Cargando datos de configuración para ExcelUploader...')
        
        const [concesionariosData, analistasData, modelosData] = await Promise.all([
          concesionarioService.getConcesionarios(),
          analistaService.getAnalistas(),
          modeloVehiculoService.getModelosVehiculos()
        ])
        
        console.log('📊 Datos cargados para ExcelUploader:')
        console.log('  - Concesionarios:', concesionariosData.length)
        console.log('  - Analistas:', analistasData.length)
        console.log('  - Modelos:', modelosData.length)
        
        setConcesionarios(concesionariosData)
        setAnalistas(analistasData)
        setModelosVehiculos(modelosData)
        
        console.log('✅ Estados actualizados correctamente en ExcelUploader')
      } catch (error) {
        console.error('❌ Error cargando datos de configuración en ExcelUploader:', error)
      }
    }

    cargarDatosConfiguracion()
  }, [])

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
        const phonePattern = /^\+58[1-9]\d{9}$/
        if (!phonePattern.test(value)) {
          return { isValid: false, message: 'Formato: +58 + 10 dígitos (no puede empezar por 0)' }
        }
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
        if (total < 1 || total > 50000000) return { isValid: false, message: 'Entre $1 y $50,000,000' }
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
        const fechaEntrega = new Date(value)
        const hoyEntrega = new Date()
        hoyEntrega.setHours(0, 0, 0, 0)
        
        // Calcular límites: 2 años atrás y 4 años adelante
        const fechaLimiteAtras = new Date(hoyEntrega)
        fechaLimiteAtras.setFullYear(hoyEntrega.getFullYear() - 2)
        
        const fechaLimiteAdelante = new Date(hoyEntrega)
        fechaLimiteAdelante.setFullYear(hoyEntrega.getFullYear() + 4)
        
        if (isNaN(fechaEntrega.getTime())) {
          return { isValid: false, message: 'Formato de fecha inválido' }
        }
        
        if (fechaEntrega < fechaLimiteAtras) {
          return { isValid: false, message: 'La fecha no puede ser anterior a hace 2 años' }
        }
        
        if (fechaEntrega > fechaLimiteAdelante) {
          return { isValid: false, message: 'La fecha no puede ser posterior a 4 años en el futuro' }
        }
        
        return { isValid: true }

      case 'estado':
        if (!value.trim()) return { isValid: false, message: 'Estado requerido' }
        const estados = ['ACTIVO', 'INACTIVO', 'FINALIZADO']
        const estadoNormalizado = value.toUpperCase().trim()
        if (!estados.includes(estadoNormalizado)) {
          return { isValid: false, message: 'Debe ser ACTIVO, INACTIVO o FINALIZADO' }
        }
        return { isValid: true }

      case 'activo':
        if (!value.trim()) return { isValid: false, message: 'Valor requerido' }
        const activos = ['true', 'false']
        if (!activos.includes(value.toLowerCase())) {
          return { isValid: false, message: 'Debe ser true o false' }
        }
        return { isValid: true }

      case 'direccion':
        if (!value.trim()) return { isValid: false, message: 'Dirección requerida' }
        if (value.trim().length < 5) return { isValid: false, message: 'Mínimo 5 caracteres' }
        return { isValid: true }

      case 'fecha_nacimiento':
        if (!value.trim()) return { isValid: false, message: 'Fecha requerida' }
        const fechaNac = new Date(value)
        const hoyNac = new Date()
        if (isNaN(fechaNac.getTime())) {
          return { isValid: false, message: 'Formato de fecha inválido' }
        }
        if (fechaNac >= hoyNac) {
          return { isValid: false, message: 'Debe ser una fecha pasada' }
        }
        return { isValid: true }

      case 'ocupacion':
        if (!value.trim()) return { isValid: false, message: 'Ocupación requerida' }
        if (value.trim().length < 2) return { isValid: false, message: 'Mínimo 2 caracteres' }
        return { isValid: true }

      case 'modelo_vehiculo':
        if (!value.trim()) return { isValid: false, message: 'Modelo requerido' }
        return { isValid: true }

      case 'concesionario':
        if (!value.trim()) return { isValid: false, message: 'Concesionario requerido' }
        return { isValid: true }

      case 'analista':
        if (!value.trim()) return { isValid: false, message: 'Analista requerido' }
        return { isValid: true }

      case 'notas':
        // Notas es opcional, siempre válido
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
          activo: row[17]?.toString() || 'TRUE', // ✅ Por defecto siempre TRUE
          notas: row[18]?.toString() || ''
        }
        
        // Validar campos requeridos
        const requiredFields = ['cedula', 'nombres', 'apellidos', 'telefono', 'email', 
                              'direccion', 'fecha_nacimiento', 'ocupacion', 'modelo_vehiculo', 
                              'concesionario', 'analista', 'estado', 'activo']
        
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
      
      // Validar dropdowns después de procesar
      updateDropdownErrors(processedData)
      
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
      
      // Actualizar estado de errores en dropdowns
      updateDropdownErrors(newData)
    }
  }

  // 🎯 VALIDAR DROPDOWNS Y ACTUALIZAR ESTADO DE ERRORES
  const updateDropdownErrors = (data: ExcelRow[]) => {
    const errors: {[key: string]: boolean} = {}
    
    data.forEach((row, index) => {
      // Validar dropdowns específicos
      if (!row.concesionario || row.concesionario.trim() === '') {
        errors[`concesionario_${index}`] = true
      }
      if (!row.analista || row.analista.trim() === '') {
        errors[`analista_${index}`] = true
      }
      if (!row.modelo_vehiculo || row.modelo_vehiculo.trim() === '') {
        errors[`modelo_${index}`] = true
      }
    })
    
    setDropdownErrors(errors)
  }

  // 💾 GUARDAR DATOS VALIDADOS
  const handleSaveData = async () => {
    // Filtrar solo registros completamente válidos
    const validData = excelData.filter(row => {
      const hasNoErrors = !row._hasErrors
      const hasConcesionario = row.concesionario && row.concesionario.trim() !== ''
      const hasAnalista = row.analista && row.analista.trim() !== ''
      const hasModelo = row.modelo_vehiculo && row.modelo_vehiculo.trim() !== ''
      
      return hasNoErrors && hasConcesionario && hasAnalista && hasModelo
    })
    
    if (validData.length === 0) {
      setShowValidationModal(true) // Abre modal de advertencias
      return
    }
    
    setIsSaving(true)
    
    try {
      console.log('💾 Guardando datos:', validData.length, 'clientes')
      console.log('📋 Datos a guardar:', validData.map(row => ({
        fila: row._rowIndex,
        cedula: row.cedula,
        nombres: row.nombres,
        estado: row.estado,
        activo: row.activo,
        errores: row._hasErrors
      })))
      
      // Guardar cada cliente individualmente
      const resultados = []
      for (const row of validData) {
        try {
          const clienteData = {
            cedula: row.cedula,
            nombres: row.nombres,
            apellidos: row.apellidos,
            telefono: row.telefono,
            email: row.email,
            direccion: row.direccion,
            fecha_nacimiento: row.fecha_nacimiento,
            ocupacion: row.ocupacion,
            modelo_vehiculo: row.modelo_vehiculo,
            concesionario: row.concesionario,
            analista: row.analista,
            estado: row.estado.toUpperCase().trim(), // ✅ Normalizar estado
            activo: row.activo === 'true' || row.activo === 'TRUE' || row.activo === '1',
            notas: row.notas || 'NA'
          }
          
          console.log(`🔄 Procesando fila ${row._rowIndex}:`, clienteData)
          
          const clienteCreado = await clienteService.createCliente(clienteData)
          resultados.push({ success: true, cliente: clienteCreado, fila: row._rowIndex })
          console.log(`✅ Cliente creado exitosamente: ${clienteData.nombres} ${clienteData.apellidos}`)
          
        } catch (error) {
          console.error(`❌ Error creando cliente en fila ${row._rowIndex}:`, error)
          resultados.push({ 
            success: false, 
            error: error instanceof Error ? error.message : 'Error desconocido', 
            fila: row._rowIndex,
            cedula: row.cedula
          })
        }
      }
      
      // Mostrar resumen de resultados
      const exitosos = resultados.filter(r => r.success).length
      const fallidos = resultados.filter(r => !r.success).length
      
      console.log(`📊 Resumen: ${exitosos} exitosos, ${fallidos} fallidos`)
      
      if (exitosos > 0) {
        // Notificar éxito y cerrar
        onDataProcessed?.(validData)
        onSuccess?.()
        onClose()
      } else {
        alert('No se pudo guardar ningún cliente. Revisa los errores.')
      }
      
    } catch (error) {
      console.error('❌ Error en proceso de guardado:', error)
      alert('Error al guardar los datos. Intenta nuevamente.')
    } finally {
      setIsSaving(false)
    }
  }

  // 🎯 CONTAR REGISTROS VÁLIDOS (sin errores + dropdowns seleccionados)
  const validRows = excelData.filter(row => {
    const hasNoErrors = !row._hasErrors
    const hasConcesionario = row.concesionario && row.concesionario.trim() !== ''
    const hasAnalista = row.analista && row.analista.trim() !== ''
    const hasModelo = row.modelo_vehiculo && row.modelo_vehiculo.trim() !== ''
    
    return hasNoErrors && hasConcesionario && hasAnalista && hasModelo
  }).length
  
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
        className="bg-white rounded-lg shadow-xl max-w-[95vw] w-full max-h-[90vh] overflow-y-auto"
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
                        disabled={validRows === 0 || isSaving}
                        className="bg-green-600 hover:bg-green-700 disabled:opacity-50"
                      >
                        {isSaving ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                            Guardando...
                          </>
                        ) : (
                          <>
                            <Save className="mr-2 h-4 w-4" />
                            Guardar ({validRows})
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Modal de Advertencias de Validación */}
              <AnimatePresence>
                {showValidationModal && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                  >
                    <motion.div
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.9, opacity: 0 }}
                      className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-y-auto"
                    >
                      <div className="p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h2 className="text-2xl font-bold text-red-600 flex items-center">
                            <AlertTriangle className="mr-2 h-6 w-6" />
                            Errores de Validación Encontrados
                          </h2>
                          <Button variant="ghost" size="sm" onClick={() => setShowValidationModal(false)}>
                            <X className="h-4 w-4" />
                          </Button>
                        </div>

                        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                          <p className="text-sm text-red-700">
                            <strong>No se puede guardar:</strong> Se encontraron {totalRows - validRows} registros con errores que deben corregirse antes de continuar.
                          </p>
                          <p className="text-sm text-red-600 mt-1">
                            <strong>Errores incluyen:</strong> Campos de validación inválidos y/o dropdowns sin seleccionar (Concesionario, Analista, Modelo Vehículo).
                          </p>
                        </div>

                        <div className="space-y-4 max-h-[50vh] overflow-y-auto">
                          {excelData.filter(row => {
                            // Incluir filas con errores de validación O con dropdowns sin seleccionar
                            const hasValidationErrors = row._hasErrors
                            const hasDropdownErrors = !row.concesionario || !row.analista || !row.modelo_vehiculo ||
                              row.concesionario.trim() === '' || row.analista.trim() === '' || row.modelo_vehiculo.trim() === ''
                            
                            return hasValidationErrors || hasDropdownErrors
                          }).map((row, index) => (
                            <div key={index} className="border border-red-200 rounded-lg p-4 bg-red-50">
                              <div className="flex items-center justify-between mb-3">
                                <h3 className="font-semibold text-red-800">
                                  Fila {row._rowIndex}: {row.nombres} {row.apellidos}
                                </h3>
                                <Badge variant="outline" className="text-red-600 border-red-300">
                                  {Object.keys(row._validation).filter(field => !row._validation[field]?.isValid).length + 
                                   (dropdownErrors[`concesionario_${index}`] ? 1 : 0) +
                                   (dropdownErrors[`analista_${index}`] ? 1 : 0) +
                                   (dropdownErrors[`modelo_${index}`] ? 1 : 0)} errores
                                </Badge>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {Object.entries(row._validation).map(([field, validation]) => {
                                  if (validation?.isValid) return null;
                                  return (
                                    <div key={field} className="flex items-start space-x-2">
                                      <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                                      <div className="flex-1">
                                        <span className="text-sm font-medium text-gray-700 capitalize">{field}:</span>
                                        <div className="text-sm text-red-600 mt-1">{validation?.message}</div>
                                      </div>
                                    </div>
                                  );
                                })}
                                
                                {/* Mostrar errores de dropdowns */}
                                {dropdownErrors[`concesionario_${index}`] && (
                                  <div className="flex items-start space-x-2">
                                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                                    <div className="flex-1">
                                      <span className="text-sm font-medium text-gray-700">Concesionario:</span>
                                      <div className="text-sm text-red-600 mt-1">Debe seleccionar un concesionario</div>
                                    </div>
                                  </div>
                                )}
                                
                                {dropdownErrors[`analista_${index}`] && (
                                  <div className="flex items-start space-x-2">
                                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                                    <div className="flex-1">
                                      <span className="text-sm font-medium text-gray-700">Analista:</span>
                                      <div className="text-sm text-red-600 mt-1">Debe seleccionar un analista</div>
                                    </div>
                                  </div>
                                )}
                                
                                {dropdownErrors[`modelo_${index}`] && (
                                  <div className="flex items-start space-x-2">
                                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                                    <div className="flex-1">
                                      <span className="text-sm font-medium text-gray-700">Modelo Vehículo:</span>
                                      <div className="text-sm text-red-600 mt-1">Debe seleccionar un modelo de vehículo</div>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                          <div className="flex items-start space-x-2">
                            <AlertTriangle className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div className="text-sm text-blue-800">
                              <strong>Instrucciones para corregir:</strong>
                              <ul className="mt-2 ml-4 list-disc space-y-1">
                                <li>Los campos con fondo rojo en la tabla tienen errores de validación</li>
                                <li>Haz clic en cualquier campo para editarlo directamente</li>
                                <li>Los errores se corrigen automáticamente al escribir valores válidos</li>
                                <li>Una vez corregidos todos los errores, podrás guardar los datos</li>
                              </ul>
                            </div>
                          </div>
                        </div>

                        <div className="mt-6 flex justify-end space-x-3">
                          <Button variant="outline" onClick={() => setShowValidationModal(false)}>
                            Cerrar
                          </Button>
                          <Button 
                            onClick={() => {
                              setShowValidationModal(false);
                              // Scroll a la tabla para que el usuario corrija
                              const tableElement = document.querySelector('.overflow-x-auto');
                              if (tableElement) {
                                tableElement.scrollIntoView({ behavior: 'smooth' });
                              }
                            }} 
                            className="bg-blue-600 hover:bg-blue-700"
                          >
                            Ir a Corregir Errores
                          </Button>
                        </div>
                      </div>
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Tabla de previsualización */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Eye className="mr-2 h-5 w-5" />
                    Previsualización de Datos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto min-w-full relative" style={{ resize: 'both', minWidth: '800px', minHeight: '400px' }}>
                    <table className="w-full border-collapse min-w-[1400px]">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-16">Fila</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">Cédula</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-32">Nombres</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-32">Apellidos</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-28">Teléfono</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-40">Email</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-48">Dirección</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">Fecha Nac.</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-32">Ocupación</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-40">Modelo Veh.</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-40">Concesionario</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-32">Analista</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">Estado</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-20">Activo</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-48">Notas</th>
                        </tr>
                      </thead>
                      <tbody>
                        {excelData.map((row, index) => (
                          <tr key={index} className={row._hasErrors ? 'bg-red-50' : 'bg-green-50'}>
                            <td className="border p-2 text-xs">{row._rowIndex}</td>
                            
                            {/* Cédula */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.cedula}
                                onChange={(e) => updateCellValue(index, 'cedula', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.cedula?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Nombres */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.nombres}
                                onChange={(e) => updateCellValue(index, 'nombres', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.nombres?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Apellidos */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.apellidos}
                                onChange={(e) => updateCellValue(index, 'apellidos', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.apellidos?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Teléfono */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.telefono}
                                onChange={(e) => updateCellValue(index, 'telefono', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.telefono?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Email */}
                            <td className="border p-2">
                              <input
                                type="email"
                                value={row.email}
                                onChange={(e) => updateCellValue(index, 'email', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.email?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Dirección */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.direccion}
                                onChange={(e) => updateCellValue(index, 'direccion', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.direccion?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Fecha Nacimiento */}
                            <td className="border p-2">
                              <input
                                type="date"
                                value={row.fecha_nacimiento}
                                onChange={(e) => updateCellValue(index, 'fecha_nacimiento', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.fecha_nacimiento?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Ocupación */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.ocupacion}
                                onChange={(e) => updateCellValue(index, 'ocupacion', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.ocupacion?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Modelo Vehículo */}
                            <td className="border p-2">
                              <SearchableSelect
                                options={modelosVehiculos.map(modelo => ({
                                  value: modelo.modelo,
                                  label: modelo.modelo
                                }))}
                                value={row.modelo_vehiculo}
                                onChange={(value) => updateCellValue(index, 'modelo_vehiculo', value)}
                                placeholder="Seleccionar modelo..."
                                className={`w-full text-sm min-w-[120px] ${
                                  dropdownErrors[`modelo_${index}`] ? 'border-red-800 bg-red-800 text-white' : 'border-gray-300 bg-white text-black'
                                }`}
                              />
                            </td>
                            
                            {/* Concesionario */}
                            <td className="border p-2">
                              <SearchableSelect
                                options={concesionarios.map(concesionario => ({
                                  value: concesionario.nombre,
                                  label: concesionario.nombre
                                }))}
                                value={row.concesionario}
                                onChange={(value) => updateCellValue(index, 'concesionario', value)}
                                placeholder="Seleccionar concesionario..."
                                className={`w-full text-sm min-w-[120px] ${
                                  dropdownErrors[`concesionario_${index}`] ? 'border-red-800 bg-red-800 text-white' : 'border-gray-300 bg-white text-black'
                                }`}
                              />
                            </td>
                            
                            {/* Analista */}
                            <td className="border p-2">
                              <SearchableSelect
                                options={analistas.map(analista => ({
                                  value: analista.nombre,
                                  label: analista.nombre
                                }))}
                                value={row.analista}
                                onChange={(value) => updateCellValue(index, 'analista', value)}
                                placeholder="Seleccionar analista..."
                                className={`w-full text-sm min-w-[120px] ${
                                  dropdownErrors[`analista_${index}`] ? 'border-red-800 bg-red-800 text-white' : 'border-gray-300 bg-white text-black'
                                }`}
                              />
                            </td>
                            
                            {/* Estado */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.estado}
                                onChange={(e) => updateCellValue(index, 'estado', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.estado?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Activo */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.activo}
                                onChange={(e) => updateCellValue(index, 'activo', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.activo?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Notas */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.notas}
                                onChange={(e) => updateCellValue(index, 'notas', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.notas?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    
                    {/* Handle de redimensionamiento */}
                    <div className="absolute bottom-0 right-0 w-4 h-4 bg-gray-400 cursor-se-resize opacity-50 hover:opacity-100 transition-opacity">
                      <div className="w-full h-full bg-gradient-to-br from-transparent via-gray-600 to-gray-800"></div>
                    </div>
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
