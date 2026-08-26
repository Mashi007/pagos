import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { FileSpreadsheet, Loader2, Upload } from 'lucide-react'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import {
  ImportacionExtractoFila,
  ImportacionExtractoLote,
  importacionExtractoService,
} from '../services/importacionExtractoService'

function errMsg(err: unknown): string {
  const e = err as { response?: { data?: { detail?: string } }; message?: string }
  return e?.response?.data?.detail || e?.message || 'Error'
}

function badgeEstado(estado: string) {
  switch (estado) {
    case 'SE_PUEDE_IMPORTAR':
      return <Badge className="bg-emerald-600">Se puede importar</Badge>
    case 'IGUAL_100':
      return <Badge variant="secondary">100% igual</Badge>
    case 'SEMEJANTE':
      return <Badge className="bg-amber-500">Semejante</Badge>
    case 'VISTO':
      return <Badge variant="outline">Visto</Badge>
    case 'IMPORTADO':
      return <Badge className="bg-sky-600">Importado</Badge>
    case 'SIN_PRESTAMO':
    case 'VARIOS_PRESTAMOS':
    case 'PARSE_ERROR':
      return <Badge variant="destructive">{estado}</Badge>
    default:
      return <Badge variant="outline">{estado}</Badge>
  }
}

const _RE_MARCA_OBS = /(Drive|Serial compuesto)/gi

function renderDetalleObservacion(f: ImportacionExtractoFila): ReactNode {
  const detalle = f.detalle?.trim()
  if (!detalle) return '—'

  const nodes: ReactNode[] = []
  let last = 0
  for (const m of detalle.matchAll(_RE_MARCA_OBS)) {
    const idx = m.index ?? 0
    if (idx > last) nodes.push(detalle.slice(last, idx))
    const word = m[0]
    const lower = word.toLowerCase()
    if (lower === 'drive' && f.alerta_banco_drive) {
      nodes.push(
        <span key={`d-${idx}`} className="font-bold text-red-600">
          Drive
        </span>
      )
    } else if (lower === 'serial compuesto' && f.alerta_serial_mixto) {
      nodes.push(
        <span key={`s-${idx}`} className="font-bold text-pink-600">
          Serial compuesto
        </span>
      )
    } else {
      nodes.push(word)
    }
    last = idx + word.length
  }
  if (last < detalle.length) nodes.push(detalle.slice(last))
  return nodes.length ? nodes : detalle
}

