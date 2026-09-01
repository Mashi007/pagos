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
const PAGE_SIZE = 200

function filtroToApiParams(filtro: string): {
  estado?: string
  solo_importables?: boolean
  solo_ocultos?: boolean
} {
  if (filtro === 'ELIMINADOS') return { solo_ocultos: true }
  if (filtro === 'IMPORTABLES') return { estado: 'SE_PUEDE_IMPORTAR' }
  if (filtro === 'TODOS') return {}
  return { estado: filtro }
}

/** IDs pendientes de OK según filtro activo (OK lote importa todas, no solo la página). */
function pendingOkListParams(filtro: string): { estado: string } | null {
  if (filtro === 'ELIMINADOS' || filtro === 'IMPORTADO' || filtro === 'PARSE_ERROR') {
    return null
  }
  if (filtro === 'IMPORTABLES' || filtro === 'TODOS') {
    return { estado: 'SE_PUEDE_IMPORTAR' }
  }
  if (filtro === 'SEMEJANTE' || filtro === 'VISTO') {
    return { estado: filtro }
  }
  return null
}

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
  const [page, setPage] = useState(0)
  const [totalFilas, setTotalFilas] = useState(0)
  const [pendientesTotal, setPendientesTotal] = useState(0)
  const [banco, setBanco] = useState<string>(BANCOS_EXTRACTO[0])
  const [modoCedula, setModoCedula] = useState(true)
  const [modoSerial, setModoSerial] = useState(false)

  const reloadFilas = useCallback(
    async (loteId: number, filtroActual: string, pageIndex = 0) => {
      setLoading(true)
      try {
        const params = filtroToApiParams(filtroActual)
        const data = await importacionExtractoService.listarFilas(loteId, {
          ...params,
          limit: PAGE_SIZE,
          offset: pageIndex * PAGE_SIZE,
        })
        setFilas(data.filas || [])
        setTotalFilas(data.total ?? 0)
        setSelected({})
        const pendParams = pendingOkListParams(filtroActual)
        if (pendParams) {
          const pend = await importacionExtractoService.listarFilas(loteId, {
            ...pendParams,
            limit: 1,
            offset: 0,
          })
          setPendientesTotal(pend.total ?? 0)
        } else {
          setPendientesTotal(0)
        }
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
    void reloadFilas(lote.id, filtro, page)
  }, [filtro, lote?.id, page, reloadFilas])

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

  const visible = filas

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

  const okImportar = async (
    scope: 'todas' | 'seleccion' | 'filas',
    filaIds?: number[]
  ) => {
    setActing(true)
    try {
      let targetIds: number[] = []
      if (scope === 'filas' && filaIds?.length) {
        targetIds = filaIds
      } else if (scope === 'seleccion') {
        targetIds = importablesSelected.map(f => f.id)
        if (!targetIds.length) {
          toast.message('Seleccione filas importables en esta página')
          return
        }
      } else {
        if (!lote) {
          toast.message('No hay filas pendientes de importar')
          return
        }
        const pendParams = pendingOkListParams(filtro)
        if (!pendParams) {
          toast.message('Este filtro no tiene importación masiva')
          return
        }
        targetIds = await importacionExtractoService.listarTodasFilasIdsPendientes(
          lote.id,
          pendParams
        )
      }
      if (!targetIds.length) {
        toast.message('No hay filas pendientes de importar (ya importadas u omitidas)')
        return
      }
      const toastId =
        targetIds.length > 8
          ? toast.loading(
              `Importando 0/${targetIds.length} pendientes (lotes de 8, sin duplicar)…`
            )
          : null
      try {
        const res = await importacionExtractoService.importar(targetIds, {
          onProgress: (done, total) => {
            if (toastId != null && total > 8) {
              toast.loading(
                `Importando ${done}/${total} pendientes (lotes de 8)…`,
                { id: toastId }
              )
            }
          },
        })
        const fallos = (res.resultados || []).filter(
          r => !r.ok && r.motivo !== 'ya_importado'
        )
        const omitidas = (res.resultados || []).filter(
          r => !r.ok && r.motivo === 'ya_importado'
        )
        const conf = res.confirmados ?? 0
        if (res.importados > 0) {
          if (conf > 0 && conf === res.importados) {
            toast.success(
              `Confirmados: ${conf}${omitidas.length ? ` · ${omitidas.length} ya estaban importados` : ''}`
            )
          } else if (conf > 0) {
            toast.success(
              `Importados: ${res.importados} (${conf} confirmados)${omitidas.length ? ` · ${omitidas.length} omitidos (ya importados)` : ''}`
            )
          } else {
            toast.success(
              `Importados: ${res.importados}${omitidas.length ? ` · ${omitidas.length} omitidos (ya importados)` : ''}`
            )
          }
        } else if (omitidas.length) {
          toast.message(`${omitidas.length} fila(s) ya estaban importadas — sin duplicar`)
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
        if (res.importados === 0 && fallos.length === 0 && !omitidas.length) {
          toast.message('No se importó ninguna fila')
        }
      } finally {
        if (toastId != null) toast.dismiss(toastId)
      }
      if (lote) await reloadFilas(lote.id, filtro, page)
    } catch (e) {
      toast.error(errMsg(e))
      if (lote) {
        try {
          await reloadFilas(lote.id, filtro, page)
        } catch {
          /* ignore */
        }
      }
    } finally {
      setActing(false)
    }
  }
  const pageFrom = totalFilas === 0 ? 0 : page * PAGE_SIZE + 1
  const pageTo = Math.min((page + 1) * PAGE_SIZE, totalFilas)
  const totalPages = Math.max(1, Math.ceil(totalFilas / PAGE_SIZE))

  const pollLoteComparado = useCallback(
    async (loteId: number) => {
      const maxWaitMs = 20 * 60 * 1000
      const intervalMs = 3000
      const t0 = Date.now()
      while (Date.now() - t0 < maxWaitMs) {
        await new Promise(r => setTimeout(r, intervalMs))
        const lotes = await importacionExtractoService.listarLotes()
        const cur =
          lotes.find(l => l.id === loteId) ||
          (lotes[0]?.id === loteId ? lotes[0] : null)
        if (!cur) continue
        setLote(cur)
        if (cur.estado === 'PROCESANDO') continue
        if (cur.estado === 'COMPARADO') {
          setStats((cur.stats as Record<string, number>) || null)
          setFiltro('TODOS')
          setPage(0)
          await reloadFilas(loteId, 'TODOS', 0)
          const total = Object.values(cur.stats || {}).reduce(
            (a, b) => a + Number(b || 0),
            0
          )
          toast.success(`Comparado: ${total || 'listo'} filas en lote #${cur.id}`)
          return
        }
        if (cur.estado === 'ERROR') {
          toast.error('Error al comparar el lote en servidor')
          return
        }
      }
      toast.error(
        'Comparación aún en curso; recargue la página en unos minutos.'
      )
    },
    [reloadFilas]
  )

  const syncLoteReciente = useCallback(
    async (preferId?: number) => {
      const lotes = await importacionExtractoService.listarLotes()
      if (!lotes.length) return null
      const pick =
        (preferId != null && lotes.find(l => l.id === preferId)) || lotes[0]
      setLote(pick)
      if (
        pick.banco &&
        BANCOS_EXTRACTO.includes(pick.banco as (typeof BANCOS_EXTRACTO)[number])
      ) {
        setBanco(pick.banco)
      }
      return pick
    },
    []
  )

  const onUpload = async (file: File | null, input?: HTMLInputElement | null) => {
    if (!file) return
    if (!modoCedula && !modoSerial) {
      toast.error('Marque al menos Cédula o Serial para continuar')
      return
    }
    setUploading(true)
    setStats(null)
    setFilas([])
    setTotalFilas(0)
    setPendientesTotal(0)
    setLote(prev =>
      prev
        ? {
            ...prev,
            archivo_nombre: file.name,
            estado: 'PROCESANDO',
          }
        : {
            id: 0,
            archivo_nombre: file.name,
            estado: 'PROCESANDO',
          }
    )
    try {
      const res = await importacionExtractoService.subirExcel(file, banco, {
        modo_cedula: modoCedula,
        modo_serial: modoSerial,
      })
      const actualizado = await syncLoteReciente(res.lote?.id)
      const loteActivo = actualizado || res.lote
      setLote(loteActivo)
      if (loteActivo.banco) setBanco(loteActivo.banco)
      if (res.async) {
        const toastId = toast.loading(
          res.message ||
            `Comparando lote #${loteActivo.id} (${file.name}) en segundo plano…`
        )
        try {
          await pollLoteComparado(loteActivo.id)
        } finally {
          toast.dismiss(toastId)
        }
        return
      }
      setStats(res.stats)
      toast.success(`Comparado lote #${loteActivo.id}: ${res.filas} filas`)
      setFiltro('TODOS')
      setPage(0)
      await reloadFilas(loteActivo.id, 'TODOS', 0)
    } catch (e) {
      toast.error(errMsg(e))
      await syncLoteReciente()
    } finally {
      setUploading(false)
      if (input) input.value = ''
    }
  }

  const toggleAllImportables = (checked: boolean) => {
    const next = { ...selected }
    for (const f of importablesVisible) {
      next[f.id] = checked
    }
    setSelected(next)
  }

  const marcarVisto = async (ids: number[]) => {
    if (!ids.length) return
    setActing(true)
    try {
      const res = await importacionExtractoService.marcarVisto(ids)
      toast.success(`Visto: ${res.marcados ?? ids.length}`)
      if (lote) await reloadFilas(lote.id, filtro, page)
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
      if (lote) await reloadFilas(lote.id, filtro, page)
    } catch (e) {
      toast.error(errMsg(e))
    } finally {
      setActing(false)
    }
  }

  const soloSerial = modoSerial && !modoCedula

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Importación extracto (faltantes)"
        description={
          soloSerial
            ? 'Solo Serial → Pagos confirmados (sin cédula ni cascada). Excel: Fecha | cedula vacía | Referencia | Monto.'
            : 'Seleccione banco y modo (Cédula y/o Serial) antes de subir. Sin marcar ninguno no avanza. Solo Serial → Pagos confirmados; con Cédula → préstamo.'
        }
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
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={modoCedula}
              disabled={uploading}
              onChange={e => setModoCedula(e.target.checked)}
            />
            Cédula → préstamo
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={modoSerial}
              disabled={uploading}
              onChange={e => setModoSerial(e.target.checked)}
            />
            Serial → Pagos confirmados
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted">
            <Upload className="h-4 w-4" />
            {uploading ? 'Subiendo…' : 'Elegir Excel'}
            <input
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              disabled={uploading || (!modoCedula && !modoSerial)}
              onChange={e => {
                const f = e.target.files?.[0] || null
                void onUpload(f, e.target)
              }}
            />
          </label>
          {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
          {soloSerial && (
            <p className="w-full text-xs text-muted-foreground">
              Formato Excel (solo Serial): columna A Fecha, B cedula vacía, C Referencia
              (serial), D Monto. En C: elija formato Texto en Excel antes de pegar, no
              después. Si ve 7.40E+14, Excel ya truncó el serial — debe repegar desde el origen.
            </p>
          )}
          {lote && (
            <span className="text-sm text-muted-foreground">
              {lote.id > 0 ? `Lote #${lote.id}` : 'Nuevo extracto'}
              {lote.estado === 'PROCESANDO' ? ' · comparando…' : ''}
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
            {lote?.id ? (
              <Badge variant="outline" className="font-normal">
                Lote #{lote.id}
                {lote.estado === 'PROCESANDO' ? ' · comparando' : ''}
              </Badge>
            ) : null}
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
              onChange={e => {
                setFiltro(e.target.value)
                setPage(0)
              }}
            >
              <option value="TODOS">Todos</option>
              <option value="IMPORTABLES">Se puede importar (100%)</option>
              <option value="SEMEJANTE">Semejante</option>
              <option value="VISTO">Visto</option>
              <option value="IMPORTADO">Importado</option>
              <option value="PARSE_ERROR">Error parseo</option>
              <option value="ELIMINADOS">Eliminados</option>
            </select>
            <Button
              size="sm"
              disabled={
                acting ||
                pendientesTotal === 0 ||
                filtro === 'ELIMINADOS' ||
                !pendingOkListParams(filtro)
              }
              title="Importa todas las pendientes del lote (todas las páginas), sin duplicar las ya importadas"
              onClick={() => okImportar('todas')}
            >
              OK lote ({pendientesTotal.toLocaleString()} pendientes)
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={
                acting ||
                importablesSelected.length === 0 ||
                filtro === 'ELIMINADOS'
              }
              title="Solo las filas marcadas en esta página"
              onClick={() => okImportar('seleccion')}
            >
              OK selección ({importablesSelected.length})
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
          {!loading && totalFilas > 0 && (
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
              <span>
                Mostrando {pageFrom}–{pageTo} de {totalFilas.toLocaleString()}
                {pendientesTotal > 0
                  ? ` · ${pendientesTotal.toLocaleString()} pendientes (OK lote = todas)`
                  : ''}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 0 || loading}
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                >
                  Anterior
                </Button>
                <span>
                  Pág. {page + 1} / {totalPages}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page + 1 >= totalPages || loading}
                  onClick={() => setPage(p => p + 1)}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
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
                      title="Seleccionar importables visibles en esta página (200 máx.)"
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
                  <TableHead>Acción</TableHead>
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
                    <TableCell>
                      {f.cedula || '—'}
                      {f.prestamo_destino_id ? (
                        <div className="text-[10px] text-muted-foreground">
                          → prestamo {f.prestamo_destino_id}
                        </div>
                      ) : f.prestamo_id ? (
                        <div className="text-[10px] text-muted-foreground">
                          → prestamo {f.prestamo_id}
                        </div>
                      ) : null}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      <div>{f.serial || f.serial_norm || '—'}</div>
                      {f.alerta_confirmado_pendiente ? (
                        <Badge
                          className="mt-1 bg-violet-600 text-[10px] font-normal"
                          title={
                            f.prestamo_destino_id
                              ? `Al OK → prestamo_id=${f.prestamo_destino_id}`
                              : 'Serial ya confirmado sin cédula; al OK pasa a préstamo'
                          }
                        >
                          Confirmado previo
                          {f.confirmado_pendiente_ids?.[0]
                            ? ` #${f.confirmado_pendiente_ids[0]}`
                            : ''}
                        </Badge>
                      ) : null}
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
                            onClick={() => okImportar('filas', [f.id])}
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
