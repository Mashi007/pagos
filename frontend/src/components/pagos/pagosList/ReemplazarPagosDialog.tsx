import { Loader2 } from 'lucide-react'
import type { Prestamo } from '../../../types'
import { Button } from '../../ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog'
import { Input } from '../../ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select'

export type ReemplazarPagosStep = 'cedula' | 'elegir' | 'confirmar'

type Props = {
  open: boolean
  step: ReemplazarPagosStep
  cedula: string
  prestamos: Prestamo[]
  prestamoId: number | null
  prestamoSeleccionado: Prestamo | undefined
  loading: boolean
  onOpenChange: (open: boolean) => void
  onCedulaChange: (value: string) => void
  onPrestamoIdChange: (id: number | null) => void
  onStepChange: (step: ReemplazarPagosStep) => void
  onBuscarPrestamos: () => void
  onConfirmar: () => void
}

export function ReemplazarPagosDialog({
  open,
  step,
  cedula,
  prestamos,
  prestamoId,
  prestamoSeleccionado,
  loading,
  onOpenChange,
  onCedulaChange,
  onPrestamoIdChange,
  onStepChange,
  onBuscarPrestamos,
  onConfirmar,
}: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reemplazar pagos</DialogTitle>
        </DialogHeader>
        {step === 'cedula' && (
          <div className="space-y-4 py-2">
            <p className="text-sm text-gray-600">
              Ingrese la cédula del cliente. Solo se consideran préstamos en
              estado APROBADO.
            </p>
            <Input
              placeholder="Cédula"
              value={cedula}
              onChange={e => onCedulaChange(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  void onBuscarPrestamos()
                }
              }}
              autoFocus
            />
            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={loading}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                onClick={() => void onBuscarPrestamos()}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Buscando...
                  </>
                ) : (
                  'Continuar'
                )}
              </Button>
            </DialogFooter>
          </div>
        )}
        {step === 'elegir' && (
          <div className="space-y-4 py-2">
            <p className="text-sm text-gray-600">
              Hay {prestamos.length} préstamos aprobados. Elija el crédito cuyos
              pagos desea borrar y reemplazar.
            </p>
            <Select
              value={prestamoId != null ? String(prestamoId) : 'none'}
              onValueChange={v =>
                onPrestamoIdChange(v === 'none' ? null : Number(v))
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Seleccione préstamo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Seleccione préstamo</SelectItem>
                {prestamos.map(p => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    #{p.id} {p.modelo_vehiculo || p.producto || 'Préstamo'} -{' '}
                    {p.nombres}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  onStepChange('cedula')
                  onPrestamoIdChange(null)
                }}
                disabled={loading}
              >
                Atrás
              </Button>
              <Button
                type="button"
                onClick={() => {
                  if (prestamoId == null) return
                  onStepChange('confirmar')
                }}
                disabled={loading || prestamoId == null}
              >
                Continuar
              </Button>
            </DialogFooter>
          </div>
        )}
        {step === 'confirmar' && prestamoId != null && prestamoSeleccionado && (
          <div className="space-y-4 py-2">
            <p className="text-sm text-gray-700">
              ¿Desea borrar <strong>todos los pagos</strong> de la cédula{' '}
              <strong>{prestamoSeleccionado.cedula}</strong> en el préstamo{' '}
              <strong>#{prestamoId}</strong>
              {prestamoSeleccionado.modelo_vehiculo
                ? ` (${prestamoSeleccionado.modelo_vehiculo})`
                : ''}
              ? Luego podrá cargar los pagos desde Excel con el flujo habitual.
            </p>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  onStepChange(prestamos.length > 1 ? 'elegir' : 'cedula')
                }
                disabled={loading}
              >
                Atrás
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => void onConfirmar()}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Borrando...
                  </>
                ) : (
                  'Sí, borrar todos los pagos'
                )}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