export default function ImportacionExtractoPage() {
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [acting, setActing] = useState(false)
  const [lote, setLote] = useState<ImportacionExtractoLote | null>(null)
  const [stats, setStats] = useState<Record<string, number> | null>(null)
  const [filas, setFilas] = useState<ImportacionExtractoFila[]>([])
  const [selected, setSelected] = useState<Record<number, boolean>>({})
  const [filtro, setFiltro] = useState<string>('TODOS')

  const reloadFilas = useCallback(async (loteId: number) => {
    setLoading(true)
    try {
      const rows = await importacionExtractoService.listarFilas(loteId)
      setFilas(rows)
      setSelected({})
    } catch (e) {
      toast.error(errMsg(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        const lotes = await importacionExtractoService.listarLotes()
        if (lotes[0]) {
          setLote(lotes[0])
          await reloadFilas(lotes[0].id)
        }
      } catch {
        /* empty */
      }
    })()
  }, [reloadFilas])

  const visible = useMemo(() => {
    if (filtro === 'TODOS') return filas
    if (filtro === 'IMPORTABLES')
      return filas.filter(f => f.estado === 'SE_PUEDE_IMPORTAR')
    return filas.filter(f => f.estado === filtro)
  }, [filas, filtro])

  const selectedIds = useMemo(
    () => visible.filter(f => selected[f.id]).map(f => f.id),
    [visible, selected]
  )

  const importablesSelected = useMemo(
    () =>
      visible.filter(
        f => selected[f.id] && f.puede_ok_importar
      ),
    [visible, selected]
  )

  const onUpload = async (file: File | null) => {
    if (!file) return
    setUploading(true)
    try {
      const res = await importacionExtractoService.subirExcel(file)
      setLote(res.lote)
      setStats(res.stats)
      toast.success(`Comparado: ${res.filas} filas`)
      await reloadFilas(res.lote.id)
    } catch (e) {
      toast.error(errMsg(e))
    } finally {
      setUploading(false)
    }
  }

  const toggleAllImportables = (checked: boolean) => {
    const next = { ...selected }
    for (const f of visible) {
      if (f.puede_ok_importar) next[f.id] = checked
    }
    setSelected(next)
  }

  const okImportar = async (ids: number[]) => {
    if (!ids.length) {
      toast.message('Seleccione filas «Se puede importar»')
      return
    }
    setActing(true)
    try {
      const res = await importacionExtractoService.importar(ids)
      toast.success(`Importados: ${res.importados}`)
      if (lote) await reloadFilas(lote.id)
    } catch (e) {
      toast.error(errMsg(e))
    } finally {
      setActing(false)
    }
  }

  const marcarVisto = async (ids: number[]) => {
    if (!ids.length) return
    setActing(true)
    try {
      const res = await importacionExtractoService.marcarVisto(ids)
      toast.success(`Visto: ${res.marcados ?? ids.length}`)
      if (lote) await reloadFilas(lote.id)
    } catch (e) {
      toast.error(errMsg(e))
    } finally {
      setActing(false)
    }
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Importación extracto (faltantes)"
        description="Excel banco. Solo préstamos APROBADO (fecha de aprobación más reciente). LIQUIDADO y DESISTIMIENTO no aparecen. Match 100% cédula+serial se omite de la lista; aquí solo faltantes (importar) y semejantes (Visto)."
        icon={FileSpreadsheet}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Subir extracto</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted">
            <Upload className="h-4 w-4" />
            {uploading ? 'Subiendo…' : 'Elegir Excel'}
            <input
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              disabled={uploading}
              onChange={e => onUpload(e.target.files?.[0] || null)}
            />
          </label>
          {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
          {lote && (
            <span className="text-sm text-muted-foreground">
              Lote #{lote.id} · {lote.archivo_nombre}
            </span>
          )}
          {stats && (
            <span className="text-xs text-muted-foreground">
              {Object.entries(stats)
                .map(([k, v]) => `${k}:${v}`)
                .join(' · ')}
            </span>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-base">Resultados</CardTitle>
          <div className="flex flex-wrap gap-2">
            <select
              className="rounded border px-2 py-1 text-sm"
              value={filtro}
              onChange={e => setFiltro(e.target.value)}
            >
              <option value="TODOS">Todos</option>
              <option value="IMPORTABLES">Se puede importar</option>
              <option value="SEMEJANTE">Semejante</option>
              <option value="VISTO">Visto</option>
              <option value="IMPORTADO">Importado</option>
              <option value="PARSE_ERROR">Error parseo</option>
            </select>
            <Button
              size="sm"
              disabled={acting || importablesSelected.length === 0}
              onClick={() =>
                okImportar(importablesSelected.map(f => f.id))
              }
            >
              OK lote ({importablesSelected.length})
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={acting || selectedIds.length === 0}
              onClick={() => marcarVisto(selectedIds)}
            >
              Visto selección
            </Button>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {loading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Cargando…
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input
                      type="checkbox"
                      title="Seleccionar importables visibles"
                      onChange={e => toggleAllImportables(e.target.checked)}
                    />
                  </TableHead>
                  <TableHead>Fila</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Cédula</TableHead>
                  <TableHead>Serial</TableHead>
                  <TableHead>Monto</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead title="100% = confiabilidad (serial ausente). Menor % = similitud con un pago existente.">
                    % conf./sim.
                  </TableHead>
                  <TableHead>Observación</TableHead>
                  <TableHead>OK</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map(f => (
                  <TableRow key={f.id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={!!selected[f.id]}
                        onChange={e =>
                          setSelected(prev => ({
                            ...prev,
                            [f.id]: e.target.checked,
                          }))
                        }
                      />
                    </TableCell>
                    <TableCell>{f.fila_excel}</TableCell>
                    <TableCell>{f.fecha_deposito || '—'}</TableCell>
                    <TableCell>{f.cedula || '—'}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {f.serial || f.serial_norm || '—'}
                    </TableCell>
                    <TableCell>
                      {f.monto_usd != null ? f.monto_usd.toFixed(2) : '—'}
                    </TableCell>
                    <TableCell>{badgeEstado(f.estado)}</TableCell>
                    <TableCell>
                      {f.similitud_pct != null
                        ? f.estado === 'SE_PUEDE_IMPORTAR'
                          ? `${Number(f.similitud_pct).toFixed(0)}% conf.`
                          : f.estado === 'SEMEJANTE'
                            ? `${Number(f.similitud_pct).toFixed(1)}% sim.`
                            : `${Number(f.similitud_pct).toFixed(1)}%`
                        : '—'}
                    </TableCell>
                    <TableCell
                      className="max-w-[280px] text-xs whitespace-normal break-words text-muted-foreground"
                      title={f.detalle || undefined}
                    >
                      {renderDetalleObservacion(f)}
                    </TableCell>
                    <TableCell>
                      {f.puede_ok_importar ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={acting}
                          onClick={() => okImportar([f.id])}
                        >
                          OK
                        </Button>
                      ) : f.estado === 'SEMEJANTE' && !f.visto ? (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={acting}
                          onClick={() => marcarVisto([f.id])}
                        >
                          Visto
                        </Button>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {visible.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-sm text-muted-foreground">
                      Sin filas. Suba un Excel de extracto.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
