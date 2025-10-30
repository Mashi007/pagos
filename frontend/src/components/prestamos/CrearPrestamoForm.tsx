import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import { 
  DollarSign, 
  Calendar, 
  CreditCard, 
  Search,
  X,
  ChevronDown,
  ChevronUp,
  Save,
  AlertCircle,
  CheckCircle2
} from 'lucide-react'
import { useDebounce } from '@/hooks/useDebounce'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { clienteService } from '@/services/clienteService'
import { useCreatePrestamo, useUpdatePrestamo } from '@/hooks/usePrestamos'
import { useSearchClientes } from '@/hooks/useClientes'
import { usePermissions } from '@/hooks/usePermissions'
import { useConcesionariosActivos } from '@/hooks/useConcesionarios'
import { useAnalistasActivos } from '@/hooks/useAnalistas'
import { useModelosVehiculosActivos } from '@/hooks/useModelosVehiculos'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { prestamoService } from '@/services/prestamoService'
import { Prestamo, PrestamoForm } from '@/types'
import { ModalValidacionPrestamoExistente } from './ModalValidacionPrestamoExistente'

interface CrearPrestamoFormProps {
  prestamo?: Prestamo // Préstamo existente para edición
  onClose: () => void
  onSuccess: () => void
}

export function CrearPrestamoForm({ prestamo, onClose, onSuccess }: CrearPrestamoFormProps) {
  const createPrestamo = useCreatePrestamo()
  const updatePrestamo = useUpdatePrestamo()
  const { canEditPrestamo, canApprovePrestamo } = usePermissions()
  
  // Función para obtener la fecha actual en formato YYYY-MM-DD
  const getCurrentDate = () => {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  const [formData, setFormData] = useState<Partial<PrestamoForm>>({
    cedula: prestamo?.cedula || '',
    total_financiamiento: prestamo?.total_financiamiento || 0,
    modalidad_pago: prestamo?.modalidad_pago || 'MENSUAL',
    fecha_requerimiento: prestamo?.fecha_requerimiento || getCurrentDate(), // Fecha actual por defecto para nuevos préstamos
    producto: prestamo?.producto || '',
    producto_financiero: prestamo?.producto_financiero || '',
    concesionario: prestamo?.concesionario || '',
    analista: prestamo?.analista || '',
    modelo_vehiculo: prestamo?.modelo_vehiculo || '',
    tasa_interes: prestamo?.tasa_interes || 0,
    observaciones: prestamo?.observaciones || '',
  })
  
  // Obtener datos de configuración con manejo de errores
  const { data: concesionarios = [], error: errorConcesionarios } = useConcesionariosActivos()
  const { data: analistas = [], error: errorAnalistas } = useAnalistasActivos()
  const { data: modelosVehiculos = [], error: errorModelos } = useModelosVehiculosActivos()
  const { user } = useSimpleAuth()

  // Log errores sin bloquear el renderizado
  if (errorConcesionarios) {
    console.warn('Error cargando concesionarios:', errorConcesionarios)
  }
  if (errorAnalistas) {
    console.warn('Error cargando analistas:', errorAnalistas)
  }
  if (errorModelos) {
    console.warn('Error cargando modelos de vehículos:', errorModelos)
  }

  const [valorActivo, setValorActivo] = useState<number>(0)
  
  // Estados para validación de préstamos existentes
  const [showModalValidacion, setShowModalValidacion] = useState(false)
  const [resumenPrestamos, setResumenPrestamos] = useState<any>(null)
  const [justificacionAutorizacion, setJustificacionAutorizacion] = useState('')
  const [anticipo, setAnticipo] = useState<number>(0)
  const [showAdditionalInfo, setShowAdditionalInfo] = useState(false)
  const [clienteData, setClienteData] = useState<any>(null)
  const [numeroCuotas, setNumeroCuotas] = useState<number>(12) // Valor por defecto: 12 cuotas
  const [cuotaPeriodo, setCuotaPeriodo] = useState<number>(0)

  // Calcular anticipo como 30% del valor activo automáticamente
  useEffect(() => {
    if (valorActivo > 0) {
      const anticipoCalculado = valorActivo * 0.30
      setAnticipo(anticipoCalculado)
    } else {
      setAnticipo(0)
    }
  }, [valorActivo])

  // Calcular total_financiamiento automáticamente
  useEffect(() => {
    const total = valorActivo - anticipo
    setFormData(prev => ({
      ...prev,
      total_financiamiento: Math.max(0, total)
    }))
  }, [valorActivo, anticipo])

  // Buscar cliente por cédula con debounce mejorado
  const debouncedCedula = useDebounce(formData.cedula || '', 500)
  const { data: clienteInfo, isLoading: isLoadingCliente } = useSearchClientes(
    debouncedCedula && debouncedCedula.length >= 2 ? debouncedCedula : ''
  )

  // Calcular cuota por período basado en el número de cuotas manual
  useEffect(() => {
    if (formData.total_financiamiento && formData.total_financiamiento > 0 && numeroCuotas > 0) {
      const cuota = formData.total_financiamiento / numeroCuotas
      setCuotaPeriodo(cuota)
    } else {
      setCuotaPeriodo(0)
    }
  }, [formData.total_financiamiento, numeroCuotas])


  // Cargar datos del cliente cuando se encuentra
  useEffect(() => {
    if (clienteInfo && clienteInfo.length > 0) {
      const cliente = clienteInfo[0]
      setClienteData(cliente)
      // Auto-llenar campos basados en cliente
      setFormData(prev => ({
        ...prev,
        producto: cliente.modelo_vehiculo || '',
        producto_financiero: cliente.analista || '',
        // También llenar nuevos campos si están disponibles en el cliente
        modelo_vehiculo: cliente.modelo_vehiculo || prev.modelo_vehiculo || '',
        analista: cliente.analista || prev.analista || '',
        concesionario: cliente.concesionario || prev.concesionario || '',
      }))
    } else if (formData.cedula && formData.cedula.length >= 2 && clienteInfo && clienteInfo.length === 0) {
      // Cliente no encontrado
      setClienteData(null)
    }
  }, [clienteInfo, formData.cedula])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validaciones requeridas
    const errors: string[] = []
    
    // Validar cédula
    if (!formData.cedula || formData.cedula.trim() === '') {
      errors.push('La cédula es requerida')
    }
    
    // Validar que el cliente exista (solo para nuevos préstamos)
    if (!prestamo && !clienteData) {
      errors.push('Debe buscar y seleccionar un cliente válido')
    }
    
    // Validar Valor Activo
    if (valorActivo <= 0) {
      errors.push('El Valor Activo debe ser mayor a 0')
    }
    
    // Validar Anticipo
    if (anticipo < 0) {
      errors.push('El Anticipo no puede ser negativo')
    }
    
    // Validar Número de Cuotas
    if (numeroCuotas < 1 || numeroCuotas > 12) {
      errors.push('El número de cuotas debe estar entre 1 y 12')
    }
    
    // Validar Total de Financiamiento
    if (!formData.total_financiamiento || formData.total_financiamiento <= 0) {
      errors.push('El Total de Financiamiento debe ser mayor a 0')
    }
    
    // Validar Modalidad de Pago
    if (!formData.modalidad_pago) {
      errors.push('La modalidad de pago es requerida')
    }
    
    // Validar Fecha de Requerimiento
    if (!formData.fecha_requerimiento || formData.fecha_requerimiento.trim() === '') {
      errors.push('La fecha de requerimiento es requerida')
    }
    
    // Requeridos adicionales del formulario
    if (!formData.producto || String(formData.producto).trim() === '') {
      errors.push('El campo Producto es requerido')
    }
    if (!formData.producto_financiero || String(formData.producto_financiero).trim() === '') {
      errors.push('El campo Producto Financiero es requerido')
    }
    if (!formData.concesionario || String(formData.concesionario).trim() === '') {
      errors.push('Debe seleccionar un Concesionario')
    }
    if (!formData.analista || String(formData.analista).trim() === '') {
      errors.push('Debe seleccionar un Analista')
    }
    if (!formData.modelo_vehiculo || String(formData.modelo_vehiculo).trim() === '') {
      errors.push('Debe seleccionar un Modelo de Vehículo')
    }

    // Si hay errores, mostrar mensajes
    if (errors.length > 0) {
      errors.forEach(error => {
        toast.error(error)
      })
      return
    }

    // Si es un nuevo préstamo, verificar si el cliente ya tiene préstamos
    if (!prestamo && formData.cedula) {
      try {
        const resumen = await prestamoService.getResumenPrestamos(formData.cedula)
        
        if (resumen.tiene_prestamos && resumen.prestamos && resumen.prestamos.length > 0) {
          // Mostrar modal de validación
          setResumenPrestamos(resumen)
          setShowModalValidacion(true)
          return // No continuar hasta que se confirme en el modal
        }
      } catch (error) {
        console.error('Error verificando préstamos existentes:', error)
        // Continuar con el proceso si hay error (no bloquear)
      }
    }

    // Proceder con la creación/actualización
    await crearOActualizarPrestamo()
  }

  const crearOActualizarPrestamo = async () => {
    try {
      // Preparar datos con numero_cuotas y cuota_periodo
      const prestamoData = {
        ...formData,
        numero_cuotas: numeroCuotas,
        cuota_periodo: cuotaPeriodo,
        fecha_base_calculo: formData.fecha_base_calculo,
        usuario_autoriza: !prestamo && justificacionAutorizacion ? user?.email : undefined,
        observaciones: justificacionAutorizacion 
          ? `${formData.observaciones || ''}\n\n--- JUSTIFICACIÓN PARA NUEVO PRÉSTAMO ---\n${justificacionAutorizacion}`.trim()
          : formData.observaciones,
      }
      
      if (prestamo) {
        // Editar préstamo existente
        await updatePrestamo.mutateAsync({
          id: prestamo.id,
          data: prestamoData
        })
      } else {
        // Crear nuevo préstamo
        await createPrestamo.mutateAsync(prestamoData as PrestamoForm)
      }
      
      onSuccess()
      onClose()
    } catch (error) {
      toast.error('Error al guardar el préstamo')
      console.error('Error saving loan:', error)
    }
  }

  const handleConfirmarAutorizacion = (justificacion: string) => {
    setJustificacionAutorizacion(justificacion)
    setShowModalValidacion(false)
    // Continuar con la creación del préstamo
    crearOActualizarPrestamo()
  }

  // Verificar permisos de edición
  const isReadOnly = prestamo ? !canEditPrestamo(prestamo.estado) : false
  const canApprove = prestamo ? canApprovePrestamo() : false

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        // Eliminado: onClick para evitar cierre por clic fuera
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => {
            // Prevenir cierre con Escape
            if (e.key === 'Escape') {
              e.preventDefault()
              e.stopPropagation()
            }
          }}
        >
          <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
            <h2 className="text-xl font-bold">
              {prestamo ? 'Editar Préstamo' : 'Nuevo Préstamo'}
            </h2>
            {/* Botón X eliminado - solo se puede cerrar con Cancelar o Crear */}
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Búsqueda de Cliente */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Búsqueda de Cliente
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Seleccionar primero el Modelo para cargar el precio */}
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Modelo de Vehículo <span className="text-red-500">*</span>
                  </label>
                  <Select
                    value={formData.modelo_vehiculo ?? ''}
                    onValueChange={(value) => {
                      setFormData({
                        ...formData,
                        modelo_vehiculo: value,
                      })
                      const modeloSel = modelosVehiculos.find((m:any) => m.modelo === value)
                      if (modeloSel && typeof modeloSel.precio === 'number') {
                        setValorActivo(modeloSel.precio)
                      } else {
                        setValorActivo(0)
                      }
                    }}
                    disabled={isReadOnly}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar modelo" />
                    </SelectTrigger>
                    <SelectContent>
                      {modelosVehiculos.map((modelo) => (
                        <SelectItem key={modelo.id} value={modelo.modelo}>
                          {modelo.modelo}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-gray-500 mt-1">Seleccione el modelo para cargar automáticamente el precio del activo.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Cédula <span className="text-red-500">*</span>
                  </label>
                  <Input
                    placeholder="Buscar por cédula..."
                    value={formData.cedula}
                    onChange={(e) => setFormData({ ...formData, cedula: e.target.value })}
                    disabled={isReadOnly || isLoadingCliente}
                  />
                </div>

                            {isLoadingCliente && formData.cedula && formData.cedula.length >= 2 && (
                              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                                <p className="text-sm text-blue-800">Buscando cliente...</p>
                              </div>
                            )}
                            
                            {clienteData && !isLoadingCliente && (
                              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                                <div className="flex items-center gap-2 mb-2">
                                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                                  <p className="font-semibold text-green-800">{clienteData.nombres}</p>
                                </div>
                                <p className="text-sm text-green-700">Cliente encontrado y datos cargados automáticamente</p>
                              </div>
                            )}

                            {!clienteData && !isLoadingCliente && formData.cedula && formData.cedula.length >= 2 && (
                              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                                <div className="flex items-center gap-2">
                                  <AlertCircle className="h-5 w-5 text-red-600" />
                                  <p className="text-sm text-red-800">Cliente no encontrado con esta cédula</p>
                                </div>
                              </div>
                            )}
              </CardContent>
            </Card>

            {/* Información Adicional del Cliente (Colapsable) */}
            {clienteData && (
              <Card>
                <CardHeader>
                  <button
                    type="button"
                    onClick={() => setShowAdditionalInfo(!showAdditionalInfo)}
                    className="flex items-center justify-between w-full"
                  >
                    <CardTitle>Datos del Cliente</CardTitle>
                    {showAdditionalInfo ? (
                      <ChevronUp className="h-5 w-5" />
                    ) : (
                      <ChevronDown className="h-5 w-5" />
                    )}
                  </button>
                </CardHeader>
                <AnimatePresence>
                  {showAdditionalInfo && (
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: 'auto' }}
                      exit={{ height: 0 }}
                    >
                      <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="text-sm text-gray-600">Teléfono</label>
                            <p className="font-medium">{clienteData.telefono}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">Email</label>
                            <p className="font-medium">{clienteData.email}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">Dirección</label>
                            <p className="font-medium">{clienteData.direccion}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">Estado</label>
                            <Badge>{clienteData.estado}</Badge>
                          </div>
                        </div>
                      </CardContent>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            )}

            {/* Datos del Préstamo */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Datos del Préstamo
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Nuevos campos: Valor Activo y Anticipo */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Valor Activo (USD) <span className="text-blue-600">(Manual)</span>
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={valorActivo === 0 ? '' : valorActivo}
                      readOnly
                      className="bg-gray-100"
                      placeholder="Se carga según el modelo seleccionado"
                      disabled={isReadOnly || !formData.modelo_vehiculo}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Anticipo (USD) <span className="text-green-600">(Automático - 30%)</span>
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={anticipo === 0 ? '' : anticipo.toFixed(2)}
                      readOnly
                      className="bg-gray-100"
                      placeholder="Calculado automáticamente"
                    />
                    <p className="text-xs text-gray-500 mt-1">30% del Valor Activo</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Total de Financiamiento (USD) <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.total_financiamiento === 0 ? '' : formData.total_financiamiento}
                      readOnly
                      className="bg-gray-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">Calculado automáticamente (Valor Activo - Anticipo)</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Modalidad de Pago <span className="text-red-500">*</span>
                    </label>
                    <Select
                      value={formData.modalidad_pago}
                      onValueChange={(value: any) => setFormData({ 
                        ...formData, 
                        modalidad_pago: value 
                      })}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="MENSUAL">Mensual</SelectItem>
                        <SelectItem value="QUINCENAL">Quincenal</SelectItem>
                        <SelectItem value="SEMANAL">Semanal</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Número de Cuotas <span className="text-red-500">*</span></label>
                    <Input
                      type="number"
                      min="1"
                      max="12"
                      value={numeroCuotas}
                      onChange={(e) => {
                        const value = parseInt(e.target.value) || 12
                        // Validar que esté entre 1 y 12
                        const validValue = Math.max(1, Math.min(12, value))
                        setNumeroCuotas(validValue)
                      }}
                      disabled={isReadOnly}
                    />
                    <p className="text-xs text-gray-500 mt-1">Mínimo: 1, Máximo: 12</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Cuota por Período (USD)</label>
                    <Input
                      value={cuotaPeriodo.toFixed(2)}
                      disabled
                      className="bg-gray-50"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Fecha de Requerimiento <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="date"
                      value={formData.fecha_requerimiento}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        fecha_requerimiento: e.target.value 
                      })}
                      disabled={isReadOnly}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Tasa de Interés (%)
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.tasa_interes === 0 ? '' : formData.tasa_interes}
                      onChange={(e) => {
                        const value = e.target.value
                        const numericValue = value === '' ? 0 : parseFloat(value.replace(/^0+/, '').replace(/^\./, '0.'))
                        setFormData({ 
                          ...formData, 
                          tasa_interes: isNaN(numericValue) ? 0 : numericValue
                        })
                      }}
                      onBlur={(e) => {
                        const value = parseFloat(e.target.value)
                        if (value >= 0) {
                          setFormData({ ...formData, tasa_interes: value })
                        }
                      }}
                      disabled={isReadOnly}
                    />
                  </div>
                </div>

                {prestamo && prestamo.estado === 'APROBADO' && (
                  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="font-semibold text-blue-900 mb-2">📅 Fecha de Desembolso (Día/Mes/Año)</h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Día <span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="number"
                          min="1"
                          max="31"
                          value={formData.fecha_base_calculo ? formData.fecha_base_calculo.split('-')[2] : ''}
                          onChange={(e) => {
                            const dia = parseInt(e.target.value) || 1
                            const fechaActual = formData.fecha_base_calculo || getCurrentDate()
                            const [año, mes] = fechaActual.split('-')
                            const nuevaFecha = `${año}-${mes}-${String(dia).padStart(2, '0')}`
                            setFormData({ ...formData, fecha_base_calculo: nuevaFecha })
                          }}
                          disabled={isReadOnly}
                          placeholder="DD"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Mes <span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="number"
                          min="1"
                          max="12"
                          value={formData.fecha_base_calculo ? formData.fecha_base_calculo.split('-')[1] : ''}
                          onChange={(e) => {
                            const mes = parseInt(e.target.value) || 1
                            const fechaActual = formData.fecha_base_calculo || getCurrentDate()
                            const [año, , dia] = fechaActual.split('-')
                            const nuevaFecha = `${año}-${String(mes).padStart(2, '0')}-${dia}`
                            setFormData({ ...formData, fecha_base_calculo: nuevaFecha })
                          }}
                          disabled={isReadOnly}
                          placeholder="MM"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Año <span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="number"
                          min="2024"
                          max="2030"
                          value={formData.fecha_base_calculo ? formData.fecha_base_calculo.split('-')[0] : ''}
                          onChange={(e) => {
                            const año = parseInt(e.target.value) || new Date().getFullYear()
                            const fechaActual = formData.fecha_base_calculo || getCurrentDate()
                            const [, mes, dia] = fechaActual.split('-')
                            const nuevaFecha = `${año}-${mes}-${dia}`
                            setFormData({ ...formData, fecha_base_calculo: nuevaFecha })
                          }}
                          disabled={isReadOnly}
                          placeholder="YYYY"
                        />
                      </div>
                    </div>
                    <p className="text-xs text-blue-700 mt-2">
                      Esta es la fecha desde la cual se calcularán las cuotas de la tabla de amortización
                    </p>
                  </div>
                )}

                {/* Eliminados campos duplicados de Producto y Analista Asignado */}

                {/* Nuevos campos de configuración (sin Modelo aquí) */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Concesionario
                    </label>
                    <Select
                      value={formData.concesionario ?? ''}
                      onValueChange={(value) => setFormData({ 
                        ...formData, 
                        concesionario: value
                      })}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger>
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
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Analista
                    </label>
                    <Select
                      value={formData.analista ?? ''}
                      onValueChange={(value) => setFormData({ 
                        ...formData, 
                        analista: value
                      })}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger>
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
                  </div>

                  {/* Modelo movido arriba */}
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Observaciones</label>
                  <Textarea
                    value={formData.observaciones || ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      observaciones: e.target.value 
                    })}
                    disabled={isReadOnly}
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Botones de Aprobación (Solo ADMIN) */}
            {prestamo && canApprove && prestamo.estado === 'EN_REVISION' && (
              <Card className="border-yellow-200 bg-yellow-50">
                <CardContent className="pt-4">
                  <div className="flex gap-3">
                    <Button
                      type="button"
                      onClick={() => {
                        // TODO: Implementar aprobación
                        console.log('Aprobar préstamo')
                      }}
                      className="flex-1 bg-green-600 hover:bg-green-700"
                    >
                      <AlertCircle className="h-4 w-4 mr-2" />
                      Aprobar
                    </Button>
                    <Button
                      type="button"
                      onClick={() => {
                        // TODO: Implementar rechazo
                        console.log('Rechazar préstamo')
                      }}
                      variant="destructive"
                      className="flex-1"
                    >
                      <X className="h-4 w-4 mr-2" />
                      Rechazar
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Botones */}
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              {!isReadOnly && (
                <Button type="submit">
                  <Save className="h-4 w-4 mr-2" />
                  {prestamo ? 'Actualizar' : 'Crear'} Préstamo
                </Button>
              )}
              {isReadOnly && (
                <Button disabled>
                  Modo Solo Lectura
                </Button>
              )}
            </div>
          </form>

          {/* Modal de Validación de Préstamos Existentes */}
          {showModalValidacion && resumenPrestamos && resumenPrestamos.tiene_prestamos && (
            <ModalValidacionPrestamoExistente
              prestamos={resumenPrestamos.prestamos || []}
              totalSaldo={resumenPrestamos.total_saldo_pendiente || 0}
              totalCuotasMora={resumenPrestamos.total_cuotas_mora || 0}
              onConfirm={handleConfirmarAutorizacion}
              onCancel={() => {
                setShowModalValidacion(false)
                setResumenPrestamos(null)
                setJustificacionAutorizacion('')
              }}
            />
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
