import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { ChevronRight, ChevronLeft } from 'lucide-react'

const MESES_NOMBRES = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
]

export interface FiltrosReporte {
  aÃ±os: number[]
  meses: number[]
}

interface DialogReporteFiltrosProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (filtros: FiltrosReporte) => void
  tituloReporte: string
}

export function DialogReporteFiltros({
  open,
  onOpenChange,
  onConfirm,
  tituloReporte,
}: DialogReporteFiltrosProps) {
  const [paso, setPaso] = useState<1 | 2>(1)
  const [aÃ±osSeleccionados, setAÃ±osSeleccionados] = useState<Set<number>>(new Set())
  const [mesesSeleccionados, setMesesSeleccionados] = useState<Set<number>>(new Set())

  const aÃ±oActual = new Date().getFullYear()
  const aÃ±osOpciones = [aÃ±oActual, aÃ±oActual - 1, aÃ±oActual - 2, aÃ±oActual - 3, aÃ±oActual - 4]

  const toggleAÃ±o = (aÃ±o: number) => {
    setAÃ±osSeleccionados((prev) => {
      const next = new Set(prev)
      if (next.has(aÃ±o)) next.delete(aÃ±o)
      else next.add(aÃ±o)
      return next
    })
  }

  const toggleMes = (mes: number) => {
    setMesesSeleccionados((prev) => {
      const next = new Set(prev)
      if (next.has(mes)) next.delete(mes)
      else next.add(mes)
      return next
    })
  }

  const seleccionarTodosAÃ±os = () => {
    setAÃ±osSeleccionados(new Set(aÃ±osOpciones))
  }

  const seleccionarTodosMeses = () => {
    setMesesSeleccionados(new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]))
  }

  const handleAbrir = (isOpen: boolean) => {
    if (!isOpen) {
      setPaso(1)
      setAÃ±osSeleccionados(new Set())
      setMesesSeleccionados(new Set())
    }
    onOpenChange(isOpen)
  }

  const handleSiguiente = () => {
    if (aÃ±osSeleccionados.size === 0) return
    setPaso(2)
  }

  const handleAtras = () => setPaso(1)

  const handleDescargar = () => {
    if (paso === 1 && aÃ±osSeleccionados.size === 0) return
    if (paso === 2 && mesesSeleccionados.size === 0) return

    const aÃ±os = paso === 1
      ? Array.from(aÃ±osSeleccionados).sort((a, b) => b - a)
      : Array.from(aÃ±osSeleccionados).sort((a, b) => b - a)
    const meses = paso === 2
      ? Array.from(mesesSeleccionados).sort((a, b) => a - b)
      : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    onConfirm({ aÃ±os, meses })
    handleAbrir(false)
  }

  const puedeContinuar = paso === 1 ? aÃ±osSeleccionados.size > 0 : mesesSeleccionados.size > 0

  return (
    <Dialog open={open} onOpenChange={handleAbrir}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{tituloReporte}</DialogTitle>
          <DialogDescription>
            {paso === 1
              ? 'Selecciona uno o varios aÃ±os'
              : 'Selecciona uno o varios meses'}
          </DialogDescription>
        </DialogHeader>

        {paso === 1 && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <Button type="button" variant="outline" size="sm" onClick={seleccionarTodosAÃ±os}>
                Seleccionar todos
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {aÃ±osOpciones.map((aÃ±o) => (
                <button
                  key={aÃ±o}
                  type="button"
                  onClick={() => toggleAÃ±o(aÃ±o)}
                  className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
                    aÃ±osSeleccionados.has(aÃ±o)
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'border-gray-200 hover:border-blue-300 text-gray-700'
                  }`}
                >
                  {aÃ±o}
                </button>
              ))}
            </div>
          </div>
        )}

        {paso === 2 && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <Button type="button" variant="outline" size="sm" onClick={seleccionarTodosMeses}>
                Seleccionar todos
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {MESES_NOMBRES.map((nombre, idx) => {
                const mes = idx + 1
                return (
                  <button
                    key={mes}
                    type="button"
                    onClick={() => toggleMes(mes)}
                    className={`px-3 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
                      mesesSeleccionados.has(mes)
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'border-gray-200 hover:border-blue-300 text-gray-700'
                    }`}
                  >
                    {nombre}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        <DialogFooter className="flex gap-2 sm:gap-0">
          {paso === 2 && (
            <Button type="button" variant="outline" onClick={handleAtras}>
              <ChevronLeft className="h-4 w-4 mr-1" />
              AtrÃ¡s
            </Button>
          )}
          <div className="flex-1" />
          <Button type="button" variant="outline" onClick={() => handleAbrir(false)}>
            Cancelar
          </Button>
          {paso === 1 ? (
            <Button type="button" onClick={handleSiguiente} disabled={!puedeContinuar}>
              Siguiente
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button type="button" onClick={handleDescargar} disabled={!puedeContinuar}>
              Descargar
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
