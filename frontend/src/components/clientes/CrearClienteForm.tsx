import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { logger } from '@/utils/logger'
import {
  User,
  CreditCard,
  Phone,
  Mail,
  DollarSign,
  Calendar,
  Users,
  Building,
  Save,
  X,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Download,
  FileSpreadsheet,
  MapPin,
  Briefcase,
  FileText,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { SearchableSelect } from '@/components/ui/searchable-select'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { clienteService } from '@/services/clienteService'
import { validadoresService } from '@/services/validadoresService'
import { ExcelUploader } from './ExcelUploader'

interface FormData {
  // Datos personales - OBLIGATORIOS
  cedula: string
  nombres: string  // ✅ UNIFICA nombres + apellidos (2-4 palabras)
  telefono: string
  email: string
  direccion: string
  fechaNacimiento: string
  ocupacion: string  // ✅ MÁXIMO 2 palabras
  
  // Estado - OBLIGATORIO
  estado: 'ACTIVO' | 'INACTIVO' | 'FINALIZADO'
  
  // Notas - OBLIGATORIO (default 'NA')
  notas: string
}

interface ValidationResult {
  field: string
  isValid: boolean
  message: string
}

interface CrearClienteFormProps {
  cliente?: any // Cliente existente para edición
  onClose: () => void
  onSuccess: () => void
  onClienteCreated?: () => void
}

export function CrearClienteForm({ cliente, onClose, onSuccess, onClienteCreated }: CrearClienteFormProps) {
  // ✅ Función para convertir DD/MM/YYYY a YYYY-MM-DD
  const convertirFechaAISO = (fechaDDMMYYYY: string): string => {
    // Si la fecha ya está en formato ISO (YYYY-MM-DD), devolverla tal cual
    if (fechaDDMMYYYY.match(/^\d{4}-\d{2}-\d{2}$/)) {
      return fechaDDMMYYYY
    }
    // Si está en formato DD/MM/YYYY, convertir
    const partes = fechaDDMMYYYY.split('/')
    if (partes.length === 3) {
      const [dia, mes, ano] = partes
      return `${ano}-${mes}-${dia}`
    }
    return fechaDDMMYYYY
  }

  // Función para convertir fecha de ISO a DD/MM/YYYY
  const convertirFechaDeISO = (fechaISO: string): string => {
    // Si ya está en formato DD/MM/YYYY, devolverla tal cual
    if (fechaISO.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
      return fechaISO
    }
    // Si está en formato ISO (YYYY-MM-DD), convertir
    if (fechaISO.match(/^\d{4}-\d{2}-\d{2}$/)) {
      const partes = fechaISO.split('-')
      if (partes.length === 3) {
        const [ano, mes, dia] = partes
        return `${dia}/${mes}/${ano}`
      }
    }
    return fechaISO
  }

  // ✅ Función para obtener fecha de hoy en formato DD/MM/YYYY
  const getTodayDate = () => {
    const today = new Date()
    const day = String(today.getDate()).padStart(2, '0')
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const year = today.getFullYear()
    return `${day}/${month}/${year}`
  }

  const [formData, setFormData] = useState<FormData>({
    cedula: '',
    nombres: '',  // ✅ UNIFICA nombres + apellidos
    telefono: '',
    email: '',
    direccion: '',
    fechaNacimiento: getTodayDate(), // ✅ Fecha por defecto: hoy
    ocupacion: '',
    estado: 'ACTIVO',
    notas: 'NA'  // ✅ Default 'NA'
  })

  const [validations, setValidations] = useState<ValidationResult[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showExcelUploader, setShowExcelUploader] = useState(false)
  
  // Pre-cargar datos del cliente si se está editando
  useEffect(() => {
    if (cliente) {
      console.log('📝 MOD訂 EDITAR - Cargando datos del cliente:', cliente)
      
      // Dividir nombres si vienen unificados de la BD
      let nombresValue = cliente.nombres || ''
      
      // Función local para convertir fecha
      const convertirFechaLocal = (fechaISO: string): string => {
        // Si ya está en formato DD/MM/YYYY, devolverla tal cual
        if (fechaISO.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
          return fechaISO
        }
        // Si está en formato ISO (YYYY-MM-DD), convertir
        if (fechaISO.match(/^\d{4}-\d{2}-\d{2}$/)) {
          const partes = fechaISO.split('-')
          if (partes.length === 3) {
            const [ano, mes, dia] = partes
            return `${dia}/${mes}/${ano}`
          }
        }
        return fechaISO
      }
      
      const newFormData = {
        cedula: cliente.cedula || '',
        nombres: nombresValue,  // ✅ nombres unificados
        telefono: cliente.telefono || '',
        email: cliente.email || '',
        direccion: cliente.direccion || '',
        fechaNacimiento: convertirFechaLocal(cliente.fecha_nacimiento || ''), // ✅ Convertir ISO a DD/MM/YYYY
        ocupacion: cliente.ocupacion || '',
        estado: cliente.estado || 'ACTIVO',
        notas: cliente.notas || 'NA'
      }
      
      console.log('📝 MOD訂 EDITAR - Datos formateados:', newFormData)
      
      setFormData(newFormData)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cliente])
  

  // ✅ Validaciones personalizadas para nombres y ocupacion
  const validateNombres = (nombres: string): ValidationResult => {
    if (!nombres || nombres.trim() === '') {
      return { field: 'nombres', isValid: false, message: 'Nombres y apellidos requeridos' }
    }
    
    const words = nombres.trim().split(/\s+/).filter(w => w.length > 0)
    
    if (words.length < 2) {
      return { field: 'nombres', isValid: false, message: 'Mínimo 2 palabras requeridas (nombre + apellido)' }
    }
    
    if (words.length > 4) {
      return { field: 'nombres', isValid: false, message: 'Máximo 4 palabras permitidas' }
    }
    
    // Validar que cada palabra tenga mínimo 2 caracteres
    const invalidWords = words.filter(w => w.length < 2)
    if (invalidWords.length > 0) {
      return { field: 'nombres', isValid: false, message: 'Cada palabra debe tener mínimo 2 caracteres' }
    }
    
    return { field: 'nombres', isValid: true, message: 'Nombres válidos' }
  }
  
  const validateOcupacion = (ocupacion: string): ValidationResult => {
    if (!ocupacion || ocupacion.trim() === '') {
      return { field: 'ocupacion', isValid: false, message: 'Ocupación requerida' }
    }
    
    // Validar longitud mínima
    if (ocupacion.trim().length < 2) {
      return { field: 'ocupacion', isValid: false, message: 'Mínimo 2 caracteres' }
    }
    
    const words = ocupacion.trim().split(/\s+/).filter(w => w.length > 0)
    
    if (words.length > 2) {
      return { field: 'ocupacion', isValid: false, message: 'Máximo 2 palabras permitidas en ocupación' }
    }
    
    return { field: 'ocupacion', isValid: true, message: 'Ocupación válida' }
  }
  
  const validateDireccion = (direccion: string): ValidationResult => {
    if (!direccion || direccion.trim() === '') {
      return { field: 'direccion', isValid: false, message: 'Dirección requerida' }
    }
    
    if (direccion.trim().length < 5) {
      return { field: 'direccion', isValid: false, message: 'La dirección debe tener mínimo 5 caracteres' }
    }
    
    return { field: 'direccion', isValid: true, message: 'Dirección válida' }
  }
  
  const validateFechaNacimiento = (fecha: string): ValidationResult => {
    if (!fecha || fecha.trim() === '') {
      return { field: 'fechaNacimiento', isValid: false, message: 'Fecha de nacimiento requerida' }
    }
    
    // Validar formato DD/MM/YYYY
    const fechaFormatRegex = /^(\d{2})\/(\d{2})\/(\d{4})$/
    if (!fechaFormatRegex.test(fecha.trim())) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Formato inválido. Use: DD/MM/YYYY' }
    }
    
    // Extraer día, mes y año
    const [, dia, mes, ano] = fecha.trim().match(fechaFormatRegex)!
    const diaNum = parseInt(dia, 10)
    const mesNum = parseInt(mes, 10)
    const anoNum = parseInt(ano, 10)
    
    // Validar rangos
    if (diaNum < 1 || diaNum > 31) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Día inválido (1-31)' }
    }
    if (mesNum < 1 || mesNum > 12) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Mes inválido (1-12)' }
    }
    if (anoNum < 1900 || anoNum > 2100) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Año inválido (1900-2100)' }
    }
    
    // Validar que la fecha sea válida (ej: no 31/02/2025)
    const fechaNac = new Date(anoNum, mesNum - 1, diaNum)
    if (fechaNac.getDate() !== diaNum || fechaNac.getMonth() !== mesNum - 1 || fechaNac.getFullYear() !== anoNum) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Fecha inválida (ej: 31/02 no existe)' }
    }
    
    // ✅ Validar que la fecha sea pasada (no futura ni hoy)
    const hoy = new Date()
    hoy.setHours(0, 0, 0, 0)
    if (fechaNac >= hoy) {
      return { field: 'fechaNacimiento', isValid: false, message: 'La fecha de nacimiento no puede ser futura o de hoy' }
    }
    
    // ✅ Validar que tenga al menos 18 años exactos
    const fecha18 = new Date(anoNum + 18, mesNum - 1, diaNum)
    if (fecha18 > hoy) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Debe tener al menos 18 años cumplidos' }
    }
    
    return { field: 'fechaNacimiento', isValid: true, message: 'Fecha válida' }
  }
  
  // ✅ Formato automático deshabilitado - respetar formato original del usuario
  const formatNombres = (text: string): string => {
    return text // Mantener formato original
  }
  
  const formatOcupacion = (text: string): string => {
    return text // Mantener formato original
  }
  
  // Validaciones usando el servicio de validadores del backend
  const validateField = async (field: string, value: string): Promise<ValidationResult> => {
    // Mapeo de campos del formulario a tipos de validadores del backend
    const campoMapper: Record<string, string> = {
      'cedula': 'cedula_venezuela',
      'nombres': 'nombre',  // ✅ Ahora unifica nombres + apellidos
      'telefono': 'telefono_venezuela',
      'email': 'email',
      'fechaNacimiento': 'fecha',
    }

    const tipoValidador = campoMapper[field]
    
    // Si no hay validador del backend para este campo, usar validación local simple
    if (!tipoValidador) {
      if (!value) {
        return { field, isValid: false, message: `${field} es obligatorio` }
      }
      return { field, isValid: true, message: '' }
    }

    // Validar con el backend
    try {
      const resultado = await validadoresService.validarCampo(tipoValidador, value, 'VENEZUELA')
      
      if (resultado.validacion.valido) {
        return { 
          field, 
          isValid: true, 
          message: resultado.validacion.mensaje || 'Campo válido' 
        }
      } else {
        // Incluir sugerencia en el mensaje de error
        const errorMsg = resultado.validacion.error || 'Campo inválido'
        const sugerencia = resultado.validacion.sugerencia || ''
        const mensajeCompleto = sugerencia ? `${errorMsg}. ${sugerencia}` : errorMsg
        
        return { 
          field, 
          isValid: false, 
          message: mensajeCompleto
        }
      }
    } catch (error) {
      // Si el servicio falla, usar validación básica como fallback
      if (!value) {
        return { field, isValid: false, message: `${field} es obligatorio` }
      }
      return { field, isValid: true, message: '' }
    }
  }

  const handleInputChange = async (field: keyof FormData, value: string) => {
    console.log(`🔧 Cambio en campo: ${field}, nuevo valor: ${value}`)
    console.log(`🔧 Modo edición: ${cliente ? 'SÍ' : 'NO'}`)
    
    let formattedValue = value
    
    // ✅ En modo edición, permitir reescribir sin validar
    if (cliente) {
      console.log('🔧 Modo edición - actualizando directamente sin validar')
      setFormData(prev => {
        const updated = { ...prev, [field]: formattedValue }
        console.log(`🔧 Estado actualizado para ${field}:`, updated)
        return updated
      })
      return
    }
    
    // ✅ Solo en modo creación: aplicar autoformato y validar
    if (field === 'nombres') {
      formattedValue = formatNombres(value)
    } else if (field === 'ocupacion') {
      formattedValue = formatOcupacion(value)
    }
    
    setFormData(prev => ({ ...prev, [field]: formattedValue }))
    
    // ✅ Validar con funciones personalizadas o backend según el campo
    let validation: ValidationResult
    
    if (field === 'nombres') {
      validation = validateNombres(formattedValue)
    } else if (field === 'ocupacion') {
      validation = validateOcupacion(formattedValue)
    } else if (field === 'direccion') {
      validation = validateDireccion(formattedValue)
    } else if (field === 'fechaNacimiento') {
      validation = validateFechaNacimiento(formattedValue)
    } else {
      validation = await validateField(field, formattedValue)
    }
    
    setValidations(prev => {
      const filtered = prev.filter(v => v.field !== field)
      return [...filtered, validation]
    })
  }

  const isFormValid = () => {
    // ✅ En modo edición, permitir guardar sin validar campos
    if (cliente) {
      return true
    }
    
    const requiredFields: (keyof FormData)[] = [
      'cedula', 'nombres', 'telefono', 'email', 
      'direccion', 'fechaNacimiento', 'ocupacion'
    ]
    
    // ✅ Solo en modo creación: validar nombres, ocupacion, direccion y fechaNacimiento con funciones personalizadas
    const nombresValidation = validateNombres(formData.nombres)
    const ocupacionValidation = validateOcupacion(formData.ocupacion)
    const direccionValidation = validateDireccion(formData.direccion)
    const fechaNacimientoValidation = validateFechaNacimiento(formData.fechaNacimiento)
    
    // Agregar validaciones personalizadas al estado
    const nombresValidationResult = validations.find(v => v.field === 'nombres')
    const ocupacionValidationResult = validations.find(v => v.field === 'ocupacion')
    const direccionValidationResult = validations.find(v => v.field === 'direccion')
    const fechaNacimientoValidationResult = validations.find(v => v.field === 'fechaNacimiento')
    
    if (!nombresValidationResult || nombresValidationResult.isValid !== nombresValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'nombres')
        return [...filtered, nombresValidation]
      })
    }
    
    if (!ocupacionValidationResult || ocupacionValidationResult.isValid !== ocupacionValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'ocupacion')
        return [...filtered, ocupacionValidation]
      })
    }
    
    if (!direccionValidationResult || direccionValidationResult.isValid !== direccionValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'direccion')
        return [...filtered, direccionValidation]
      })
    }
    
    if (!fechaNacimientoValidationResult || fechaNacimientoValidationResult.isValid !== fechaNacimientoValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'fechaNacimiento')
        return [...filtered, fechaNacimientoValidation]
      })
    }
    
    return requiredFields.every(field => {
      // Usar validaciones personalizadas para nombres, ocupacion, direccion y fechaNacimiento
      if (field === 'nombres') {
        return nombresValidation.isValid && formData[field]
      }
      if (field === 'ocupacion') {
        return ocupacionValidation.isValid && formData[field]
      }
      if (field === 'direccion') {
        return direccionValidation.isValid && formData[field]
      }
      if (field === 'fechaNacimiento') {
        return fechaNacimientoValidation.isValid && formData[field]
      }
      
      const validation = validations.find(v => v.field === field)
      return validation?.isValid && formData[field]
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // ✅ VALIDACIÓN: Asegurar que campos requeridos NO estén vacíos
    if (!formData.direccion || !formData.direccion.trim()) {
      alert('⚠️ ERROR: Debe completar el campo Dirección')
      return
    }
    if (!formData.fechaNacimiento || !formData.fechaNacimiento.trim()) {
      alert('⚠️ ERROR: Debe completar el campo Fecha de Nacimiento')
      return
    }
    if (!formData.ocupacion || !formData.ocupacion.trim()) {
      alert('⚠️ ERROR: Debe completar el campo Ocupación')
      return
    }
    
    if (!isFormValid()) {
      return
    }

    setIsSubmitting(true)
    
    try {
      const clienteData = {
        cedula: formData.cedula,
        nombres: formData.nombres,  // ✅ nombres unificados (nombres + apellidos)
        telefono: formData.telefono,
        email: formData.email,
        direccion: formData.direccion,
        fecha_nacimiento: convertirFechaAISO(formData.fechaNacimiento), // ✅ Convertir DD/MM/YYYY → YYYY-MM-DD
        ocupacion: formData.ocupacion,
        estado: formData.estado,
        notas: formData.notas || 'NA'
      }

      console.log('🔍 DEBUG - Datos a enviar al backend:', clienteData)

      if (cliente) {
        // Editar cliente existente
        console.log('✏️ Editando cliente existente:', cliente.id)
        await clienteService.updateCliente(cliente.id, clienteData)
        console.log('✅ Cliente actualizado exitosamente')
      } else {
        // Crear nuevo cliente
        console.log('➕ Creando nuevo cliente')
        await clienteService.createCliente(clienteData)
        console.log('✅ Cliente creado exitosamente')
      }
      onSuccess()
      onClienteCreated?.()
      onClose()
    } catch (error: any) {
      logger.error('Error creando cliente', {
        action: 'create_client_error',
        component: 'CrearClienteForm',
        error: error instanceof Error ? error.message : String(error),
        status: error?.response?.status,
        detail: error?.response?.data?.detail,
        message: error?.response?.data?.message
      })
      
      // Mostrar mensaje de error al usuario
      let errorMessage = 'Error al crear el cliente. Por favor, intente nuevamente.'
      
      if (error.response?.status === 400) {
        // Error de cliente duplicado (misma cédula y mismo nombre)
        errorMessage = error.response?.data?.detail || 'No se puede crear un cliente con la misma cédula y el mismo nombre. Ya existe un cliente con estos datos.'
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      }
      
      alert(`⚠️ ${errorMessage}`)
    } finally {
      // ✅ CORRECCIÓN: Siempre ejecutar setIsSubmitting(false) en finally
      // El manejo específico de duplicados ya se hizo en el catch block
      setIsSubmitting(false)
    }
  }


  const getFieldValidation = (field: string) => {
    // ✅ En modo edición, no mostrar mensajes de validación
    if (cliente) {
      return null
    }
    return validations.find(v => v.field === field)
  }

  if (showExcelUploader) {
    return (
      <ExcelUploader 
        onClose={() => {
          setShowExcelUploader(false)
          // Solo cerrar ExcelUploader, mantener CrearClienteForm abierto
        }}
        onSuccess={() => {
          setShowExcelUploader(false)
          // ✅ Solo cerrar ExcelUploader, NO cerrar formulario Nuevo Cliente
          // El usuario debe decidir qué hacer después
        }}
      />
    )
  }

  return (
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
        className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        <div className="sticky top-0 bg-white border-b p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {cliente ? 'Editar Cliente' : 'Nuevo Cliente'}
          </h2>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowExcelUploader(true)}
              className="flex items-center gap-2"
            >
              <FileSpreadsheet className="w-4 h-4" />
              Cargar Excel
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              className="flex items-center gap-2"
              title="Cerrar formulario"
            >
              <X className="w-4 h-4" />
              <span className="sr-only">Cerrar</span>
            </Button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Datos Personales */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Datos Personales
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Cédula <span className="text-red-500">*</span>
                  </label>
                <div className="relative">
                  <CreditCard className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.cedula}
                    onChange={(e) => handleInputChange('cedula', e.target.value)}
                    className={`pl-10 ${getFieldValidation('cedula')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="12345678"
                  />
                </div>
                {getFieldValidation('cedula') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('cedula')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('cedula')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('cedula')?.message}
                  </div>
                )}
                </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Nombres y Apellidos <span className="text-red-500">*</span> <span className="text-gray-500 text-xs">(2-4 palabras)</span>
                  </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.nombres}
                    onChange={(e) => handleInputChange('nombres', e.target.value)}
                    className={`pl-10 ${getFieldValidation('nombres')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="Ejemplo: Juan Carlos Pérez González"
                  />
                </div>
                {getFieldValidation('nombres') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('nombres')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('nombres')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('nombres')?.message}
                    </div>
                  )}
              </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Teléfono <span className="text-red-500">*</span>
                  </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                            <Input
                              type="tel"
                              value={formData.telefono}
                              onChange={(e) => handleInputChange('telefono', e.target.value)}
                              className={`pl-10 ${getFieldValidation('telefono')?.isValid === false ? 'border-red-500' : ''}`}
                              placeholder="+58 1234567890"
                            />
                </div>
                {getFieldValidation('telefono') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('telefono')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('telefono')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('telefono')?.message}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Email <span className="text-red-500">*</span>
                  </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    className={`pl-10 ${getFieldValidation('email')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="juan@email.com"
                  />
                </div>
                {getFieldValidation('email') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('email')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('email')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('email')?.message}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Fecha de Nacimiento <span className="text-red-500">*</span> <span className="text-gray-500 text-xs">(DD/MM/YYYY)</span>
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.fechaNacimiento}
                    onChange={(e) => handleInputChange('fechaNacimiento', e.target.value)}
                    placeholder="DD/MM/YYYY"
                    className={`pl-10 ${getFieldValidation('fechaNacimiento')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                  />
                </div>
                {getFieldValidation('fechaNacimiento') && getFieldValidation('fechaNacimiento')?.isValid === false && (
                  <div className="text-xs flex items-center gap-1 text-red-600 font-medium">
                    <XCircle className="w-3 h-3" />
                    <span className="font-semibold">{getFieldValidation('fechaNacimiento')?.message}</span>
                  </div>
                )}
                {getFieldValidation('fechaNacimiento')?.isValid && (
                  <div className="text-xs flex items-center gap-1 text-green-600">
                    <CheckCircle className="w-3 h-3" />
                    {getFieldValidation('fechaNacimiento')?.message}
                  </div>
                )}
              </div>

              <div className="space-y-2 md:col-span-2">
                <label className="text-sm font-medium text-gray-700">
                  Dirección <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 text-gray-400 w-4 h-4" />
                  <Textarea
                    value={formData.direccion}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleInputChange('direccion', e.target.value)}
                    className={`pl-10 ${getFieldValidation('direccion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                    placeholder="Dirección completa del cliente"
                    rows={2}
                  />
                </div>
                {getFieldValidation('direccion') && getFieldValidation('direccion')?.isValid === false && (
                  <div className="text-xs flex items-center gap-1 text-red-600 font-medium">
                    <XCircle className="w-3 h-3" />
                    <span className="font-semibold">{getFieldValidation('direccion')?.message}</span>
                  </div>
                )}
                {getFieldValidation('direccion')?.isValid && (
                  <div className="text-xs flex items-center gap-1 text-green-600">
                    <CheckCircle className="w-3 h-3" />
                    {getFieldValidation('direccion')?.message}
                  </div>
                )}
              </div>

              <div className="space-y-2 min-h-[80px]"> {/* ✅ Estabilizar altura del campo */}
                <label className="text-sm font-medium text-gray-700">
                  Ocupación <span className="text-red-500">*</span> <span className="text-gray-500 text-xs">(máximo 2 palabras)</span>
                </label>
                <div className="relative">
                  <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.ocupacion}
                    onChange={(e) => handleInputChange('ocupacion', e.target.value)}
                    className={`pl-10 w-full ${getFieldValidation('ocupacion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                    placeholder="Ejemplo: Ingeniero, Gerente General"
                  />
                </div>
                {getFieldValidation('ocupacion') && getFieldValidation('ocupacion')?.isValid === false && (
                  <div className="text-xs flex items-center gap-1 text-red-600 font-medium">
                    <XCircle className="w-3 h-3" />
                    <span className="font-semibold">{getFieldValidation('ocupacion')?.message}</span>
                  </div>
                )}
                {getFieldValidation('ocupacion')?.isValid && (
                  <div className="text-xs flex items-center gap-1 text-green-600">
                    <CheckCircle className="w-3 h-3" />
                    {getFieldValidation('ocupacion')?.message}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Estado y Notas */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Estado y Notas
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Estado <span className="text-red-500">*</span>
                  </label>
                <Select
                  value={formData.estado}
                  onValueChange={(value: 'ACTIVO' | 'INACTIVO' | 'FINALIZADO') => handleInputChange('estado', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar estado" />
                    </SelectTrigger>
                    <SelectContent>
                    <SelectItem value="ACTIVO">Activo</SelectItem>
                    <SelectItem value="INACTIVO">Inactivo</SelectItem>
                    <SelectItem value="FINALIZADO">Finalizado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Notas (Opcional)
                  </label>
                <Textarea
                  value={formData.notas}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleInputChange('notas', e.target.value)}
                  placeholder="Notas adicionales sobre el cliente"
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {/* Botones */}
          <div className="flex justify-end gap-4 pt-6 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={!isFormValid() || isSubmitting}
              className="flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {isSubmitting ? 'Guardando...' : 'Guardar Cliente'}
            </Button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}