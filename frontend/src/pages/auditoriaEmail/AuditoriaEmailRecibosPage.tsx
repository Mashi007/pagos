import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Loader2, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useMemo, useState } from 'react'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'
import { ComprobanteThumb } from '../../components/pagos/ComprobanteThumb'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'
import { getErrorMessage } from '../../types/errors'

const PAGE = 500
const POLL_MS = 5000

function estadoLabel(r: Record<string, unknown>): {
  text: string
  className: string
} {
  const st = String(r.status || '').toLowerCase()
  if (st === 'approved') {
    return { text: 'APROBADO', className: 'text-emerald-700 font-medium' }
  }
  if (st === 'revision') {
    return { text: 'REVISIÓN', className: 'text-amber-700 font-medium' }
  }
  const se = String(r.serialEstado || '').toUpperCase()
  if (se === 'DUPLICADO') {
    return { text: 'DUPLICADO', className: 'text-rose-700 font-semibold' }
  }
  if (se === 'SIN_SERIAL') {
    return { text: 'SIN SERIAL', className: 'text-amber-700 font-medium' }
  }
  if (se === 'UNICO') {
    return { text: 'UNICO', className: 'text-emerald-700 font-semibold' }
  }
  return { text: 'UNICO', className: 'text-emerald-700 font-semibold' }
}

function prestamoEstadosDe(r: Record<string, unknown>): string[] {
  const arr = r.prestamoEstados
  if (Array.isArray(arr) && arr.length) {
    return arr.map(x => String(x || '').trim().toUpperCase()).filter(Boolean)
  }
  const uno = String(r.prestamoEstado || '').trim().toUpperCase()
  return uno ? [uno] : []
}

function prestamoEstadoClass(est: string): string {
  if (est === 'APROBADO') return 'text-emerald-700 font-semibold'
  if (est === 'DESISTIMIENTO') return 'text-amber-800 font-semibold'
  if (est === 'LIQUIDADO') return 'text-slate-600 font-semibold'
  return 'text-muted-foreground'
}

export default function AuditoriaEmailRecibosPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [status, setStatus] = useState('pending')
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busyId, setBusyId] = useState<number | null>(null)
  const [accionMasiva, setAccionMasiva] = useState<'ok' | 'eliminar'>('ok')

  const q = useQuery({
    queryKey: ['auditoria-email', 'recibos', status, page],
    queryFn: () => auditoriaEmailService.recibos(page * PAGE, PAGE, status),
    refetchInterval: q => (q.state.error ? false : POLL_MS),
  })

  const items = Array.isArray(q.data?.items) ? q.data.items : []
  const total = Number(q.data?.total) || 0
  const shown = items.length
  const counts = q.data?.counts
  const nPending = counts?.pending ?? (status === 'pending' ? total : 0)
  const nApproved = counts?.approved ?? 0
  const nRevision = counts?.revision ?? 0
  const nOmitidos = counts?.omitidos_sin_aprobado ?? 0

  const verFiltro = (v: string) => {
    setStatus(v)
    setPage(0)
    setSelected(new Set())
  }
  const pendingIds = useMemo(
    () =>
      items
        .filter(r => String(r.status || '') === 'pending')
        .map(r => Number(r.id))
        .filter(n => Number.isFinite(n)),
    [items]
  )

  const toggle = (id: number, on: boolean) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (on) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const toggleAllPending = (on: boolean) => {
    setSelected(on ? new Set(pendingIds) : new Set())
  }

  const aprobarUno = useMutation({
    mutationFn: (id: number) => auditoriaEmailService.aprobarRecibo(id),
    onMutate: id => setBusyId(id),
    onSettled: () => setBusyId(null),
    onSuccess: res => {
      void qc.invalidateQueries({ queryKey: ['auditoria-email'] })
      setSelected(prev => {
        const next = new Set(prev)
        next.delete(Number(res.id))
        return next
      })
      if (res.ok) {
        toast.success('OK · aplicado a cuotas')
        if (status === 'pending' && nPending <= 1) {
          verFiltro('approved')
        }
        return
      }
      if (res.redirect || res.hint) {
        toast.message('No pasó validadores → revisión manual')
        navigate(String(res.redirect || res.hint))
        return
      }
      toast.error(String(res.motivo || res.error || 'No se pudo aplicar'))
    },
    onError: e => toast.error(getErrorMessage(e) || 'No se pudo aplicar OK'),
  })

  const aprobarLote = useMutation({
    mutationFn: (ids: number[]) => auditoriaEmailService.aprobarRecibosLote(ids),
    onSuccess: res => {
      setSelected(new Set())
      void qc.invalidateQueries({ queryKey: ['auditoria-email'] })
      const parts = [
        `OK (cuotas): ${res.aprobados}`,
        `Revisión manual: ${res.revision}`,
      ]
      if (res.errores) parts.push(`Errores: ${res.errores}`)
      if (res.omitidos) parts.push(`Omitidos: ${res.omitidos}`)
      toast.success(parts.join(' · '))
      if (res.revision > 0 && res.redirectRevision) {
        toast.message('Algunos no pasaron validadores → revisión manual')
        navigate(String(res.redirectRevision))
      } else if (res.aprobados > 0 && status === 'pending') {
        verFiltro('approved')
      }
    },
    onError: e => toast.error(getErrorMessage(e) || 'No se pudo aprobar el lote'),
  })

  const eliminar = useMutation({
    mutationFn: (id: number) => auditoriaEmailService.eliminarRecibo(id),
    onMutate: id => setBusyId(id),
    onSettled: () => setBusyId(null),
    onSuccess: (_res, id) => {
      toast.success(`Eliminado #${id}`)
      void qc.invalidateQueries({ queryKey: ['auditoria-email'] })
      setSelected(prev => {
        const next = new Set(prev)
        next.delete(Number(id))
        return next
      })
    },
    onError: e => toast.error(getErrorMessage(e) || 'No se pudo eliminar'),
  })

  const eliminarLote = useMutation({
    mutationFn: (ids: number[]) => auditoriaEmailService.eliminarRecibosLote(ids),
    onSuccess: res => {
      setSelected(new Set())
      void qc.invalidateQueries({ queryKey: ['auditoria-email'] })
      const parts = [`Eliminados: ${res.eliminados}`]
      if (res.errores) parts.push(`Errores: ${res.errores}`)
      if (res.omitidos) parts.push(`Omitidos: ${res.omitidos}`)
      toast.success(parts.join(' · '))
    },
    onError: e => toast.error(getErrorMessage(e) || 'No se pudo eliminar el lote'),
  })

  const busy =
    aprobarLote.isPending ||
    aprobarUno.isPending ||
    eliminar.isPending ||
    eliminarLote.isPending
  const selectedPending = [...selected].filter(id => pendingIds.includes(id))

  const runMasivo = () => {
    if (selectedPending.length === 0) return
    if (accionMasiva === 'eliminar') {
      if (
        !window.confirm(
          `¿Eliminar totalmente ${selectedPending.length} recibo(s) de la cola?`
        )
      ) {
        return
      }
      eliminarLote.mutate(selectedPending)
      return
    }
    aprobarLote.mutate(selectedPending)
  }

  return (
    <Card>
      <CardHeader className="space-y-2">
        <div className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-base">
            Recibos · cola de aprobación ({shown}
            {total !== shown ? ` de ${total}` : ''})
          </CardTitle>
          <Select
            value={status}
            onValueChange={verFiltro}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pending">Pendientes ({nPending})</SelectItem>
              <SelectItem value="approved">Aprobados ({nApproved})</SelectItem>
              <SelectItem value="revision">Revisión ({nRevision})</SelectItem>
              <SelectItem value="all">Todos</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          <strong>Préstamo</strong>: APROBADO, DESISTIMIENTO o LIQUIDADO (los
          que tenga esa cédula). <strong>Cola</strong>: UNICO (serial libre) o
          DUPLICADO. El escaneo carga <strong>todas</strong> las imágenes; solo
          con APROBADO el OK aplica cuotas. Sin APROBADO queda para revisión
          manual. <strong>Eliminar</strong> quita el caso de la cola.
        </p>
        {nOmitidos > 0 ? (
          <p className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            {nOmitidos} recibo(s) con cédula sin préstamo APROBADO: están en
            cola con imagen; el OK los manda a revisión manual, no a cuotas.
          </p>
        ) : null}
        {status === 'pending' || status === 'all' ? (
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                Acción masiva
              </label>
              <Select
                value={accionMasiva}
                onValueChange={v => setAccionMasiva(v as 'ok' | 'eliminar')}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ok">OK masivo</SelectItem>
                  <SelectItem value="eliminar">Eliminar masivo</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              type="button"
              variant={accionMasiva === 'eliminar' ? 'destructive' : 'default'}
              disabled={busy || selectedPending.length === 0}
              onClick={() => runMasivo()}
            >
              {aprobarLote.isPending || eliminarLote.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : accionMasiva === 'eliminar' ? (
                <Trash2 className="mr-2 h-4 w-4" />
              ) : (
                <Check className="mr-2 h-4 w-4" />
              )}
              {accionMasiva === 'eliminar' ? 'Eliminar' : 'OK'} selección (
              {selectedPending.length})
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={busy || pendingIds.length === 0}
              onClick={() => toggleAllPending(true)}
            >
              Seleccionar todos pendientes
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={selected.size === 0}
              onClick={() => setSelected(new Set())}
            >
              Limpiar
            </Button>
          </div>
        ) : null}
      </CardHeader>
      <CardContent>
        {q.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : q.isError ? (
          <div className="space-y-2 py-6 text-center">
            <p className="text-sm text-red-700">
              No se pudo cargar la cola: {getErrorMessage(q.error) || 'Error de red'}
            </p>
            <Button type="button" size="sm" variant="outline" onClick={() => void q.refetch()}>
              Reintentar
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            {shown < total && shown < PAGE && page === 0 ? (
              <p className="mb-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                La cola tiene {total} recibos pero esta página solo recibió{' '}
                {shown}. Recargá o cambiá el filtro; si sigue, el listado del
                servidor está incompleto.
              </p>
            ) : null}
            <Table containerClassName="overflow-visible">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input
                      type="checkbox"
                      checked={
                        pendingIds.length > 0 &&
                        pendingIds.every(id => selected.has(id))
                      }
                      onChange={e => toggleAllPending(e.target.checked)}
                      aria-label="Seleccionar todos pendientes"
                      disabled={pendingIds.length === 0}
                    />
                  </TableHead>
                  <TableHead>Imagen</TableHead>
                  <TableHead>Cédula</TableHead>
                  <TableHead>Préstamo</TableHead>
                  <TableHead>Banco</TableHead>
                  <TableHead>Fecha pago</TableHead>
                  <TableHead>Monto</TableHead>
                  <TableHead>Serial</TableHead>
                  <TableHead>Cola</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={10}
                      className="py-6 text-center text-muted-foreground"
                    >
                      {status === 'pending' && nApproved > 0 ? (
                        <>
                          No hay pendientes. Los que acabás de aprobar están en{' '}
                          <button
                            type="button"
                            className="font-medium text-blue-700 underline"
                            onClick={() => verFiltro('approved')}
                          >
                            Aprobados ({nApproved})
                          </button>
                          .
                        </>
                      ) : status === 'pending' && nOmitidos > 0 ? (
                        <>
                          No hay pendientes listos para OK automático. {nOmitidos}{' '}
                          recibo(s) sin APROBADO siguen en cola para revisión
                          manual.
                        </>
                      ) : (
                        <>
                          Sin recibos en este filtro. Aparecen al digitalizar
                          cada correo. Revisá Escanear si el lote sigue activo.
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((r, idx) => {
                    const id = Number(r.id)
                    const rowKey = `recibo-${String(r.id ?? 'x')}-${String(r.gmailMessageId || '')}-${idx}`
                    const ced = String(r.cedula || '').trim()
                    const pending = String(r.status || '') === 'pending'
                    const imageUrl = String(r.imageUrl || '').trim() || null
                    const est = estadoLabel(r)
                    const prestamos = prestamoEstadosDe(r)
                    const rowBusy = busyId === id
                    return (
                      <TableRow key={rowKey}>
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={selected.has(id)}
                            disabled={!pending}
                            onChange={e => toggle(id, e.target.checked)}
                            aria-label={`Seleccionar recibo ${id}`}
                          />
                        </TableCell>
                        <TableCell>
                          <ComprobanteThumb
                            url={imageUrl}
                            className="h-14 w-14 rounded border object-cover"
                            placeholderText="—"
                          />
                        </TableCell>
                        <TableCell>
                          {ced ? (
                            <Link
                              className="text-blue-700 hover:underline"
                              to={`/clientes?q=${encodeURIComponent(ced)}`}
                            >
                              {ced}
                            </Link>
                          ) : (
                            '—'
                          )}
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-xs">
                          {prestamos.length ? (
                            <span>
                              {prestamos.map((p, i) => (
                                <span key={p}>
                                  {i > 0 ? (
                                    <span className="text-muted-foreground">
                                      {' · '}
                                    </span>
                                  ) : null}
                                  <span className={prestamoEstadoClass(p)}>
                                    {p}
                                  </span>
                                </span>
                              ))}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell>{String(r.banco || '—')}</TableCell>
                        <TableCell className="whitespace-nowrap text-xs">
                          {String(r.fechaPago || '—')}
                        </TableCell>
                        <TableCell>
                          {r.monto != null ? String(r.monto) : '—'}
                        </TableCell>
                        <TableCell className="max-w-[140px] truncate text-xs">
                          {String(r.numeroReferencia || r.serial || '—')}
                        </TableCell>
                        <TableCell className={`text-sm ${est.className}`}>
                          {est.text}
                          {r.lastError ? (
                            <div className="max-w-[160px] truncate text-xs font-normal text-amber-700">
                              {String(r.lastError)}
                            </div>
                          ) : null}
                        </TableCell>
                        <TableCell className="text-right">
                          {pending ? (
                            <div className="flex flex-wrap items-center justify-end gap-1">
                              <Button
                                type="button"
                                size="sm"
                                disabled={busy}
                                onClick={() => aprobarUno.mutate(id)}
                                title="Validadores vigentes → cuotas o revisión manual"
                              >
                                {rowBusy && aprobarUno.isPending ? (
                                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                ) : (
                                  <Check className="mr-1 h-4 w-4" />
                                )}
                                OK
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="destructive"
                                disabled={busy}
                                onClick={() => {
                                  if (
                                    !window.confirm(
                                      `¿Eliminar totalmente el recibo #${id} de la cola?`
                                    )
                                  ) {
                                    return
                                  }
                                  eliminar.mutate(id)
                                }}
                                title="Elimina el caso de la cola Recibos"
                              >
                                {rowBusy && eliminar.isPending ? (
                                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                ) : (
                                  <Trash2 className="mr-1 h-4 w-4" />
                                )}
                                Eliminar
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          </div>
        )}
        {!q.isLoading && !q.isError ? (
          <div className="mt-3 flex items-center justify-between">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page === 0}
              onClick={() => {
                setPage(p => Math.max(0, p - 1))
                setSelected(new Set())
              }}
            >
              Anterior
            </Button>
            <span className="text-xs text-muted-foreground">
              Página {page + 1}
              {total > 0
                ? ` · ${shown} en pantalla · ${
                    shown === 0 ? 0 : page * PAGE + 1
                  }-${page * PAGE + shown} de ${total}`
                : ''}
            </span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={(page + 1) * PAGE >= total}
              onClick={() => {
                setPage(p => p + 1)
                setSelected(new Set())
              }}
            >
              Siguiente
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
