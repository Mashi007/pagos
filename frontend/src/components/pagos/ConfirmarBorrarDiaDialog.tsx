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
      ? `Se revisaron ${correosRevisados} correo(s)` +
        (archivosProcesados != null && archivosProcesados >= 0
          ? ` y ${archivosProcesados} archivo(s)`
          : '') +
        '.'
      : null

  const MENSAJE = fechaDatos
    ? `Se descargará el Excel de pagos del ${fechaDatos}. ¿Vaciar la BD después de descargar? Sí = descarga y vacía BD. No = descarga y mantiene los datos en BD.`
    : 'Se descargará el Excel. ¿Vaciar la BD después de descargar? Sí = descarga y vacía BD. No = descarga y mantiene los datos en BD.'

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

        {resumenRevisado && (
          <p className="mb-2 text-sm font-medium text-gray-800">
            {resumenRevisado}
          </p>
        )}

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
