Ã¯Â»Â¿import {
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
  fechaDatos?: string | null
  correosRevisados?: number
  archivosProcesados?: number
}

export function ConfirmarBorrarDiaDialog({
  open,
  onOpenChange,
  onElegir,
  fechaDatos,
  correosRevisados,
  archivosProcesados,
}: ConfirmarBorrarDiaDialogProps) {
  const resumenRevisado =
    correosRevisados != null && correosRevisados >= 0
      ? `Se revisaron ${correosRevisados} correo(s)` + (archivosProcesados != null && archivosProcesados >= 0 ? ` y ${archivosProcesados} archivo(s)` : '') + '.'
      : null
  const MENSAJE = fechaDatos
    ? `Se descargarÃÂ¡ el Excel de pagos del ${fechaDatos}. ÃÂ¿Vaciar la BD despuÃÂ©s de descargar? SÃÂ­ = descarga y vacÃÂ­a BD. No = descarga y mantiene los datos en BD.`
    : 'Se descargarÃÂ¡ el Excel. ÃÂ¿Vaciar la BD despuÃÂ©s de descargar? SÃÂ­ = descarga y vacÃÂ­a BD. No = descarga y mantiene los datos en BD.'
  const handleSÃÂ­ = async () => {
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
        {resumenRevisado && (
          <p className="text-sm font-medium text-gray-800 mb-2">{resumenRevisado}</p>
        )}
        <p className="text-sm text-gray-600">{MENSAJE}</p>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleNo}>
            No
          </Button>
          <Button type="button" onClick={handleSÃÂ­}>
            SÃÂ­
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
