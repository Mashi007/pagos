import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Database, LayoutList, Search, RefreshCw, XCircle } from 'lucide-react'
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
  type FechaQAuditoriaLoteItem,
} from '../services/notificacionService'
import { reporteService } from '../services/reporteService'
import { getErrorMessage } from '../types/errors'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA } from './notificaciones/notificacionesPage.constants'
import { Fechas2BusquedaPanel } from './notificaciones/Fechas2BusquedaPanel'
import { fmtFechaNotifIso } from './notificaciones/notificacionesPageCells'

const QK = ['notificaciones', 'fecha-q-auditoria-total'] as const
const QK_LOTES = ['notificaciones', 'fecha-q-auditoria-lotes'] as const

function fmtIso(s?: string | null): string {
  if (!s) return '-'
  const t = String(s).trim()
  return t.length >= 10 ? t.slice(0, 10) : t
}

function fmtFechaQHojaAuditoria(row: FechaQAuditoriaTotalItem): string {
  const tryFmt = (v: unknown): string | null => {
    if (v == null) return null
    const s = String(v).trim()
    if (!s) return null
    const out = fmtFechaNotifIso(s)
    return out === '-' ? null : out
  }
  const primero = tryFmt(row.q_fecha_iso)
  if (primero) return primero
  const qc = row.q_cache
  if (qc && typeof qc === 'object') {
    const o = qc as Record<string, unknown>
    const norm = tryFmt(o.fecha_entrega_column_q_norm_iso)
    if (norm) return norm
    const rawQ = tryFmt(o.fecha_entrega_column_q)
    if (rawQ) return rawQ
    const rawCell = tryFmt(o.fecha_entrega_column_q_raw)
    if (rawCell) return rawCell
  }
  return '-'
}

function loteDesdeItem(row: FechaQAuditoriaTotalItem): string {
  const qc = row.q_cache
  const loteRaw =
    qc && typeof qc === 'object' && 'lote_aplicado' in qc
      ? (qc as { lote_aplicado?: unknown }).lote_aplicado
      : undefined
  const s = typeof loteRaw === 'string' ? loteRaw.trim() : ''
  return s || '(sin lote)'
}

