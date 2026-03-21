import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
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
  const queryClient = useQueryClient()
  const [fechaAprobacion, setFechaAprobacion] = useState<string>(() => {
    if (prestamo.fecha_aprobacion) return new Date(prestamo.fecha_aprobacion).toISOString().split('T')[0]
    if (prestamo.fecha_requerimiento) return new Date(prestamo.fecha_requerimiento).toISOString().split('T')[0]
    return new Date().toISOString().split('T')[0]
  })
  const [isLoading, setIsLoading] = useState(false)

  const fechaRequerimientoStr = prestamo.fecha_requerimiento
    ? new Date(prestamo.fecha_requerimiento).toISOString().split('T')[0]
    : null

  const handleAsignarFecha = async () => {
    if (!fechaAprobacion) {
      toast.error('Debe seleccionar una fecha de aprobaciÃÂ³n')
      return
    }
    if (fechaRequerimientoStr && fechaAprobacion < fechaRequerimientoStr) {
      toast.error(`La fecha de aprobaciÃÂ³n debe ser igual o posterior a la fecha de requerimiento (${new Date(fechaRequerimientoStr).toLocaleDateString()})`)
      return
    }

    const mensajeConfirmacion =
      `ÃÂ¿Desea desembolsar el prÃÂ©stamo con fecha ${new Date(fechaAprobacion).toLocaleDateString()}?\n\n` +
      `Esta acciÃÂ³n:\n` +
      `Ã¢ÂÂ¢ MantendrÃÂ¡ el estado en APROBADO (con fecha de aprobaciÃÂ³n)\n` +
      `Ã¢ÂÂ¢ GenerarÃÂ¡ la tabla de amortizaciÃÂ³n\n` +
      `Ã¢ÂÂ¢ CrearÃÂ¡ todas las cuotas\n` +
      `Ã¢ÂÂ¢ Requiere calificaciÃÂ³n mÃÂ­nima de 70 puntos`

    if (!window.confirm(mensajeConfirmacion)) {
      return
    }

    setIsLoading(true)

    try {
      const resultado = await prestamoService.asignarFechaAprobacion(prestamo.id, fechaAprobacion)
      toast.success(
        `Fecha de aprobaciÃÂ³n asignada. Estado: APROBADO. ` +
        `Tabla de amortizaciÃÂ³n generada con ${resultado.cuotas_recalculadas || 0} cuotas.`
      )
      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['prestamos'] })
      onSuccess()
      onClose()
    } catch (error: any) {
      console.error('Error asignando fecha de aprobaciÃÂ³n:', error)
      toast.error(error.response?.data?.detail || error.message || 'Error al asignar fecha de aprobaciÃÂ³n')
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
                Asignar Fecha de AprobaciÃÂ³n - PrÃÂ©stamo #{prestamo.id}
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
                <h5 className="font-semibold text-green-900 mb-4">ÃÂ°ÃÂ¸Ã¢ÂÂÃ¢ÂÂ¦ Fecha de AprobaciÃÂ³n y Desembolso:</h5>
                <div className="bg-blue-50 p-3 rounded border border-blue-200 mb-4">
                  <p className="text-sm font-medium text-blue-900 mb-2">
                    ÃÂ¢ÃÂ¡ ÃÂ¯ÃÂ¸ÃÂ Requisitos para desembolsar:
                  </p>
                  <ul className="text-xs text-blue-800 list-disc list-inside space-y-1">
                    <li>CalificaciÃÂ³n mÃÂ­nima de evaluaciÃÂ³n de riesgo: 70 puntos</li>
                    <li>El prÃÂ©stamo debe estar en estado APROBADO</li>
                    <li>Se generarÃÂ¡ la tabla de amortizaciÃÂ³n automÃÂ¡ticamente</li>
                    <li>Se crearÃÂ¡n todas las cuotas en la tabla de cuotas</li>
                    <li>El estado quedarÃÂ¡ en APROBADO (con fecha de aprobaciÃÂ³n)</li>
                  </ul>
                </div>
                <p className="text-sm text-gray-700 mb-4">
                  Seleccione la fecha de aprobaciÃÂ³n del crÃÂ©dito. Esta fecha se utilizarÃÂ¡ como base 
                  para recalcular la tabla de amortizaciÃÂ³n y determinar las fechas de vencimiento de las cuotas.
                </p>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Fecha de AprobaciÃÂ³n <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <Input
                      type="date"
                      value={fechaAprobacion}
                      onChange={(e) => setFechaAprobacion(e.target.value)}
                      className="pl-10"
                      min={fechaRequerimientoStr || (prestamo.fecha_registro ? new Date(prestamo.fecha_registro).toISOString().split('T')[0] : undefined)}
                    />
                  </div>
                  <p className="text-xs text-gray-500">
                    Esta fecha serÃÂ¡ la base para calcular las fechas de vencimiento de todas las cuotas
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
                  title={!fechaAprobacion ? 'Debe seleccionar una fecha de aprobaciÃÂ³n' : 'Asignar fecha y recalcular amortizaciÃÂ³n'}
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
