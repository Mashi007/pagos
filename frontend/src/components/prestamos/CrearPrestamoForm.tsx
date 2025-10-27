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
import { Prestamo, PrestamoForm } from '@/types'

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
    tasa_interes: prestamo?.tasa_interes || 0,
    observaciones: prestamo?.observaciones || '',
  })

  const [valorActivo, setValorActivo] = useState<number>(0)
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
    
    // Validar Valor Activo (solo para nuevos préstamos)
    if (!prestamo && valorActivo <= 0) {
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
    // Para nuevos préstamos, requerir > 0
    // Para edición, solo validar si está usando los nuevos campos (valorActivo y anticipo)
    if (!prestamo && (!formData.total_financiamiento || formData.total_financiamiento <= 0)) {
      errors.push('El Total de Financiamiento debe ser mayor a 0')
    } else if (prestamo && valorActivo > 0 && (!formData.total_financiamiento || formData.total_financiamiento <= 0)) {
      // Si está editando y usó los nuevos campos, validar
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
    
    // Si hay errores, mostrar mensajes
    if (errors.length > 0) {
      errors.forEach(error => {
        toast.error(error)
      })
      return
    }

    try {
      if (prestamo) {
        // Editar préstamo existente
        await updatePrestamo.mutateAsync({
          id: prestamo.id,
          data: formData
        })
        toast.success('Préstamo actualizado exitosamente')
      } else {
        // Crear nuevo préstamo
        await createPrestamo.mutateAsync(formData as PrestamoForm)
        toast.success('Préstamo creado exitosamente')
      }
      
      onSuccess()
      onClose()
    } catch (error) {
      toast.error('Error al guardar el préstamo')
      console.error('Error saving loan:', error)
    }
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
                      Valor Activo (USD) <span className="text-green-600">(Automático)</span>
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={valorActivo === 0 ? '' : valorActivo}
                      onChange={(e) => {
                        const value = e.target.value === '' ? 0 : parseFloat(e.target.value) || 0
                        setValorActivo(value)
                      }}
                      placeholder="Se llena automáticamente"
                      disabled={isReadOnly}
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

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Producto</label>
                    <Input
                      value={formData.producto}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        producto: e.target.value 
                      })}
                      disabled={isReadOnly || !!clienteData}
                      placeholder="Modelo de vehículo"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Analista Asignado</label>
                    <Input
                      value={formData.producto_financiero}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        producto_financiero: e.target.value 
                      })}
                      disabled={isReadOnly || !!clienteData}
                      placeholder="Nombre del analista"
                    />
                  </div>
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
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
