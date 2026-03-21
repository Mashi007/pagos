import { useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { motion } from 'framer-motion'

import { toast } from 'sonner'

import { X, Calendar, CheckCircle2 } from 'lucide-react'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

import { prestamoService } from '../../services/prestamoService'

interface AsignarFechaAprobacionModalProps {
  prestamo: any

  onClose: () => void

  onSuccess: () => void
}

export function AsignarFechaAprobacionModal({
  prestamo,
  onClose,
  onSuccess,
}: AsignarFechaAprobacionModalProps) {
  const queryClient = useQueryClient()

  const [fechaAprobacion, setFechaAprobacion] = useState<string>(() => {
    if (prestamo.fecha_aprobacion)
      return new Date(prestamo.fecha_aprobacion).toISOString().split('T')[0]

    if (prestamo.fecha_requerimiento)
      return new Date(prestamo.fecha_requerimiento).toISOString().split('T')[0]

    return new Date().toISOString().split('T')[0]
  })

  const [isLoading, setIsLoading] = useState(false)

  const fechaRequerimientoStr = prestamo.fecha_requerimiento
    ? new Date(prestamo.fecha_requerimiento).toISOString().split('T')[0]
    : null

  const handleAsignarFecha = async () => {
    if (!fechaAprobacion) {
      toast.error('Debe seleccionar una fecha de aprobación')

      return
    }

    if (fechaRequerimientoStr && fechaAprobacion < fechaRequerimientoStr) {
      toast.error(
        `La fecha de aprobación debe ser igual o posterior a la fecha de requerimiento (${new Date(fechaRequerimientoStr).toLocaleDateString()})`
      )

      return
    }

    const mensajeConfirmacion =
      `¿Desea desembolsar el préstamo con fecha ${new Date(fechaAprobacion).toLocaleDateString()}?\n\n` +
      `Esta acción:\n` +
      `• Mantendrá el estado en APROBADO (con fecha de aprobación)\n` +
      `• Generará la tabla de amortización\n` +
      `• Creará todas las cuotas\n` +
      `• Requiere calificación mínima de 70 puntos`

    if (!window.confirm(mensajeConfirmacion)) {
      return
    }

    setIsLoading(true)

    try {
      const resultado = await prestamoService.asignarFechaAprobacion(
        prestamo.id,
        fechaAprobacion
      )

      toast.success(
        `Fecha de aprobación asignada. Estado: APROBADO. ` +
          `Tabla de amortización generada con ${resultado.cuotas_recalculadas || 0} cuotas.`
      )

      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })

      queryClient.invalidateQueries({ queryKey: ['prestamos'] })

      onSuccess()

      onClose()
    } catch (error: any) {
      console.error('Error asignando fecha de aprobación:', error)

      toast.error(
        error.response?.data?.detail ||
          error.message ||
          'Error al asignar fecha de aprobación'
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="w-full max-w-md rounded-lg bg-white shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        <Card>
          <CardHeader className="bg-gradient-to-r from-green-600 to-green-700 text-white">
            <div className="flex items-center justify-between">
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
              <div className="rounded border border-green-200 bg-green-50 p-4">
                <h5 className="mb-4 font-semibold text-green-900">
                  ðŸ"… Fecha de Aprobación y Desembolso:
                </h5>

                <div className="mb-4 rounded border border-blue-200 bg-blue-50 p-3">
                  <p className="mb-2 text-sm font-medium text-blue-900">
                    âš ï¸ Requisitos para desembolsar:
                  </p>

                  <ul className="list-inside list-disc space-y-1 text-xs text-blue-800">
                    <li>
                      Calificación mínima de evaluación de riesgo: 70 puntos
                    </li>

                    <li>El préstamo debe estar en estado APROBADO</li>

                    <li>
                      Se generará la tabla de amortización automáticamente
                    </li>

                    <li>Se crearán todas las cuotas en la tabla de cuotas</li>

                    <li>
                      El estado quedará en APROBADO (con fecha de aprobación)
                    </li>
                  </ul>
                </div>

                <p className="mb-4 text-sm text-gray-700">
                  Seleccione la fecha de aprobación del crédito. Esta fecha se
                  utilizará como base para recalcular la tabla de amortización y
                  determinar las fechas de vencimiento de las cuotas.
                </p>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Fecha de Aprobación <span className="text-red-500">*</span>
                  </label>

                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                    <Input
                      type="date"
                      value={fechaAprobacion}
                      onChange={e => setFechaAprobacion(e.target.value)}
                      className="pl-10"
                      min={
                        fechaRequerimientoStr ||
                        (prestamo.fecha_registro
                          ? new Date(prestamo.fecha_registro)
                              .toISOString()
                              .split('T')[0]
                          : undefined)
                      }
                    />
                  </div>

                  <p className="text-xs text-gray-500">
                    Esta fecha será la base para calcular las fechas de
                    vencimiento de todas las cuotas
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3 border-t pt-4">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancelar
                </Button>

                <Button
                  type="button"
                  className="bg-green-600 text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={handleAsignarFecha}
                  disabled={isLoading || !fechaAprobacion}
                  title={
                    !fechaAprobacion
                      ? 'Debe seleccionar una fecha de aprobación'
                      : 'Asignar fecha y recalcular amortización'
                  }
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
