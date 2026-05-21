import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { CobranzaGestionCaso, type CobranzaGestionCasoProps } from './CobranzaGestionCaso'
import type { CobranzaPrestamoResumen } from '../../services/cobranzaService'

export interface CobranzaNegociacionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  prestamo: CobranzaPrestamoResumen | null
  aperturaToken: number
  onCasoActualizado?: CobranzaGestionCasoProps['onCasoActualizado']
}

export function CobranzaNegociacionDialog({
  open,
  onOpenChange,
  prestamo,
  aperturaToken,
  onCasoActualizado,
}: CobranzaNegociacionDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Negociacion de pago</DialogTitle>
          <DialogDescription>
            {prestamo
              ? `Prestamo #${prestamo.id} · ${prestamo.nombres || prestamo.cedula}`
              : ''}
          </DialogDescription>
        </DialogHeader>
        {prestamo && open ? (
          <CobranzaGestionCaso
            prestamo={prestamo}
            aperturaToken={aperturaToken}
            onCasoActualizado={onCasoActualizado}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
