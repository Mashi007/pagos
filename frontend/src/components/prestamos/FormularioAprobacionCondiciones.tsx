import { useState, useEffect } from 'react'

import { motion } from 'framer-motion'

import { toast } from 'sonner'

import { X, DollarSign, Calendar, FileText } from 'lucide-react'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Textarea } from '../../components/ui/textarea'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

import { useAplicarCondicionesAprobacion } from '../../hooks/usePrestamos'

import { prestamoService } from '../../services/prestamoService'
import { formatDate } from '../../utils'

interface FormularioAprobacionCondicionesProps {
  prestamo: any

  onClose: () => void

  onSuccess: () => void
}

export function FormularioAprobacionCondiciones({
  prestamo,
  onClose,
  onSuccess,
}: FormularioAprobacionCondicionesProps) {
  const defaultFechaAprobacion = prestamo.fecha_aprobacion
    ? new Date(prestamo.fecha_aprobacion).toISOString().split('T')[0]
    : ''

  const [condicionesAprobacion, setCondicionesAprobacion] = useState({
    tasa_interes: 0.0, // Siempre 0% - producto sin interés

    plazo_maximo: prestamo.numero_cuotas || 36,

    fecha_aprobacion: defaultFechaAprobacion,

    observaciones: prestamo.observaciones || '',
  })

  const [isLoading, setIsLoading] = useState(false)

  const [sugerencias, setSugerencias] = useState<any>(null)

  const fechaRequerimientoYmd = prestamo.fecha_requerimiento
    ? new Date(prestamo.fecha_requerimiento).toISOString().split('T')[0]
    : undefined

  const aplicarCondiciones = useAplicarCondicionesAprobacion()

  // Obtener sugerencias desde la última evaluación de riesgo

  useEffect(() => {
    const obtenerSugerencias = async () => {
      try {
        await prestamoService.getAuditoria(prestamo.id)

        // tasa_interes siempre 0% - no se sobreescribe desde sugerencias
      } catch (error) {
        console.log(
          'No se encontraron sugerencias previas, usando valores por defecto'
        )
      }
    }

    obtenerSugerencias()
  }, [prestamo.id])

  const handleAprobar = async () => {
    console.log('ðŸ"„ handleAprobar llamado')

    console.log('ðŸ"‹ Condiciones:', condicionesAprobacion)

    // Validaciones

    if (!condicionesAprobacion.fecha_aprobacion) {
      console.error('Validacion fallida: fecha_aprobacion vacia')

      toast.error('Debe seleccionar una fecha de desembolso')

      return
    }

    if (
      fechaRequerimientoYmd &&
      condicionesAprobacion.fecha_aprobacion < fechaRequerimientoYmd
    ) {
      toast.error(
        `La fecha de aprobacion debe ser igual o posterior a la fecha de requerimiento (${formatDate(fechaRequerimientoYmd)})`
      )

      return
    }

    if (
      condicionesAprobacion.tasa_interes < 0 ||
      condicionesAprobacion.tasa_interes > 100
    ) {
      console.error(
        'âŒ Validación fallida: tasa_interes fuera de rango',
        condicionesAprobacion.tasa_interes
      )

      toast.error('La tasa de interés debe estar entre 0 y 100%')

      return
    }

    if (condicionesAprobacion.plazo_maximo <= 0) {
      console.error(
        'âŒ Validación fallida: plazo_maximo inválido',
        condicionesAprobacion.plazo_maximo
      )

      toast.error('El plazo máximo debe ser mayor a 0 meses')

      return
    }

    console.log('âœ… Validaciones pasadas')

    const mensajeConfirmacion =
      `¿Desea aprobar este préstamo con las siguientes condiciones?\n\n` +
      `• Tasa de Interés: ${condicionesAprobacion.tasa_interes}%\n` +
      `• Plazo Máximo: ${condicionesAprobacion.plazo_maximo} meses\n` +
      `• Fecha de Aprobacion / Desembolso: ${formatDate(condicionesAprobacion.fecha_aprobacion)}`

    if (!window.confirm(mensajeConfirmacion)) {
      console.log('âŒ Usuario canceló la confirmación')

      return
    }

    console.log('âœ… Confirmación aceptada por el usuario')

    setIsLoading(true)

    try {
      const condiciones = {
        estado: 'APROBADO',

        tasa_interes: condicionesAprobacion.tasa_interes,

        plazo_maximo: condicionesAprobacion.plazo_maximo,

        fecha_aprobacion: condicionesAprobacion.fecha_aprobacion,

        observaciones:
          condicionesAprobacion.observaciones ||
          `Aprobado manualmente. Préstamo ID: ${prestamo.id}`,
      }

      console.log('ðŸ"¤ Enviando condiciones al backend:', condiciones)

      console.log('ðŸ†" Prestamo ID:', prestamo.id)

      const resultado = await aplicarCondiciones.mutateAsync({
        prestamoId: prestamo.id,

        condiciones,
      })

      console.log('âœ… Respuesta del backend:', resultado)

      toast.success(
        'âœ… Préstamo aprobado exitosamente. La tabla de amortización ha sido generada automáticamente.'
      )

      onSuccess()

      onClose()
    } catch (error: any) {
      console.error('âŒ Error completo al aprobar préstamo:', error)

      console.error('âŒ Error response:', error.response)

      console.error('âŒ Error message:', error.message)

      toast.error(
        error.response?.data?.detail ||
          error.message ||
          'Error al aprobar préstamo'
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
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        <Card>
          <CardHeader className="bg-gradient-to-r from-blue-600 to-blue-700 text-white">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Aprobar Crédito - Préstamo #{prestamo.id}
              </CardTitle>

              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-white hover:bg-blue-800"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            <div className="space-y-6">
              <div className="rounded border border-blue-200 bg-blue-50 p-4">
                <h5 className="mb-4 font-semibold text-blue-900">
                  ðŸ"‹ Condiciones para Aprobación:
                </h5>

                <div className="space-y-4 rounded border border-blue-300 bg-white p-4">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Tasa de Interés (%){' '}
                        <span className="text-red-500">*</span>
                      </label>

                      <div className="relative">
                        <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          max="100"
                          value={condicionesAprobacion.tasa_interes || ''}
                          onChange={e => {
                            const valor =
                              e.target.value === ''
                                ? 0
                                : parseFloat(e.target.value)

                            console.log('ðŸ" Tasa de interés cambiada:', valor)

                            setCondicionesAprobacion({
                              ...condicionesAprobacion,

                              tasa_interes: isNaN(valor) ? 0 : valor,
                            })
                          }}
                          className="pl-10"
                          placeholder="0.0"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Plazo Máximo (meses){' '}
                        <span className="text-red-500">*</span>
                      </label>

                      <Input
                        type="number"
                        step="1"
                        min="1"
                        value={condicionesAprobacion.plazo_maximo || ''}
                        onChange={e => {
                          const valor =
                            e.target.value === ''
                              ? 36
                              : parseInt(e.target.value)

                          console.log('ðŸ" Plazo máximo cambiado:', valor)

                          setCondicionesAprobacion({
                            ...condicionesAprobacion,

                            plazo_maximo: isNaN(valor) ? 36 : valor,
                          })
                        }}
                        placeholder="36"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Fecha de Aprobacion / Desembolso{' '}
                        <span className="text-red-500">*</span>
                      </label>

                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                        <Input
                          type="date"
                          value={condicionesAprobacion.fecha_aprobacion}
                          onChange={e =>
                            setCondicionesAprobacion({
                              ...condicionesAprobacion,

                              fecha_aprobacion: e.target.value,
                            })
                          }
                          className="pl-10"
                          min={fechaRequerimientoYmd}
                        />
                      </div>

                      <p className="text-xs text-gray-500">
                        Misma fecha se guarda como base de cálculo de la
                        amortización. El minimo permitido es la fecha de
                        requerimiento del préstamo (no la fecha del sistema).
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">
                      Observaciones
                    </label>

                    <Textarea
                      value={condicionesAprobacion.observaciones}
                      onChange={e =>
                        setCondicionesAprobacion({
                          ...condicionesAprobacion,

                          observaciones: e.target.value,
                        })
                      }
                      placeholder="Observaciones adicionales sobre la aprobación..."
                      rows={3}
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 border-t pt-4">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancelar
                </Button>

                <Button
                  type="button"
                  className="bg-green-600 text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={e => {
                    e.preventDefault()

                    e.stopPropagation()

                    console.log('ðŸ-±ï¸ Click en botón Aprobar Préstamo')

                    console.log(
                      'ðŸ"‹ Estado actual de condiciones:',
                      condicionesAprobacion
                    )

                    handleAprobar()
                  }}
                  disabled={
                    isLoading ||
                    !condicionesAprobacion.fecha_aprobacion ||
                    condicionesAprobacion.tasa_interes < 0 ||
                    condicionesAprobacion.tasa_interes > 100 ||
                    condicionesAprobacion.plazo_maximo <= 0
                  }
                  title={
                    !condicionesAprobacion.fecha_aprobacion
                      ? 'Debe seleccionar una fecha de desembolso'
                      : condicionesAprobacion.tasa_interes < 0 ||
                          condicionesAprobacion.tasa_interes > 100
                        ? 'La tasa de interés debe estar entre 0 y 100%'
                        : condicionesAprobacion.plazo_maximo <= 0
                          ? 'El plazo máximo debe ser mayor a 0'
                          : 'Aprobar préstamo con las condiciones especificadas'
                  }
                >
                  {isLoading ? 'Aprobando...' : 'Aprobar Préstamo'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
