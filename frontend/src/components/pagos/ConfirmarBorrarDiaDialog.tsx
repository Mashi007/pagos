import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog'
import { Button } from '../ui/button'

interface ConfirmarBorrarDiaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onElegir: (borrar: boolean) => void | Promise<void>
  fechaDatos?: string | null  // fecha de los datos a descargar (puede ser distinta al día actual)
}

export function ConfirmarBorrarDiaDialog({
  open,
  onOpenChange,
  onElegir,
  fechaDatos,
}: ConfirmarBorrarDiaDialogProps) {
  const MENSAJE = fechaDatos
    ? `Se descargará el Excel de pagos del ${fechaDatos}. ¿Quiere borrar esa información de la BD? Sí = se borra. No = se mantiene.`
    : '¿Quiere borrar la información del día? Sí = se borra. No = se mantiene en BD.'
  const handleSí = async () => {
    await onElegir(true)
    onOpenChange(false)
  }
  const handleNo = async () => {
    await onElegir(false)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirmar</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-gray-600">{MENSAJE}</p>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleNo}>
            No
          </Button>
          <Button type="button" onClick={handleSí}>
            Sí
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
