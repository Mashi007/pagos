import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { FileSpreadsheet, Loader2, Trash2, Upload } from 'lucide-react'
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
  BANCOS_EXTRACTO,
  importacionExtractoService,
} from '../services/importacionExtractoService'

function errMsg(err: unknown): string {
  const e = err as { response?: { data?: { detail?: string } }; message?: string }
  return e?.response?.data?.detail || e?.message || 'Error'
}

const ESTADOS_OK_IMPORTAR = ['SE_PUEDE_IMPORTAR', 'SEMEJANTE', 'VISTO'] as const

function filaPuedeOkImportar(f: ImportacionExtractoFila): boolean {
  if (f.importado || f.oculto) return false
  if (typeof f.puede_ok_importar === 'boolean') return f.puede_ok_importar
  return ESTADOS_OK_IMPORTAR.includes(f.estado as (typeof ESTADOS_OK_IMPORTAR)[number])
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
    case 'PRESTAMO_PAGADO':
      return <Badge className="bg-slate-500">Préstamo pagado</Badge>
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
  const [banco, setBanco] = useState<string>(BANCOS_EXTRACTO[0])

  const reloadFilas = useCallback(
    async (loteId: number, soloOcultos = false) => {
      setLoading(true)
      try {
        const rows = await importacionExtractoService.listarFilas(loteId, {
          solo_ocultos: soloOcultos || undefined,
        })
        setFilas(rows)
        setSelected({})
      } catch (e) {
        toast.error(errMsg(e))
      } finally {
        setLoading(false)
      }
    },
    []
  )

  useEffect(() => {
    if (!lote) return
    void reloadFilas(lote.id, filtro === 'ELIMINADOS')
  }, [filtro, lote?.id, reloadFilas])

  useEffect(() => {
    ;(async () => {
      try {
        const lotes = await importacionExtractoService.listarLotes()
        if (lotes[0]) {
          setLote(lotes[0])
          if (lotes[0].banco && BANCOS_EXTRACTO.includes(lotes[0].banco as (typeof BANCOS_EXTRACTO)[number])) {
            setBanco(lotes[0].banco)
          }
        }
      } catch {
        /* empty */
      }
    })()
  }, [])

  const visible = useMemo(() => {
    if (filtro === 'ELIMINADOS') return filas
    const sinDrive = (f: ImportacionExtractoFila) =>
      !f.alerta_banco_drive &&
      !(f.detalle || '').toLowerCase().includes('drive')
    let rows = filas.filter(sinDrive)
    if (filtro === 'TODOS') return rows
    if (filtro === 'IMPORTABLES')
      return rows.filter(f => f.estado === 'SE_PUEDE_IMPORTAR')
    return rows.filter(f => f.estado === filtro)
  }, [filas, filtro])

  const importablesVisible = useMemo(
    () => visible.filter(filaPuedeOkImportar),
    [visible]
  )

  const selectedIds = useMemo(
    () => visible.filter(f => selected[f.id]).map(f => f.id),
    [visible, selected]
  )

  const importablesSelected = useMemo(
    () => importablesVisible.filter(f => selected[f.id]),
    [importablesVisible, selected]
  )

  const allImportablesChecked =
    importablesVisible.length > 0 &&
    importablesVisible.every(f => selected[f.id])

  const idsParaOkLote = useMemo(() => {
    const src =
      importablesSelected.length > 0 ? importablesSelected : importablesVisible
    return src.map(f => f.id)
  }, [importablesSelected, importablesVisible])

  const onUpload = async (file: File | null) => {
    if (!file) return
    setUploading(true)
    try {
      const res = await importacionExtractoService.subirExcel(file, banco)
      setLote(res.lote)
      if (res.lote.banco) setBanco(res.lote.banco)
      setStats(res.stats)
      toast.success(`Comparado: ${res.filas} filas`)
      setFiltro('TODOS')
      await reloadFilas(res.lote.id, false)
    } catch (e) {
      toast.error(errMsg(e))
    } finally {
      setUploading(false)
    }
  }

  const toggleAllImportables = (checked: boolean) => {
    const next = { ...selected }
    for (const f of importablesVisible) {
      next[f.id] = checked
    }
    setSelected(next)
  }

  const okImportar = async (ids: number[]) => {
    if (!ids.length) {
      toast.message('No hay filas importables (faltantes, semejantes o visto)')
      return
    }
    setActing(true)
    const toastId =
      ids.length > 8
        ? toast.loading(`Importando ${ids.length} filas (por lotes de 8)…`)
        : null
    try {
      const res = await importacionExtractoService.importar(ids)
      if (toastId != null) toast.dismiss(toastId)
      const fallos = (res.resultados || []).filter(r => !r.ok)
      if (res.importados > 0) {
        toast.success(`Importados: ${res.importados}`)
      }
      if (fallos.length) {
        const msg = fallos
          .slice(0, 3)
          .map(
            r =>
              `#${r.fila_id}: ${(r as { motivo?: string; detalle?: string }).motivo || (r as { detalle?: string }).detalle || 'error'}`
          )
          .join('; ')
        toast.error(
          fallos.length === 1 ? msg : `${fallos.length} fallos — ${msg}`
        )
      }
      if (res.importados === 0 && fallos.length === 0) {
        toast.message('No se importó ninguna fila')
      }
      if (lote) await reloadFilas(lote.id, filtro === 'ELIMINADOS')
    } catch (e) {
      if (toastId != null) toast.dismiss(toastId)
      toast.error(errMsg(e))
      if (lote) {
        try {
          await reloadFilas(lote.id, filtro === 'ELIMINADOS')
        } catch {
          /* ignore */
        }
      }
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
      if (lote) await reloadFilas(lote.id, filtro === 'ELIMINADOS')
    } catch (e) {
      toast.error(errMsg(e))
    } finally {
      setActing(false)
    }
  }

  const ocultarFilas = async (ids: number[]) => {
    if (!ids.length) {
      toast.message('Seleccione filas para ocultar')
      return
    }
    if (
      !window.confirm(
        `¿Ocultar ${ids.length} fila(s)? Dejarán de mostrarse en auditoría.`
      )
    ) {
      return
    }
    setActing(true)
    try {
      const res = await importacionExtractoService.ocultar(ids)
      toast.success(`Ocultadas: ${res.ocultados ?? ids.length}`)
      if (lote) await reloadFilas(lote.id, filtro === 'ELIMINADOS')
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
        description="Seleccione el banco del extracto antes de subir el Excel; todo el lote se etiqueta con ese banco al importar. Solo préstamos APROBADO; match 100% se omite."
        icon={FileSpreadsheet}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Subir extracto</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Banco del extracto</span>
            <select
              className="rounded border px-2 py-1.5 text-sm font-medium"
              value={banco}
              disabled={uploading}
              onChange={e => setBanco(e.target.value)}
              title="Todo el archivo pertenece a este banco"
            >
              {BANCOS_EXTRACTO.map(b => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </label>
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
              Lote #{lote.id}
              {lote.banco ? ` · ${lote.banco}` : ''} · {lote.archivo_nombre}
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
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-base">Resultados</CardTitle>
            {lote?.banco && (
              <Badge variant="outline" className="font-normal">
                Banco: {lote.banco}
              </Badge>
            )}
          </div>
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
              <option value="ELIMINADOS">Eliminados</option>
            </select>
            <Button
              size="sm"
              disabled={acting || idsParaOkLote.length === 0 || filtro === 'ELIMINADOS'}
              onClick={() => okImportar(idsParaOkLote)}
            >
              OK lote ({idsParaOkLote.length})
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={acting || selectedIds.length === 0}
              onClick={() => marcarVisto(selectedIds)}
            >
              Visto selección
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="text-destructive hover:text-destructive"
              disabled={acting || selectedIds.length === 0}
              onClick={() => ocultarFilas(selectedIds)}
            >
              <Trash2 className="mr-1 h-3.5 w-3.5" />
              Ocultar ({selectedIds.length})
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
                      title="Seleccionar todas las filas importables visibles"
                      checked={allImportablesChecked}
                      disabled={importablesVisible.length === 0 || filtro === 'ELIMINADOS'}
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
                  <TableHead>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="h-7 px-2"
                      disabled={
                        acting ||
                        importablesVisible.length === 0 ||
                        filtro === 'ELIMINADOS'
                      }
                      title="Importar todas las filas importables visibles"
                      onClick={() =>
                        okImportar(importablesVisible.map(f => f.id))
                      }
                    >
                      OK
                    </Button>
                  </TableHead>
                  <TableHead className="w-12"> </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map(f => (
                  <TableRow key={f.id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={!!selected[f.id]}
                        disabled={!filaPuedeOkImportar(f) || filtro === 'ELIMINADOS'}
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
                      {filaPuedeOkImportar(f) ? (
                        <div className="flex flex-wrap gap-1">
                          <Button
                            size="sm"
                            variant="secondary"
                            disabled={acting || filtro === 'ELIMINADOS'}
                            onClick={() => okImportar([f.id])}
                          >
                            OK
                          </Button>
                          {f.estado === 'SEMEJANTE' && !f.visto ? (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={acting}
                              onClick={() => marcarVisto([f.id])}
                            >
                              Visto
                            </Button>
                          ) : null}
                        </div>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                        disabled={acting}
                        title="Ocultar fila"
                        onClick={() => ocultarFilas([f.id])}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {visible.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={11} className="text-center text-sm text-muted-foreground">
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
