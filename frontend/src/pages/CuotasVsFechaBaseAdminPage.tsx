import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, RefreshCw, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog'
import {
  prestamoService,
  type CuotaVsFechaBaseItem,
} from '../services/prestamoService'
import { getErrorMessage } from '../types/errors'
import { useSimpleAuth } from '../store/simpleAuthStore'

const QK = ['actualizaciones', 'cuotas-vs-fecha-base'] as const

const PAGE_SIZE = 50

function fmtIso(s?: string | null): string {
  if (!s) return '—'
  const t = String(s).trim()
  return t.length >= 10 ? t.slice(0, 10) : t
}

/** Todas las filas del listado son elegibles para «Sí» (recalcular fechas). */
function filaElegibleSi(_row: CuotaVsFechaBaseItem): boolean {
  return true
}

export default function CuotasVsFechaBaseAdminPage() {
  const queryClient = useQueryClient()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const [cedula, setCedula] = useState('')
  const [appliedCedula, setAppliedCedula] = useState('')
  const [offset, setOffset] = useState(0)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(() => new Set())
  const [batchRunning, setBatchRunning] = useState(false)
  const [confirmLoteSi, setConfirmLoteSi] = useState(false)

  const q = useQuery({
    queryKey: [...QK, appliedCedula, offset],
    queryFn: () =>
      prestamoService.getCuotasVsFechaBaseDesalineadas({
        limit: PAGE_SIZE,
        offset,
        cedula_q: appliedCedula || undefined,
      }),
  })

  const total = q.data?.total ?? 0
  const items = q.data?.items ?? []
  const hasPrev = offset > 0
  const hasNext = offset + PAGE_SIZE < total

  const rangoTxt = useMemo(() => {
    if (total === 0) return '0 resultados'
    const ini = offset + 1
    const fin = Math.min(offset + PAGE_SIZE, total)
    return `${ini}-${fin} de ${total}`
  }, [offset, total])

  useEffect(() => {
    setSelected(new Set())
  }, [offset, appliedCedula])

  const elegiblesPagina = useMemo(
    () => items.filter(filaElegibleSi),
    [items],
  )
  const todosElegiblesSeleccionados =
    elegiblesPagina.length > 0 && elegiblesPagina.every(r => selected.has(r.prestamo_id))
  const algunElegibleSeleccionado = elegiblesPagina.some(r => selected.has(r.prestamo_id))

  const idsSeleccionadosOrdenados = useMemo(() => {
    const ids: number[] = []
    for (const r of items) {
      if (selected.has(r.prestamo_id)) ids.push(r.prestamo_id)
    }
    return ids
  }, [items, selected])

  const seleccionadosElegiblesParaSi = useMemo(() => {
    const out: number[] = []
    for (const pid of idsSeleccionadosOrdenados) {
      const row = items.find(r => r.prestamo_id === pid)
      if (row && filaElegibleSi(row)) out.push(pid)
    }
    return out
  }, [idsSeleccionadosOrdenados, items])

  const ejecutarSi = async (row: CuotaVsFechaBaseItem) => {
    if (!esAdmin || busyId != null) return
    setBusyId(row.prestamo_id)
    try {
      await prestamoService.postRecalcularFechasAmortizacion(row.prestamo_id)
      toast.success(
        `Préstamo #${row.prestamo_id}: fechas de amortización actualizadas según la fecha de aprobación / base.`
      )
      await queryClient.invalidateQueries({ queryKey: [...QK] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudieron recalcular las fechas de cuotas.')
    } finally {
      setBusyId(null)
    }
  }

  const ejecutarNo = (_row: CuotaVsFechaBaseItem) => {
    // Igual que «No» en Fechas (Q vs BD) respecto a BD: no persiste nada.
  }

  const ejecutarLoteSi = async () => {
    if (!esAdmin || batchRunning || seleccionadosElegiblesParaSi.length === 0) return
    setBatchRunning(true)
    setConfirmLoteSi(false)
    let ok = 0
    const errores: string[] = []
    for (const pid of seleccionadosElegiblesParaSi) {
      try {
        await prestamoService.postRecalcularFechasAmortizacion(pid)
        ok += 1
      } catch (e) {
        errores.push(`#${pid}: ${getErrorMessage(e) || 'error'}`)
      }
    }
    if (errores.length === 0) {
      toast.success(`Sí en lote: ${ok} préstamo(s) con fechas de cuotas recalculadas.`)
    } else {
      toast.message(
        `Sí en lote: ${ok} ok, ${errores.length} error(es). Revise consola o reintente fila a fila.`
      )
      console.warn('[cuotas-vs-fecha-base] lote Sí', errores)
    }
    setSelected(new Set())
    await queryClient.invalidateQueries({ queryKey: [...QK] })
    setBatchRunning(false)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Actualizaciones · Cuotas vs fecha base"
        description="Préstamos donde el vencimiento de la cuota 1 es anterior a la fecha base de amortización (fecha_base_calculo o día de fecha_aprobacion). Use Sí para recalcular solo las fechas de vencimiento de la tabla de amortización según la fecha de aprobación/base ya guardada en el préstamo (mismo criterio que Notificaciones · Fechas: acción explícita). No no modifica la base de datos."
        icon={AlertTriangle}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">
              Cédula (opcional)
            </label>
            <Input
              value={cedula}
              onChange={e => setCedula(e.target.value)}
              placeholder="V12345678…"
            />
          </div>
          <Button
            type="button"
            onClick={() => {
              setAppliedCedula(cedula.trim())
              setOffset(0)
            }}
            className="gap-2"
          >
            <Search className="h-4 w-4" />
            Buscar
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => void q.refetch()}
            className="gap-2"
            disabled={q.isFetching}
          >
            <RefreshCw className={`h-4 w-4 ${q.isFetching ? 'animate-spin' : ''}`} />
            Refrescar
          </Button>
          <Button asChild type="button" variant="outline">
            <Link to="/notificaciones/fecha">Ir a Fechas (Q vs BD)</Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resultados ({rangoTxt})</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {q.isFetching ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : q.isError ? (
            <p className="text-sm text-destructive">{getErrorMessage(q.error)}</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin casos para este filtro (total global puede ser 0).
            </p>
          ) : (
            <>
              <div className="mb-3 space-y-2 border-b border-border/60 pb-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    Con casilla marcada:{' '}
                    <span className="font-semibold text-foreground">{idsSeleccionadosOrdenados.length}</span>
                    {' · '}
                    Listos para <strong>Sí</strong> (recalcular fechas):{' '}
                    <span className="font-semibold text-foreground">
                      {seleccionadosElegiblesParaSi.length}
                    </span>
                    {' · '}
                    Elegibles en esta página: {elegiblesPagina.length}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={selected.size === 0 || batchRunning}
                    onClick={() => setSelected(new Set())}
                  >
                    Limpiar selección
                  </Button>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    className="gap-1.5 bg-blue-600 text-white hover:bg-blue-700"
                    disabled={
                      !esAdmin || seleccionadosElegiblesParaSi.length === 0 || batchRunning
                    }
                    onClick={() => setConfirmLoteSi(true)}
                  >
                    <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />
                    Sí en lote (recalcular fechas)
                  </Button>
                </div>
              </div>

              <table className="w-full min-w-[960px] border-collapse text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="w-10 py-2 pr-1 text-center font-medium">
                      <input
                        type="checkbox"
                        ref={el => {
                          if (el) {
                            el.indeterminate =
                              algunElegibleSeleccionado && !todosElegiblesSeleccionados
                          }
                        }}
                        checked={todosElegiblesSeleccionados}
                        onChange={() => {
                          setSelected(prev => {
                            const n = new Set(prev)
                            if (todosElegiblesSeleccionados) {
                              elegiblesPagina.forEach(r => n.delete(r.prestamo_id))
                            } else {
                              elegiblesPagina.forEach(r => n.add(r.prestamo_id))
                            }
                            return n
                          })
                        }}
                        disabled={!esAdmin || batchRunning || elegiblesPagina.length === 0}
                        title="Seleccionar o quitar todos los de esta página"
                        aria-label="Seleccionar todos en esta página"
                      />
                    </th>
                    <th className="py-2 pr-2 font-medium">Préstamo</th>
                    <th className="py-2 pr-2 font-medium">Cédula</th>
                    <th className="py-2 pr-2 font-medium">Estado</th>
                    <th className="py-2 pr-2 font-medium">Fecha base</th>
                    <th className="py-2 pr-2 font-medium">Venc. cuota 1</th>
                    <th className="py-2 pr-2 font-medium">Días (C1 − base)</th>
                    <th className="py-2 pr-2 font-medium">Modalidad</th>
                    <th className="py-2 pr-2 font-medium">Nº cuotas</th>
                    <th className="py-2 pr-2 font-medium">Ver</th>
                    <th className="py-2 pr-2 font-medium">Sí / No</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map(row => {
                    const elegible = filaElegibleSi(row)
                    return (
                      <tr key={row.prestamo_id} className="border-b border-border/60">
                        <td className="py-2 pr-1 text-center align-middle">
                          {elegible ? (
                            <input
                              type="checkbox"
                              checked={selected.has(row.prestamo_id)}
                              onChange={e => {
                                setSelected(prev => {
                                  const n = new Set(prev)
                                  if (e.target.checked) n.add(row.prestamo_id)
                                  else n.delete(row.prestamo_id)
                                  return n
                                })
                              }}
                              disabled={!esAdmin || batchRunning}
                              aria-label={`Seleccionar préstamo ${row.prestamo_id}`}
                            />
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="py-2 pr-2 font-mono">{row.prestamo_id}</td>
                        <td className="py-2 pr-2">{row.cedula || '—'}</td>
                        <td className="py-2 pr-2">{row.estado || '—'}</td>
                        <td className="py-2 pr-2">{fmtIso(row.fecha_base)}</td>
                        <td className="py-2 pr-2">{fmtIso(row.vencimiento_cuota_1)}</td>
                        <td className="py-2 pr-2 font-mono">
                          {row.dias_cuota1_menos_base ?? '—'}
                        </td>
                        <td className="py-2 pr-2">{row.modalidad_pago || '—'}</td>
                        <td className="py-2 pr-2">{row.numero_cuotas}</td>
                        <td className="py-2 pr-2">
                          <Button
                            asChild
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs"
                          >
                            <Link to={`/prestamos?prestamo_id=${row.prestamo_id}`}>Ver</Link>
                          </Button>
                        </td>
                        <td className="py-2 pr-2">
                          {elegible ? (
                            <span className="inline-flex flex-wrap gap-1">
                              <Button
                                type="button"
                                size="sm"
                                variant="default"
                                className="h-7 px-2 text-xs"
                                disabled={!esAdmin || batchRunning || busyId === row.prestamo_id}
                                title={
                                  esAdmin
                                    ? 'Recalcular fechas de vencimiento de todas las cuotas según fecha de aprobación / base del préstamo (sin cambiar montos ni borrar cuotas).'
                                    : 'Solo administrador.'
                                }
                                onClick={() => {
                                  if (!esAdmin || batchRunning || busyId != null) return
                                  void ejecutarSi(row)
                                }}
                              >
                                Sí
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                className="h-7 px-2 text-xs"
                                disabled={!esAdmin || batchRunning || busyId === row.prestamo_id}
                                title={
                                  esAdmin
                                    ? 'No modifica la base de datos (solo descarta la acción en esta fila).'
                                    : 'Solo administrador.'
                                }
                                onClick={() => {
                                  if (!esAdmin || batchRunning || busyId != null) return
                                  ejecutarNo(row)
                                }}
                              >
                                No
                              </Button>
                            </span>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </>
          )}

          {total > PAGE_SIZE ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!hasPrev || q.isFetching}
                onClick={() => setOffset(o => Math.max(0, o - PAGE_SIZE))}
              >
                Anterior
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!hasNext || q.isFetching}
                onClick={() => setOffset(o => o + PAGE_SIZE)}
              >
                Siguiente
              </Button>
              <span className="text-xs text-muted-foreground">
                Página {Math.floor(offset / PAGE_SIZE) + 1} de{' '}
                {Math.max(1, Math.ceil(total / PAGE_SIZE))}
              </span>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Dialog open={confirmLoteSi} onOpenChange={open => !open && setConfirmLoteSi(false)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Sí en lote (recalcular fechas de cuotas)</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Se aplicará la misma acción que el botón <strong>Sí</strong> en cada fila: recalcular las fechas de
            vencimiento de la tabla de amortización según la <strong>fecha de aprobación / base</strong> ya guardada
            en el préstamo (montos y aplicación de pagos no se borran) en{' '}
            <span className="font-semibold tabular-nums">{seleccionadosElegiblesParaSi.length}</span> préstamo(s){' '}
            con casilla marcada. Los que fallen se pueden revisar uno a uno.
          </p>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => setConfirmLoteSi(false)} disabled={batchRunning}>
              Cancelar
            </Button>
            <Button type="button" onClick={() => void ejecutarLoteSi()} disabled={batchRunning}>
              {batchRunning ? 'Ejecutando…' : 'Confirmar y aplicar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
