Ã¯Â»Â¿import { useState, useEffect, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { ChevronRight, ChevronLeft, Search, Check } from 'lucide-react'
import { reporteService } from '../../services/reporteService'

const MESES_NOMBRES = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
]

export interface FiltrosReporteContable {
  aÃÂ±os: number[]
  meses: number[]
  cedulas: string[] | 'todas'
}

interface DialogReporteContableFiltrosProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (filtros: FiltrosReporteContable) => void
}

export function DialogReporteContableFiltros({
  open,
  onOpenChange,
  onConfirm,
}: DialogReporteContableFiltrosProps) {
  const [paso, setPaso] = useState<1 | 2 | 3>(1)
  const [aÃÂ±osSeleccionados, setAÃÂ±osSeleccionados] = useState<Set<number>>(new Set())
  const [mesesSeleccionados, setMesesSeleccionados] = useState<Set<number>>(new Set())
  const [busquedaCedula, setBusquedaCedula] = useState('')
  const [cedulasDisponibles, setCedulasDisponibles] = useState<Array<{ cedula: string; nombre: string }>>([])
  const [cedulasSeleccionadas, setCedulasSeleccionadas] = useState<Set<string>>(new Set())
  const [todasLasCedulas, setTodasLasCedulas] = useState(false)
  const [loadingCedulas, setLoadingCedulas] = useState(false)

  const aÃÂ±oActual = new Date().getFullYear()
  const aÃÂ±osOpciones = [aÃÂ±oActual, aÃÂ±oActual - 1, aÃÂ±oActual - 2, aÃÂ±oActual - 3, aÃÂ±oActual - 4].filter((a) => a !== 2022 && a !== 2023)

  const buscarCedulas = useCallback(async (q: string) => {
    setLoadingCedulas(true)
    try {
      const res = await reporteService.buscarCedulasContable(q)
      setCedulasDisponibles(res.cedulas || [])
    } catch {
      setCedulasDisponibles([])
    } finally {
      setLoadingCedulas(false)
    }
  }, [])

  useEffect(() => {
    if (paso === 3 && open) {
      const t = setTimeout(() => buscarCedulas(busquedaCedula), 300)
      return () => clearTimeout(t)
    }
  }, [paso, open, busquedaCedula, buscarCedulas])

  const toggleAÃÂ±o = (aÃÂ±o: number) => {
    setAÃÂ±osSeleccionados((prev) => {
      const next = new Set(prev)
      if (next.has(aÃÂ±o)) next.delete(aÃÂ±o)
      else next.add(aÃÂ±o)
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

  const toggleCedula = (cedula: string) => {
    setCedulasSeleccionadas((prev) => {
      const next = new Set(prev)
      if (next.has(cedula)) next.delete(cedula)
      else next.add(cedula)
      return next
    })
  }

  const seleccionarTodosAÃÂ±os = () => setAÃÂ±osSeleccionados(new Set(aÃÂ±osOpciones))
  const seleccionarTodosMeses = () => setMesesSeleccionados(new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]))

  const handleAbrir = (isOpen: boolean) => {
    if (!isOpen) {
      setPaso(1)
      setAÃÂ±osSeleccionados(new Set())
      setMesesSeleccionados(new Set())
      setCedulasSeleccionadas(new Set())
      setTodasLasCedulas(false)
      setBusquedaCedula('')
    }
    onOpenChange(isOpen)
  }

  const handleSiguiente = () => {
    if (paso === 1 && aÃÂ±osSeleccionados.size > 0) setPaso(2)
    else if (paso === 2 && mesesSeleccionados.size > 0) setPaso(3)
  }

  const handleAtras = () => {
    if (paso === 2) setPaso(1)
    else if (paso === 3) setPaso(2)
  }

  const handleDescargar = () => {
    const aÃÂ±os = Array.from(aÃÂ±osSeleccionados).sort((a, b) => b - a)
    const meses = Array.from(mesesSeleccionados).sort((a, b) => a - b)
    const cedulas = todasLasCedulas ? 'todas' : Array.from(cedulasSeleccionadas)
    onConfirm({ aÃÂ±os, meses, cedulas })
    handleAbrir(false)
  }

  const puedeContinuar =
    (paso === 1 && aÃÂ±osSeleccionados.size > 0) ||
    (paso === 2 && mesesSeleccionados.size > 0) ||
    (paso === 3 && (todasLasCedulas || cedulasSeleccionadas.size > 0))

  return (
    <Dialog open={open} onOpenChange={handleAbrir}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Reporte Contable</DialogTitle>
          <DialogDescription>
            {paso === 1 && 'Selecciona uno o varios aÃÂ±os'}
            {paso === 2 && 'Selecciona uno o varios meses (solo meses pasados tendrÃÂ¡n datos de pagos)'}
            {paso === 3 && 'Busca y selecciona cÃÂ©dulas, o marca "Todas"'}
          </DialogDescription>
        </DialogHeader>

        {paso === 1 && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <Button type="button" variant="outline" size="sm" onClick={seleccionarTodosAÃÂ±os}>
                Seleccionar todos
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {aÃÂ±osOpciones.map((aÃÂ±o) => (
                <button
                  key={aÃÂ±o}
                  type="button"
                  onClick={() => toggleAÃÂ±o(aÃÂ±o)}
                  className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
                    aÃÂ±osSeleccionados.has(aÃÂ±o)
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'border-gray-200 hover:border-blue-300 text-gray-700'
                  }`}
                >
                  {aÃÂ±o}
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

        {paso === 3 && (
          <div className="space-y-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={todasLasCedulas}
                onChange={(e) => setTodasLasCedulas(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-medium">Todas las cÃÂ©dulas</span>
            </label>

            {!todasLasCedulas && (
              <>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar por cÃÂ©dula o nombre..."
                    value={busquedaCedula}
                    onChange={(e) => setBusquedaCedula(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <div className="max-h-48 overflow-y-auto border rounded-md p-2 space-y-1">
                  {loadingCedulas ? (
                    <p className="text-sm text-muted-foreground py-4 text-center">Buscando...</p>
                  ) : cedulasDisponibles.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-4 text-center">
                      {busquedaCedula ? 'Sin resultados' : 'Escribe para buscar'}
                    </p>
                  ) : (
                    cedulasDisponibles.map((c) => (
                      <button
                        key={c.cedula}
                        type="button"
                        onClick={() => toggleCedula(c.cedula)}
                        className={`w-full flex items-center justify-between px-3 py-2 rounded text-left text-sm transition-colors ${
                          cedulasSeleccionadas.has(c.cedula)
                            ? 'bg-blue-100 border border-blue-300'
                            : 'hover:bg-gray-50 border border-transparent'
                        }`}
                      >
                        <span>
                          {c.cedula} Ã¢ÂÂ {c.nombre || '(sin nombre)'}
                        </span>
                        {cedulasSeleccionadas.has(c.cedula) && (
                          <Check className="h-4 w-4 text-blue-600 shrink-0" />
                        )}
                      </button>
                    ))
                  )}
                </div>
              </>
            )}
          </div>
        )}

        <DialogFooter className="flex gap-2 sm:gap-0">
          {paso > 1 && (
            <Button type="button" variant="outline" onClick={handleAtras}>
              <ChevronLeft className="h-4 w-4 mr-1" />
              AtrÃÂ¡s
            </Button>
          )}
          <div className="flex-1" />
          <Button type="button" variant="outline" onClick={() => handleAbrir(false)}>
            Cancelar
          </Button>
          {paso < 3 ? (
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
