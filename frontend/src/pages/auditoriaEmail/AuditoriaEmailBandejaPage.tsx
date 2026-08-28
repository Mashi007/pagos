import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Loader2, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'
import { getErrorMessage } from '../../types/errors'

const PAGE = 50

export default function AuditoriaEmailBandejaPage() {
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busy, setBusy] = useState(false)

  const list = useQuery({
    queryKey: ['auditoria-email', 'bandeja', q, page],
    queryFn: () =>
      auditoriaEmailService.bandeja({
        skip: page * PAGE,
        limit: PAGE,
        q: q.trim() || undefined,
      }),
  })

  const items = list.data?.items || []
  const total = list.data?.total || 0
  const allIds = useMemo(
    () => items.map(r => Number(r.id)).filter(n => Number.isFinite(n)),
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

  const toggleAll = (on: boolean) => {
    setSelected(on ? new Set(allIds) : new Set())
  }

  const onReescaneo = async () => {
    if (selected.size === 0) {
      toast.message('Seleccione al menos un mensaje.')
      return
    }
    setBusy(true)
    try {
      const res = await auditoriaEmailService.reescaneo([...selected])
      toast.success(`Re-escaneados: ${res.reescaneados}`)
      await qc.invalidateQueries({ queryKey: ['auditoria-email'] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo re-escanear')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
        <CardTitle className="text-base">Bandeja ({total})</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Input
            className="w-[220px]"
            placeholder="Buscar cédula / asunto"
            value={q}
            onChange={e => {
              setPage(0)
              setQ(e.target.value)
            }}
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={busy || selected.size === 0}
            onClick={() => void onReescaneo()}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Re-escaneo ({selected.size})
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <input
                    type="checkbox"
                    checked={
                      allIds.length > 0 &&
                      allIds.every(id => selected.has(id))
                    }
                    onChange={e => toggleAll(e.target.checked)}
                    aria-label="Seleccionar página"
                  />
                </TableHead>
                <TableHead>Cédula</TableHead>
                <TableHead>Fecha de correo</TableHead>
                <TableHead>Adjuntos</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={4}
                    className="py-8 text-center text-muted-foreground"
                  >
                    Sin mensajes. Ejecute un escaneo.
                  </TableCell>
                </TableRow>
              ) : (
                items.map(row => {
                  const id = Number(row.id)
                  const ced = String(row.cedula || '').trim()
                  const nAtt = Number(row.attachmentCount ?? 0)
                  return (
                    <TableRow key={id}>
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selected.has(id)}
                          onChange={e => toggle(id, e.target.checked)}
                          aria-label={`Seleccionar ${id}`}
                        />
                      </TableCell>
                      <TableCell>
                        {ced ? (
                          <Link
                            className="text-sm text-blue-700 hover:underline"
                            to={`/clientes?q=${encodeURIComponent(ced)}`}
                          >
                            {ced}
                          </Link>
                        ) : (
                          <Link
                            className="text-sm text-muted-foreground hover:underline"
                            to={`/auditoria/email/bandeja/${id}`}
                          >
                            —
                          </Link>
                        )}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        {row.internalDate
                          ? new Date(String(row.internalDate)).toLocaleString(
                              'es-VE'
                            )
                          : '—'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {nAtt > 0 ? nAtt : '—'}
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
        <div className="mt-3 flex items-center justify-between">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={page === 0}
            onClick={() => setPage(p => Math.max(0, p - 1))}
          >
            Anterior
          </Button>
          <span className="text-xs text-muted-foreground">
            Página {page + 1}
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={(page + 1) * PAGE >= total}
            onClick={() => setPage(p => p + 1)}
          >
            Siguiente
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
