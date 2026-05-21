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
  onCasoActualizado?: CobranzaGestionCasoProps['onCasoActualizado']
}

export function CobranzaNegociacionDialog({
  open,
  onOpenChange,
  prestamo,
  onCasoActualizado,
}: CobranzaNegociacionDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
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
            onCasoActualizado={onCasoActualizado}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
