import { useState } from 'react'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { X, Calendar, CheckCircle2 } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { prestamoService } from '../../services/prestamoService'

interface AsignarFechaAprobacionModalProps {
  prestamo: any
  onClose: () => void
  onSuccess: () => void
}

export function AsignarFechaAprobacionModal({ prestamo, onClose, onSuccess }: AsignarFechaAprobacionModalProps) {
  const [fechaAprobacion, setFechaAprobacion] = useState<string>(
    prestamo.fecha_aprobacion 
      ? new Date(prestamo.fecha_aprobacion).toISOString().split('T')[0]
      : new Date().toISOString().split('T')[0]
  )
  const [isLoading, setIsLoading] = useState(false)

  const handleAsignarFecha = async () => {
    if (!fechaAprobacion) {
      toast.error('Debe seleccionar una fecha de aprobación')
      return
    }

    const mensajeConfirmacion =
      `¿Desea desembolsar el préstamo con fecha ${new Date(fechaAprobacion).toLocaleDateString()}?\n\n` +
      `Esta acción:\n` +
      `â€¢ Cambiará el estado a DESEMBOLSADO\n` +
      `â€¢ Generará la tabla de amortización\n` +
      `â€¢ Creará todas las cuotas\n` +
      `â€¢ Requiere calificación mínima de 70 puntos`

    if (!window.confirm(mensajeConfirmacion)) {
      return
    }

    setIsLoading(true)

    try {
      const resultado = await prestamoService.asignarFechaAprobacion(prestamo.id, fechaAprobacion)
      toast.success(
        `âœ… Préstamo desembolsado exitosamente. Estado: DESEMBOLSADO. ` +
        `Tabla de amortización generada con ${resultado.cuotas_recalculadas || 0} cuotas.`
      )
      onSuccess()
      onClose()
    } catch (error: any) {
      console.error('Error asignando fecha de aprobación:', error)
      toast.error(error.response?.data?.detail || error.message || 'Error al asignar fecha de aprobación')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-lg shadow-xl max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <Card>
          <CardHeader className="bg-gradient-to-r from-green-600 to-green-700 text-white">
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                Asignar Fecha de Aprobación - Préstamo #{prestamo.id}
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-white hover:bg-green-800"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            <div className="space-y-6">
              <div className="bg-green-50 p-4 rounded border border-green-200">
                <h5 className="font-semibold text-green-900 mb-4">ðŸ“… Fecha de Aprobación y Desembolso:</h5>
                <div className="bg-blue-50 p-3 rounded border border-blue-200 mb-4">
                  <p className="text-sm font-medium text-blue-900 mb-2">
                    âš ï¸ Requisitos para desembolsar:
                  </p>
                  <ul className="text-xs text-blue-800 list-disc list-inside space-y-1">
                    <li>Calificación mínima de evaluación de riesgo: 70 puntos</li>
                    <li>El préstamo debe estar en estado APROBADO</li>
                    <li>Se generará la tabla de amortización automáticamente</li>
                    <li>Se crearán todas las cuotas en la tabla de cuotas</li>
                    <li>El estado cambiará a DESEMBOLSADO (dinero entregado)</li>
                  </ul>
                </div>
                <p className="text-sm text-gray-700 mb-4">
                  Seleccione la fecha de aprobación del crédito. Esta fecha se utilizará como base 
                  para recalcular la tabla de amortización y determinar las fechas de vencimiento de las cuotas.
                </p>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Fecha de Aprobación <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <Input
                      type="date"
                      value={fechaAprobacion}
                      onChange={(e) => setFechaAprobacion(e.target.value)}
                      className="pl-10"
                      min={prestamo.fecha_registro ? new Date(prestamo.fecha_registro).toISOString().split('T')[0] : undefined}
                    />
                  </div>
                  <p className="text-xs text-gray-500">
                    Esta fecha será la base para calcular las fechas de vencimiento de todas las cuotas
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancelar
                </Button>
                <Button
                  type="button"
                  className="bg-green-600 hover:bg-green-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={handleAsignarFecha}
                  disabled={isLoading || !fechaAprobacion}
                  title={!fechaAprobacion ? 'Debe seleccionar una fecha de aprobación' : 'Asignar fecha y recalcular amortización'}
                >
                  {isLoading ? 'Asignando...' : 'Asignar Fecha y Recalcular'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
