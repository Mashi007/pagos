import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  DollarSign,
  Calendar,
  CreditCard,
  FileText,
  Building2,
  Upload,
  Loader2,
  CheckCircle,
  AlertCircle,
  Info,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { pagoService, type PagoCreate } from '../../services/pagoService'
import { usePrestamosByCedula, usePrestamo } from '../../hooks/usePrestamos'
import { useDebounce } from '../../hooks/useDebounce'
import { getErrorMessage, isAxiosError, getErrorDetail } from '../../types/errors'

interface RegistrarPagoFormProps {
  onClose: () => void
  onSuccess: () => void
  pagoInicial?: Partial<PagoCreate>
  pagoId?: number  // âœ… Si está presente, es modo edición
}

export function RegistrarPagoForm({ onClose, onSuccess, pagoInicial, pagoId }: RegistrarPagoFormProps) {
  const isEditing = !!pagoId
  const [formData, setFormData] = useState<PagoCreate>({
    cedula_cliente: pagoInicial?.cedula_cliente || '',
    prestamo_id: pagoInicial?.prestamo_id || null,
    fecha_pago: pagoInicial?.fecha_pago || new Date().toISOString().split('T')[0],
    monto_pagado: pagoInicial?.monto_pagado || 0,
    numero_documento: pagoInicial?.numero_documento || '',
    institucion_bancaria: pagoInicial?.institucion_bancaria || null,
    notas: pagoInicial?.notas || null,
  })

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Debounce de la cédula para buscar préstamos
  const debouncedCedula = useDebounce(formData.cedula_cliente, 500)

  // Buscar préstamos cuando cambia la cédula (con al menos 2 caracteres)
  const { data: prestamos, isLoading: isLoadingPrestamos } = usePrestamosByCedula(
    debouncedCedula.length >= 2 ? debouncedCedula : ''
  )

  // Obtener información del préstamo seleccionado para validaciones
  const { data: prestamoSeleccionado } = usePrestamo(formData.prestamo_id || 0)

  // Auto-seleccionar préstamo si hay solo uno disponible
  useEffect(() => {
    if (prestamos && prestamos.length === 1 && !formData.prestamo_id) {
      setFormData(prev => ({ ...prev, prestamo_id: prestamos[0].id }))
    } else if (prestamos && prestamos.length === 0) {
      // Limpiar ID si no hay préstamos
      setFormData(prev => ({ ...prev, prestamo_id: null }))
    }
  }, [prestamos])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // âœ… VALIDACIONES SEGÃšN CRITERIOS DOCUMENTADOS

    // Validar campos básicos
    const newErrors: Record<string, string> = {}
    if (!formData.cedula_cliente) {
      newErrors.cedula_cliente = 'Cédula requerida'
    }

    // Si hay préstamos disponibles, el ID de préstamo es obligatorio
    if (prestamos && prestamos.length > 0 && !formData.prestamo_id) {
      newErrors.prestamo_id = 'Debe seleccionar un crédito'
    }

    // âœ… CRITERIO 1: Verificación de cédula del pago vs cédula del préstamo
    if (formData.prestamo_id && prestamoSeleccionado) {
      if (formData.cedula_cliente !== prestamoSeleccionado.cedula) {
        newErrors.cedula_cliente = `La cédula del pago (${formData.cedula_cliente}) no coincide con la cédula del préstamo (${prestamoSeleccionado.cedula}). El pago solo se aplicará si las cédulas coinciden.`
        newErrors.prestamo_id = 'La cédula del pago debe coincidir con la cédula del préstamo seleccionado'
      }
    }

    // âœ… CRITERIO 2: Validación de monto
    if (!formData.monto_pagado || formData.monto_pagado <= 0) {
      newErrors.monto_pagado = 'Monto inválido. Debe ser mayor a cero'
    } else if (formData.monto_pagado > 1000000) {
      newErrors.monto_pagado = 'Monto muy alto. Por favor verifique el valor'
    }

    // âœ… CRITERIO 3: Validación y normalización de número de documento
    // Normalizar formato científico si existe (ej: 7.40087E+14 -> 740087000000000)
    let numeroDocumentoNormalizado = formData.numero_documento.trim()
    if (numeroDocumentoNormalizado && (/[eE]/.test(numeroDocumentoNormalizado))) {
      try {
        const numeroFloat = parseFloat(numeroDocumentoNormalizado)
        numeroDocumentoNormalizado = Math.floor(numeroFloat).toString()
        // Mostrar advertencia al usuario
        console.warn(`âš ï¸ Número de documento normalizado de formato científico: ${formData.numero_documento} -> ${numeroDocumentoNormalizado}`)
      } catch (e) {
        console.error('Error normalizando número de documento:', e)
      }
    }
    
    if (!numeroDocumentoNormalizado || numeroDocumentoNormalizado === '') {
      newErrors.numero_documento = 'Número de documento requerido'
    }

    // âœ… CRITERIO 4: Validación de fecha
    if (!formData.fecha_pago) {
      newErrors.fecha_pago = 'Fecha de pago requerida'
    } else {
      const fechaPago = new Date(formData.fecha_pago)
      const hoy = new Date()
      hoy.setHours(23, 59, 59, 999) // Permitir hasta el final del día
      if (fechaPago > hoy) {
        newErrors.fecha_pago = 'La fecha de pago no puede ser futura'
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    setIsSubmitting(true)
    try {
      // Aplicar normalización al número de documento antes de enviar
      const datosEnvio = {
        ...formData,
        numero_documento: numeroDocumentoNormalizado
      }
      
      if (isEditing && pagoId) {
        console.log('ðŸ”„ Iniciando actualización de pago...', { pagoId, datosEnvio })
        const result = await pagoService.updatePago(pagoId, datosEnvio)
        console.log('âœ… Pago actualizado exitosamente:', result)
      } else {
        console.log('ðŸ”„ Iniciando registro de pago...', datosEnvio)
        const result = await pagoService.createPago(datosEnvio)
        console.log('âœ… Pago registrado exitosamente:', result)
      }
      onSuccess()
    } catch (error: unknown) {
      console.error(`âŒ Error ${isEditing ? 'actualizando' : 'registrando'} pago:`, error)
      let errorMessage = getErrorMessage(error)
      if (isAxiosError(error)) {
        const detail = getErrorDetail(error)
        if (detail) {
          errorMessage = detail
        }
      }
      setErrors({ general: errorMessage || `Error al ${isEditing ? 'actualizar' : 'registrar'} el pago` })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95 }}
          className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
            <h2 className="text-xl font-bold">{isEditing ? 'Editar Pago' : 'Registrar Pago'}</h2>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Error general */}
            {errors.general && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {errors.general}
              </div>
            )}

            {/* Cédula e ID Préstamo */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Cédula Cliente <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <CreditCard className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.cedula_cliente}
                    onChange={e => {
                      setFormData({ ...formData, cedula_cliente: e.target.value, prestamo_id: null })
                    }}
                    className={`pl-10 ${errors.cedula_cliente ? 'border-red-500' : ''}`}
                    placeholder="V12345678"
                  />
                </div>
                {errors.cedula_cliente && (
                  <p className="text-sm text-red-600">{errors.cedula_cliente}</p>
                )}
                {isLoadingPrestamos && formData.cedula_cliente.length >= 2 && (
                  <p className="text-xs text-blue-600 flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Buscando préstamos...
                  </p>
                )}
                {!isLoadingPrestamos && prestamos && prestamos.length > 0 && formData.cedula_cliente.length >= 2 && (
                  <p className="text-xs text-green-600 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    {prestamos.length} préstamo{prestamos.length !== 1 ? 's' : ''} encontrado{prestamos.length !== 1 ? 's' : ''}
                  </p>
                )}
                {!isLoadingPrestamos && prestamos && prestamos.length === 0 && formData.cedula_cliente.length >= 2 && (
                  <p className="text-xs text-yellow-600">
                    No se encontraron préstamos para esta cédula
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  ID Crédito {formData.cedula_cliente && prestamos && prestamos.length > 0 && <span className="text-red-500">*</span>}
                </label>
                {prestamos && prestamos.length > 0 ? (
                  <Select
                    value={formData.prestamo_id?.toString() || undefined}
                    onValueChange={(value) => setFormData({ ...formData, prestamo_id: parseInt(value) })}
                  >
                    <SelectTrigger className={errors.prestamo_id ? 'border-red-500' : ''}>
                      <SelectValue placeholder="Seleccione un crédito" />
                    </SelectTrigger>
                    <SelectContent>
                      {prestamos.map((prestamo) => (
                        <SelectItem key={prestamo.id} value={prestamo.id.toString()}>
                          ID {prestamo.id} - ${Number(prestamo.total_financiamiento ?? 0).toFixed(2)} - {prestamo.estado}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    type="number"
                    value={formData.prestamo_id || ''}
                    onChange={e => setFormData({ ...formData, prestamo_id: e.target.value ? parseInt(e.target.value) : null })}
                    placeholder="ID del crédito"
                    disabled={!formData.cedula_cliente}
                    className={errors.prestamo_id ? 'border-red-500' : ''}
                  />
                )}
                {(errors.prestamo_id || (formData.cedula_cliente && prestamos && prestamos.length > 0 && !formData.prestamo_id)) && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {errors.prestamo_id || 'Debe seleccionar un crédito'}
                  </p>
                )}

                {/* âœ… Verificación de cédula del préstamo vs cédula del pago */}
                {formData.prestamo_id && prestamoSeleccionado && formData.cedula_cliente && (
                  <div className={`text-xs p-2 rounded flex items-start gap-2 ${
                    formData.cedula_cliente === prestamoSeleccionado.cedula
                      ? 'bg-green-50 text-green-700 border border-green-200'
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}>
                    {formData.cedula_cliente === prestamoSeleccionado.cedula ? (
                      <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    )}
                    <div>
                      {formData.cedula_cliente === prestamoSeleccionado.cedula ? (
                        <span className="font-medium">âœ… Cédulas coinciden</span>
                      ) : (
                        <div>
                          <span className="font-medium">âš ï¸ Cédulas no coinciden</span>
                          <p className="mt-1">
                            Cédula del pago: <strong>{formData.cedula_cliente}</strong><br />
                            Cédula del préstamo: <strong>{prestamoSeleccionado.cedula}</strong><br />
                            <span className="text-xs">El pago solo se aplicará si las cédulas coinciden.</span>
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Fecha y Monto */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Fecha de Pago <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="date"
                    value={formData.fecha_pago}
                    onChange={e => setFormData({ ...formData, fecha_pago: e.target.value })}
                    className={`pl-10 ${errors.fecha_pago ? 'border-red-500' : ''}`}
                    max={new Date().toISOString().split('T')[0]} // âœ… No permitir fechas futuras
                  />
                </div>
                {errors.fecha_pago && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {errors.fecha_pago}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Monto Pagado <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.monto_pagado}
                    onChange={e => setFormData({ ...formData, monto_pagado: parseFloat(e.target.value) || 0 })}
                    className={`pl-10 ${errors.monto_pagado ? 'border-red-500' : ''}`}
                    placeholder="0.00"
                  />
                </div>
                {errors.monto_pagado && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {errors.monto_pagado}
                  </p>
                )}

                {/* âœ… Información sobre cómo se aplicará el pago */}
                {formData.monto_pagado > 0 && formData.prestamo_id && prestamoSeleccionado && (
                  <div className="bg-blue-50 border border-blue-200 rounded p-2 text-xs text-blue-700">
                    <div className="flex items-start gap-2">
                      <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="font-medium mb-1">â„¹ï¸ Cómo se aplicará el pago:</p>
                        <ul className="list-disc list-inside space-y-1 ml-2">
                          <li>Se aplicará a las cuotas más antiguas primero (por fecha de vencimiento)</li>
                          <li>Se distribuirá proporcionalmente entre capital e interés</li>
                          {formData.monto_pagado >= 500 && (
                            <li>Si el monto cubre una cuota completa y sobra, el exceso se aplicará a la siguiente cuota</li>
                          )}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Institución Bancaria */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Institución Bancaria
              </label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  type="text"
                  value={formData.institucion_bancaria || ''}
                  onChange={e => setFormData({ ...formData, institucion_bancaria: e.target.value || null })}
                  className="pl-10"
                  placeholder="Banco de Venezuela, Banesco, etc."
                />
              </div>
            </div>

            {/* Número de Documento */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Número de Documento <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <FileText className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  type="text"
                  value={formData.numero_documento}
                  onChange={e => setFormData({ ...formData, numero_documento: e.target.value })}
                  className={`pl-10 ${errors.numero_documento ? 'border-red-500' : ''}`}
                  placeholder="Número de referencia"
                />
              </div>
              {errors.numero_documento && (
                <p className="text-sm text-red-600">{errors.numero_documento}</p>
              )}
            </div>

            {/* Notas */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Notas (Opcional)
              </label>
              <Textarea
                value={formData.notas || ''}
                onChange={e => setFormData({ ...formData, notas: e.target.value || null })}
                placeholder="Observaciones adicionales"
                rows={3}
              />
            </div>

            {/* Botones */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    {isEditing ? 'Actualizando...' : 'Registrando...'}
                  </>
                ) : (
                  <>
                    <DollarSign className="w-4 h-4 mr-2" />
                    {isEditing ? 'Actualizar Pago' : 'Registrar Pago'}
                  </>
                )}
              </Button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

