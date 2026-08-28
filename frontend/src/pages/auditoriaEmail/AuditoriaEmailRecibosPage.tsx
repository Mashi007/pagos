import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Loader2, Pencil } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useState } from 'react'

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

export default function AuditoriaEmailRecibosPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [status, setStatus] = useState('pending')

  const q = useQuery({
    queryKey: ['auditoria-email', 'recibos', status],
    queryFn: () => auditoriaEmailService.recibos(0, 100, status),
    refetchInterval: 3000,
  })

  const aprobar = useMutation({
    mutationFn: (id: number) => auditoriaEmailService.aprobarRecibo(id),
    onSuccess: res => {
      void qc.invalidateQueries({ queryKey: ['auditoria-email'] })
      if (res.ok) {
        toast.success(`Aprobado · pago #${String(res.pagoId || '—')}`)
        return
      }
      if (res.motivo === 'exception') {
        toast.error(
          `Error técnico: ${String(res.error || res.lastError || 'reintente')}`
        )
        return
      }
      if (res.motivo && String(res.motivo).startsWith('estado_no_pending')) {
        toast.message('Este recibo ya no está pendiente.')
        return
      }
      // No pasó validadores → pestaña revisión manual en /pagos
      const destino = String(
        res.redirect || res.hint || '/pagos?pestana=revision&revisar=1'
      )
      toast.message(
        `No pasó validadores (${String(res.motivo || 'validación')}). Abriendo revisión manual…`
      )
      navigate(
        destino.startsWith('/') ? destino : '/pagos?pestana=revision&revisar=1'
      )
    },
    onError: e => toast.error(getErrorMessage(e) || 'No se pudo aprobar'),
  })

  const revision = useMutation({
    mutationFn: (id: number) => auditoriaEmailService.revisionManualRecibo(id),
    onSuccess: res => {
      toast.success('Enviado a revisión manual')
      void qc.invalidateQueries({ queryKey: ['auditoria-email'] })
      navigate(
        String(res.redirect || res.hint || '/pagos?pestana=revision&revisar=1')
      )
    },
    onError: e => toast.error(getErrorMessage(e) || 'No se pudo enviar a revisión'),
  })

  const items = q.data?.items || []
  const busyId =
    aprobar.isPending || revision.isPending
      ? Number(aprobar.variables ?? revision.variables)
      : null

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
        <CardTitle className="text-base">
          Recibos · cola de aprobación ({q.data?.total ?? 0})
        </CardTitle>
        <Select value={status} onValueChange={setStatus}>
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
      </CardHeader>
      <CardContent>
        {q.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
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
                      colSpan={8}
                      className="py-6 text-center text-muted-foreground"
                    >
                      Sin recibos pendientes. Solo aparecen aquí los comprobantes
                      digitalizados con fecha/cédula/monto. Si Gemini falla (
                      falto_fecha), mire Bandeja — no Pagos ni Recibos.
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map(r => {
                    const id = Number(r.id)
                    const ced = String(r.cedula || '').trim()
                    const pending = String(r.status || '') === 'pending'
                    const imageUrl = String(r.imageUrl || '').trim() || null
                    return (
                      <TableRow key={String(id)}>
                        <TableCell>
                          <ComprobanteThumb
                            url={imageUrl}
                            className="h-14 w-14 rounded object-cover border"
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
                        <TableCell className="text-sm">
                          {String(r.status || '—')}
                          {r.lastError ? (
                            <div className="text-xs text-amber-700 max-w-[160px] truncate">
                              {String(r.lastError)}
                            </div>
                          ) : null}
                        </TableCell>
                        <TableCell className="text-right space-x-1">
                          {pending ? (
                            <>
                              <Button
                                type="button"
                                size="sm"
                                disabled={busyId === id}
                                onClick={() => aprobar.mutate(id)}
                              >
                                {busyId === id && aprobar.isPending ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <>
                                    <Check className="mr-1 h-4 w-4" />
                                    Aprobar
                                  </>
                                )}
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                disabled={busyId === id}
                                onClick={() => revision.mutate(id)}
                              >
                                <Pencil className="mr-1 h-4 w-4" />
                                Revisión
                              </Button>
                            </>
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
