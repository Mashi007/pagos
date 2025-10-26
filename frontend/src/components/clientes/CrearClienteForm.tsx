import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { logger } from '@/utils/logger'
import {
  User,
  CreditCard,
  Phone,
  Mail,
  Car,
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
import { concesionarioService, type Concesionario } from '@/services/concesionarioService'
import { analistaService, type Analista } from '@/services/analistaService'
import { modeloVehiculoService, type ModeloVehiculo } from '@/services/modeloVehiculoService'
import { clienteService } from '@/services/clienteService'
import { validadoresService } from '@/services/validadoresService'
import { ExcelUploader } from './ExcelUploader'
import { ConfirmacionDuplicadoModal } from './ConfirmacionDuplicadoModal'

interface FormData {
  // Datos personales - OBLIGATORIOS
  cedula: string
  nombres: string
  apellidos: string
  telefono: string
  email: string
  direccion: string
  fechaNacimiento: string
  ocupacion: string
  
  // Datos del vehículo - OBLIGATORIOS
  modeloVehiculo: string
  concesionario: string
  analista: string
  
  // Estado - OBLIGATORIO
  estado: 'ACTIVO' | 'INACTIVO' | 'FINALIZADO'
  
  // Notas - OPCIONAL
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
  // ✅ Función para obtener fecha de hoy en formato YYYY-MM-DD
  const getTodayDate = () => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  }

  const [formData, setFormData] = useState<FormData>({
    cedula: '',
    nombres: '',
    apellidos: '',
    telefono: '',
    email: '',
    direccion: '',
    fechaNacimiento: getTodayDate(), // ✅ Fecha por defecto: hoy
    ocupacion: '',
    modeloVehiculo: '',
    concesionario: '',
    analista: '',
    estado: 'ACTIVO',
    notas: ''
  })

  const [validations, setValidations] = useState<ValidationResult[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showExcelUploader, setShowExcelUploader] = useState(false)
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false)
  const [duplicateCedula, setDuplicateCedula] = useState('')
  const [clienteExistente, setClienteExistente] = useState<any>(null)
  
  // DEBUG: Log de cambios de estado
  useEffect(() => {
    // Debug logs removidos según normas
  }, [showDuplicateWarning])
  
  useEffect(() => {
    // Debug logs removidos según normas
  }, [duplicateCedula])
  
  // Pre-cargar datos del cliente si se está editando
  useEffect(() => {
    if (cliente) {
      // Debug logs removidos según normas
      setFormData({
        cedula: cliente.cedula || '',
        nombres: cliente.nombres || '',
        apellidos: cliente.apellidos || '',
        telefono: cliente.telefono || '',
        email: cliente.email || '',
        direccion: cliente.direccion || '',
        fechaNacimiento: cliente.fecha_nacimiento || '',
        ocupacion: cliente.ocupacion || '',
        modeloVehiculo: cliente.modelo_vehiculo || '',
        concesionario: cliente.concesionario || '',
        analista: cliente.analista || '',
        estado: cliente.estado || 'ACTIVO',
        notas: cliente.notas || ''
      })
    }
  }, [cliente])
  
  // Datos de configuración
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [analistas, setAnalistas] = useState<Analista[]>([])
  const [modelosVehiculos, setModelosVehiculos] = useState<ModeloVehiculo[]>([])

  // Cargar datos de configuración
  useEffect(() => {
    const cargarDatosConfiguracion = async () => {
      try {
        logger.info('Cargando datos de configuración', {
          action: 'load_config_data',
          component: 'CrearClienteForm'
        })
        
        const [concesionariosData, analistasData, modelosData] = await Promise.all([
          concesionarioService.getConcesionarios(),
          analistaService.getAnalistas(),
          modeloVehiculoService.getModelosVehiculos()
        ])
        
        logger.info('Datos de configuración cargados exitosamente', {
          action: 'config_data_loaded',
          component: 'CrearClienteForm',
          concesionarios: concesionariosData.length,
          analistas: analistasData.length,
          modelos: modelosData.length
        })
        
        setConcesionarios(concesionariosData)
        setAnalistas(analistasData)
        setModelosVehiculos(modelosData)
        
        logger.info('Estados actualizados correctamente', {
          action: 'states_updated',
          component: 'CrearClienteForm'
        })
      } catch (error) {
        logger.error('Error cargando datos de configuración', {
          action: 'load_config_error',
          component: 'CrearClienteForm',
          error: error instanceof Error ? error.message : String(error)
        })
      }
    }

    cargarDatosConfiguracion()
  }, [])

  // Validaciones usando el servicio de validadores del backend
  const validateField = async (field: string, value: string): Promise<ValidationResult> => {
    // Mapeo de campos del formulario a tipos de validadores del backend
    const campoMapper: Record<string, string> = {
      'cedula': 'cedula_venezuela',
      'nombres': 'nombre',
      'apellidos': 'apellido',
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
        return { 
          field, 
          isValid: false, 
          message: resultado.validacion.error || 'Campo inválido' 
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
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Validar campo en tiempo real usando el servicio del backend
    const validation = await validateField(field, value)
    setValidations(prev => {
      const filtered = prev.filter(v => v.field !== field)
      return [...filtered, validation]
    })
  }

  const isFormValid = () => {
    const requiredFields: (keyof FormData)[] = [
      'cedula', 'nombres', 'apellidos', 'telefono', 'email', 
      'direccion', 'fechaNacimiento', 'ocupacion', 'modeloVehiculo', 
      'concesionario', 'analista'
    ]
    
    return requiredFields.every(field => {
      const validation = validations.find(v => v.field === field)
      return validation?.isValid && formData[field]
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!isFormValid()) {
      return
    }

    setIsSubmitting(true)
    
    try {
      const clienteData = {
        cedula: formData.cedula,
        nombres: formData.nombres,
        apellidos: formData.apellidos,
        telefono: formData.telefono,
        email: formData.email,
        direccion: formData.direccion,
        fecha_nacimiento: formData.fechaNacimiento,
        ocupacion: formData.ocupacion,
        modelo_vehiculo: formData.modeloVehiculo,
        concesionario: formData.concesionario,
        analista: formData.analista,
        estado: formData.estado,
        notas: formData.notas || 'NA'
      }

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
      
      // Verificar si es error de cédula duplicada (CORREGIDO: ahora es 409)
      if (error.response?.status === 409 && 
          error.response?.data?.detail?.error === 'CLIENTE_DUPLICADO') {
        
        console.log('✅ DEBUG - Activando popup de duplicados (status 409)')
        console.log('✅ DEBUG - Datos del cliente existente:', error.response?.data?.detail?.cliente_existente)
        
        // Mostrar popup de advertencia con datos del cliente existente
        setDuplicateCedula(formData.cedula)
        setClienteExistente(error.response?.data?.detail?.cliente_existente)
        setShowDuplicateWarning(true)
        setIsSubmitting(false) // ✅ CORRECCIÓN: Mover aquí antes del return
        return // ✅ CORRECCIÓN CRÍTICA: Prevenir propagación de la promesa rechazada
      }
      
      // Fallback para el formato anterior (503) por compatibilidad
      if (error.response?.status === 503 && 
          typeof error.response?.data?.detail === 'string' &&
          (error.response?.data?.detail?.includes('duplicate key') ||
           error.response?.data?.detail?.includes('already exists') ||
           error.response?.data?.message?.includes('duplicate key') ||
           error.response?.data?.message?.includes('already exists'))) {
        
        console.log('✅ DEBUG - Activando popup de duplicados (fallback 503)')
        setDuplicateCedula(formData.cedula)
        setShowDuplicateWarning(true)
        setIsSubmitting(false)
        return // ✅ CORRECCIÓN CRÍTICA: Prevenir propagación de la promesa rechazada
      }
      
      console.log('❌ DEBUG - Error no es de duplicado, status:', error.response?.status)
      
      // Otros errores
      console.error('Error no manejado:', error)
    } finally {
      // ✅ CORRECCIÓN: Siempre ejecutar setIsSubmitting(false) en finally
      // El manejo específico de duplicados ya se hizo en el catch block
      setIsSubmitting(false)
    }
  }

  const handleConfirmDuplicate = async (comentarios: string) => {
    setIsSubmitting(true)
    setShowDuplicateWarning(false)
    
    try {
      const clienteData = {
        cedula: formData.cedula,
        nombres: formData.nombres,
        apellidos: formData.apellidos,
        telefono: formData.telefono,
        email: formData.email,
        direccion: formData.direccion,
        fecha_nacimiento: formData.fechaNacimiento,
        ocupacion: formData.ocupacion,
        modelo_vehiculo: formData.modeloVehiculo,
        concesionario: formData.concesionario,
        analista: formData.analista,
        estado: formData.estado,
        notas: formData.notas || 'NA'
      }

      console.log('➕ Creando cliente con cédula duplicada (confirmado por usuario)')
      await clienteService.createClienteWithConfirmation(
        clienteData, 
        comentarios || `Usuario confirmó crear cliente con cédula duplicada: ${formData.cedula}`
      )
      console.log('✅ Cliente creado exitosamente (duplicado permitido)')
      
      onSuccess()
      onClienteCreated?.()
      onClose()
    } catch (error) {
      console.error('Error creando cliente duplicado:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const getFieldValidation = (field: string) => {
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
          // Cerrar el formulario Nuevo Cliente al guardar exitosamente
          onClose()
          onSuccess()
          onClienteCreated?.()
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
                  Nombres <span className="text-red-500">*</span>
                  </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.nombres}
                    onChange={(e) => handleInputChange('nombres', e.target.value)}
                    className={`pl-10 ${getFieldValidation('nombres')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="Juan Carlos"
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
                  Apellidos <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.apellidos}
                    onChange={(e) => handleInputChange('apellidos', e.target.value)}
                    className={`pl-10 ${getFieldValidation('apellidos')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="Pérez González"
                  />
                </div>
                {getFieldValidation('apellidos') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('apellidos')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('apellidos')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('apellidos')?.message}
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
                    placeholder="0987654321"
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
                  Fecha de Nacimiento <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="date"
                    value={formData.fechaNacimiento}
                    onChange={(e) => handleInputChange('fechaNacimiento', e.target.value)}
                    className={`pl-10 ${getFieldValidation('fechaNacimiento')?.isValid === false ? 'border-red-500' : ''}`}
                  />
                </div>
                {getFieldValidation('fechaNacimiento') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('fechaNacimiento')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('fechaNacimiento')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
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
                    className={`pl-10 ${getFieldValidation('direccion')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="Dirección completa del cliente"
                    rows={2}
                  />
                </div>
                {getFieldValidation('direccion') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('direccion')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('direccion')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('direccion')?.message}
                  </div>
                )}
              </div>

              <div className="space-y-2 min-h-[80px]"> {/* ✅ Estabilizar altura del campo */}
                <label className="text-sm font-medium text-gray-700">
                  Ocupación <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.ocupacion}
                    onChange={(e) => handleInputChange('ocupacion', e.target.value)}
                    className={`pl-10 w-full ${getFieldValidation('ocupacion')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="Ingeniero"
                  />
                </div>
                {getFieldValidation('ocupacion') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('ocupacion')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('ocupacion')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('ocupacion')?.message}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Datos del Vehículo */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Car className="w-5 h-5" />
                Datos del Vehículo
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Modelo de Vehículo <span className="text-red-500">*</span>
                  </label>
                <SearchableSelect
                  options={modelosVehiculos
                    .filter(modelo => modelo.modelo) // ✅ CORREGIDO: campo 'modelo', no 'nombre'
                    .map(modelo => ({
                      value: modelo.modelo,          // ✅ CORREGIDO: campo 'modelo', no 'nombre'
                      label: modelo.modelo           // ✅ CORREGIDO: campo 'modelo', no 'nombre'
                    }))}
                  value={formData.modeloVehiculo || ''}
                  onChange={(value) => handleInputChange('modeloVehiculo', value)}
                  placeholder="Buscar modelo de vehículo..."
                  className={getFieldValidation('modeloVehiculo')?.isValid === false ? 'border-red-500' : ''}
                />
                {/* Debug: Modelos disponibles */}
                {(() => {
                  console.log('🔍 Modelos disponibles para SearchableSelect:', modelosVehiculos.map(m => m.modelo)) // ✅ CORREGIDO: campo 'modelo'
                  return null
                })()}
                {getFieldValidation('modeloVehiculo') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('modeloVehiculo')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('modeloVehiculo')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('modeloVehiculo')?.message}
                </div>
                  )}
                </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Concesionario <span className="text-red-500">*</span>
                  </label>
                <SearchableSelect
                  options={concesionarios.map(concesionario => ({
                    value: concesionario.nombre,
                    label: concesionario.nombre
                  }))}
                  value={formData.concesionario}
                  onChange={(value) => handleInputChange('concesionario', value)}
                  placeholder="Buscar concesionario..."
                  className={getFieldValidation('concesionario')?.isValid === false ? 'border-red-500' : ''}
                />
                {getFieldValidation('concesionario') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('concesionario')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('concesionario')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('concesionario')?.message}
                </div>
                  )}
                </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Analista <span className="text-red-500">*</span>
                  </label>
                <SearchableSelect
                  options={analistas.map(analista => ({
                    value: analista.nombre,
                    label: analista.nombre
                  }))}
                  value={formData.analista}
                  onChange={(value) => handleInputChange('analista', value)}
                  placeholder="Buscar analista..."
                  className={getFieldValidation('analista')?.isValid === false ? 'border-red-500' : ''}
                />
                {getFieldValidation('analista') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('analista')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('analista')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('analista')?.message}
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
        
        {/* Popup de confirmación para cédulas duplicadas */}
        {showDuplicateWarning && clienteExistente && (
          <ConfirmacionDuplicadoModal
            isOpen={showDuplicateWarning}
            onClose={() => setShowDuplicateWarning(false)}
            onConfirm={handleConfirmDuplicate}
            clienteExistente={{
              id: clienteExistente.id,
              nombres: clienteExistente.nombres,
              apellidos: clienteExistente.apellidos,
              cedula: duplicateCedula,
              telefono: clienteExistente.telefono,
              email: clienteExistente.email,
              fecha_registro: new Date().toISOString() // Usar fecha actual como fallback
            }}
            clienteNuevo={{
              nombres: formData.nombres,
              apellidos: formData.apellidos,
              cedula: formData.cedula,
              telefono: formData.telefono,
              email: formData.email
            }}
          />
        )}
      </motion.div>
    </motion.div>
  )
}