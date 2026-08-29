import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
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
import { auditoriaEmailService } from '../../services/auditoriaEmailService'
import { getErrorMessage } from '../../types/errors'

const PAGE = 500
const POLL_MS = 2500

type CedulaFiltroMode = 'all' | 'na' | 'valor'

function classifyBadge(classify: unknown): { text: string; className: string } {
  const c = String(classify || '—').trim() || '—'
  if (c === 'en_proceso')
    return { text: 'En proceso', className: 'text-amber-700' }
  if (c === 'sin_digitalizacion')
    return { text: 'Sin digitalizar', className: 'text-muted-foreground' }
  if (c === 'error_pipeline')
    return { text: 'Error', className: 'text-red-700' }
  if (c === 'digitalizado')
    return { text: 'Digitalizado', className: 'text-emerald-700' }
  return { text: c, className: 'text-foreground' }
}

export default function AuditoriaEmailBandejaPage() {
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const [cedulaMode, setCedulaMode] = useState<CedulaFiltroMode>('all')
  const [cedulaValor, setCedulaValor] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busy, setBusy] = useState(false)
  const [live, setLive] = useState(true)

  const cedulaParam = useMemo(() => {
    if (cedulaMode === 'na') return 'NA'
    if (cedulaMode === 'valor' && cedulaValor.trim()) return cedulaValor.trim()
    return undefined
  }, [cedulaMode, cedulaValor])

  const list = useQuery({
    queryKey: ['auditoria-email', 'bandeja', q, page, cedulaParam],
    queryFn: () =>
      auditoriaEmailService.bandeja({
        skip: page * PAGE,
        limit: PAGE,
        q: q.trim() || undefined,
        cedula: cedulaParam,
      }),
    refetchInterval: live ? POLL_MS : false,
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

  const onEliminar = async () => {
    if (selected.size === 0) {
      toast.message('Seleccione al menos un mensaje.')
      return
    }
    if (
      !window.confirm(
        `¿Eliminar ${selected.size} mensaje(s) de la Bandeja? También se quitan recibos pending ligados.`
      )
    ) {
      return
    }
    setBusy(true)
    try {
      const res = await auditoriaEmailService.eliminarBandejaLote([...selected])
      setSelected(new Set())
      const parts = [`Eliminados: ${res.eliminados}`]
      if (res.recibosEliminados) {
        parts.push(`Recibos: ${res.recibosEliminados}`)
      }
      if (res.omitidos) parts.push(`Omitidos: ${res.omitidos}`)
      if (res.errores) parts.push(`Errores: ${res.errores}`)
      toast.success(parts.join(' · '))
      await qc.invalidateQueries({ queryKey: ['auditoria-email'] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo eliminar')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
        <div>
          <CardTitle className="text-base">Bandeja ({total})</CardTitle>
          <p className="text-xs text-muted-foreground">
            {live
              ? 'Actualización automática cada 2,5 s mientras escanea.'
              : 'Actualización automática pausada.'}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={live}
              onChange={e => setLive(e.target.checked)}
            />
            En vivo
          </label>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={list.isFetching}
            onClick={() => void list.refetch()}
          >
            {list.isFetching ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Actualizar
          </Button>
          <Input
            className="w-[180px]"
            placeholder="Buscar email / asunto"
            value={q}
            onChange={e => {
              setPage(0)
              setQ(e.target.value)
            }}
          />
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Filtro cédula
            </label>
            <Select
              value={cedulaMode}
              onValueChange={v => {
                setPage(0)
                setCedulaMode(v as CedulaFiltroMode)
              }}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="na">Solo NA</SelectItem>
                <SelectItem value="valor">Por cédula</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {cedulaMode === 'valor' ? (
            <Input
              className="w-[140px]"
              placeholder="Ej. V12345678"
              value={cedulaValor}
              onChange={e => {
                setPage(0)
                setCedulaValor(e.target.value)
              }}
            />
          ) : null}
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
          <Button
            type="button"
            size="sm"
            variant="destructive"
            disabled={busy || selected.size === 0}
            onClick={() => void onEliminar()}
          >
            {busy ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="mr-2 h-4 w-4" />
            )}
            Eliminar ({selected.size})
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
                <TableHead>Fecha</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Asunto</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Cédula</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="py-8 text-center text-muted-foreground"
                  >
                    Sin mensajes. Inicie un escaneo: aparecerán aquí al instante
                    (en proceso) y se irán actualizando.
                  </TableCell>
                </TableRow>
              ) : (
                items.map(row => {
                  const id = Number(row.id)
                  const cedLabel =
                    String(row.cedulaLabel || row.cedula || 'NA').trim() || 'NA'
                  const hasCed = cedLabel !== 'NA'
                  const email = String(row.fromEmail || '').trim()
                  const subject = String(row.subject || '').trim() || '—'
                  const badge = classifyBadge(row.classify)
                  const enProceso = String(row.classify) === 'en_proceso'
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
                      <TableCell className="whitespace-nowrap text-xs">
                        <Link
                          className="hover:underline"
                          to={`/auditoria/email/bandeja/${id}`}
                        >
                          {row.internalDate
                            ? new Date(String(row.internalDate)).toLocaleString(
                                'es-VE'
                              )
                            : '—'}
                        </Link>
                      </TableCell>
                      <TableCell className="max-w-[160px] truncate text-sm">
                        {email || '—'}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm">
                        {subject}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        <span className={badge.className}>
                          {enProceso ? (
                            <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />
                          ) : null}
                          {badge.text}
                        </span>
                      </TableCell>
                      <TableCell>
                        {hasCed ? (
                          <Link
                            className="text-sm text-blue-700 hover:underline"
                            to={`/clientes?q=${encodeURIComponent(cedLabel)}`}
                          >
                            {cedLabel}
                          </Link>
                        ) : (
                          <span className="text-sm text-muted-foreground">
                            NA
                          </span>
                        )}
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
