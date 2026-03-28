import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  BarChart3,
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Loader2,
  RefreshCw,
} from 'lucide-react'

import { Button } from '../ui/button'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { Input } from '../ui/input'

import { Label } from '../ui/label'

import { Badge } from '../ui/badge'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'

import {
  auditoriaService,
  PrestamoCarteraChequeo,
  type CarteraRevisionItem,
} from '../../services/auditoriaService'

import { useSimpleAuth } from '../../store/simpleAuthStore'

import { toast } from 'sonner'

import { Link } from 'react-router-dom'

import {
  AUDITORIA_CARTERA_CONTROLES_CATALOGO,
  numeroControlAuditoriaCartera,
} from './auditoriaCarteraControlesCatalogo'

function controlDismissKey(prestamoId: number, codigo: string) {
  return `${prestamoId}:${codigo}`
}

const COD_DESAJUSTE_PAGOS = 'total_pagado_vs_aplicado_cuotas'

const PAGE_SIZE_DEFAULT = 25

function csvEscapeCell(val: string): string {
  if (/[",\n\r]/.test(val)) {
    return `"${val.replace(/"/g, '""')}"`
  }
  return val
}

type FiltrosApi = { cedula: string; prestamo_id?: number }

const SESSION_CACHE_KEY = 'auditoria_cartera_ui_v1'

type CarteraSessionCacheV1 = {
  v: 1
  items: PrestamoCarteraChequeo[]
  resumen: Record<string, unknown>
  filtrosApi: FiltrosApi
  page: number
  filtroControlCodigo: string
  ocultosKeys: string[]
}

function loadCarteraSessionCache(): CarteraSessionCacheV1 | null {
  try {
    const raw = sessionStorage.getItem(SESSION_CACHE_KEY)
    if (!raw) return null
    const c = JSON.parse(raw) as Partial<CarteraSessionCacheV1>
    if (c.v !== 1 || !Array.isArray(c.items) || !c.filtrosApi) return null
    return {
      v: 1,
      items: c.items,
      resumen: (c.resumen && typeof c.resumen === 'object' ? c.resumen : {}) as Record<
        string,
        unknown
      >,
      filtrosApi: {
        cedula: typeof c.filtrosApi.cedula === 'string' ? c.filtrosApi.cedula : '',
        prestamo_id: c.filtrosApi.prestamo_id,
      },
      page: typeof c.page === 'number' && c.page >= 1 ? c.page : 1,
      filtroControlCodigo:
        typeof c.filtroControlCodigo === 'string' ? c.filtroControlCodigo : '',
      ocultosKeys: Array.isArray(c.ocultosKeys) ? c.ocultosKeys : [],
    }
  } catch {
    return null
  }
}

function saveCarteraSessionCache(payload: {
  items: PrestamoCarteraChequeo[]
  resumen: Record<string, unknown>
  filtrosApi: FiltrosApi
  page: number
  filtroControlCodigo: string
  ocultosKeys: string[]
}) {
  try {
    const row: CarteraSessionCacheV1 = {
      v: 1,
      items: payload.items,
      resumen: payload.resumen,
      filtrosApi: payload.filtrosApi,
      page: payload.page,
      filtroControlCodigo: payload.filtroControlCodigo,
      ocultosKeys: payload.ocultosKeys,
    }
    sessionStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(row))
  } catch {
    /* quota o modo privado */
  }
}

