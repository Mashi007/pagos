import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  BarChart3,
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Filter,
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
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'

import { Textarea } from '../ui/textarea'

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

const NOTA_EXCEPCION_MIN_LEN = 15

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
  /** Legacy; UI ya no filtra por control (se persiste vacio). */
  filtroControlCodigo: string
  ocultosKeys: string[]
  /** true = ver tambien excepciones ya aceptadas (motor completo). */
  vista_motor_crudo?: boolean
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
      resumen: (c.resumen && typeof c.resumen === 'object'
        ? c.resumen
        : {}) as Record<string, unknown>,
      filtrosApi: {
        cedula:
          typeof c.filtrosApi.cedula === 'string' ? c.filtrosApi.cedula : '',
        prestamo_id: c.filtrosApi.prestamo_id,
      },
      page: typeof c.page === 'number' && c.page >= 1 ? c.page : 1,
      filtroControlCodigo:
        typeof c.filtroControlCodigo === 'string' ? c.filtroControlCodigo : '',
      ocultosKeys: Array.isArray(c.ocultosKeys) ? c.ocultosKeys : [],
      vista_motor_crudo: c.vista_motor_crudo === true,
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
  vista_motor_crudo: boolean
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
      vista_motor_crudo: payload.vista_motor_crudo,
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

  const [vistaMotorCrudo, setVistaMotorCrudo] = useState(
    () => boot?.vista_motor_crudo === true
  )

  const [loadingKpis, setLoadingKpis] = useState(false)

  const [okDialogOpen, setOkDialogOpen] = useState(false)

  const [okTarget, setOkTarget] = useState<{
    prestamoId: number
    codigo: string
    titulo: string
  } | null>(null)

  const [okNota, setOkNota] = useState('')

  const [okSubmitting, setOkSubmitting] = useState(false)

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
          excluir_marcar_ok: !vistaMotorCrudo,
        })

        const nextItems = cheq.items || []
        const nextResumen = (cheq.resumen as Record<string, unknown>) || {}

        setItems(nextItems)
        setResumen(nextResumen)

        const exclSrv = nextResumen.excluye_marcar_ok === true
        const ocultos = exclSrv
          ? new Set<string>()
          : await syncOcultosConItems(nextItems)
        if (exclSrv) {
          setOcultosKeys(new Set())
        }
        saveCarteraSessionCache({
          items: nextItems,
          resumen: nextResumen,
          filtrosApi,
          page,
          filtroControlCodigo: '',
          ocultosKeys: [...ocultos],
          vista_motor_crudo: vistaMotorCrudo,
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
    [page, pageSize, filtrosApi, vistaMotorCrudo, syncOcultosConItems]
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
        excluir_marcar_ok: !vistaMotorCrudo,
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
        excluir_marcar_ok: !vistaMotorCrudo,
      })
      const header =
        'prestamo_id,cedula,nombres,estado_prestamo,codigo_control,titulo_control,detalle'
      const lines = [`\ufeff${header}`]
      for (const row of cheq.items || []) {
        for (const c of row.controles) {
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

  const servidorExcluyeMarcarOk = resumen?.excluye_marcar_ok === true

  const visibleRows = useMemo(() => {
    return items
      .map(row => ({
        ...row,
        controles: servidorExcluyeMarcarOk
          ? row.controles
          : row.controles.filter(
              c =>
                !ocultosKeys.has(controlDismissKey(row.prestamo_id, c.codigo))
            ),
      }))
      .filter(row => row.controles.length > 0)
  }, [items, ocultosKeys, servidorExcluyeMarcarOk])

  const conteosPorControlCodigo = useMemo(() => {
    const raw = resumen?.conteos_por_control
    if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
      return raw as Record<string, number>
    }
    return {}
  }, [resumen])

  const abrirDialogoExcepcion = (
    prestamoId: number,
    codigo: string,
    titulo: string
  ) => {
    setOkTarget({ prestamoId, codigo, titulo })
    setOkNota('')
    setOkDialogOpen(true)
  }

  const confirmarExcepcionOk = async () => {
    if (!okTarget) return
    const nota = okNota.trim()
    if (nota.length < NOTA_EXCEPCION_MIN_LEN) {
      toast.error(
        `Indique motivo de la excepcion (minimo ${NOTA_EXCEPCION_MIN_LEN} caracteres), ej. acuerdo con cliente o referencia interna.`
      )
      return
    }
    try {
      setOkSubmitting(true)
      await auditoriaService.crearRevisionCartera({
        prestamo_id: okTarget.prestamoId,
        codigo_control: okTarget.codigo,
        nota,
      })
      setOkDialogOpen(false)
      setOkTarget(null)
      setOkNota('')
      toast.success(
        'Excepcion guardada en bitacora. Deja de contar en la cola operativa (vista normal).'
      )
      void fetchLista({ silent: true })
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al registrar revision'
      toast.error(msg)
    } finally {
      setOkSubmitting(false)
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
      <Card className="rounded-lg border-amber-200/90 bg-amber-50/70 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-amber-950">
            Excepciones operativas (acuerdos de negocio)
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-3 text-sm text-amber-950/90">
          <p>
            En la vista normal, un caso <strong>solo</strong> deja de mostrarse
            como alarma pendiente si (1) se <strong>acepta excepcion</strong>{' '}
            (bitacora con nota obligatoria) o (2) se corrige la{' '}
            <strong>causa raiz</strong> en datos y el motor ya no marca{' '}
            <strong>SI</strong>. No hay otro mecanismo de ocultacion. Si el
            motor sigue en SI y no hay aceptacion, el caso sigue en cola.
            Trazabilidad en <strong>Historial revisiones</strong>; aceptar no
            altera el calculo objetivo del motor.
          </p>

          <label className="flex cursor-pointer items-start gap-2.5">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 shrink-0 rounded border-amber-300"
              checked={vistaMotorCrudo}
              onChange={e => setVistaMotorCrudo(e.target.checked)}
            />

            <span>
              <strong>Ver motor completo</strong>: mostrar tambien alertas ya
              cubiertas por excepcion (misma data que el informe crudo;
              desactiva el filtro{' '}
              <span className="font-mono text-xs">excluir_marcar_ok</span> en la
              API).
            </span>
          </label>
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-slate-200/90 shadow-sm">
        <CardHeader className="space-y-1 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white py-3 sm:py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-800 text-white">
              <Filter className="h-4 w-4" aria-hidden />
            </div>
            <div>
              <CardTitle className="text-base text-slate-900">
                Consulta y controles de cartera
              </CardTitle>
              <p className="text-xs font-normal text-muted-foreground">
                Totales por control: use{' '}
                <strong className="font-medium text-slate-700">
                  Solo KPIs
                </strong>{' '}
                (panel inferior) con los mismos filtros cedula/prestamo.{' '}
                <strong className="font-medium text-slate-700">
                  Ver motor completo
                </strong>{' '}
                incluye excepciones MARCAR_OK en la API.
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-wrap items-center gap-2">
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

            <Button
              size="sm"
              onClick={ejecutarAhora}
              disabled={running || loading}
              title="Recalcula controles desde la BD (motor objetivo) y guarda KPIs en configuracion. Igual criterio que el job 03:00; sin usar MARCAR_OK en esos totales."
            >
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
          </div>

          <p className="text-xs text-muted-foreground">
            La lista se guarda en la sesion del navegador; los chequeos son en
            vivo contra la BD. El job 03:00 actualiza la meta en configuracion,
            no sustituye una recarga manual si hubo cambios despues.
          </p>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-12 lg:items-end">
            <div className="flex flex-col gap-1.5 sm:col-span-1 lg:col-span-2">
              <Label
                htmlFor="auditoria-cedula-filtro"
                className="text-xs font-medium text-slate-700"
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
                className="h-9 border-slate-200"
              />
            </div>

            <div className="flex flex-col gap-1.5 sm:col-span-1 lg:col-span-2">
              <Label
                htmlFor="auditoria-prestamo-filtro"
                className="text-xs font-medium text-slate-700"
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
                className="h-9 border-slate-200"
              />
            </div>

            <div className="flex flex-wrap items-end gap-2 sm:col-span-2 lg:col-span-3">
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
                title="Misma logica que la lista pero sin devolver prestamos (GET .../cartera/resumen)."
              >
                {loadingKpis ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <BarChart3 className="mr-2 h-4 w-4" />
                )}
                Solo KPIs
              </Button>
            </div>
          </div>

          {resumen && !loading ? (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-slate-100 bg-slate-50/80 px-3 py-2 text-sm text-slate-700">
              <span>
                Evaluados:{' '}
                <strong className="text-slate-900">
                  {String(resumen.prestamos_evaluados ?? '-')}
                </strong>
              </span>
              <span className="text-slate-300" aria-hidden>
                |
              </span>
              <span>
                Con alerta:{' '}
                <strong className="text-slate-900">
                  {String(resumen.prestamos_con_alerta ?? '-')}
                </strong>
              </span>
              <span className="text-slate-300" aria-hidden>
                |
              </span>
              <span>
                Mostrando{' '}
                <strong className="text-slate-900">
                  {rangoDesde}-{rangoHasta}
                </strong>{' '}
                de <strong className="text-slate-900">{totalListados}</strong>
              </span>
              {resumen.fecha_referencia ? (
                <>
                  <span className="text-slate-300" aria-hidden>
                    |
                  </span>
                  <span className="font-mono text-xs">
                    Ref. {String(resumen.fecha_referencia)}
                  </span>
                </>
              ) : null}
              {resumen.reglas_version ? (
                <>
                  <span className="text-slate-300" aria-hidden>
                    |
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {String(resumen.reglas_version)}
                  </span>
                </>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

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

            <div className="max-h-40 overflow-y-auto rounded-md border border-slate-200 bg-white p-2 text-xs">
              {(() => {
                const c = panelKpis.conteos_por_control
                if (!c || typeof c !== 'object' || Array.isArray(c)) {
                  return <span className="text-slate-500">Sin conteos</span>
                }
                const map = c as Record<string, number>
                return (
                  <ul className="space-y-1 text-slate-700">
                    {AUDITORIA_CARTERA_CONTROLES_CATALOGO.map(def => {
                      const v = map[def.codigo] ?? 0
                      return (
                        <li key={def.codigo} className="flex gap-2">
                          <span className="shrink-0 font-mono text-muted-foreground">
                            {def.n}.
                          </span>
                          <span className="min-w-0 flex-1">{def.titulo}</span>
                          <span className="shrink-0 font-medium tabular-nums text-slate-900">
                            {v}
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                )
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
                En esta pagina no quedan filas (paginacion o casos fuera de cola
                por aceptacion o motor ya en NO). Pulse{' '}
                <strong>Recargar</strong> o <strong>Ver motor completo</strong>{' '}
                para revisar el motor sin filtro operativo.
              </p>
            ) : (
              <div className="space-y-8">
                {visibleRows.map(row => (
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
                            onClick={() =>
                              void abrirHistorialRevisiones(row.prestamo_id)
                            }
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
                                  aria-label={`Aceptar excepcion para control: ${c.titulo}`}
                                  onClick={() =>
                                    abrirDialogoExcepcion(
                                      row.prestamo_id,
                                      c.codigo,
                                      c.titulo
                                    )
                                  }
                                >
                                  <Check className="h-3.5 w-3.5" />
                                  Aceptar excepcion
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
        open={okDialogOpen}
        onOpenChange={open => {
          setOkDialogOpen(open)
          if (!open) {
            setOkTarget(null)
            setOkNota('')
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Registrar excepcion aceptada</DialogTitle>
          </DialogHeader>

          {okTarget ? (
            <p className="text-sm text-slate-600">
              Prestamo <strong>#{okTarget.prestamoId}</strong> ·{' '}
              <strong>{okTarget.titulo}</strong>
            </p>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="auditoria-ok-nota">
              Motivo, acuerdo con cliente o referencia interna (minimo{' '}
              {NOTA_EXCEPCION_MIN_LEN} caracteres)
            </Label>

            <Textarea
              id="auditoria-ok-nota"
              value={okNota}
              onChange={e => setOkNota(e.target.value)}
              rows={4}
              placeholder="Ej. Acuerdo de pago firmado 12/03/2026; cliente J.Perez; no reaplicar cuota 5..."
              className="resize-y"
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOkDialogOpen(false)}
              disabled={okSubmitting}
            >
              Cancelar
            </Button>

            <Button
              type="button"
              onClick={() => void confirmarExcepcionOk()}
              disabled={okSubmitting}
            >
              {okSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Guardar en bitacora'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
