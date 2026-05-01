import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { AlertCircle, CheckCircle2 } from 'lucide-react'

interface ModalCambiarCedulaProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (mismaCedula: string, nuevaCedula: string) => void
  isLoading?: boolean
}

export function ModalCambiarCedula({
  isOpen,
  onClose,
  onConfirm,
  isLoading = false,
}: ModalCambiarCedulaProps) {
  const [mismaCedula, setMismaCedula] = useState('')
  const [nuevaCedula, setNuevaCedula] = useState('')

  const handleConfirm = () => {
    // Validaciones
    if (!mismaCedula.trim()) {
      toast.error('Ingrese la cédula actual')
      return
    }
    if (!nuevaCedula.trim()) {
      toast.error('Ingrese la nueva cédula')
      return
    }
    if (mismaCedula.trim() === nuevaCedula.trim()) {
      toast.error('Las cédulas no pueden ser iguales')
      return
    }

    onConfirm(mismaCedula.trim(), nuevaCedula.trim())
  }

  const handleClose = () => {
    setMismaCedula('')
    setNuevaCedula('')
    onClose()
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleConfirm()
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            Nuevo Escaneo
          </DialogTitle>
          <DialogDescription>
            Ingresa el cambio de cédula para continuar con el nuevo escaneo
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Aviso informativo */}
          <div className="flex gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3">
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" />
            <p className="text-sm text-blue-900">
              Se conservará la cédula validada, la tasa y el archivo del
              comprobante del deudor actual en el paso del comprobante si
              corresponde otro deudor.
            </p>
          </div>

          {/* Misma cédula (actual) */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Cédula Actual (Misma cédula)
            </label>
            <Input
              type="text"
              placeholder="Ej: V12345678"
              value={mismaCedula}
              onChange={e => setMismaCedula(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              className="text-sm"
            />
            <p className="text-xs text-gray-500">
              La cédula del deudor que ya validamos
            </p>
          </div>

          {/* Nueva cédula (nuevo deudor) */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Nueva Cédula (Nuevo deudor)
            </label>
            <Input
              type="text"
              placeholder="Ej: E87654321"
              value={nuevaCedula}
              onChange={e => setNuevaCedula(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              className="text-sm"
            />
            <p className="text-xs text-gray-500">
              La cédula del nuevo deudor a documentar
            </p>
          </div>
        </div>

        <DialogFooter className="flex gap-2">
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isLoading}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isLoading ? 'Procesando...' : 'Continuar Escaneo'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
