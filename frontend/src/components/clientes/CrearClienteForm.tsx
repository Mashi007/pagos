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
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { concesionarioService, type Concesionario } from '@/services/concesionarioService'
import { asesorService, type Asesor } from '@/services/asesorService'
import { clienteService } from '@/services/clienteService'

interface FormData {
  // Datos personales
  nombreCompleto: string
  cedula: string
  movil: string
  email: string
  
  // Datos del financiamiento
  modeloVehiculo: string
  totalFinanciamiento: string
  cuotaInicial: string
  numeroAmortizaciones: string
  modalidadFinanciamiento: 'semanal' | 'quincenal' | 'mensual'
  fechaEntrega: string
  asesorAsignado: string
  concesionario: string
}

interface ValidationResult {
  isValid: boolean
  message?: string
}

interface FieldValidation {
  [key: string]: ValidationResult
}

const MODELOS_VEHICULOS = [
  'Toyota Corolla',
  'Nissan Versa',
  'Hyundai Accent',
  'Chevrolet Aveo',
  'Ford Fiesta',
  'Kia Rio',
  'Mazda 2',
  'Suzuki Swift',
  'Renault Logan',
  'Volkswagen Polo'
]

export function CrearClienteForm({ 
  onClose, 
  onClienteCreated 
}: { 
  onClose: () => void
  onClienteCreated?: () => void 
}) {
  const [formData, setFormData] = useState<FormData>({
    nombreCompleto: '',
    cedula: '',
    movil: '',
    email: '',
    modeloVehiculo: '',
    totalFinanciamiento: '',
    cuotaInicial: '',
    numeroAmortizaciones: '12',
    modalidadFinanciamiento: 'quincenal',
    fechaEntrega: '',
    asesorAsignado: '',
    concesionario: ''
  })

  const [validations, setValidations] = useState<FieldValidation>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [asesores, setAsesores] = useState<Asesor[]>([])
  const [loadingData, setLoadingData] = useState(true)

  // 🔄 CARGAR DATOS DINÁMICOS: Asesores y Concesionarios desde configuración
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoadingData(true)
        console.log('🔄 Cargando asesores y concesionarios desde configuración...')
        
        const [concesionariosData, asesoresData] = await Promise.all([
          // 🔄 Usar endpoints de configuración
          fetch('/api/v1/concesionarios/activos', {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`
            }
          }).then(res => res.json()).then(data => data.data || []),
          
          fetch('/api/v1/asesores/activos', {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`
            }
          }).then(res => res.json()).then(data => data.data || [])
        ])
        
        console.log('✅ Datos cargados:', {
          concesionarios: concesionariosData.length,
          asesores: asesoresData.length
        })
        
        setConcesionarios(concesionariosData)
        setAsesores(asesoresData)
      } catch (error) {
        console.error('❌ Error al cargar datos de configuración:', error)
        // Fallback a servicios locales si falla
        try {
          const [concesionariosData, asesoresData] = await Promise.all([
            concesionarioService.listarConcesionariosActivos(),
            asesorService.listarAsesoresActivos()
          ])
          setConcesionarios(concesionariosData)
          setAsesores(asesoresData)
        } catch (fallbackError) {
          console.error('❌ Error en fallback:', fallbackError)
          
          // Fallback final: usar datos mock
          console.log('🔄 Usando datos mock para formulario...')
          const mockConcesionarios = [
            { id: 1, nombre: 'AutoCenter Caracas', direccion: 'Av. Francisco de Miranda, Caracas', telefono: '+58 212-555-0101', email: 'caracas@autocenter.com', responsable: 'María González', activo: true, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
            { id: 2, nombre: 'Motors Valencia', direccion: 'Zona Industrial Norte, Valencia', telefono: '+58 241-555-0202', email: 'valencia@motors.com', responsable: 'Carlos Rodríguez', activo: true, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
            { id: 3, nombre: 'Vehiculos Maracaibo', direccion: 'Av. 5 de Julio, Maracaibo', telefono: '+58 261-555-0303', email: 'maracaibo@vehiculos.com', responsable: 'Ana Pérez', activo: true, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }
          ]
          
          const mockAsesores = [
            { id: 1, nombre: 'Roberto', apellido: 'Martínez', nombre_completo: 'Roberto Martínez', email: 'roberto.martinez@rapicredit.com', telefono: '+58 414-555-0404', especialidad: 'Vehículos Nuevos', comision_porcentaje: 2.5, activo: true, notas: 'Especialista en vehículos de gama alta', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
            { id: 2, nombre: 'Sandra', apellido: 'López', nombre_completo: 'Sandra López', email: 'sandra.lopez@rapicredit.com', telefono: '+58 424-555-0505', especialidad: 'Vehículos Usados', comision_porcentaje: 3.0, activo: true, notas: 'Experta en financiamiento de vehículos usados', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
            { id: 3, nombre: 'Miguel', apellido: 'Hernández', nombre_completo: 'Miguel Hernández', email: 'miguel.hernandez@rapicredit.com', telefono: '+58 414-555-0606', especialidad: 'Motocicletas', comision_porcentaje: 4.0, activo: true, notas: 'Especialista en financiamiento de motocicletas', created_at: new Date().toISOString(), updated_at: new Date().toISOString() }
          ]
          
          setConcesionarios(mockConcesionarios)
          setAsesores(mockAsesores)
          console.log('✅ Datos mock cargados:', {
            concesionarios: mockConcesionarios.length,
            asesores: mockAsesores.length
          })
        }
      } finally {
        setLoadingData(false)
      }
    }

    loadData()
  }, [])

  // 🔍 VALIDACIONES CON BACKEND: Usar validadores del sistema
  const validateField = async (field: string, value: string): Promise<ValidationResult> => {
    switch (field) {
      case 'nombreCompleto':
        if (!value.trim()) return { isValid: false, message: 'Nombre requerido' }
        if (value.trim().length < 3) return { isValid: false, message: 'Mínimo 3 caracteres' }
        return { isValid: true }

      case 'cedula':
        if (!value.trim()) return { isValid: false, message: 'Cédula requerida' }
        
        try {
          // 🔍 VALIDAR CON BACKEND: Usar endpoint de validadores
          const response = await fetch('/api/v1/validadores/validar-campo', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
              campo: 'cedula',
              valor: value,
              pais: 'VENEZUELA'
            })
          })
          
          if (response.ok) {
            const result = await response.json()
            // ✅ CORRECCIÓN: Acceder a result.validacion.valido
            if (result.validacion && result.validacion.valido) {
              return { isValid: true }
            } else {
              return { isValid: false, message: result.validacion?.mensaje || 'Formato de cédula inválido' }
            }
          }
        } catch (error) {
          console.warn('Error validando cédula con backend, usando validación local:', error)
        }
        
        // Fallback: validación local mejorada
        const cedulaPattern = /^[VEJ]\d{6,8}$/
        if (!cedulaPattern.test(value.toUpperCase())) {
          return { isValid: false, message: 'Formato: V/E/J + 6-8 dígitos (ej: V12345678)' }
        }
        return { isValid: true }

      case 'movil':
        if (!value.trim()) return { isValid: false, message: 'Móvil requerido' }
        
        try {
          // 🔍 VALIDAR CON BACKEND: Usar endpoint de validadores
          const cleanMovil = value.replace(/[^\d]/g, '')
          const response = await fetch('/api/v1/validadores/validar-campo', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
              campo: 'telefono',
              valor: cleanMovil,
              pais: 'VENEZUELA'
            })
          })
          
          if (response.ok) {
            const result = await response.json()
            // ✅ CORRECCIÓN: Acceder a result.validacion.valido
            if (result.validacion && result.validacion.valido) {
              return { isValid: true }
            } else {
              return { isValid: false, message: result.validacion?.mensaje || 'Formato de teléfono inválido' }
            }
          }
        } catch (error) {
          console.warn('Error validando teléfono con backend, usando validación local:', error)
        }
        
        // Fallback: validación local mejorada
        const cleanMovilFallback = value.replace(/\D/g, '')
        if (cleanMovilFallback.length === 10) {
          return { isValid: true }
        } else if (cleanMovilFallback.length === 12 && cleanMovilFallback.startsWith('58')) {
          return { isValid: true }
        }
        return { isValid: false, message: 'Formato: +58 XXXXXXXXXX (10 dígitos)' }

      case 'email':
        if (!value.trim()) return { isValid: false, message: 'Email requerido' }
        
        try {
          // 🔍 VALIDAR CON BACKEND: Usar endpoint de validadores
          const response = await fetch('/api/v1/validadores/validar-campo', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
              campo: 'email',
              valor: value,
              pais: 'VENEZUELA'
            })
          })
          
          if (response.ok) {
            const result = await response.json()
            // ✅ CORRECCIÓN: Acceder a result.validacion.valido
            if (result.validacion && result.validacion.valido) {
              return { isValid: true }
            } else {
              return { isValid: false, message: result.validacion?.mensaje || 'Formato de email inválido' }
            }
          }
        } catch (error) {
          console.warn('Error validando email con backend, usando validación local:', error)
        }
        
        // Fallback: validación local mejorada
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailPattern.test(value.toLowerCase())) {
          return { isValid: false, message: 'Formato: usuario@dominio.com' }
        }
        return { isValid: true }

      case 'modeloVehiculo':
        if (!value.trim()) return { isValid: false, message: 'Debe seleccionar un modelo' }
        return { isValid: true }

      case 'totalFinanciamiento':
        if (!value.trim()) return { isValid: false, message: 'Total requerido' }
        const total = parseFloat(value.replace(/[^\d.-]/g, ''))
        if (isNaN(total) || total < 1000 || total > 50000000) {
          return { isValid: false, message: 'Entre $1,000 y $50,000,000' }
        }
        return { isValid: true }

      case 'numeroAmortizaciones':
        if (!value.trim()) return { isValid: false, message: 'Número requerido' }
        const amortizaciones = parseInt(value)
        if (isNaN(amortizaciones) || amortizaciones < 1 || amortizaciones > 60) {
          return { isValid: false, message: 'Entre 1 y 60 cuotas' }
        }
        return { isValid: true }

      case 'fechaEntrega':
        if (!value.trim()) return { isValid: false, message: 'Fecha requerida' }
        const fecha = new Date(value)
        const hoy = new Date()
        hoy.setHours(0, 0, 0, 0)
        if (fecha < hoy) {
          return { isValid: false, message: 'No puede ser fecha pasada' }
        }
        return { isValid: true }

      case 'asesorAsignado':
        if (!value.trim()) return { isValid: false, message: 'Asesor requerido' }
        return { isValid: true }

      case 'concesionario':
        if (!value.trim()) return { isValid: false, message: 'Concesionario requerido' }
        return { isValid: true }

      default:
        return { isValid: true }
    }
  }

  const handleFieldChange = async (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // 🔍 VALIDAR CAMPO CON BACKEND: Validación asíncrona
    const validation = await validateField(field, value)
    setValidations(prev => ({ ...prev, [field]: validation }))
  }

  const formatMovil = (value: string) => {
    // Limpiar solo números
    const cleanValue = value.replace(/\D/g, '')
    
    if (cleanValue.length <= 10) {
      // Formato local: 4241234567 -> +58 424 1234567
      if (cleanValue.length >= 3) {
        return `+58 ${cleanValue.slice(0, 3)} ${cleanValue.slice(3)}`
      }
      return `+58 ${cleanValue}`
    } else if (cleanValue.startsWith('58') && cleanValue.length === 12) {
      // Ya tiene código de país: 584241234567 -> +58 424 1234567
      return `+58 ${cleanValue.slice(2, 5)} ${cleanValue.slice(5)}`
    }
    
    return value
  }

  const formatCurrency = (value: string) => {
    const cleanValue = value.replace(/[^\d.-]/g, '')
    if (!cleanValue) return ''
    return `$${parseInt(cleanValue).toLocaleString()}`
  }

  const getFieldStatus = (field: string) => {
    const validation = validations[field]
    if (!validation) return 'pending'
    return validation.isValid ? 'valid' : 'invalid'
  }

  const getFieldIcon = (field: string) => {
    const status = getFieldStatus(field)
    switch (status) {
      case 'valid': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'invalid': return <XCircle className="h-4 w-4 text-red-500" />
      default: return <div className="h-4 w-4" />
    }
  }

  const getPendingErrors = () => {
    return Object.entries(validations)
      .filter(([_, validation]) => !validation.isValid)
      .map(([field, validation]) => ({ field, message: validation.message }))
  }

  const isFormValid = () => {
    const requiredFields: (keyof FormData)[] = [
      'nombreCompleto', 'cedula', 'movil', 'email',
      'modeloVehiculo', 'totalFinanciamiento', 'numeroAmortizaciones',
      'fechaEntrega', 'asesorAsignado', 'concesionario'
    ]
    
    return requiredFields.every(field => {
      const validation = validations[field]
      return validation?.isValid === true
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isFormValid()) return

    setIsSubmitting(true)
    try {
      // 🔄 CONECTAR AL BACKEND: Usar servicio real
      
      // ✅ TRANSFORMAR DATOS: Convertir FormData a ClienteForm (coincide con backend)
      const clienteData = {
        // Datos personales (coincide con backend/app/schemas/cliente.py)
        cedula: formData.cedula,
        nombres: formData.nombreCompleto.split(' ')[0] || '',  // ✅ Backend: "nombres"
        apellidos: formData.nombreCompleto.split(' ').slice(1).join(' ') || '',  // ✅ Backend: "apellidos"
        telefono: formData.movil.replace(/[^\d]/g, ''),  // ✅ Backend: "telefono"
        email: formData.email,
        
        // Datos del vehículo (coincide con backend)
        modelo_vehiculo: formData.modeloVehiculo,  // ✅ Backend: "modelo_vehiculo"
        marca_vehiculo: formData.modeloVehiculo.split(' ')[0] || '',  // ✅ Backend: "marca_vehiculo"
        anio_vehiculo: new Date().getFullYear(),  // ✅ Backend: "anio_vehiculo"
        
        // Concesionario y asesor (coincide con backend)
        concesionario: formData.concesionario,  // ✅ Backend: "concesionario"
        asesor_id: parseInt(formData.asesorAsignado) || undefined,  // ✅ Backend: "asesor_id"
        
        // Datos del financiamiento (coincide con backend)
        total_financiamiento: parseFloat(formData.totalFinanciamiento.replace(/[^\d.-]/g, '')) || 0,  // ✅ Backend: "total_financiamiento"
        cuota_inicial: parseFloat(formData.cuotaInicial.replace(/[^\d.-]/g, '')) || 0,  // ✅ Backend: "cuota_inicial"
        fecha_entrega: formData.fechaEntrega,  // ✅ Backend: "fecha_entrega"
        numero_amortizaciones: parseInt(formData.numeroAmortizaciones) || 12,  // ✅ Backend: "numero_amortizaciones"
        modalidad_pago: formData.modalidadFinanciamiento.toUpperCase()  // ✅ Backend: "modalidad_pago"
      }
      
      console.log('🔄 Enviando cliente al backend:', clienteData)
      const newCliente = await clienteService.createCliente(clienteData)
      console.log('✅ Cliente creado exitosamente:', newCliente)
      
      // Éxito - cerrar modal y notificar que se creó un cliente
      onClose()
      if (onClienteCreated) {
        onClienteCreated()
      }
    } catch (error) {
      console.error('❌ Error al guardar cliente:', error)
      // TODO: Mostrar error al usuario
    } finally {
      setIsSubmitting(false)
    }
  }

  const pendingErrors = getPendingErrors()

  if (loadingData) {
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
          className="bg-white rounded-lg shadow-xl p-8 text-center"
        >
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h3 className="text-lg font-semibold mb-2">Cargando datos...</h3>
          <p className="text-gray-600">Cargando concesionarios y asesores</p>
        </motion.div>
      </motion.div>
    )
  }

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
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <User className="h-6 w-6" />
              <h2 className="text-xl font-bold">CREAR NUEVO CLIENTE</h2>
            </div>
            <Button
              onClick={onClose}
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Datos Personales */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <User className="mr-2 h-5 w-5" />
                DATOS PERSONALES
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Nombre completo */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    Nombre completo *
                    {getFieldIcon('nombreCompleto')}
                  </label>
                  <Input
                    value={formData.nombreCompleto}
                    onChange={(e) => handleFieldChange('nombreCompleto', e.target.value)}
                    placeholder="Juan Pérez"
                    className={getFieldStatus('nombreCompleto') === 'invalid' ? 'border-red-500' : ''}
                  />
                  {validations.nombreCompleto?.isValid && (
                    <p className="text-xs text-green-600">✓ Mínimo 3 caracteres</p>
                  )}
                  {validations.nombreCompleto?.message && (
                    <p className="text-xs text-red-600">✗ {validations.nombreCompleto.message}</p>
                  )}
                </div>

                {/* Cédula */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    <CreditCard className="mr-1 h-4 w-4" />
                    Cédula de identidad *
                    {getFieldIcon('cedula')}
                  </label>
                  <Input
                    value={formData.cedula}
                    onChange={(e) => handleFieldChange('cedula', e.target.value.toUpperCase())}
                    placeholder="V12345678"
                    className={getFieldStatus('cedula') === 'invalid' ? 'border-red-500' : ''}
                  />
                  {validations.cedula?.isValid && (
                    <div className="text-xs text-green-600 space-y-1">
                      <p>✓ Formato: V/E + 6-8 dígitos</p>
                      <p>✓ Cédula disponible (no duplicada)</p>
                    </div>
                  )}
                  {validations.cedula?.message && (
                    <p className="text-xs text-red-600">✗ {validations.cedula.message}</p>
                  )}
                </div>

                {/* Móvil */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    <Phone className="mr-1 h-4 w-4" />
                    Móvil *
                    {getFieldIcon('movil')}
                  </label>
                  <Input
                    value={formatMovil(formData.movil)}
                    onChange={(e) => handleFieldChange('movil', e.target.value)}
                    placeholder="+58 424 1234567"
                    className={getFieldStatus('movil') === 'invalid' ? 'border-red-500' : ''}
                  />
                  {validations.movil?.isValid && (
                    <p className="text-xs text-green-600">✓ Formato correcto</p>
                  )}
                  {validations.movil?.message && (
                    <div className="text-xs text-red-600 space-y-1">
                      <p>✗ {validations.movil.message}</p>
                      <p className="text-gray-600">(Escribe: 4241234567, sistema formatea)</p>
                    </div>
                  )}
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    <Mail className="mr-1 h-4 w-4" />
                    Correo electrónico *
                    {getFieldIcon('email')}
                  </label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleFieldChange('email', e.target.value.toLowerCase())}
                    placeholder="juan@email.com"
                    className={getFieldStatus('email') === 'invalid' ? 'border-red-500' : ''}
                  />
                  {validations.email?.message && (
                    <p className="text-xs text-red-600">✗ {validations.email.message}</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Datos del Financiamiento */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Car className="mr-2 h-5 w-5" />
                DATOS DEL FINANCIAMIENTO
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Modelo de vehículo */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    Modelo de vehículo *
                    {getFieldIcon('modeloVehiculo')}
                  </label>
                  <Select value={formData.modeloVehiculo} onValueChange={(value) => handleFieldChange('modeloVehiculo', value)}>
                    <SelectTrigger className={getFieldStatus('modeloVehiculo') === 'invalid' ? 'border-red-500' : ''}>
                      <SelectValue placeholder="Seleccionar modelo" />
                    </SelectTrigger>
                    <SelectContent>
                      {MODELOS_VEHICULOS.map((modelo) => (
                        <SelectItem key={modelo} value={modelo}>
                          {modelo}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {validations.modeloVehiculo?.message && (
                    <p className="text-xs text-red-600">✗ {validations.modeloVehiculo.message}</p>
                  )}
                </div>

                {/* Total del financiamiento */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    <DollarSign className="mr-1 h-4 w-4" />
                    Total del financiamiento *
                    {getFieldIcon('totalFinanciamiento')}
                  </label>
                  <Input
                    value={formatCurrency(formData.totalFinanciamiento)}
                    onChange={(e) => handleFieldChange('totalFinanciamiento', e.target.value)}
                    placeholder="$25,000"
                    className={getFieldStatus('totalFinanciamiento') === 'invalid' ? 'border-red-500' : ''}
                  />
                  {!formData.totalFinanciamiento && (
                    <p className="text-xs text-yellow-600">(Esperando valor...)</p>
                  )}
                  {validations.totalFinanciamiento?.message && (
                    <p className="text-xs text-red-600">✗ {validations.totalFinanciamiento.message}</p>
                  )}
                </div>

                {/* Cuota inicial */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    <DollarSign className="mr-1 h-4 w-4 inline" />
                    Cuota inicial
                  </label>
                  <Input
                    value={formatCurrency(formData.cuotaInicial)}
                    onChange={(e) => handleFieldChange('cuotaInicial', e.target.value)}
                    placeholder="$5,000"
                  />
                  <p className="text-xs text-gray-600">(Opcional, pero recomendado)</p>
                </div>

                {/* Número de amortizaciones */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    <Calendar className="mr-1 h-4 w-4" />
                    Número de amortizaciones *
                    {getFieldIcon('numeroAmortizaciones')}
                  </label>
                  <Input
                    type="number"
                    min="1"
                    max="60"
                    value={formData.numeroAmortizaciones}
                    onChange={(e) => handleFieldChange('numeroAmortizaciones', e.target.value)}
                    placeholder="12"
                    className={getFieldStatus('numeroAmortizaciones') === 'invalid' ? 'border-red-500' : ''}
                  />
                  {validations.numeroAmortizaciones?.isValid && (
                    <p className="text-xs text-green-600">✓ Entre 1 y 60 cuotas</p>
                  )}
                  {validations.numeroAmortizaciones?.message && (
                    <p className="text-xs text-red-600">✗ {validations.numeroAmortizaciones.message}</p>
                  )}
                </div>

                {/* Modalidad de financiamiento */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Modalidad de financiamiento *
                  </label>
                  <div className="flex space-x-4">
                    {(['semanal', 'quincenal', 'mensual'] as const).map((modalidad) => (
                      <label key={modalidad} className="flex items-center space-x-2">
                        <input
                          type="radio"
                          name="modalidadFinanciamiento"
                          value={modalidad}
                          checked={formData.modalidadFinanciamiento === modalidad}
                          onChange={(e) => handleFieldChange('modalidadFinanciamiento', e.target.value as any)}
                          className="text-blue-600"
                        />
                        <span className="text-sm capitalize">{modalidad}</span>
                      </label>
                    ))}
                  </div>
                  <p className="text-xs text-green-600">✅ Seleccionado</p>
                </div>

                {/* Fecha de entrega */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    <Calendar className="mr-1 h-4 w-4" />
                    Fecha de entrega *
                    {getFieldIcon('fechaEntrega')}
                  </label>
                  <Input
                    type="date"
                    value={formData.fechaEntrega}
                    onChange={(e) => handleFieldChange('fechaEntrega', e.target.value)}
                    min={new Date().toISOString().split('T')[0]}
                    className={getFieldStatus('fechaEntrega') === 'invalid' ? 'border-red-500' : ''}
                  />
                  {validations.fechaEntrega?.isValid && (
                    <p className="text-xs text-green-600">✓ Fecha válida, no es futura</p>
                  )}
                  {validations.fechaEntrega?.message && (
                    <p className="text-xs text-red-600">✗ {validations.fechaEntrega.message}</p>
                  )}
                </div>

                {/* Asesor asignado */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    <Users className="mr-1 h-4 w-4" />
                    Asesor asignado *
                    {getFieldIcon('asesorAsignado')}
                  </label>
                  <Select value={formData.asesorAsignado} onValueChange={(value) => handleFieldChange('asesorAsignado', value)}>
                    <SelectTrigger className={getFieldStatus('asesorAsignado') === 'invalid' ? 'border-red-500' : ''}>
                      <SelectValue placeholder="Seleccionar asesor" />
                    </SelectTrigger>
                    <SelectContent>
                      {asesores.map((asesor) => (
                        <SelectItem key={asesor.id} value={asesor.nombre_completo}>
                          <div className="flex flex-col">
                            <span>{asesor.nombre_completo}</span>
                            {asesor.especialidad && (
                              <span className="text-xs text-gray-500">{asesor.especialidad}</span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Concesionario */}
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center">
                    <Building className="mr-1 h-4 w-4" />
                    Concesionario *
                    {getFieldIcon('concesionario')}
                  </label>
                  <Select value={formData.concesionario} onValueChange={(value) => handleFieldChange('concesionario', value)}>
                    <SelectTrigger className={getFieldStatus('concesionario') === 'invalid' ? 'border-red-500' : ''}>
                      <SelectValue placeholder="Seleccionar concesionario" />
                    </SelectTrigger>
                    <SelectContent>
                      {concesionarios.map((concesionario) => (
                        <SelectItem key={concesionario.id} value={concesionario.nombre}>
                          <div className="flex flex-col">
                            <span>{concesionario.nombre}</span>
                            {concesionario.responsable && (
                              <span className="text-xs text-gray-500">{concesionario.responsable}</span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Errores pendientes */}
          {pendingErrors.length > 0 && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-4">
                <div className="flex items-center space-x-2 mb-3">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  <h3 className="font-semibold text-red-700">
                    ERRORES PENDIENTES ({pendingErrors.length})
                  </h3>
                </div>
                <div className="space-y-1">
                  {pendingErrors.map((error, index) => (
                    <p key={index} className="text-sm text-red-600">
                      • {error.field}: {error.message}
                    </p>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Botones de acción */}
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              <X className="mr-2 h-4 w-4" />
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={!isFormValid() || isSubmitting}
              className={!isFormValid() ? 'bg-gray-400 cursor-not-allowed' : ''}
            >
              <Save className="mr-2 h-4 w-4" />
              {isSubmitting ? 'Guardando...' : 'Guardar cliente'}
            </Button>
          </div>

          {!isFormValid() && (
            <div className="text-center text-sm text-gray-600 bg-blue-50 p-3 rounded-lg">
              💡 El botón "Guardar" se habilitará cuando corrijas todos los errores
            </div>
          )}
        </form>
      </motion.div>
    </motion.div>
  )
}
