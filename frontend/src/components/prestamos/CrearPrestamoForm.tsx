import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { 
  User, 
  DollarSign, 
  Calendar, 
  CreditCard,
  Loader2,
  CheckCircle,
  AlertCircle,
  X,
  Search
} from 'lucide-react'
import { prestamoService, PrestamoCreate, PrestamoUpdate } from '@/services/prestamoService'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface ClienteData {
  id: number
  cedula: string
  nombres: string
  apellidos: string
  telefono: string
  email: string
  direccion: string
}

interface CrearPrestamoFormProps {
  prestamo?: any // Prestamo para editar
  onSuccess?: () => void
  onCancel?: () => void
}

export function CrearPrestamoForm({ prestamo, onSuccess, onCancel }: CrearPrestamoFormProps) {
  const queryClient = useQueryClient()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSearchingClient, setIsSearchingClient] = useState(false)
  const [clienteEncontrado, setClienteEncontrado] = useState<ClienteData | null>(null)
  const [cedulaError, setCedulaError] = useState('')

  // Form state
  const [formData, setFormData] = useState<PrestamoCreate>({
    cliente_id: 0,
    monto_total: 0,
    monto_financiado: 0,
    monto_inicial: 0,
    tasa_interes: 0,
    numero_cuotas: 12,
    monto_cuota: 0,
    fecha_aprobacion: new Date().toISOString().split('T')[0],
    fecha_desembolso: '',
    fecha_primer_vencimiento: '',
    modalidad: 'MENSUAL',
    destino_credito: '',
    observaciones: ''
  })

  // Auto-rellenar si es edición
  useEffect(() => {
    if (prestamo) {
      setFormData({
        cliente_id: prestamo.cliente_id,
        monto_total: prestamo.monto_total,
        monto_financiado: prestamo.monto_financiado,
        monto_inicial: prestamo.monto_inicial || 0,
        tasa_interes: prestamo.tasa_interes || 0,
        numero_cuotas: prestamo.numero_cuotas,
        monto_cuota: prestamo.monto_cuota,
        fecha_aprobacion: prestamo.fecha_aprobacion || new Date().toISOString().split('T')[0],
        fecha_desembolso: prestamo.fecha_desembolso || '',
        fecha_primer_vencimiento: prestamo.fecha_primer_vencimiento || '',
        modalidad: prestamo.modalidad || 'MENSUAL',
        destino_credito: prestamo.destino_credito || '',
        observaciones: prestamo.observaciones || ''
      })
    }
  }, [prestamo])

  // Función para buscar cliente por cédula
  const buscarCliente = async (cedula: string) => {
    if (!cedula || cedula.length < 8) {
      setCedulaError('')
      setClienteEncontrado(null)
      return
    }

    setIsSearchingClient(true)
    setCedulaError('')

    try {
      const cliente = await prestamoService.buscarClientePorCedula(cedula)
      setClienteEncontrado(cliente)
      setFormData(prev => ({
        ...prev,
        cliente_id: cliente.id
      }))
      toast.success(`✅ Cliente encontrado: ${cliente.nombres} ${cliente.apellidos}`)
    } catch (error) {
      setCedulaError('Cliente no encontrado')
      setClienteEncontrado(null)
      setFormData(prev => ({
        ...prev,
        cliente_id: 0
      }))
    } finally {
      setIsSearchingClient(false)
    }
  }

  // Calcular cuota automáticamente
  useEffect(() => {
    if (formData.monto_financiado && formData.numero_cuotas) {
      const cuota = formData.monto_financiado / formData.numero_cuotas
      setFormData(prev => ({
        ...prev,
        monto_cuota: Math.round(cuota * 100) / 100
      }))
    }
  }, [formData.monto_financiado, formData.numero_cuotas])

  // Calcular fecha de primer vencimiento
  useEffect(() => {
    if (formData.fecha_aprobacion && formData.modalidad) {
      const fechaAprobacion = new Date(formData.fecha_aprobacion)
      let diasSumar = 30 // MENSUAL por defecto
      
      switch (formData.modalidad) {
        case 'SEMANAL':
          diasSumar = 7
          break
        case 'QUINCENAL':
          diasSumar = 15
          break
        case 'MENSUAL':
          diasSumar = 30
          break
        case 'BIMESTRAL':
          diasSumar = 60
          break
      }
      
      const fechaVencimiento = new Date(fechaAprobacion)
      fechaVencimiento.setDate(fechaAprobacion.getDate() + diasSumar)
      
      setFormData(prev => ({
        ...prev,
        fecha_primer_vencimiento: fechaVencimiento.toISOString().split('T')[0]
      }))
    }
  }, [formData.fecha_aprobacion, formData.modalidad])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!clienteEncontrado && !prestamo) {
      toast.error('❌ Debe buscar un cliente válido')
      return
    }

    setIsSubmitting(true)

    try {
      if (prestamo) {
        // Actualizar préstamo existente
        const updateData: PrestamoUpdate = {
          monto_total: formData.monto_total,
          monto_financiado: formData.monto_financiado,
          monto_inicial: formData.monto_inicial,
          tasa_interes: formData.tasa_interes,
          numero_cuotas: formData.numero_cuotas,
          monto_cuota: formData.monto_cuota,
          fecha_aprobacion: formData.fecha_aprobacion,
          fecha_desembolso: formData.fecha_desembolso || undefined,
          fecha_primer_vencimiento: formData.fecha_primer_vencimiento,
          modalidad: formData.modalidad,
          destino_credito: formData.destino_credito || undefined,
          observaciones: formData.observaciones || undefined
        }
        
        await prestamoService.actualizarPrestamo(prestamo.id, updateData)
        toast.success('✅ Préstamo actualizado exitosamente')
      } else {
        // Crear nuevo préstamo
        await prestamoService.crearPrestamo(formData)
        toast.success('✅ Préstamo creado exitosamente')
      }

      // Refrescar datos
      queryClient.invalidateQueries({ queryKey: ['prestamos-list'] })
      queryClient.invalidateQueries({ queryKey: ['prestamos-stats'] })
      
      // Cerrar formulario
      onSuccess?.()
      
    } catch (error) {
      console.error('Error al guardar préstamo:', error)
      toast.error('❌ Error al guardar préstamo')
    } finally {
      setIsSubmitting(false)
    }
  }

  const resetForm = () => {
    setFormData({
      cliente_id: 0,
      monto_total: 0,
      monto_financiado: 0,
      monto_inicial: 0,
      tasa_interes: 0,
      numero_cuotas: 12,
      monto_cuota: 0,
      fecha_aprobacion: new Date().toISOString().split('T')[0],
      fecha_desembolso: '',
      fecha_primer_vencimiento: '',
      modalidad: 'MENSUAL',
      destino_credito: '',
      observaciones: ''
    })
    setClienteEncontrado(null)
    setCedulaError('')
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
    >
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold flex items-center">
              <CreditCard className="mr-2 h-6 w-6" />
              {prestamo ? 'Editar Préstamo' : 'Nuevo Préstamo'}
            </h2>
            <Button variant="ghost" size="sm" onClick={onCancel}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Búsqueda de Cliente */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <User className="mr-2 h-5 w-5" />
                  Datos del Cliente
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label htmlFor="cedula" className="block text-sm font-medium text-gray-700 mb-1">Cédula del Cliente</label>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 relative">
                      <Input
                        id="cedula"
                        placeholder="Ej: V-12345678"
                        onChange={(e) => buscarCliente(e.target.value)}
                        className={cedulaError ? 'border-red-500' : ''}
                      />
                      {isSearchingClient && (
                        <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 animate-spin text-blue-600" />
                      )}
                    </div>
                  </div>
                  {cedulaError && (
                    <p className="text-sm text-red-600 mt-1">{cedulaError}</p>
                  )}
                </div>

                {/* Datos del Cliente Encontrado */}
                {clienteEncontrado && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 bg-green-50 border border-green-200 rounded-lg"
                  >
                    <div className="flex items-center mb-2">
                      <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
                      <span className="font-semibold text-green-800">Cliente Encontrado</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium">Nombre:</span> {clienteEncontrado.nombres} {clienteEncontrado.apellidos}
                      </div>
                      <div>
                        <span className="font-medium">Teléfono:</span> {clienteEncontrado.telefono}
                      </div>
                      <div>
                        <span className="font-medium">Email:</span> {clienteEncontrado.email}
                      </div>
                      <div>
                        <span className="font-medium">Dirección:</span> {clienteEncontrado.direccion}
                      </div>
                    </div>
                  </motion.div>
                )}
              </CardContent>
            </Card>

            {/* Datos del Préstamo */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <DollarSign className="mr-2 h-5 w-5" />
                  Datos del Préstamo
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="monto_total" className="block text-sm font-medium text-gray-700 mb-1">Monto Total</label>
                    <Input
                      id="monto_total"
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.monto_total}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        monto_total: parseFloat(e.target.value) || 0
                      }))}
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="monto_financiado" className="block text-sm font-medium text-gray-700 mb-1">Monto Financiado</label>
                    <Input
                      id="monto_financiado"
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.monto_financiado}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        monto_financiado: parseFloat(e.target.value) || 0
                      }))}
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="monto_inicial" className="block text-sm font-medium text-gray-700 mb-1">Cuota Inicial</label>
                    <Input
                      id="monto_inicial"
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.monto_inicial}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        monto_inicial: parseFloat(e.target.value) || 0
                      }))}
                    />
                  </div>
                  <div>
                    <label htmlFor="tasa_interes" className="block text-sm font-medium text-gray-700 mb-1">Tasa de Interés (%)</label>
                    <Input
                      id="tasa_interes"
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={formData.tasa_interes}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        tasa_interes: parseFloat(e.target.value) || 0
                      }))}
                    />
                  </div>
                  <div>
                    <label htmlFor="numero_cuotas" className="block text-sm font-medium text-gray-700 mb-1">Número de Cuotas</label>
                    <Input
                      id="numero_cuotas"
                      type="number"
                      min="1"
                      value={formData.numero_cuotas}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        numero_cuotas: parseInt(e.target.value) || 1
                      }))}
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="monto_cuota" className="block text-sm font-medium text-gray-700 mb-1">Monto por Cuota</label>
                    <Input
                      id="monto_cuota"
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.monto_cuota}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        monto_cuota: parseFloat(e.target.value) || 0
                      }))}
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="fecha_aprobacion" className="block text-sm font-medium text-gray-700 mb-1">Fecha de Aprobación</label>
                    <Input
                      id="fecha_aprobacion"
                      type="date"
                      value={formData.fecha_aprobacion}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        fecha_aprobacion: e.target.value
                      }))}
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="fecha_desembolso" className="block text-sm font-medium text-gray-700 mb-1">Fecha de Desembolso</label>
                    <Input
                      id="fecha_desembolso"
                      type="date"
                      value={formData.fecha_desembolso}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        fecha_desembolso: e.target.value
                      }))}
                    />
                  </div>
                  <div>
                    <label htmlFor="fecha_primer_vencimiento" className="block text-sm font-medium text-gray-700 mb-1">Primer Vencimiento</label>
                    <Input
                      id="fecha_primer_vencimiento"
                      type="date"
                      value={formData.fecha_primer_vencimiento}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        fecha_primer_vencimiento: e.target.value
                      }))}
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="modalidad" className="block text-sm font-medium text-gray-700 mb-1">Modalidad de Pago</label>
                    <Select value={formData.modalidad} onValueChange={(value) => setFormData(prev => ({ ...prev, modalidad: value }))}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="SEMANAL">Semanal</SelectItem>
                        <SelectItem value="QUINCENAL">Quincenal</SelectItem>
                        <SelectItem value="MENSUAL">Mensual</SelectItem>
                        <SelectItem value="BIMESTRAL">Bimestral</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <label htmlFor="destino_credito" className="block text-sm font-medium text-gray-700 mb-1">Destino del Crédito</label>
                  <Input
                    id="destino_credito"
                    value={formData.destino_credito}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      destino_credito: e.target.value
                    }))}
                    placeholder="Ej: Compra de vehículo"
                  />
                </div>

                <div>
                  <label htmlFor="observaciones" className="block text-sm font-medium text-gray-700 mb-1">Observaciones</label>
                  <Textarea
                    id="observaciones"
                    value={formData.observaciones}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      observaciones: e.target.value
                    }))}
                    placeholder="Observaciones adicionales..."
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Botones */}
            <div className="flex justify-end space-x-3">
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancelar
              </Button>
              <Button type="button" variant="outline" onClick={resetForm}>
                Limpiar
              </Button>
              <Button type="submit" disabled={isSubmitting || (!clienteEncontrado && !prestamo)}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  <>
                    <CreditCard className="h-4 w-4 mr-2" />
                    {prestamo ? 'Actualizar' : 'Crear'} Préstamo
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>
      </motion.div>
    </motion.div>
  )
}
