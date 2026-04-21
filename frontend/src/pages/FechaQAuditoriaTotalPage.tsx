import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Search, RefreshCw } from 'lucide-react'
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
  notificacionService,
  type FechaQAuditoriaTotalItem,
} from '../services/notificacionService'
import { getErrorMessage } from '../types/errors'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA } from './notificaciones/notificacionesPage.constants'

const QK = ['notificaciones', 'fecha-q-auditoria-total'] as const

function filaElegibleAcciones(row: FechaQAuditoriaTotalItem): boolean {
  return row.puede_aplicar === true && Boolean((row.cedula || '').trim())
}

function loteDesdeAuditoriaItem(row: FechaQAuditoriaTotalItem): string | undefined {
  const qc = row.q_cache
  const loteRaw =
    qc && typeof qc === 'object' && 'lote_aplicado' in qc
      ? (qc as { lote_aplicado?: unknown }).lote_aplicado
      : undefined
  return typeof loteRaw === 'string' && loteRaw.trim() ? loteRaw.trim() : undefined
}

function fmtIso(s?: string | null): string {
  if (!s) return '—'
  const t = String(s).trim()
  return t.length >= 10 ? t.slice(0, 10) : t
}

export default function FechaQAuditoriaTotalPage() {
  const queryClient = useQueryClient()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const [cedula, setCedula] = useState('')
  const [appliedCedula, setAppliedCedula] = useState('')
  const [soloConDiferencia, setSoloConDiferencia] = useState(true)
  /** Si true, el GET envía `excluir_marcados_no: false` y vuelven a listarse los marcados «No». */
  const [incluirMarcadosNo, setIncluirMarcadosNo] = useState(false)
  const [offset, setOffset] = useState(0)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(() => new Set())
  const [batchRunning, setBatchRunning] = useState(false)
  const [confirmLote, setConfirmLote] = useState<'si' | 'no' | null>(null)
  const limit = NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA

  const q = useQuery({
    queryKey: [...QK, appliedCedula, soloConDiferencia, incluirMarcadosNo, offset],
    queryFn: () =>
      notificacionService.getFechaQAuditoriaTotal({
        limit,
        offset,
        cedula_q: appliedCedula || undefined,
        solo_con_diferencia: soloConDiferencia,
        excluir_marcados_no: !incluirMarcadosNo,
      }),
  })

  const total = q.data?.total ?? 0
  const items = q.data?.items ?? []
  const hasPrev = offset > 0
  const hasNext = offset + limit < total
  const rangoTxt = useMemo(() => {
    if (total === 0) return '0 resultados'
    const ini = offset + 1
    const fin = Math.min(offset + limit, total)
    return `${ini}-${fin} de ${total}`
  }, [offset, total, limit])

  useEffect(() => {
    setSelected(new Set())
  }, [offset, appliedCedula, soloConDiferencia, incluirMarcadosNo])

  const elegiblesPagina = useMemo(
    () => items.filter(filaElegibleAcciones),
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

  const ejecutarLoteSi = async () => {
    if (!esAdmin || batchRunning || idsSeleccionadosOrdenados.length === 0) return
    setBatchRunning(true)
    setConfirmLote(null)
    let ok = 0
    const errores: string[] = []
    for (const pid of idsSeleccionadosOrdenados) {
      const row = items.find(r => r.prestamo_id === pid)
      if (!row || !filaElegibleAcciones(row)) continue
      const ced = (row.cedula || '').trim()
      const lote = loteDesdeAuditoriaItem(row)
      try {
        await notificacionService.postAplicarFechaEntregaQComoFechaAprobacion({
          cedula: ced,
          prestamoId: pid,
          ...(lote ? { lote } : {}),
        })
        ok += 1
      } catch (e) {
        errores.push(`#${pid}: ${getErrorMessage(e) || 'error'}`)
      }
    }
    if (errores.length === 0) {
      toast.success(`Sí en lote: ${ok} préstamo(s) actualizado(s).`)
    } else {
      toast.message(`Sí en lote: ${ok} ok, ${errores.length} error(es). Revise el detalle en consola o reintente fila a fila.`)
      console.warn('[fecha-q-auditoria] lote Sí', errores)
    }
    setSelected(new Set())
    await queryClient.invalidateQueries({ queryKey: [...QK] })
    setBatchRunning(false)
  }

  const ejecutarLoteNo = async () => {
    if (!esAdmin || batchRunning || idsSeleccionadosOrdenados.length === 0) return
    setBatchRunning(true)
    setConfirmLote(null)
    let ok = 0
    const errores: string[] = []
    for (const pid of idsSeleccionadosOrdenados) {
      const row = items.find(r => r.prestamo_id === pid)
      if (!row || !filaElegibleAcciones(row)) continue
      try {
        await notificacionService.postFechaQAuditoriaMarcaNoAplicar({ prestamoId: pid })
        ok += 1
      } catch (e) {
        errores.push(`#${pid}: ${getErrorMessage(e) || 'error'}`)
      }
    }
    if (errores.length === 0) {
      toast.success(`No en lote: ${ok} préstamo(s) marcado(s) en auditoría.`)
    } else {
      toast.message(`No en lote: ${ok} ok, ${errores.length} error(es).`)
      console.warn('[fecha-q-auditoria] lote No', errores)
    }
    setSelected(new Set())
    await queryClient.invalidateQueries({ queryKey: [...QK] })
    setBatchRunning(false)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Auditoría Total Q vs Sistema"
        description="Columna Q (caché) vs fecha de aprobación en BD. El caché se recalcula en bloque cada vez que la hoja CONCILIACIÓN se sincroniza desde Drive, y también por job los lunes y jueves a las 04:00 (Caracas). Marque casos y use «Ejecutar Sí/No en lote» con confirmación. Selección por página (10 filas)."
        icon={Database}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">Cédula (opcional)</label>
            <Input
              value={cedula}
              onChange={e => setCedula(e.target.value)}
              placeholder="V12345678 / J..."
            />
          </div>
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={soloConDiferencia}
              onChange={e => {
                setSoloConDiferencia(e.target.checked)
                setOffset(0)
              }}
            />
            Solo con diferencia de fecha
          </label>
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={incluirMarcadosNo}
              onChange={e => {
                setIncluirMarcadosNo(e.target.checked)
                setOffset(0)
              }}
            />
            Incluir marcados «No aplicar Q»
          </label>
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
          >
            <RefreshCw className="h-4 w-4" />
            Refrescar
          </Button>
          <Button asChild type="button" variant="outline">
            <Link to="/notificaciones/fecha">Ir a Notificaciones · Fechas</Link>
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
            <p className="text-sm text-muted-foreground">Sin filas para este filtro.</p>
          ) : (
            <>
              {elegiblesPagina.length > 0 ? (
                <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-border/60 pb-3">
                  <span className="text-sm text-muted-foreground">
                    Seleccionados:{' '}
                    <span className="font-semibold text-foreground">{idsSeleccionadosOrdenados.length}</span>
                    {' · '}
                    Elegibles en página: {elegiblesPagina.length}
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
                  <Button
                    type="button"
                    size="sm"
                    disabled={!esAdmin || idsSeleccionadosOrdenados.length === 0 || batchRunning}
                    onClick={() => setConfirmLote('si')}
                  >
                    Ejecutar «Sí» en lote…
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={!esAdmin || idsSeleccionadosOrdenados.length === 0 || batchRunning}
                    onClick={() => setConfirmLote('no')}
                  >
                    Ejecutar «No» en lote…
                  </Button>
                </div>
              ) : null}
              <table className="w-full min-w-[1380px] border-collapse text-sm">
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
                      title="Seleccionar o quitar todos los casos elegibles de esta página"
                      aria-label="Seleccionar todos los elegibles en esta página"
                    />
                  </th>
                  <th className="py-2 pr-2 font-medium">Préstamo</th>
                  <th className="py-2 pr-2 font-medium">Cédula</th>
                  <th className="py-2 pr-2 font-medium">Estado</th>
                  <th className="py-2 pr-2 font-medium">Aprobación BD</th>
                  <th className="py-2 pr-2 font-medium">Q (ISO caché)</th>
                  <th className="py-2 pr-2 font-medium">Q (texto hoja)</th>
                  <th className="py-2 pr-2 font-medium">Dif. días</th>
                  <th className="py-2 pr-2 font-medium">Puede aplicar</th>
                  <th className="py-2 pr-2 font-medium">Q anterior corrige</th>
                  <th className="py-2 pr-2 font-medium">Req. BD</th>
                  <th className="py-2 pr-2 font-medium">Base BD</th>
                  <th className="py-2 pr-2 font-medium">Sí / No</th>
                  <th className="py-2 pr-2 font-medium">Corrección</th>
                </tr>
              </thead>
              <tbody>
                {items.map(row => {
                  const elegible = filaElegibleAcciones(row)
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
                    <td className="py-2 pr-2">{fmtIso(row.fecha_aprobacion)}</td>
                    <td className="py-2 pr-2">{fmtIso(row.q_fecha_iso)}</td>
                    <td className="py-2 pr-2 max-w-[200px] break-all font-mono text-xs">
                      {row.q_fecha_raw != null && String(row.q_fecha_raw).trim() !== ''
                        ? String(row.q_fecha_raw)
                        : '—'}
                    </td>
                    <td className="py-2 pr-2">{row.diferencia_dias ?? '—'}</td>
                    <td className="py-2 pr-2">
                      {row.puede_aplicar == null ? '—' : row.puede_aplicar ? 'Sí' : 'No'}
                    </td>
                    <td className="py-2 pr-2">
                      {row.correccion_desde_q_anterior_bd == null
                        ? '—'
                        : row.correccion_desde_q_anterior_bd
                          ? 'Sí'
                          : 'No'}
                    </td>
                    <td className="py-2 pr-2">{fmtIso(row.fecha_requerimiento)}</td>
                    <td className="py-2 pr-2">{fmtIso(row.fecha_base_calculo)}</td>
                    <td className="py-2 pr-2">
                      {row.puede_aplicar === true && (row.cedula || '').trim() ? (
                        <span className="inline-flex flex-wrap gap-1">
                          <Button
                            type="button"
                            size="sm"
                            variant="default"
                            className="h-7 px-2 text-xs"
                            disabled={!esAdmin || batchRunning || busyId === row.prestamo_id}
                            title={
                              esAdmin
                                ? 'Guardar en BD la fecha Q como fecha de aprobación (y reglas del servidor).'
                                : 'Solo administrador.'
                            }
                            onClick={() => {
                              if (!esAdmin || batchRunning || busyId != null) return
                              const ced = (row.cedula || '').trim()
                              const qc = row.q_cache
                              const loteRaw =
                                qc && typeof qc === 'object' && 'lote_aplicado' in qc
                                  ? (qc as { lote_aplicado?: unknown }).lote_aplicado
                                  : undefined
                              const lote =
                                typeof loteRaw === 'string' && loteRaw.trim()
                                  ? loteRaw.trim()
                                  : undefined
                              setBusyId(row.prestamo_id)
                              void (async () => {
                                try {
                                  await notificacionService.postAplicarFechaEntregaQComoFechaAprobacion({
                                    cedula: ced,
                                    prestamoId: row.prestamo_id,
                                    ...(lote ? { lote } : {}),
                                  })
                                  toast.success(
                                    'Fecha de aprobación actualizada con la Q; requerimiento y vencimientos según reglas del servidor.'
                                  )
                                  await queryClient.invalidateQueries({ queryKey: [...QK] })
                                } catch (e) {
                                  toast.error(getErrorMessage(e) || 'No se pudo aplicar la fecha Q.')
                                } finally {
                                  setBusyId(null)
                                }
                              })()
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
                                ? 'Descartar en auditoría (no cambia la aprobación en BD).'
                                : 'Solo administrador.'
                            }
                            onClick={() => {
                              if (!esAdmin || batchRunning || busyId != null) return
                              setBusyId(row.prestamo_id)
                              void (async () => {
                                try {
                                  await notificacionService.postFechaQAuditoriaMarcaNoAplicar({
                                    prestamoId: row.prestamo_id,
                                  })
                                  toast.message('Marcado como no aplicar en esta auditoría.')
                                  await queryClient.invalidateQueries({ queryKey: [...QK] })
                                } catch (e) {
                                  toast.error(getErrorMessage(e) || 'No se pudo marcar.')
                                } finally {
                                  setBusyId(null)
                                }
                              })()
                            }}
                          >
                            No
                          </Button>
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="py-2 pr-2 whitespace-nowrap">
                      <Link
                        className="text-xs text-blue-700 underline"
                        to={`/revision-manual/editar/${row.prestamo_id}`}
                      >
                        Revisión manual
                      </Link>
                    </td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
            </>
          )}

          <div className="mt-4 flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!hasPrev || q.isFetching}
              onClick={() => setOffset(o => Math.max(0, o - limit))}
            >
              Anterior
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!hasNext || q.isFetching}
              onClick={() => setOffset(o => o + limit)}
            >
              Siguiente
            </Button>
          </div>
        </CardContent>
      </Card>

      <Dialog open={confirmLote === 'si'} onOpenChange={open => !open && setConfirmLote(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Aplicar «Sí» en lote</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Se aplicará la misma acción que el botón <strong>Sí</strong> fila a fila: guardar la fecha Q como{' '}
            <strong>fecha de aprobación</strong> en BD (requerimiento = día anterior, recálculo de vencimientos si el
            servidor lo aplica) en <span className="font-semibold tabular-nums">{idsSeleccionadosOrdenados.length}</span>{' '}
            préstamo(s) seleccionado(s). Los que fallen se pueden revisar uno a uno.
          </p>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => setConfirmLote(null)} disabled={batchRunning}>
              Cancelar
            </Button>
            <Button type="button" onClick={() => void ejecutarLoteSi()} disabled={batchRunning}>
              {batchRunning ? 'Ejecutando…' : 'Confirmar y aplicar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmLote === 'no'} onOpenChange={open => !open && setConfirmLote(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Marcar «No» en lote</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Se aplicará la misma acción que el botón <strong>No</strong>: marcar en caché «no aplicar Q» en auditoría
            (sin cambiar aprobación en BD) en{' '}
            <span className="font-semibold tabular-nums">{idsSeleccionadosOrdenados.length}</span> préstamo(s).
          </p>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => setConfirmLote(null)} disabled={batchRunning}>
              Cancelar
            </Button>
            <Button type="button" variant="secondary" onClick={() => void ejecutarLoteNo()} disabled={batchRunning}>
              {batchRunning ? 'Ejecutando…' : 'Confirmar y marcar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
