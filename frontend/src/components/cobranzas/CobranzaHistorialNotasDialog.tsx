import React, { useCallback, useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, History, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Button } from '../ui/button'
import {
  obtenerCasoCobranza,
  type CobranzaAcuerdo,
  type CobranzaPrestamoResumen,
} from '../../services/cobranzaService'
import {
  CobranzaNotaDetallePanel,
  notasGuardadasOrdenadas,
  resumenNotaLinea,
} from './cobranzaNotaUi'

export interface CobranzaHistorialNotasDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  prestamo: CobranzaPrestamoResumen | null
}

export function CobranzaHistorialNotasDialog({
  open,
  onOpenChange,
  prestamo,
}: CobranzaHistorialNotasDialogProps) {
  const [cargando, setCargando] = useState(false)
  const [notas, setNotas] = useState<CobranzaAcuerdo[]>([])
  const [notaSel, setNotaSel] = useState<CobranzaAcuerdo | null>(null)

  const cargar = useCallback(async () => {
    if (!prestamo?.caso_id) {
      setNotas([])
      return
    }
    setCargando(true)
    try {
      const det = await obtenerCasoCobranza(prestamo.caso_id)
      setNotas(notasGuardadasOrdenadas(det.acuerdos))
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al cargar historial')
      setNotas([])
    } finally {
      setCargando(false)
    }
  }, [prestamo?.caso_id])

  useEffect(() => {
    if (!open) {
      setNotaSel(null)
      return
    }
    void cargar()
  }, [open, cargar])

  const enDetalle = notaSel != null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {enDetalle ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2"
                onClick={() => setNotaSel(null)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            ) : (
              <History className="h-5 w-5 text-violet-600" />
            )}
            {enDetalle ? 'Detalle de la nota' : 'Historial de notas'}
          </DialogTitle>
          <DialogDescription>
            {prestamo
              ? `Prestamo #${prestamo.id} · ${prestamo.nombres || prestamo.cedula}`
              : ''}
          </DialogDescription>
        </DialogHeader>

        {cargando && (
          <div className="flex items-center gap-2 py-8 text-slate-600">
            <Loader2 className="h-5 w-5 animate-spin" />
            Cargando notas...
          </div>
        )}

        {!cargando && !prestamo?.caso_id && (
          <p className="py-6 text-center text-sm text-slate-500">
            Este prestamo aun no tiene notas guardadas. Use Gestionar o
            Negociacion para registrar la primera nota.
          </p>
        )}

        {!cargando && prestamo?.caso_id && !enDetalle && notas.length === 0 && (
          <p className="py-6 text-center text-sm text-slate-500">
            Sin notas guardadas en este caso.
          </p>
        )}

        {!cargando && !enDetalle && notas.length > 0 && (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200">
            {notas.map(n => (
              <li key={n.id}>
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-3 text-left text-sm hover:bg-violet-50"
                  onClick={() => setNotaSel(n)}
                >
                  <span className="min-w-0 flex-1 text-slate-800">
                    {resumenNotaLinea(n)}
                  </span>
                  <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
                </button>
              </li>
            ))}
          </ul>
        )}

        {!cargando && enDetalle && notaSel && (
          <CobranzaNotaDetallePanel nota={notaSel} />
        )}
      </DialogContent>
    </Dialog>
  )
}