export function AuditoriaCarteraTab() {
  const { user } = useSimpleAuth()

  const esAdmin = (user?.rol || 'operativo') === 'administrador'

  const boot = useMemo(() => loadCarteraSessionCache(), [])

  const [loading, setLoading] = useState(() => boot === null)

  const [running, setRunning] = useState(false)

  const [corrigiendo, setCorrigiendo] = useState(false)

  const [exportando, setExportando] = useState(false)

  const [items, setItems] = useState<PrestamoCarteraChequeo[]>(
    () => boot?.items ?? []
  )

  const [resumen, setResumen] = useState<Record<string, unknown> | null>(
    () => boot?.resumen ?? null
  )

  /** Claves `prestamo_id:codigo_control` con ultimo MARCAR_OK en BD (POST ocultos). */
  const [ocultosKeys, setOcultosKeys] = useState<Set<string>>(
    () => new Set(boot?.ocultosKeys ?? [])
  )

  const [historialOpen, setHistorialOpen] = useState(false)

  const [historialPid, setHistorialPid] = useState<number | null>(null)

  const [historialRows, setHistorialRows] = useState<CarteraRevisionItem[]>([])

  const [historialLoading, setHistorialLoading] = useState(false)

  const [cedulaInput, setCedulaInput] = useState(
    () => boot?.filtrosApi.cedula ?? ''
  )

  const [prestamoInput, setPrestamoInput] = useState(() =>
    boot?.filtrosApi.prestamo_id != null
      ? String(boot.filtrosApi.prestamo_id)
      : ''
  )

  const [filtrosApi, setFiltrosApi] = useState<FiltrosApi>(
    () => boot?.filtrosApi ?? { cedula: '' }
  )

  const [page, setPage] = useState(() => boot?.page ?? 1)

  const [pageSize] = useState(PAGE_SIZE_DEFAULT)

  const [filtroControlCodigo, setFiltroControlCodigo] = useState(
    () => boot?.filtroControlCodigo ?? ''
  )

  const [loadingKpis, setLoadingKpis] = useState(false)

  /** Ultima respuesta GET /prestamos/cartera/resumen (mismos filtros que filtrosApi). */
  const [panelKpis, setPanelKpis] = useState<Record<string, unknown> | null>(
    null
  )

  const [metaUltimaCorridaPanel, setMetaUltimaCorridaPanel] = useState<Record<
    string,
    unknown
  > | null>(null)

  const syncOcultosConItems = useCallback(
    async (list: PrestamoCarteraChequeo[]): Promise<Set<string>> => {
      const ids = [...new Set(list.map(r => r.prestamo_id))]
      if (ids.length === 0) {
        const empty = new Set<string>()
        setOcultosKeys(empty)
        return empty
      }
      try {
        const r = await auditoriaService.listarRevisionesOcultos(ids)
        const s = new Set(
          (r.ocultos || []).map(o => `${o.prestamo_id}:${o.codigo_control}`)
        )
        setOcultosKeys(s)
        return s
      } catch (e: unknown) {
        const empty = new Set<string>()
        setOcultosKeys(empty)
        const msg =
          e && typeof e === 'object' && 'message' in e
            ? String((e as { message?: string }).message)
            : 'Error al cargar revisiones en BD (tabla migrada?)'
        toast.error(msg)
        return empty
      }
    },
    []
  )

  const fetchLista = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true
      try {
        if (!silent) setLoading(true)

        const cheq = await auditoriaService.listarCarteraChequeos({
          skip: (page - 1) * pageSize,
          limit: pageSize,
          cedula: filtrosApi.cedula.trim() || undefined,
          prestamo_id: filtrosApi.prestamo_id,
        })

        const nextItems = cheq.items || []
        const nextResumen = (cheq.resumen as Record<string, unknown>) || {}

        setItems(nextItems)
        setResumen(nextResumen)

        const ocultos = await syncOcultosConItems(nextItems)
        saveCarteraSessionCache({
          items: nextItems,
          resumen: nextResumen,
          filtrosApi,
          page,
          filtroControlCodigo,
          ocultosKeys: [...ocultos],
        })
      } catch (e: unknown) {
        const msg =
          e && typeof e === 'object' && 'message' in e
            ? String((e as { message?: string }).message)
            : 'Error al cargar auditoria de cartera'

        toast.error(msg)

        if (!silent) {
          setItems([])
          setResumen(null)
          setOcultosKeys(new Set())
        }
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [
      page,
      pageSize,
      filtrosApi,
      filtroControlCodigo,
      syncOcultosConItems,
    ]
  )

  const primeraCargaRef = useRef(true)
  const bootRef = useRef(boot)
  bootRef.current = boot

  useEffect(() => {
    const b = bootRef.current
    if (primeraCargaRef.current && b) {
      primeraCargaRef.current = false
      void fetchLista({ silent: true })
      return
    }
    primeraCargaRef.current = false
    void fetchLista()
  }, [fetchLista])

  const resetFiltrosUiYSesion = useCallback(() => {
    setFiltroControlCodigo('')
    setCedulaInput('')
    setPrestamoInput('')
    setFiltrosApi({ cedula: '' })
    setPage(1)
    setPanelKpis(null)
    setMetaUltimaCorridaPanel(null)
    setHistorialOpen(false)
    setHistorialPid(null)
    setHistorialRows([])
  }, [])

  const recargarCompleta = useCallback(() => {
    resetFiltrosUiYSesion()
  }, [resetFiltrosUiYSesion])

  const aplicarFiltros = useCallback(() => {
    let pid: number | undefined
    const p = prestamoInput.trim()
    if (p) {
      const n = parseInt(p, 10)
      if (!Number.isFinite(n) || n < 1) {
        toast.error('ID de prestamo invalido')
        return
      }
      pid = n
    }
    setFiltrosApi({ cedula: cedulaInput.trim(), prestamo_id: pid })
    setPage(1)
  }, [cedulaInput, prestamoInput])

  const soloKpisResumen = async () => {
    try {
      setLoadingKpis(true)
      const r = await auditoriaService.obtenerCarteraResumen({
        cedula: filtrosApi.cedula.trim() || undefined,
        prestamo_id: filtrosApi.prestamo_id,
      })
      setPanelKpis((r.resumen as Record<string, unknown>) || {})
      setMetaUltimaCorridaPanel(
        (r.meta_ultima_corrida as Record<string, unknown>) || {}
      )
      toast.success('Resumen KPI actualizado (sin cargar lista de prestamos).')
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al obtener resumen de cartera'
      toast.error(msg)
    } finally {
      setLoadingKpis(false)
    }
  }

  const ejecutarAhora = async () => {
    try {
      setRunning(true)

      const cheq = await auditoriaService.ejecutarCartera()

      resetFiltrosUiYSesion()

      const s = cheq.sincronizar_estado_cuotas
      const extra =
        s && typeof s.estados_actualizados === 'number'
          ? ` Estados de cuota alineados: ${s.estados_actualizados} fila(s).`
          : ''
      toast.success(`Auditoria ejecutada y metadatos actualizados.${extra}`)
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al ejecutar auditoria'

      toast.error(msg)
    } finally {
      setRunning(false)
    }
  }

  const exportarCsv = async () => {
    try {
      setExportando(true)
      const cheq = await auditoriaService.listarCarteraChequeos({
        skip: 0,
        limit: 5000,
        cedula: filtrosApi.cedula.trim() || undefined,
        prestamo_id: filtrosApi.prestamo_id,
      })
      const header =
        'prestamo_id,cedula,nombres,estado_prestamo,codigo_control,titulo_control,detalle'
      const lines = [`\ufeff${header}`]
      for (const row of cheq.items || []) {
        for (const c of row.controles) {
          if (filtroControlCodigo && c.codigo !== filtroControlCodigo) {
            continue
          }
          lines.push(
            [
              String(row.prestamo_id),
              csvEscapeCell(row.cedula || ''),
              csvEscapeCell(row.nombres || ''),
              csvEscapeCell(row.estado_prestamo || ''),
              csvEscapeCell(c.codigo),
              csvEscapeCell(c.titulo),
              csvEscapeCell(c.detalle || ''),
            ].join(',')
          )
        }
      }
      const blob = new Blob([lines.join('\r\n')], {
        type: 'text/csv;charset=utf-8',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `auditoria_cartera_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('CSV descargado (hasta 5000 prestamos con alerta).')
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al exportar CSV'
      toast.error(msg)
    } finally {
      setExportando(false)
    }
  }

  const visibleRows = useMemo(() => {
    return items
      .map(row => ({
        ...row,
        controles: row.controles.filter(
          c => !ocultosKeys.has(controlDismissKey(row.prestamo_id, c.codigo))
        ),
      }))
      .filter(row => row.controles.length > 0)
  }, [items, ocultosKeys])

  const conteosPorControlCodigo = useMemo(() => {
    const raw = resumen?.conteos_por_control
    if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
      return raw as Record<string, number>
    }
    return {}
  }, [resumen])

  const displayRows = useMemo(() => {
    if (!filtroControlCodigo) return visibleRows
    return visibleRows
      .filter(row => row.controles.some(c => c.codigo === filtroControlCodigo))
      .map(row => ({
        ...row,
        controles: row.controles.filter(c => c.codigo === filtroControlCodigo),
      }))
  }, [visibleRows, filtroControlCodigo])

  const marcarControlOk = async (prestamoId: number, codigo: string) => {
    try {
      await auditoriaService.crearRevisionCartera({
        prestamo_id: prestamoId,
        codigo_control: codigo,
      })
      const k = controlDismissKey(prestamoId, codigo)
      setOcultosKeys(prev => {
        const next = new Set([...prev, k])
        saveCarteraSessionCache({
          items,
          resumen: resumen ?? {},
          filtrosApi,
          page,
          filtroControlCodigo,
          ocultosKeys: [...next],
        })
        return next
      })
      toast.success('Revision guardada en base de datos')
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al registrar revision'
      toast.error(msg)
    }
  }

  const abrirHistorialRevisiones = async (pid: number) => {
    setHistorialPid(pid)
    setHistorialOpen(true)
    setHistorialLoading(true)
    setHistorialRows([])
    try {
      const rows = await auditoriaService.historialRevisionesCartera(pid, 100)
      setHistorialRows(Array.isArray(rows) ? rows : [])
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al cargar historial'
      toast.error(msg)
    } finally {
      setHistorialLoading(false)
    }
  }

  const totalListados = Number(
    resumen?.prestamos_listados_total ?? resumen?.prestamos_con_alerta ?? 0
  )

  const hayAlertas = totalListados > 0

  const totalPages = Math.max(1, Math.ceil(totalListados / pageSize))

  const skipActual = (page - 1) * pageSize

  const rangoDesde =
    totalListados === 0 ? 0 : Math.min(skipActual + 1, totalListados)

  const rangoHasta = Math.min(skipActual + items.length, totalListados)

  const hayDesajustePagosVsAplicado = useMemo(() => {
    return (conteosPorControlCodigo[COD_DESAJUSTE_PAGOS] ?? 0) > 0
  }, [conteosPorControlCodigo])

  const corregirDesajustePagos = async () => {
    try {
      setCorrigiendo(true)
      const res = await auditoriaService.corregirCartera({
        sincronizar_estados: true,
        reaplicar_cascada_desajuste_pagos: true,
        max_reaplicaciones: 100,
      })
      resetFiltrosUiYSesion()
      const ok = (res.reaplicar_cascada || []).filter(
        (x: Record<string, unknown>) => x.ok === true
      ).length
      const fail = (res.reaplicar_cascada || []).length - ok
      const sync = res.sincronizar_estado_cuotas
      toast.success(
        `Correccion: cascada ${ok} prestamo(s) OK${fail ? `, ${fail} con error` : ''}.` +
          (sync && typeof sync.estados_actualizados === 'number'
            ? ` Estados sincronizados: ${sync.estados_actualizados}.`
            : '')
      )
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al corregir cartera'
      toast.error(msg)
    } finally {
      setCorrigiendo(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => recargarCompleta()}
          disabled={loading}
          title="Vuelve a pedir la lista al servidor (siempre lee la BD en tiempo real)."
        >
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Recargar
        </Button>

        <Button size="sm" onClick={ejecutarAhora} disabled={running || loading}>
          {running ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Ejecutar ahora y guardar meta
        </Button>

        {esAdmin && hayDesajustePagosVsAplicado && !loading ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void corregirDesajustePagos()}
            disabled={corrigiendo || running || loading}
            title="Reaplica pagos en cascada en prestamos con alerta de suma pagos vs cuota_pagos, luego sincroniza estados de cuota."
          >
            {corrigiendo ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Corregir desajuste pagos (cascada)
          </Button>
        ) : null}

        <p className="w-full text-xs text-muted-foreground">
          La vista de cartera permanece en memoria al cambiar de pestaña. En la misma sesion del
          navegador se restaura la ultima lista y filtros; al volver se actualiza en segundo plano.
          Los chequeos se calculan en vivo contra la BD; el job 03:00 actualiza la meta guardada
          (KPIs en configuracion), no sustituye una recarga manual si hubo cambios despues.
        </p>

        {hayAlertas && !loading ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => void exportarCsv()}
            disabled={exportando}
          >
            {exportando ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            Exportar CSV
          </Button>
        ) : null}

        <div className="flex w-full min-w-[200px] max-w-sm flex-col gap-1 sm:w-auto">
          <Label
            htmlFor="auditoria-cedula-filtro"
            className="text-xs text-gray-600"
          >
            Cedula (fragmento)
          </Label>

          <Input
            id="auditoria-cedula-filtro"
            type="search"
            placeholder="Ej. V12345678"
            value={cedulaInput}
            onChange={e => setCedulaInput(e.target.value)}
            autoComplete="off"
            className="h-9"
          />
        </div>

        <div className="flex w-full min-w-[140px] max-w-xs flex-col gap-1 sm:w-auto">
          <Label
            htmlFor="auditoria-prestamo-filtro"
            className="text-xs text-gray-600"
          >
            ID prestamo
          </Label>

          <Input
            id="auditoria-prestamo-filtro"
            inputMode="numeric"
            placeholder="Opcional"
            value={prestamoInput}
            onChange={e => setPrestamoInput(e.target.value)}
            autoComplete="off"
            className="h-9"
          />
        </div>

        <div className="flex flex-wrap items-end gap-2 pb-0.5">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={aplicarFiltros}
            disabled={loading}
          >
            Aplicar filtros
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void soloKpisResumen()}
            disabled={loading || loadingKpis}
            title="Misma logica que la lista pero sin devolver prestamos (GET .../cartera/resumen). Usa filtros ya aplicados."
          >
            {loadingKpis ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <BarChart3 className="mr-2 h-4 w-4" />
            )}
            Solo KPIs
          </Button>
        </div>

        {hayAlertas && !loading ? (
          <div className="flex w-full min-w-[240px] max-w-xl flex-col gap-1 sm:w-auto">
            <Label
              htmlFor="auditoria-control-filtro"
              className="text-xs text-gray-600"
            >
              Filtrar por control
            </Label>

            <Select
              value={filtroControlCodigo || '__todos__'}
              onValueChange={v =>
                setFiltroControlCodigo(v === '__todos__' ? '' : v)
              }
            >
              <SelectTrigger
                id="auditoria-control-filtro"
                className="h-9 w-full"
              >
                <SelectValue placeholder="Todos los controles" />
              </SelectTrigger>

              <SelectContent>
                <SelectItem value="__todos__">
                  Todos los controles (cualquier alerta)
                </SelectItem>

                {AUDITORIA_CARTERA_CONTROLES_CATALOGO.map(def => {
                  const cnt = conteosPorControlCodigo[def.codigo] ?? 0

                  return (
                    <SelectItem
                      key={def.codigo}
                      value={def.codigo}
                      title={def.titulo}
                    >
                      <span className="font-mono text-xs text-muted-foreground">
                        {def.n}.
                      </span>{' '}
                      {def.titulo}
                      <span className="text-muted-foreground"> ({cnt})</span>
                    </SelectItem>
                  )
                })}
              </SelectContent>
            </Select>
          </div>
        ) : null}

        {resumen && !loading ? (
          <span className="text-sm text-gray-600">
            Evaluados:{' '}
            <strong>{String(resumen.prestamos_evaluados ?? '-')}</strong>
            {' · '}
            Con alerta:{' '}
            <strong>{String(resumen.prestamos_con_alerta ?? '-')}</strong>
            {' · '}
            Mostrando:{' '}
            <strong>
              {rangoDesde}-{rangoHasta}
            </strong>{' '}
            de <strong>{totalListados}</strong>
            {resumen.fecha_referencia ? (
              <>
                {' · '}
                Fecha referencia (Caracas):{' '}
                <strong className="font-mono">
                  {String(resumen.fecha_referencia)}
                </strong>
              </>
            ) : null}
            {resumen.reglas_version ? (
              <>
                {' · '}
                Version reglas:{' '}
                <strong className="font-mono text-xs">
                  {String(resumen.reglas_version)}
                </strong>
              </>
            ) : null}
          </span>
        ) : null}
      </div>

      {panelKpis ? (
        <Card className="border-dashed border-blue-200 bg-blue-50/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-slate-800">
              Resumen solo KPIs (GET /prestamos/cartera/resumen)
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-2 text-sm text-slate-700">
            <p>
              Evaluados:{' '}
              <strong>{String(panelKpis.prestamos_evaluados ?? '-')}</strong>
              {' · '}
              Con alerta:{' '}
              <strong>{String(panelKpis.prestamos_con_alerta ?? '-')}</strong>
              {' · '}
              Version reglas:{' '}
              <strong className="font-mono text-xs">
                {String(panelKpis.reglas_version ?? '-')}
              </strong>
            </p>

            {metaUltimaCorridaPanel &&
            metaUltimaCorridaPanel.ultima_ejecucion_utc ? (
              <p className="text-xs text-slate-600">
                Ultima corrida guardada en BD (meta):{' '}
                <span className="font-mono">
                  {String(metaUltimaCorridaPanel.ultima_ejecucion_utc)}
                </span>
                {metaUltimaCorridaPanel.reglas_version ? (
                  <>
                    {' '}
                    · version persistida:{' '}
                    <span className="font-mono">
                      {String(metaUltimaCorridaPanel.reglas_version)}
                    </span>
                  </>
                ) : null}
              </p>
            ) : null}

            <div className="max-h-36 overflow-y-auto rounded border border-slate-200 bg-white p-2 font-mono text-xs">
              {(() => {
                const c = panelKpis.conteos_por_control
                if (!c || typeof c !== 'object' || Array.isArray(c)) {
                  return <span className="text-slate-500">Sin conteos</span>
                }
                const entries = Object.entries(c as Record<string, number>)
                if (entries.length === 0) {
                  return <span className="text-slate-500">Sin conteos</span>
                }
                return entries.map(([k, v]) => (
                  <div key={k}>
                    {k}: {String(v)}
                  </div>
                ))
              })()}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {hayAlertas && !loading && totalPages > 1 ? (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={page <= 1 || loading}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            <ChevronLeft className="mr-1 h-4 w-4" />
            Anterior
          </Button>
          <span className="text-sm text-gray-600">
            Pagina <strong>{page}</strong> de <strong>{totalPages}</strong> (
            {pageSize} por pagina)
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={page >= totalPages || loading}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          >
            Siguiente
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        </div>
      ) : null}

      {hayAlertas && !loading ? (
        <Card className="border-slate-200 bg-slate-50/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-slate-800">
              Controles numerados (mismo orden que la auditoria en servidor)
            </CardTitle>
          </CardHeader>

          <CardContent>
            <p className="mb-3 text-xs text-slate-600">
              Los conteos reflejan todos los prestamos con alerta bajo los
              filtros aplicados (no solo la pagina). Use el desplegable{' '}
              <strong>Filtrar por control</strong> para ver solo una regla en la
              tabla.
            </p>

            <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-800">
              {AUDITORIA_CARTERA_CONTROLES_CATALOGO.map(def => (
                <li key={def.codigo}>
                  <span className="font-medium">{def.titulo}</span>
                  {conteosPorControlCodigo[def.codigo] ? (
                    <span className="text-muted-foreground">
                      {' '}
                      - {conteosPorControlCodigo[def.codigo]} prestamo(s) con
                      esta alerta
                    </span>
                  ) : (
                    <span className="text-muted-foreground">
                      {' '}
                      - sin casos con filtros actuales
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      ) : null}

      {loading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-12 text-gray-500">
              <Loader2 className="mr-2 h-6 w-6 animate-spin" />
              Analizando cartera...
            </div>
          </CardContent>
        </Card>
      ) : !hayAlertas ? (
        <p className="py-6 text-center text-sm text-gray-600">
          No hay prestamos con controles en SI segun estos criterios. La cartera
          esta alineada con lo que aqui se revisa, o no hay prestamos
          APROBADO/LIQUIDADO que cumplan el filtro.
        </p>
      ) : (
        <Card>
          <CardContent className="pt-6">
            {visibleRows.length === 0 ? (
              <p className="py-8 text-center text-gray-600">
                Todos los controles visibles estan marcados con <strong>OK</strong>{' '}
                en base de datos para esta pagina, o no hay alertas. Pulse{' '}
                <strong>Recargar</strong> o <strong>Ejecutar ahora</strong> para
                reevaluar; si la alerta desaparecio en BD, no volvera a mostrarse.
              </p>
            ) : displayRows.length === 0 ? (
              <p className="py-8 text-center text-gray-600">
                {filtroControlCodigo && visibleRows.length > 0 ? (
                  <>
                    Ningun prestamo cumple el{' '}
                    <strong>control seleccionado</strong> en esta pagina (puede
                    estar oculto por <strong>OK</strong> en BD o no hay casos).
                    Pruebe <strong>Todos los controles</strong> u otra pagina.
                  </>
                ) : (
                  <>
                    Sin filas en esta pagina. Pruebe otra pagina o ajuste
                    filtros.
                  </>
                )}
              </p>
            ) : (
              <div className="space-y-8">
                {displayRows.map(row => (
                  <div
                    key={row.prestamo_id}
                    className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="text-lg font-semibold text-slate-900">
                          Prestamo #{row.prestamo_id}{' '}
                          <span className="text-slate-500">
                            · {row.nombres}
                          </span>
                        </div>

                        <div className="text-sm text-slate-600">
                          Cedula:{' '}
                          <span className="font-mono">{row.cedula}</span>
                          {' · '}
                          Estado:{' '}
                          <Badge variant="secondary">
                            {row.estado_prestamo}
                          </Badge>
                          {' · '}
                          <Link
                            className="text-blue-600 underline"
                            to={`/prestamos?prestamo_id=${row.prestamo_id}`}
                          >
                            Abrir prestamo
                          </Link>
                          {' · '}
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 text-blue-600 underline"
                            onClick={() => void abrirHistorialRevisiones(row.prestamo_id)}
                          >
                            <FileText className="h-3.5 w-3.5" />
                            Historial revisiones (BD)
                          </button>
                        </div>
                      </div>
                    </div>

                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[280px]">
                            Control (alerta SI)
                          </TableHead>

                          <TableHead>Detalle</TableHead>

                          <TableHead className="w-[100px] text-right">
                            Accion
                          </TableHead>
                        </TableRow>
                      </TableHeader>

                      <TableBody>
                        {row.controles.map(c => {
                          const numCtrl = numeroControlAuditoriaCartera(
                            c.codigo
                          )

                          return (
                            <TableRow key={`${row.prestamo_id}-${c.codigo}`}>
                              <TableCell className="align-top text-sm font-medium">
                                {numCtrl != null ? (
                                  <span
                                    className="mr-2 inline-flex h-5 min-w-[1.35rem] items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-1 font-mono text-xs text-slate-700"
                                    title={`Control ${numCtrl}`}
                                  >
                                    {numCtrl}
                                  </span>
                                ) : null}
                                {c.titulo}
                              </TableCell>

                              <TableCell className="align-top text-sm text-slate-700">
                                {c.detalle || '-'}
                              </TableCell>

                              <TableCell className="text-right align-top">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className="gap-1"
                                  aria-label={`Marcar como revisado en BD: ${c.titulo}`}
                                  onClick={() =>
                                    void marcarControlOk(row.prestamo_id, c.codigo)
                                  }
                                >
                                  <Check className="h-3.5 w-3.5" />
                                  OK
                                </Button>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog
        open={historialOpen}
        onOpenChange={open => {
          setHistorialOpen(open)
          if (!open) {
            setHistorialPid(null)
            setHistorialRows([])
          }
        }}
      >
        <DialogContent className="max-h-[85vh] max-w-lg overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              Historial revisiones cartera
              {historialPid != null ? ` · Prestamo #${historialPid}` : ''}
            </DialogTitle>
          </DialogHeader>

          {historialLoading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-slate-600">
              <Loader2 className="h-5 w-5 animate-spin" />
              Cargando...
            </div>
          ) : historialRows.length === 0 ? (
            <p className="py-4 text-sm text-slate-600">
              Sin registros en bitacora para este prestamo.
            </p>
          ) : (
            <ul className="space-y-3 text-sm">
              {historialRows.map(h => (
                <li
                  key={h.id}
                  className="rounded-md border border-slate-200 bg-slate-50/80 p-3"
                >
                  <div className="font-mono text-xs text-slate-500">
                    {h.creado_en}
                  </div>
                  <div>
                    <strong>{h.codigo_control}</strong> · {h.tipo}
                  </div>
                  <div className="text-slate-600">
                    {h.usuario_email || `usuario_id=${h.usuario_id}`}
                  </div>
                  {h.nota ? (
                    <div className="mt-1 text-slate-700">Nota: {h.nota}</div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