export default function FechaQAuditoriaTotalPage() {
  const queryClient = useQueryClient()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const [cedula, setCedula] = useState('')
  const [appliedCedula, setAppliedCedula] = useState('')
  const [soloConDiferencia, setSoloConDiferencia] = useState(false)
  const [incluirMarcadosNo, setIncluirMarcadosNo] = useState(false)
  const [offset, setOffset] = useState(0)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [syncingDrive, setSyncingDrive] = useState(false)
  const [batchRunning, setBatchRunning] = useState(false)

  type ConfirmState =
    | null
    | { accion: 'si_todos' }
    | { accion: 'si_lote'; lote: string; elegibles: number }
    | { accion: 'no_todos' }
    | { accion: 'no_lote'; lote: string; elegibles: number }
    | { accion: 'elegir_lote_si' }
    | { accion: 'elegir_lote_no' }

  const [confirmState, setConfirmState] = useState<ConfirmState>(null)
  const limit = NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA

  const q = useQuery({
    queryKey: [
      ...QK,
      appliedCedula,
      soloConDiferencia,
      incluirMarcadosNo,
      offset,
    ],
    queryFn: () =>
      notificacionService.getFechaQAuditoriaTotal({
        limit,
        offset,
        cedula_q: appliedCedula || undefined,
        solo_con_diferencia: soloConDiferencia,
        excluir_marcados_no: !incluirMarcadosNo,
      }),
  })

  const lotesQ = useQuery({
    queryKey: [...QK_LOTES, incluirMarcadosNo],
    queryFn: () =>
      notificacionService.getFechaQAuditoriaLotes({
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

  const totalElegibles = lotesQ.data?.total_elegibles ?? 0
  const lotes = lotesQ.data?.lotes ?? []

  const invalidarTodo = async () => {
    await queryClient.invalidateQueries({ queryKey: [...QK] })
    await queryClient.invalidateQueries({ queryKey: [...QK_LOTES] })
  }

  const ejecutarMasivoSi = async (
    modo: 'todos' | 'por_lote',
    lote?: string
  ) => {
    if (!esAdmin || batchRunning) return
    setBatchRunning(true)
    setConfirmState(null)
    try {
      const res = await notificacionService.postFechaQAuditoriaAplicarMasivo({
        modo,
        lote: modo === 'por_lote' ? lote : undefined,
        excluir_marcados_no: !incluirMarcadosNo,
      })
      if (res.errores === 0) {
        toast.success(
          `Aprobado: ${res.aplicados} prestamo(s) actualizado(s).`
        )
      } else {
        toast.message(
          `${res.aplicados} ok, ${res.errores} error(es). Revise detalle en consola.`
        )
        console.warn('[fecha-q-auditoria] masivo Si', res.errores_detalle)
      }
      await invalidarTodo()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'Error en la aprobacion masiva.')
    } finally {
      setBatchRunning(false)
    }
  }

  const ejecutarMasivoNo = async (
    modo: 'todos' | 'por_lote',
    lote?: string
  ) => {
    if (!esAdmin || batchRunning) return
    setBatchRunning(true)
    setConfirmState(null)
    try {
      const res = await notificacionService.postFechaQAuditoriaMarcarNoMasivo({
        modo,
        lote: modo === 'por_lote' ? lote : undefined,
        excluir_marcados_no: !incluirMarcadosNo,
      })
      if (res.errores === 0) {
        toast.success(
          `No en lote: ${res.marcados} prestamo(s) marcado(s).`
        )
      } else {
        toast.message(
          `${res.marcados} ok, ${res.errores} error(es).`
        )
      }
      await invalidarTodo()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'Error al marcar No masivamente.')
    } finally {
      setBatchRunning(false)
    }
  }

  const confirmDialogOpen = confirmState != null
  const esElegirLote =
    confirmState?.accion === 'elegir_lote_si' ||
    confirmState?.accion === 'elegir_lote_no'

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Notificaciones - Fechas (Q vs BD)"
        description="Comparacion por prestamo: cedula, fecha de la columna Q de la hoja CONCILIACION (cache en BD) y fecha de aprobacion en base de datos. Si la Q es la referencia y difiere, use Si para alinear la aprobacion en BD (o No para descartar en auditoria)."
        icon={Database}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">
              Cedula (opcional)
            </label>
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
            Incluir marcados "No aplicar Q"
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
            disabled={q.isFetching || syncingDrive}
          >
            <RefreshCw className="h-4 w-4" />
            Refrescar
          </Button>
          <Button
            type="button"
            variant="outline"
            className="gap-2"
            disabled={q.isFetching || syncingDrive}
            onClick={() => {
              if (syncingDrive) return
              setSyncingDrive(true)
              void (async () => {
                try {
                  const res =
                    await reporteService.syncConciliacionSheetDesdeDrive()
                  await invalidarTodo()
                  await q.refetch()
                  const rowCountRaw = (res as { row_count?: unknown } | null)
                    ?.row_count
                  const rowCount =
                    typeof rowCountRaw === 'number' &&
                    Number.isFinite(rowCountRaw)
                      ? rowCountRaw
                      : null
                  toast.success(
                    rowCount != null
                      ? `Drive sincronizado (${rowCount} fila(s)). Listado actualizado.`
                      : 'Drive sincronizado. Listado actualizado.'
                  )
                } catch (e) {
                  toast.error(
                    getErrorMessage(e) || 'No se pudo recargar desde Drive.'
                  )
                } finally {
                  setSyncingDrive(false)
                }
              })()
            }}
          >
            <RefreshCw
              className={`h-4 w-4 ${syncingDrive ? 'animate-spin' : ''}`}
            />
            {syncingDrive ? 'Recargando...' : 'Recargar desde Drive'}
          </Button>
          <Button asChild type="button" variant="outline">
            <Link to="/notificaciones/general">
              Ir a listados de mora (General)
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* Acciones masivas */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Acciones masivas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Total elegibles (Q distinta de aprobacion BD, con cedula):{' '}
            <span className="font-semibold text-foreground">
              {lotesQ.isFetching ? '...' : totalElegibles}
            </span>
            {lotes.length > 0 && (
              <>
                {' '}en{' '}
                <span className="font-semibold text-foreground">
                  {lotes.length}
                </span>{' '}
                lote(s)
              </>
            )}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              className="gap-1.5 bg-blue-600 text-white hover:bg-blue-700"
              disabled={
                !esAdmin || totalElegibles === 0 || batchRunning
              }
              onClick={() => setConfirmState({ accion: 'si_todos' })}
            >
              <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />
              Aprobar todos ({totalElegibles})
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="gap-1.5"
              disabled={
                !esAdmin || lotes.length === 0 || batchRunning
              }
              onClick={() => setConfirmState({ accion: 'elegir_lote_si' })}
            >
              <LayoutList className="h-4 w-4 shrink-0" aria-hidden />
              Aprobar por lote
            </Button>
            <span className="mx-2 h-5 w-px bg-border" />
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={
                !esAdmin || totalElegibles === 0 || batchRunning
              }
              onClick={() => setConfirmState({ accion: 'no_todos' })}
            >
              <XCircle className="h-4 w-4 shrink-0" aria-hidden />
              Marcar No todos ({totalElegibles})
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              className="gap-1.5"
              disabled={
                !esAdmin || lotes.length === 0 || batchRunning
              }
              onClick={() => setConfirmState({ accion: 'elegir_lote_no' })}
            >
              <LayoutList className="h-4 w-4 shrink-0" aria-hidden />
              Marcar No por lote
            </Button>
          </div>
          {!esAdmin && (
            <p className="text-xs text-muted-foreground">
              Solo administradores pueden ejecutar acciones masivas.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resultados ({rangoTxt})</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {q.isFetching ? (
            <p className="text-sm text-muted-foreground">Cargando...</p>
          ) : q.isError ? (
            <p className="text-sm text-destructive">
              {getErrorMessage(q.error)}
            </p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin filas para este filtro.
            </p>
          ) : (
            <table className="w-full min-w-[850px] border-collapse text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-2 font-medium">Prestamo</th>
                  <th className="py-2 pr-2 font-medium">Cedula</th>
                  <th className="py-2 pr-2 font-medium">Lote</th>
                  <th className="py-2 pr-2 font-medium">Fecha Q (hoja)</th>
                  <th className="py-2 pr-2 font-medium">
                    Fecha BD (aprobacion)
                  </th>
                  <th className="py-2 pr-2 font-medium">
                    Dif. dias (Q - BD)
                  </th>
                  <th className="py-2 pr-2 font-medium">Puede aplicar</th>
                  <th className="py-2 pr-2 font-medium">
                    Q anterior corrige
                  </th>
                  <th className="py-2 pr-2 font-medium">Si / No</th>
                </tr>
              </thead>
              <tbody>
                {items.map(row => {
                  const elegible =
                    row.puede_aplicar === true &&
                    Boolean((row.cedula || '').trim())
                  return (
                    <tr
                      key={row.prestamo_id}
                      className="border-b border-border/60"
                    >
                      <td className="py-2 pr-2 font-mono">
                        {row.prestamo_id}
                      </td>
                      <td className="py-2 pr-2">{row.cedula || '-'}</td>
                      <td className="py-2 pr-2 text-xs text-muted-foreground">
                        {loteDesdeItem(row)}
                      </td>
                      <td className="py-2 pr-2 tabular-nums">
                        {fmtFechaQHojaAuditoria(row)}
                      </td>
                      <td className="py-2 pr-2">
                        {fmtIso(row.fecha_aprobacion)}
                      </td>
                      <td className="py-2 pr-2">
                        {row.diferencia_dias ?? '-'}
                      </td>
                      <td className="py-2 pr-2">
                        {row.puede_aplicar == null
                          ? '-'
                          : row.puede_aplicar
                            ? 'Si'
                            : 'No'}
                      </td>
                      <td className="py-2 pr-2">
                        {row.correccion_desde_q_anterior_bd == null
                          ? '-'
                          : row.correccion_desde_q_anterior_bd
                            ? 'Si'
                            : 'No'}
                      </td>
                      <td className="py-2 pr-2">
                        {elegible ? (
                          <span className="inline-flex flex-wrap gap-1">
                            <Button
                              type="button"
                              size="sm"
                              variant="default"
                              className="h-7 px-2 text-xs"
                              disabled={
                                !esAdmin ||
                                batchRunning ||
                                busyId === row.prestamo_id
                              }
                              title={
                                esAdmin
                                  ? 'Guardar en BD la fecha Q como fecha de aprobacion.'
                                  : 'Solo administrador.'
                              }
                              onClick={() => {
                                if (
                                  !esAdmin ||
                                  batchRunning ||
                                  busyId != null
                                )
                                  return
                                const ced = (row.cedula || '').trim()
                                const qc = row.q_cache
                                const loteRaw =
                                  qc &&
                                  typeof qc === 'object' &&
                                  'lote_aplicado' in qc
                                    ? (qc as { lote_aplicado?: unknown })
                                        .lote_aplicado
                                    : undefined
                                const lote =
                                  typeof loteRaw === 'string' &&
                                  loteRaw.trim()
                                    ? loteRaw.trim()
                                    : undefined
                                setBusyId(row.prestamo_id)
                                void (async () => {
                                  try {
                                    await notificacionService.postAplicarFechaEntregaQComoFechaAprobacion(
                                      {
                                        cedula: ced,
                                        prestamoId: row.prestamo_id,
                                        ...(lote ? { lote } : {}),
                                      }
                                    )
                                    toast.success(
                                      'Fecha de aprobacion actualizada con la Q.'
                                    )
                                    await invalidarTodo()
                                  } catch (e) {
                                    toast.error(
                                      getErrorMessage(e) ||
                                        'No se pudo aplicar la fecha Q.'
                                    )
                                  } finally {
                                    setBusyId(null)
                                  }
                                })()
                              }}
                            >
                              Si
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              className="h-7 px-2 text-xs"
                              disabled={
                                !esAdmin ||
                                batchRunning ||
                                busyId === row.prestamo_id
                              }
                              title={
                                esAdmin
                                  ? 'Descartar en auditoria (no cambia la aprobacion en BD).'
                                  : 'Solo administrador.'
                              }
                              onClick={() => {
                                if (
                                  !esAdmin ||
                                  batchRunning ||
                                  busyId != null
                                )
                                  return
                                setBusyId(row.prestamo_id)
                                void (async () => {
                                  try {
                                    await notificacionService.postFechaQAuditoriaMarcaNoAplicar(
                                      {
                                        prestamoId: row.prestamo_id,
                                      }
                                    )
                                    toast.message(
                                      'Marcado como no aplicar en esta auditoria.'
                                    )
                                    await invalidarTodo()
                                  } catch (e) {
                                    toast.error(
                                      getErrorMessage(e) ||
                                        'No se pudo marcar.'
                                    )
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
                          <span className="text-xs text-muted-foreground">
                            -
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
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

      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-800">
          Ajuste manual por dia de aprobacion
        </h2>
        <p className="text-xs text-muted-foreground">
          Busqueda y edicion puntual de fechas (sin depender de la columna Q).
        </p>
        <Fechas2BusquedaPanel embedded />
      </div>

      {/* Dialogo: elegir lote */}
      <Dialog
        open={esElegirLote}
        onOpenChange={open => !open && setConfirmState(null)}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {confirmState?.accion === 'elegir_lote_si'
                ? 'Seleccione lote para aprobar'
                : 'Seleccione lote para marcar No'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {lotesQ.isFetching ? (
              <p className="text-sm text-muted-foreground">Cargando lotes...</p>
            ) : lotes.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No hay lotes con prestamos elegibles.
              </p>
            ) : (
              <div className="grid gap-2">
                {lotes.map((l: FechaQAuditoriaLoteItem) => (
                  <Button
                    key={l.lote}
                    type="button"
                    variant="outline"
                    className="justify-between gap-4 text-left"
                    onClick={() => {
                      if (confirmState?.accion === 'elegir_lote_si') {
                        setConfirmState({
                          accion: 'si_lote',
                          lote: l.lote,
                          elegibles: l.elegibles,
                        })
                      } else {
                        setConfirmState({
                          accion: 'no_lote',
                          lote: l.lote,
                          elegibles: l.elegibles,
                        })
                      }
                    }}
                  >
                    <span className="font-mono text-sm">{l.lote}</span>
                    <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs font-semibold tabular-nums">
                      {l.elegibles} elegible(s)
                    </span>
                  </Button>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmState(null)}
            >
              Cancelar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialogo: confirmar Si todos */}
      <Dialog
        open={confirmState?.accion === 'si_todos'}
        onOpenChange={open => !open && setConfirmState(null)}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Aprobar todos los elegibles</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Se aplicara la fecha Q como{' '}
            <strong>fecha de aprobacion</strong> en BD para{' '}
            <span className="font-semibold tabular-nums text-foreground">
              {totalElegibles}
            </span>{' '}
            prestamo(s) donde la Q difiere de la aprobacion actual.
            Requerimiento y vencimientos se recalculan segun reglas del
            servidor.
          </p>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmState(null)}
              disabled={batchRunning}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={() => void ejecutarMasivoSi('todos')}
              disabled={batchRunning}
            >
              {batchRunning ? 'Ejecutando...' : 'Confirmar y aplicar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialogo: confirmar Si por lote */}
      <Dialog
        open={confirmState?.accion === 'si_lote'}
        onOpenChange={open => !open && setConfirmState(null)}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Aprobar lote</DialogTitle>
          </DialogHeader>
          {confirmState?.accion === 'si_lote' && (
            <p className="text-sm text-muted-foreground">
              Se aplicara la fecha Q como{' '}
              <strong>fecha de aprobacion</strong> en BD para{' '}
              <span className="font-semibold tabular-nums text-foreground">
                {confirmState.elegibles}
              </span>{' '}
              prestamo(s) del lote{' '}
              <span className="font-mono font-semibold text-foreground">
                {confirmState.lote}
              </span>
              .
            </p>
          )}
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                setConfirmState({ accion: 'elegir_lote_si' })
              }
              disabled={batchRunning}
            >
              Volver
            </Button>
            <Button
              type="button"
              onClick={() => {
                if (confirmState?.accion === 'si_lote') {
                  void ejecutarMasivoSi('por_lote', confirmState.lote)
                }
              }}
              disabled={batchRunning}
            >
              {batchRunning ? 'Ejecutando...' : 'Confirmar y aplicar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialogo: confirmar No todos */}
      <Dialog
        open={confirmState?.accion === 'no_todos'}
        onOpenChange={open => !open && setConfirmState(null)}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Marcar No todos los elegibles</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Se marcaran como{' '}
            <strong>No aplicar Q</strong> en auditoria{' '}
            <span className="font-semibold tabular-nums text-foreground">
              {totalElegibles}
            </span>{' '}
            prestamo(s). No cambia la aprobacion en BD.
          </p>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmState(null)}
              disabled={batchRunning}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void ejecutarMasivoNo('todos')}
              disabled={batchRunning}
            >
              {batchRunning ? 'Ejecutando...' : 'Confirmar y marcar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialogo: confirmar No por lote */}
      <Dialog
        open={confirmState?.accion === 'no_lote'}
        onOpenChange={open => !open && setConfirmState(null)}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Marcar No en lote</DialogTitle>
          </DialogHeader>
          {confirmState?.accion === 'no_lote' && (
            <p className="text-sm text-muted-foreground">
              Se marcaran como{' '}
              <strong>No aplicar Q</strong>{' '}
              <span className="font-semibold tabular-nums text-foreground">
                {confirmState.elegibles}
              </span>{' '}
              prestamo(s) del lote{' '}
              <span className="font-mono font-semibold text-foreground">
                {confirmState.lote}
              </span>
              . No cambia la aprobacion en BD.
            </p>
          )}
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                setConfirmState({ accion: 'elegir_lote_no' })
              }
              disabled={batchRunning}
            >
              Volver
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                if (confirmState?.accion === 'no_lote') {
                  void ejecutarMasivoNo('por_lote', confirmState.lote)
                }
              }}
              disabled={batchRunning}
            >
              {batchRunning ? 'Ejecutando...' : 'Confirmar y marcar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
