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
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { pagoService, type PagoCreate } from '@/services/pagoService'
import { usePrestamosByCedula } from '@/hooks/usePrestamos'
import { useDebounce } from '@/hooks/useDebounce'
import { getErrorMessage, isAxiosError, getErrorDetail } from '@/types/errors'

interface RegistrarPagoFormProps {
  onClose: () => void
  onSuccess: () => void
  pagoInicial?: Partial<PagoCreate>
  pagoId?: number  // ✅ Si está presente, es modo edición
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
    
    // Validar
    const newErrors: Record<string, string> = {}
    if (!formData.cedula_cliente) newErrors.cedula_cliente = 'Cédula requerida'
    
    // Si hay préstamos disponibles, el ID de préstamo es obligatorio
    if (prestamos && prestamos.length > 0 && !formData.prestamo_id) {
      newErrors.prestamo_id = 'Debe seleccionar un crédito'
    }
    
    if (!formData.monto_pagado || formData.monto_pagado <= 0) newErrors.monto_pagado = 'Monto inválido'
    if (!formData.numero_documento) newErrors.numero_documento = 'Número de documento requerido'
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    setIsSubmitting(true)
    try {
      if (isEditing && pagoId) {
        console.log('🔄 Iniciando actualización de pago...', { pagoId, formData })
        const result = await pagoService.updatePago(pagoId, formData)
        console.log('✅ Pago actualizado exitosamente:', result)
      } else {
        console.log('🔄 Iniciando registro de pago...', formData)
        const result = await pagoService.createPago(formData)
        console.log('✅ Pago registrado exitosamente:', result)
      }
      onSuccess()
    } catch (error: unknown) {
      console.error(`❌ Error ${isEditing ? 'actualizando' : 'registrando'} pago:`, error)
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
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccione un crédito" />
                    </SelectTrigger>
                    <SelectContent>
                      {prestamos.map((prestamo) => (
                        <SelectItem key={prestamo.id} value={prestamo.id.toString()}>
                          ID {prestamo.id} - ${prestamo.total_financiamiento?.toFixed(2)} - {prestamo.estado}
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
                  />
                )}
                {(errors.prestamo_id || (formData.cedula_cliente && prestamos && prestamos.length > 0 && !formData.prestamo_id)) && (
                  <p className="text-sm text-red-600">{errors.prestamo_id || 'Debe seleccionar un crédito'}</p>
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
                    className="pl-10"
                  />
                </div>
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
                  <p className="text-sm text-red-600">{errors.monto_pagado}</p>
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

