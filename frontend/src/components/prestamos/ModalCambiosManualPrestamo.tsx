/**
 * ModalCambiosManualPrestamo.tsx
 * Modal para realizar cambios manuales de fecha de aprobación y recalcular amortización
 * Reemplaza la funcionalidad del botón Editar
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { Calendar, RefreshCw, Save } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent } from '../../components/ui/card'
import { prestamoService } from '../../services/prestamoService'
import { Prestamo } from '../../types'

interface ModalCambiosManualPrestamoProps {
  open: boolean
  prestamo?: Prestamo
  onClose: () => void
  onSuccess?: () => void
}

export function ModalCambiosManualPrestamo({
  open,
  prestamo,
  onClose,
  onSuccess,
}: ModalCambiosManualPrestamoProps) {
  const [fechaAprobacion, setFechaAprobacion] = useState(
    prestamo?.fecha_aprobacion
      ? new Date(prestamo.fecha_aprobacion).toISOString().split('T')[0]
      : ''
  )
  const [isRecalculando, setIsRecalculando] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const handleRecalcularAmortizacion = async () => {
    if (!prestamo || !fechaAprobacion) {
      toast.error('Por favor ingresa la fecha de aprobación')
      return
    }

    setIsRecalculando(true)
    try {
      // Primero actualizar la fecha de aprobación
      await prestamoService.updatePrestamo(prestamo.id, {
        fecha_aprobacion: `${fechaAprobacion}T00:00:00`,
      })

      // Luego recalcular las fechas de amortización
      const resultado = await prestamoService.recalcularFechasAmortizacion(
        prestamo.id
      )

      toast.success(
        `Amortización recalculada: ${resultado.cuotas_recalculadas || 0} cuota(s) actualizadas`
      )
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || 'Error al recalcular amortización'
      )
    } finally {
      setIsRecalculando(false)
    }
  }

  const handleGuardar = async () => {
    if (!prestamo || !fechaAprobacion) {
      toast.error('Por favor ingresa la fecha de aprobación')
      return
    }

    setIsSaving(true)
    try {
      // Solo guardar cambios (fecha ya fue guardada en recalcular)
      await prestamoService.updatePrestamo(prestamo.id, {
        estado_edicion: 'COMPLETADO',
      })

      toast.success('Cambios guardados correctamente')

      // Actualizar estado de edición a COMPLETADO
      onSuccess?.()
      onClose()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al guardar cambios')
    } finally {
      setIsSaving(false)
    }
  }

  if (!prestamo) return null

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Cambios Manuales de Préstamo</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Información del préstamo */}
          <Card>
            <CardContent className="pt-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-600">Cliente</p>
                  <p className="font-semibold">{prestamo.nombres}</p>
                </div>
                <div>
                  <p className="text-gray-600">Cédula</p>
                  <p className="font-semibold">{prestamo.cedula}</p>
                </div>
                <div>
                  <p className="text-gray-600">Monto</p>
                  <p className="font-semibold">
                    $
                    {Number(prestamo.total_financiamiento).toLocaleString(
                      'en-US',
                      {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      }
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-gray-600">Estado</p>
                  <p className="font-semibold">{prestamo.estado}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Cambios Manuales */}
          <Card>
            <CardContent className="pt-4">
              <div className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    <Calendar className="mr-2 inline h-4 w-4" />
                    Fecha de Aprobación
                  </label>
                  <Input
                    type="date"
                    value={fechaAprobacion}
                    onChange={e => setFechaAprobacion(e.target.value)}
                    className="w-full"
                  />
                  {fechaAprobacion !==
                    new Date(prestamo.fecha_aprobacion || '')
                      .toISOString()
                      .split('T')[0] && (
                    <p className="mt-1 text-xs text-orange-600">
                      ⚠️ La fecha ha sido modificada
                    </p>
                  )}
                </div>

                <div className="rounded border border-blue-200 bg-blue-50 p-3">
                  <p className="text-xs text-blue-800">
                    💡 <strong>Nota:</strong> Cuando cambies la fecha de
                    aprobación, la tabla de amortización se recalculará
                    automáticamente.
                  </p>
                </div>

                <Button
                  onClick={handleRecalcularAmortizacion}
                  disabled={isRecalculando || !fechaAprobacion}
                  variant="outline"
                  className="w-full"
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  {isRecalculando
                    ? 'Recalculando...'
                    : 'Recalcular Amortización'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={handleGuardar}
            disabled={isSaving}
            className="bg-green-600 hover:bg-green-700"
          >
            <Save className="mr-2 h-4 w-4" />
            {isSaving ? 'Guardando...' : 'Guardar y Cerrar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
