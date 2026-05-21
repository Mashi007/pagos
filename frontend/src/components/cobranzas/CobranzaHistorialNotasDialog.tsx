import React, { useCallback, useEffect, useState } from 'react'
import {
  ChevronLeft,
  History,
  Loader2,
  MessageSquare,
} from 'lucide-react'
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
import { formatCurrency } from '../../utils'
import { CobranzaGestionCaso } from './CobranzaGestionCaso'
import {
  CobranzaConversacionCard,
  CobranzaNotaDetallePanel,
  notasGuardadasOrdenadas,
} from './cobranzaNotaUi'

type VistaHistorial = 'conversaciones' | 'detalle' | 'nueva'

export interface CobranzaHistorialNotasDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  prestamo: CobranzaPrestamoResumen | null
  onCasoActualizado?: (prestamoId: number, casoId: number) => void
}

export function CobranzaHistorialNotasDialog({
  open,
  onOpenChange,
  prestamo,
  onCasoActualizado,
}: CobranzaHistorialNotasDialogProps) {
  const [cargando, setCargando] = useState(false)
  const [notas, setNotas] = useState<CobranzaAcuerdo[]>([])
  const [notaSel, setNotaSel] = useState<CobranzaAcuerdo | null>(null)
  const [vista, setVista] = useState<VistaHistorial>('conversaciones')
  const [tokenNuevaNota, setTokenNuevaNota] = useState(0)

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
      setVista('conversaciones')
      return
    }
    setVista('conversaciones')
    setNotaSel(null)
    void cargar()
  }, [open, cargar, prestamo?.id, prestamo?.caso_id])

  const irADetalle = (n: CobranzaAcuerdo) => {
    setNotaSel(n)
    setVista('detalle')
  }

  const irANueva = () => {
    setTokenNuevaNota(Date.now())
    setVista('nueva')
  }

  const volverAlHistorial = () => {
    setNotaSel(null)
    setVista('conversaciones')
    void cargar()
  }

  const titulo =
    vista === 'detalle'
      ? 'Detalle de conversacion'
      : vista === 'nueva'
        ? 'Registrar conversacion'
        : 'Historial de conversaciones'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {(vista === 'detalle' || vista === 'nueva') && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2"
                onClick={volverAlHistorial}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            )}
            {vista === 'conversaciones' && (
              <History className="h-5 w-5 text-violet-600" />
            )}
            {titulo}
          </DialogTitle>
          <DialogDescription>
            {prestamo ? (
              <>
                Prestamo #{prestamo.id} · {prestamo.nombres || prestamo.cedula}
                {' · '}
                Pendiente {formatCurrency(prestamo.saldo_pendiente)}
              </>
            ) : (
              ''
            )}
          </DialogDescription>
        </DialogHeader>

        {vista === 'detalle' && notaSel && (
          <CobranzaNotaDetallePanel nota={notaSel} />
        )}

        {vista === 'nueva' && prestamo && (
          <CobranzaGestionCaso
            prestamo={prestamo}
            aperturaToken={tokenNuevaNota}
            autoIniciarSesion
            formularioInicialExpandido
            mostrarCabecera={false}
            onCasoActualizado={onCasoActualizado}
            onNotaGuardada={volverAlHistorial}
          />
        )}

        {vista === 'conversaciones' && prestamo && (
          <div className="space-y-4">
            <div className="rounded-lg border border-violet-200 bg-violet-50/50 px-4 py-3 text-sm text-violet-900">
              Bitacora de negociacion: conversaciones, acuerdos de cobranza y
              evidencias (PDF o imagenes), de la mas reciente a la mas antigua.
            </div>

            {cargando && (
              <div className="flex items-center justify-center gap-2 py-12 text-slate-600">
                <Loader2 className="h-6 w-6 animate-spin" />
                Cargando conversaciones...
              </div>
            )}

            {!cargando && notas.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center">
                <History className="mx-auto mb-2 h-10 w-10 text-slate-300" />
                <p className="text-sm font-medium text-slate-700">
                  Sin conversaciones registradas
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Registre la primera nota con mensaje, acuerdo de monto y
                  evidencias.
                </p>
              </div>
            )}

            {!cargando && notas.length > 0 && (
              <div className="space-y-3">
                {notas.map((n, idx) => (
                  <div key={n.id} className="relative pl-6">
                    {idx < notas.length - 1 && (
                      <span
                        className="absolute left-2 top-10 bottom-0 w-px bg-violet-200"
                        aria-hidden
                      />
                    )}
                    <span
                      className="absolute left-0 top-4 h-4 w-4 rounded-full border-2 border-violet-500 bg-white"
                      aria-hidden
                    />
                    <CobranzaConversacionCard
                      nota={n}
                      onClick={() => irADetalle(n)}
                      activa={notaSel?.id === n.id}
                    />
                  </div>
                ))}
              </div>
            )}

            <div className="sticky bottom-0 border-t border-slate-200 bg-white pt-3">
              <Button
                type="button"
                className="w-full bg-violet-600 hover:bg-violet-700"
                onClick={irANueva}
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                Registrar nueva conversacion
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
