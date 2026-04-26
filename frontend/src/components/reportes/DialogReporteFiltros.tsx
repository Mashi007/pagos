import { useEffect, useState, useRef } from 'react'

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

import { ChevronRight, ChevronLeft } from 'lucide-react'

const MESES_NOMBRES = [
  'Ene',
  'Feb',
  'Mar',
  'Abr',
  'May',
  'Jun',

  'Jul',
  'Ago',
  'Sep',
  'Oct',
  'Nov',
  'Dic',
]

export interface FiltrosReporte {
  años: number[]

  meses: number[]

  /** Clientes (hoja): filtro por columna LOTE en la hoja sincronizada. */
  lotes?: number[]

  /** Rango calendario YYYY-MM-DD (reporte Pagos Gmail). */
  fecha_desde?: string

  fecha_hasta?: string
}

interface DialogReporteFiltrosProps {
  open: boolean

  onOpenChange: (open: boolean) => void

  onConfirm: (filtros: FiltrosReporte) => void

  tituloReporte: string

  /** `lotes`: un paso, números de lote separados por coma (columna LOTE). `rango_fechas`: desde/hasta día. */
  variant?: 'periodo' | 'lotes' | 'rango_fechas'
}

export function DialogReporteFiltros({
  open,

  onOpenChange,

  onConfirm,

  tituloReporte,

  variant = 'periodo',
}: DialogReporteFiltrosProps) {
  const [paso, setPaso] = useState<1 | 2>(1)

  const [añosSeleccionados, setAñosSeleccionados] = useState<Set<number>>(
    new Set()
  )

  const [mesesSeleccionados, setMesesSeleccionados] = useState<Set<number>>(
    new Set()
  )

  const [lotesTexto, setLotesTexto] = useState('')

  const defaultFechaDesde = () => {
    const d = new Date()
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    return `${y}-${m}-01`
  }

  const defaultFechaHasta = () => new Date().toISOString().slice(0, 10)

  const [fechaDesde, setFechaDesde] = useState(defaultFechaDesde)

  const [fechaHasta, setFechaHasta] = useState(defaultFechaHasta)

  /** Solo al pasar de cerrado → abierto: evita borrar el texto si el efecto corre tarde tras pegar. */
  const lotesDialogEstabaAbiertoRef = useRef(false)

  useEffect(() => {
    const estaba = lotesDialogEstabaAbiertoRef.current
    lotesDialogEstabaAbiertoRef.current = open
    if (open && !estaba && variant === 'lotes') {
      setLotesTexto('')
    }
    if (open && !estaba && variant === 'rango_fechas') {
      setFechaDesde(defaultFechaDesde())
      setFechaHasta(defaultFechaHasta())
    }
  }, [open, variant])

  const añoActual = new Date().getFullYear()

  const añosOpciones = [
    añoActual,
    añoActual - 1,
    añoActual - 2,
    añoActual - 3,
    añoActual - 4,
  ].filter(a => a !== 2022 && a !== 2023)

  const toggleAño = (año: number) => {
    setAñosSeleccionados(prev => {
      const next = new Set(prev)

      if (next.has(año)) next.delete(año)
      else next.add(año)

      return next
    })
  }

  const toggleMes = (mes: number) => {
    setMesesSeleccionados(prev => {
      const next = new Set(prev)

      if (next.has(mes)) next.delete(mes)
      else next.add(mes)

      return next
    })
  }

  const seleccionarTodosAños = () => {
    setAñosSeleccionados(new Set(añosOpciones))
  }

  const seleccionarTodosMeses = () => {
    setMesesSeleccionados(new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]))
  }

  const handleAbrir = (isOpen: boolean) => {
    if (!isOpen) {
      setPaso(1)

      setAñosSeleccionados(new Set())

      setMesesSeleccionados(new Set())

      setLotesTexto('')
    }

    onOpenChange(isOpen)
  }

  const handleSiguiente = () => {
    if (añosSeleccionados.size === 0) return

    setPaso(2)
  }

  const handleAtras = () => setPaso(1)

  const handleDescargar = () => {
    if (paso === 1 && añosSeleccionados.size === 0) return

    if (paso === 2 && mesesSeleccionados.size === 0) return

    const años =
      paso === 1
        ? Array.from(añosSeleccionados).sort((a, b) => b - a)
        : Array.from(añosSeleccionados).sort((a, b) => b - a)

    const meses =
      paso === 2
        ? Array.from(mesesSeleccionados).sort((a, b) => a - b)
        : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    onConfirm({ años, meses })

    handleAbrir(false)
  }

  const puedeContinuar =
    paso === 1 ? añosSeleccionados.size > 0 : mesesSeleccionados.size > 0

  const parseLotesDesdeTexto = (text: string): number[] => {
    const out: number[] = []
    const seen = new Set<number>()
    for (const raw of text.split(/[,;\s]+/)) {
      const t = raw.trim()
      if (!t || !/^\d+$/.test(t)) continue
      const n = Number.parseInt(t, 10)
      if (!Number.isFinite(n) || !Number.isInteger(n)) continue
      if (!seen.has(n)) {
        seen.add(n)
        out.push(n)
      }
    }
    return out
  }

  const handleDescargarLotes = () => {
    const lotes = parseLotesDesdeTexto(lotesTexto)
    if (!lotes.length) return
    onConfirm({ años: [], meses: [], lotes })
    handleAbrir(false)
  }

  const handleDescargarRangoFechas = () => {
    const d0 = (fechaDesde || '').trim()
    const d1 = (fechaHasta || '').trim()
    if (!d0 || !d1) return
    onConfirm({
      años: [],
      meses: [],
      fecha_desde: d0,
      fecha_hasta: d1,
    })
    handleAbrir(false)
  }

  const lotesPreview = parseLotesDesdeTexto(lotesTexto)

  if (variant === 'rango_fechas') {
    return (
      <Dialog open={open} onOpenChange={handleAbrir}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{tituloReporte}</DialogTitle>
            <DialogDescription>
              Filtra por día de registro en auditoría (fecha/hora guardada en el
              servidor). Rango máximo 366 días.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label
                className="text-sm font-medium text-gray-800"
                htmlFor="fecha-desde-reporte"
              >
                Fecha desde
              </label>
              <Input
                id="fecha-desde-reporte"
                type="date"
                value={fechaDesde}
                onChange={e => setFechaDesde(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label
                className="text-sm font-medium text-gray-800"
                htmlFor="fecha-hasta-reporte"
              >
                Fecha hasta
              </label>
              <Input
                id="fecha-hasta-reporte"
                type="date"
                value={fechaHasta}
                onChange={e => setFechaHasta(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="flex gap-2 sm:gap-0">
            <div className="flex-1" />
            <Button
              type="button"
              variant="outline"
              onClick={() => handleAbrir(false)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleDescargarRangoFechas}
              disabled={!fechaDesde.trim() || !fechaHasta.trim()}
            >
              Descargar Excel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  if (variant === 'lotes') {
    return (
      <Dialog open={open} onOpenChange={handleAbrir}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{tituloReporte}</DialogTitle>

            <DialogDescription>
              Indique el número de lote de la columna{' '}
              <span className="font-mono">LOTE</span> en la hoja CONCILIACIÓN
              (sincronizada en el servidor). Puede escribir varios separados por
              coma; se exportan las filas cuyo lote coincida con el informe que
              eligió (Clientes: cédula, nombre, teléfono, correo; Préstamos
              Drive: diez columnas de préstamo).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            <label
              className="text-sm font-medium text-gray-800"
              htmlFor="lotes-hoja-input"
            >
              Lotes
            </label>
            <Input
              id="lotes-hoja-input"
              inputMode="numeric"
              autoComplete="off"
              placeholder="Ej. 70 o 70, 71"
              value={lotesTexto}
              onChange={e => setLotesTexto(e.target.value)}
            />
            {lotesPreview.length > 0 ? (
              <p className="text-xs text-gray-600">
                Se descargarán filas con LOTE:{' '}
                <span className="font-mono font-medium">
                  {lotesPreview.join(', ')}
                </span>
              </p>
            ) : (
              <p className="text-xs text-amber-800/90">
                Escriba al menos un entero (solo números, separados por coma).
              </p>
            )}
          </div>

          <DialogFooter className="flex gap-2 sm:gap-0">
            <div className="flex-1" />
            <Button
              type="button"
              variant="outline"
              onClick={() => handleAbrir(false)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleDescargarLotes}
              disabled={lotesPreview.length === 0}
            >
              Descargar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={handleAbrir}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{tituloReporte}</DialogTitle>

          <DialogDescription>
            {paso === 1
              ? 'Selecciona uno o varios años'
              : 'Selecciona uno o varios meses'}
          </DialogDescription>
        </DialogHeader>

        {paso === 1 && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={seleccionarTodosAños}
              >
                Seleccionar todos
              </Button>
            </div>

            <div className="flex flex-wrap gap-2">
              {añosOpciones.map(año => (
                <button
                  key={año}
                  type="button"
                  onClick={() => toggleAño(año)}
                  className={`rounded-lg border-2 px-4 py-2 text-sm font-medium transition-colors ${
                    añosSeleccionados.has(año)
                      ? 'border-blue-600 bg-blue-600 text-white'
                      : 'border-gray-200 text-gray-700 hover:border-blue-300'
                  }`}
                >
                  {año}
                </button>
              ))}
            </div>
          </div>
        )}

        {paso === 2 && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={seleccionarTodosMeses}
              >
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
                    className={`rounded-lg border-2 px-3 py-2 text-sm font-medium transition-colors ${
                      mesesSeleccionados.has(mes)
                        ? 'border-blue-600 bg-blue-600 text-white'
                        : 'border-gray-200 text-gray-700 hover:border-blue-300'
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
              <ChevronLeft className="mr-1 h-4 w-4" />
              Atrás
            </Button>
          )}

          <div className="flex-1" />

          <Button
            type="button"
            variant="outline"
            onClick={() => handleAbrir(false)}
          >
            Cancelar
          </Button>

          {paso === 1 ? (
            <Button
              type="button"
              onClick={handleSiguiente}
              disabled={!puedeContinuar}
            >
              Siguiente
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              onClick={handleDescargar}
              disabled={!puedeContinuar}
            >
              Descargar
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
