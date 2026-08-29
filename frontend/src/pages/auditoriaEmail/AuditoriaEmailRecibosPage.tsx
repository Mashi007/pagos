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

export default function AuditoriaEmailRecibosPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [status, setStatus] = useState('pending')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busyId, setBusyId] = useState<number | null>(null)

  const q = useQuery({
    queryKey: ['auditoria-email', 'recibos', status],
    queryFn: () => auditoriaEmailService.recibos(0, 100, status),
    refetchInterval: 3000,
  })

  const items = q.data?.items || []
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

  const busy = aprobarLote.isPending || aprobarUno.isPending || eliminar.isPending
  const selectedPending = [...selected].filter(id => pendingIds.includes(id))

  return (
    <Card>
      <CardHeader className="space-y-2">
        <div className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-base">
            Recibos · cola de aprobación ({q.data?.total ?? 0})
          </CardTitle>
          <Select
            value={status}
            onValueChange={v => {
              setStatus(v)
              setSelected(new Set())
            }}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pending">Pendientes</SelectItem>
              <SelectItem value="approved">Aprobados</SelectItem>
              <SelectItem value="revision">Revisión</SelectItem>
              <SelectItem value="all">Todos</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          <strong>Estado</strong>: UNICO (serial libre en BD) o DUPLICADO (ya
          existe en pagos / pagos con errores u otro pending).{' '}
          <strong>OK</strong> dispara validadores vigentes → cuotas o revisión
          manual. <strong>Eliminar</strong> quita el caso de la cola.
        </p>
        {status === 'pending' || status === 'all' ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              disabled={busy || selectedPending.length === 0}
              onClick={() => aprobarLote.mutate(selectedPending)}
            >
              {aprobarLote.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Check className="mr-2 h-4 w-4" />
              )}
              OK selección ({selectedPending.length})
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
        ) : (
          <div className="overflow-x-auto">
            <Table>
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
                  <TableHead>Banco</TableHead>
                  <TableHead>Fecha pago</TableHead>
                  <TableHead>Monto</TableHead>
                  <TableHead>Serial</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={9}
                      className="py-6 text-center text-muted-foreground"
                    >
                      Sin recibos en este filtro.
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map(r => {
                    const id = Number(r.id)
                    const ced = String(r.cedula || '').trim()
                    const pending = String(r.status || '') === 'pending'
                    const imageUrl = String(r.imageUrl || '').trim() || null
                    const est = estadoLabel(r)
                    const rowBusy = busyId === id
                    return (
                      <TableRow key={String(id)}>
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
      </CardContent>
    </Card>
  )
}
