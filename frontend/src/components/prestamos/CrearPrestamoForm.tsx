import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  DollarSign, 
  Calendar, 
  CreditCard, 
  Search,
  X,
  ChevronDown,
  ChevronUp,
  Save,
  AlertCircle
} from 'lucide-react'
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
  
  const [formData, setFormData] = useState<Partial<PrestamoForm>>({
    cedula: prestamo?.cedula || '',
    total_financiamiento: prestamo?.total_financiamiento || 0,
    modalidad_pago: prestamo?.modalidad_pago || 'MENSUAL',
    fecha_requerimiento: prestamo?.fecha_requerimiento || '',
    producto: prestamo?.producto || '',
    producto_financiero: prestamo?.producto_financiero || '',
    tasa_interes: prestamo?.tasa_interes || 0,
    observaciones: prestamo?.observaciones || '',
  })

  const [showAdditionalInfo, setShowAdditionalInfo] = useState(false)
  const [clienteData, setClienteData] = useState<any>(null)
  const [numeroCuotas, setNumeroCuotas] = useState<number>(0)
  const [cuotaPeriodo, setCuotaPeriodo] = useState<number>(0)

  // Buscar cliente por cédula
  const { data: clienteInfo, isLoading: isLoadingCliente } = useSearchClientes(formData.cedula || '')

  // Calcular cuotas automáticamente
  const calcularCuotas = (total: number, modalidad: string) => {
    let cuotas = 36 // Default MENSUAL
    if (modalidad === 'QUINCENAL') cuotas = 72
    if (modalidad === 'SEMANAL') cuotas = 144
    
    const cuota = total / cuotas
    setNumeroCuotas(cuotas)
    setCuotaPeriodo(cuota)
  }

  // Cuando cambia el monto o modalidad, recalcular cuotas
  useEffect(() => {
    if (formData.total_financiamiento && formData.modalidad_pago) {
      calcularCuotas(formData.total_financiamiento, formData.modalidad_pago)
    }
  }, [formData.total_financiamiento, formData.modalidad_pago])

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
    }
  }, [clienteInfo])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.cedula || !formData.total_financiamiento || !formData.modalidad_pago) {
      return
    }

    if (prestamo) {
      // Editar préstamo existente
      await updatePrestamo.mutateAsync({
        id: prestamo.id,
        data: formData
      })
    } else {
      // Crear nuevo préstamo
      await createPrestamo.mutateAsync(formData as PrestamoForm)
    }
    
    onSuccess()
    onClose()
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
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
            <h2 className="text-xl font-bold">
              {prestamo ? 'Editar Préstamo' : 'Nuevo Préstamo'}
            </h2>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
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

                {clienteData && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="font-semibold text-green-800">{clienteData.nombres}</p>
                    <p className="text-sm text-green-700">Cliente encontrado</p>
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
                      onChange={(e) => {
                        const value = e.target.value
                        // Eliminar ceros a la izquierda y manejar strings vacíos
                        const numericValue = value === '' ? 0 : parseFloat(value.replace(/^0+/, '').replace(/^\./, '0.'))
                        setFormData({ 
                          ...formData, 
                          total_financiamiento: isNaN(numericValue) ? 0 : numericValue
                        })
                      }}
                      onBlur={(e) => {
                        // Asegurar que el valor final no empiece con 0
                        const value = parseFloat(e.target.value)
                        if (value >= 0) {
                          setFormData({ ...formData, total_financiamiento: value })
                        }
                      }}
                      disabled={isReadOnly}
                    />
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
                    <label className="block text-sm font-medium mb-1">Número de Cuotas</label>
                    <Input
                      value={numeroCuotas}
                      disabled
                      className="bg-gray-50"
                    />
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
