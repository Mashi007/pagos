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

  /** Rango calendario YYYY-MM-DD (reporte Pagos Gmail / Cuentas por cobrar). */
  fecha_desde?: string

  fecha_hasta?: string

  /** Cuentas por cobrar: cantidad de cuotas impagas (1-15). */
  cuotas_impagas_min?: number

  cuotas_impagas_max?: number

  /** Formato de descarga solicitado desde el dialogo. */
  formato?: 'excel' | 'pdf'
}

interface DialogReporteFiltrosProps {
  open: boolean

  onOpenChange: (open: boolean) => void

  onConfirm: (filtros: FiltrosReporte) => void

  tituloReporte: string

  /** `lotes`: LOTE. `rango_fechas`: desde/hasta. `cartera`: fechas + cuotas. `aseguradora`: corte fijo sin fechas. */
  variant?: 'periodo' | 'lotes' | 'rango_fechas' | 'cartera' | 'aseguradora'
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

  const toYmdLocal = (d: Date) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }

  /** Cartera: por defecto hace ~60 dias (no el dia 1 del mes). */
  const defaultFechaDesde = () => {
    const d = new Date()
    d.setDate(d.getDate() - 60)
    return toYmdLocal(d)
  }

  const defaultFechaHasta = () => toYmdLocal(new Date())

  const [fechaDesde, setFechaDesde] = useState(defaultFechaDesde)

  const [fechaHasta, setFechaHasta] = useState(defaultFechaHasta)

  const [cuotasImpagasMin, setCuotasImpagasMin] = useState(1)

  const [cuotasImpagasMax, setCuotasImpagasMax] = useState(15)

  /** Solo al pasar de cerrado → abierto: evita borrar el texto si el efecto corre tarde tras pegar. */
  const lotesDialogEstabaAbiertoRef = useRef(false)

  useEffect(() => {
    const estaba = lotesDialogEstabaAbiertoRef.current
    lotesDialogEstabaAbiertoRef.current = open
    if (open && !estaba && variant === 'lotes') {
      setLotesTexto('')
    }
    if (
      open &&
      !estaba &&
      (variant === 'rango_fechas' || variant === 'cartera')
    ) {
      // Siempre al abrir: defaults locales (hoy-60 / hoy). Evita el viejo
      // dia 1 del mes y fechas UTC desfasadas que ignoraban el rango elegido.
      setFechaDesde(defaultFechaDesde())
      setFechaHasta(defaultFechaHasta())
    }
    if (open && !estaba && variant === 'cartera') {
      setCuotasImpagasMin(1)
      setCuotasImpagasMax(15)
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

  /** Orden cronologico: menor -> mayor (columnas desde/hasta comparables). */
  const ordenarFechasAsc = (a: string, b: string): [string, string] => {
    const x = (a || '').trim()
    const y = (b || '').trim()
    if (!x || !y) return [x, y]
    return x <= y ? [x, y] : [y, x]
  }

  const [fechaMenorPreview, fechaMayorPreview] = ordenarFechasAsc(
    fechaDesde,
    fechaHasta
  )

  const handleDescargarRangoFechas = () => {
    const [d0, d1] = ordenarFechasAsc(fechaDesde, fechaHasta)
    if (!d0 || !d1) return
    if (d0 !== fechaDesde || d1 !== fechaHasta) {
      setFechaDesde(d0)
      setFechaHasta(d1)
    }
    onConfirm({
      años: [],
      meses: [],
      fecha_desde: d0,
      fecha_hasta: d1,
    })
    handleAbrir(false)
  }

  const lotesPreview = parseLotesDesdeTexto(lotesTexto)

  const handleDescargarCartera = (formato: 'excel' | 'pdf') => {
    const [d0, d1] = ordenarFechasAsc(fechaDesde, fechaHasta)
    if (!d0 || !d1) return
    if (d0 !== fechaDesde || d1 !== fechaHasta) {
      setFechaDesde(d0)
      setFechaHasta(d1)
    }
    const minN = Math.min(15, Math.max(1, Number(cuotasImpagasMin) || 1))
    const maxN = Math.min(15, Math.max(1, Number(cuotasImpagasMax) || 15))
    onConfirm({
      años: [],
      meses: [],
      fecha_desde: d0,
      fecha_hasta: d1,
      cuotas_impagas_min: Math.min(minN, maxN),
      cuotas_impagas_max: Math.max(minN, maxN),
      formato,
    })
    handleAbrir(false)
  }

  const opcionesCuotasImpagas = Array.from({ length: 15 }, (_, i) => i + 1)

  if (variant === 'cartera') {
    return (
      <Dialog open={open} onOpenChange={handleAbrir}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{tituloReporte}</DialogTitle>
            <DialogDescription>
              Indique dos fechas de corte: siempre se ordenan de la menor a la
              mayor (columnas izquierda = fecha menor, derecha = mayor) para ver
              el cambio. Impagas = no pagadas al 100%. El filtro 1-15 aplica al
              total en la fecha mayor (hasta).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label
                className="text-sm font-medium text-gray-800"
                htmlFor="cartera-fecha-desde"
              >
                Desde (fecha menor)
              </label>
              <Input
                id="cartera-fecha-desde"
                type="date"
                value={fechaDesde}
                onChange={e => setFechaDesde(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label
                className="text-sm font-medium text-gray-800"
                htmlFor="cartera-fecha-hasta"
              >
                Hasta (fecha mayor)
              </label>
              <Input
                id="cartera-fecha-hasta"
                type="date"
                value={fechaHasta}
                onChange={e => setFechaHasta(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label
                  className="text-sm font-medium text-gray-800"
                  htmlFor="cartera-impagas-min"
                >
                  Min. impagas (hasta)
                </label>
                <select
                  id="cartera-impagas-min"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={cuotasImpagasMin}
                  onChange={e => setCuotasImpagasMin(Number(e.target.value))}
                >
                  {opcionesCuotasImpagas.map(n => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label
                  className="text-sm font-medium text-gray-800"
                  htmlFor="cartera-impagas-max"
                >
                  Max. impagas (hasta)
                </label>
                <select
                  id="cartera-impagas-max"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={cuotasImpagasMax}
                  onChange={e => setCuotasImpagasMax(Number(e.target.value))}
                >
                  {opcionesCuotasImpagas.map(n => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <p className="text-xs text-gray-600">
              Ejemplo: Min 1 / Max 15 incluye toda la cartera con impagas a la
              fecha hasta (suele ser miles de prestamos). Min 3 excluye los de
              1-2 cuotas.
            </p>

            <p className="rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-900">
              Se exportara: fechas{' '}
              <span className="font-semibold">
                {fechaMenorPreview || '-'}
                {' a '}
                {fechaMayorPreview || '-'}
              </span>{' '}
              | filtro impagas en fecha hasta:{' '}
              <span className="font-semibold">
                {Math.min(cuotasImpagasMin, cuotasImpagasMax)}-
                {Math.max(cuotasImpagasMin, cuotasImpagasMax)}
              </span>
              . Min 1 / Max 15 = casi toda la cartera; use p. ej. 3-7 para
              acotar.
            </p>
          </div>
          <DialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleAbrir(false)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleDescargarCartera('pdf')}
              disabled={!fechaDesde.trim() || !fechaHasta.trim()}
            >
              Descargar PDF
            </Button>
            <Button
              type="button"
              onClick={() => handleDescargarCartera('excel')}
              disabled={!fechaDesde.trim() || !fechaHasta.trim()}
            >
              Descargar Excel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  if (variant === 'aseguradora') {
    const handleDescargarAseguradora = (formato: 'excel' | 'pdf') => {
      onConfirm({
        años: [],
        meses: [],
        formato,
      })
      handleAbrir(false)
    }

    return (
      <Dialog open={open} onOpenChange={handleAbrir}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{tituloReporte}</DialogTitle>
            <DialogDescription>
              Solo cuotas no pagadas del universo de la hoja, con corte fijo al
              1 de agosto de 2026. Incluye unicamente cedulas con 4 o mas cuotas
              impagas (3 o menos no entran). Sin filtros de fechas ni de cuotas.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <p className="rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-900">
              Corte fijo:{' '}
              <span className="font-semibold">2026-08-01</span>
              {' · '}
              Condicion:{' '}
              <span className="font-semibold">4 o mas cuotas sin pagar</span>
            </p>
          </div>
          <DialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleAbrir(false)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleDescargarAseguradora('pdf')}
            >
              Descargar PDF
            </Button>
            <Button
              type="button"
              onClick={() => handleDescargarAseguradora('excel')}
            >
              Descargar Excel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

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
