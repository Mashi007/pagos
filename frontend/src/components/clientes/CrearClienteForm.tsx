import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
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
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { concesionarioService, type Concesionario } from '@/services/concesionarioService'
import { analistaService, type Analista } from '@/services/analistaService'
import { modeloVehiculoService, type ModeloVehiculo } from '@/services/modeloVehiculoService'
import { clienteService } from '@/services/clienteService'
import { ExcelUploader } from './ExcelUploader'

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
  onClose: () => void
  onSuccess: () => void
  onClienteCreated?: () => void
}

export function CrearClienteForm({ onClose, onSuccess, onClienteCreated }: CrearClienteFormProps) {
  const [formData, setFormData] = useState<FormData>({
    cedula: '',
    nombres: '',
    apellidos: '',
    telefono: '',
    email: '',
    direccion: '',
    fechaNacimiento: '',
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
  
  // Datos de configuración
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [analistas, setAnalistas] = useState<Analista[]>([])
  const [modelosVehiculos, setModelosVehiculos] = useState<ModeloVehiculo[]>([])

  // Cargar datos de configuración
  useEffect(() => {
    const cargarDatosConfiguracion = async () => {
      try {
        const [concesionariosData, analistasData, modelosData] = await Promise.all([
          concesionarioService.getConcesionarios(),
          analistaService.getAnalistas(),
          modeloVehiculoService.getModelosVehiculos()
        ])
        
        setConcesionarios(concesionariosData)
        setAnalistas(analistasData)
        setModelosVehiculos(modelosData)
      } catch (error) {
        console.error('Error cargando datos de configuración:', error)
      }
    }

    cargarDatosConfiguracion()
  }, [])

  // Validaciones en tiempo real
  const validateField = (field: string, value: string): ValidationResult => {
    switch (field) {
      case 'cedula':
        if (!value) return { field, isValid: false, message: 'Cédula es obligatoria' }
        if (value.length < 8 || value.length > 20) {
          return { field, isValid: false, message: 'Cédula debe tener entre 8 y 20 caracteres' }
        }
        return { field, isValid: true, message: 'Cédula válida' }
      
      case 'nombres':
        if (!value) return { field, isValid: false, message: 'Nombres son obligatorios' }
        const nombresWords = value.trim().split(' ').filter(word => word.length > 0)
        if (nombresWords.length < 2) {
          return { field, isValid: false, message: 'Mínimo 2 palabras: nombre y apellido' }
        }
        if (nombresWords.length > 2) {
          return { field, isValid: false, message: 'Máximo 2 palabras en nombres' }
        }
        return { field, isValid: true, message: 'Nombres válidos' }
      
      case 'apellidos':
        if (!value) return { field, isValid: false, message: 'Apellidos son obligatorios' }
        const apellidosWords = value.trim().split(' ').filter(word => word.length > 0)
        if (apellidosWords.length < 2) {
          return { field, isValid: false, message: 'Mínimo 2 palabras: apellido paterno y materno' }
        }
        if (apellidosWords.length > 2) {
          return { field, isValid: false, message: 'Máximo 2 palabras en apellidos' }
        }
        return { field, isValid: true, message: 'Apellidos válidos' }
      
      case 'telefono':
        if (!value) return { field, isValid: false, message: 'Teléfono es obligatorio' }
        // Validar formato venezolano: +58 XXXXXXXXXX (10 dígitos, primer dígito no puede ser 0)
        const telefonoLimpio = value.replace(/\s+/g, '').replace(/\+58/g, '')
        if (telefonoLimpio.length !== 10) {
          return { field, isValid: false, message: 'Formato: +58 XXXXXXXXXX (10 dígitos, primer dígito no puede ser 0)' }
        }
        if (telefonoLimpio[0] === '0') {
          return { field, isValid: false, message: 'Primer dígito no puede ser 0' }
        }
        if (!/^\d{10}$/.test(telefonoLimpio)) {
          return { field, isValid: false, message: 'Solo se permiten números' }
        }
        return { field, isValid: true, message: 'Teléfono válido' }
      
      case 'email':
        if (!value) return { field, isValid: false, message: 'Email es obligatorio' }
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRegex.test(value)) {
          return { field, isValid: false, message: 'Email inválido' }
        }
        return { field, isValid: true, message: 'Email válido' }
      
      case 'direccion':
        if (!value) return { field, isValid: false, message: 'Dirección es obligatoria' }
        if (value.length < 5) {
          return { field, isValid: false, message: 'Dirección debe tener al menos 5 caracteres' }
        }
        return { field, isValid: true, message: 'Dirección válida' }
      
      case 'fechaNacimiento':
        if (!value) return { field, isValid: false, message: 'Fecha de nacimiento es obligatoria' }
        const fecha = new Date(value)
        const hoy = new Date()
        if (fecha > hoy) {
          return { field, isValid: false, message: 'Fecha de nacimiento no puede ser futura' }
        }
        return { field, isValid: true, message: 'Fecha válida' }
      
      case 'ocupacion':
        if (!value) return { field, isValid: false, message: 'Ocupación es obligatoria' }
        return { field, isValid: true, message: 'Ocupación válida' }
      
      case 'modeloVehiculo':
        if (!value) return { field, isValid: false, message: 'Modelo de vehículo es obligatorio' }
        return { field, isValid: true, message: 'Modelo válido' }
      
      case 'concesionario':
        if (!value) return { field, isValid: false, message: 'Concesionario es obligatorio' }
        return { field, isValid: true, message: 'Concesionario válido' }
      
      case 'analista':
        if (!value) return { field, isValid: false, message: 'Analista es obligatorio' }
        return { field, isValid: true, message: 'Analista válido' }
      
      default:
        return { field, isValid: true, message: '' }
    }
  }

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Validar campo en tiempo real
    const validation = validateField(field, value)
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

      await clienteService.createCliente(clienteData)
      onSuccess()
      onClienteCreated?.()
      onClose()
    } catch (error) {
      console.error('Error creando cliente:', error)
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
        onClose={() => setShowExcelUploader(false)}
        onSuccess={() => {
          setShowExcelUploader(false)
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
          <h2 className="text-2xl font-bold text-gray-900">Nuevo Cliente</h2>
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
            >
              <X className="w-4 h-4" />
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

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Ocupación <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.ocupacion}
                    onChange={(e) => handleInputChange('ocupacion', e.target.value)}
                    className={`pl-10 ${getFieldValidation('ocupacion')?.isValid === false ? 'border-red-500' : ''}`}
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
                <Select
                  value={formData.modeloVehiculo}
                  onValueChange={(value) => handleInputChange('modeloVehiculo', value)}
                >
                  <SelectTrigger className={getFieldValidation('modeloVehiculo')?.isValid === false ? 'border-red-500' : ''}>
                    <SelectValue placeholder="Seleccionar modelo" />
                  </SelectTrigger>
                  <SelectContent>
                    {modelosVehiculos.map((modelo) => (
                      <SelectItem key={modelo.id} value={modelo.nombre}>
                        {modelo.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
                <Select
                  value={formData.concesionario}
                  onValueChange={(value) => handleInputChange('concesionario', value)}
                >
                  <SelectTrigger className={getFieldValidation('concesionario')?.isValid === false ? 'border-red-500' : ''}>
                    <SelectValue placeholder="Seleccionar concesionario" />
                  </SelectTrigger>
                  <SelectContent>
                    {concesionarios.map((concesionario) => (
                      <SelectItem key={concesionario.id} value={concesionario.nombre}>
                        {concesionario.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
                <Select
                  value={formData.analista}
                  onValueChange={(value) => handleInputChange('analista', value)}
                >
                  <SelectTrigger className={getFieldValidation('analista')?.isValid === false ? 'border-red-500' : ''}>
                    <SelectValue placeholder="Seleccionar analista" />
                  </SelectTrigger>
                  <SelectContent>
                    {analistas.map((analista) => (
                      <SelectItem key={analista.id} value={analista.nombre}>
                        {analista.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
      </motion.div>
    </motion.div>
  )
}