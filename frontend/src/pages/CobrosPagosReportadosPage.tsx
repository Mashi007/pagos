/**









 * Listado de pagos reportados (módulo Cobros). Filtros, tabla, acciones Ver detalle / Aprobar / Rechazar.
 * Vista por defecto: sin aprobados/importados/rechazados ni exportados al Excel; con checkbox se incluyen exportados para seguir gestionando en Cobranzas. El Excel solo vuelca fallas de validación.









 */

import React, { useState, useEffect } from 'react'

import { useNavigate } from 'react-router-dom'

import { useQueryClient } from '@tanstack/react-query'

import { invalidateListasNotificacionesMora } from '../constants/queryKeys'

import {
  listPagosReportadosConKpis,
  cambiarEstadoPago,
  openComprobanteInNewTab,
  eliminarPagoReportado,
  exportarPagosReportadosAprobadosExcel,
  getTendenciaFallosGemini,
  type PagoReportadoItem,
  type ListPagosReportadosResponse,
  type PagosReportadosKpis,
  type CambiarEstadoPagoResponse,
  type TendenciaFalloGeminiPunto,
  type TendenciaFallosGeminiResponse,
  etiquetaCanalReportado,
} from '../services/cobrosService'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Badge } from '../components/ui/badge'

import toast from 'react-hot-toast'

/** Toast según envío real del correo de rechazo (API devuelve mensaje + flags). */
function toastAfterRechazoCobros(data: CambiarEstadoPagoResponse) {
  const msg = data.mensaje ?? 'Estado actualizado a rechazado.'
  if (data.rechazo_correo_enviado === true) {
    toast.success(msg)
  } else if (data.rechazo_correo_enviado === false) {
    const err = data.rechazo_correo_error
    toast.error(
      err ? `${msg} (${err.length > 160 ? `${err.slice(0, 160)}…` : err})` : msg
    )
  } else {
    toast(msg, { duration: 7000 })
  }
}

import {
  Loader2,
  FileText,
  Settings,
  Clock,
  Search,
  CheckCircle,
  XCircle,
  Trash2,
  AlertCircle,
  AlertTriangle,
  Edit,
  Mail,
  Eye,
  TrendingDown,
} from 'lucide-react'

import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

import { PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

import { TEXTO_AVISO_PAGOS_REPORTADOS_ADMIN } from '../constants/reporteCobrosDocumento'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog'

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover'

const MENSAJE_RECHAZO_POR_DEFECTO = `Buenas tardes



















La imagen no se aprecia detalles, agradezco enviar una imagen sin recortar a cobranza@rapicreditca.com



















Gracias`

const ESTADO_CONFIG: Record<
  string,
  {
    label: string
    short: string
    variant: 'default' | 'secondary' | 'destructive' | 'outline'
    Icon: typeof Clock
  }
> = {
  pendiente: {
    label: 'Pendiente',
    short: 'Pend.',
    variant: 'secondary',
    Icon: Clock,
  },

  en_revision: {
    label: 'En revisión (manual)',
    short: 'Revisión',
    variant: 'outline',
    Icon: Search,
  },

  aprobado: {
    label: 'Aprobado',
    short: 'Aprobado',
    variant: 'default',
    Icon: CheckCircle,
  },

  importado: {
    label: 'Importado a Pagos',
    short: 'Import.',
    variant: 'default',
    Icon: CheckCircle,
  },

  rechazado: {
    label: 'Rechazado',
    short: 'Rechazado',
    variant: 'destructive',
    Icon: XCircle,
  },
}

const normalizeEstadoValue = (value: string) =>
  String(value ?? '')
    .normalize('NFD')

    .replace(/[\u0300-\u036f]/g, '')

    .trim()

    .replace(/\s+/g, '_')

    .toLowerCase()

export default function CobrosPagosReportadosPage() {
  const navigate = useNavigate()

  const queryClient = useQueryClient()

  const [data, setData] = useState<ListPagosReportadosResponse | null>(null)

  const [loading, setLoading] = useState(true)

  const [page, setPage] = useState(1)

  const [estado, setEstado] = useState<string>('')

  const [fechaDesde, setFechaDesde] = useState('')

  const [fechaHasta, setFechaHasta] = useState('')

  const [cedula, setCedula] = useState('')

  const [institucion, setInstitucion] = useState('')

  const [incluirExportados, setIncluirExportados] = useState(false)

  const [changingEstadoId, setChangingEstadoId] = useState<number | null>(null)

  const [viewingComprobanteId, setViewingComprobanteId] = useState<
    number | null
  >(null)

  const [deletingId, setDeletingId] = useState<number | null>(null)

  const [rechazarModal, setRechazarModal] = useState<{
    open: boolean
    row: PagoReportadoItem | null
  }>({ open: false, row: null })

  const [motivoRechazo, setMotivoRechazo] = useState('')

  const [descargandoExcelAprobados, setDescargandoExcelAprobados] =
    useState(false)

  const [kpis, setKpis] = useState<PagosReportadosKpis | null>(null)

  const [diasTendencia, setDiasTendencia] = useState(90)

  const [tendencia, setTendencia] =
    useState<TendenciaFallosGeminiResponse | null>(null)

  const [tendenciaLoading, setTendenciaLoading] = useState(true)

  const load = async (overrides?: { estado?: string; page?: number }) => {
    const effectiveEstado =
      overrides?.estado !== undefined ? overrides.estado : estado

    const effectivePage = overrides?.page !== undefined ? overrides.page : page

    if (overrides) {
      if (overrides.estado !== undefined) setEstado(overrides.estado)

      if (overrides.page !== undefined) setPage(overrides.page)
    }

    setLoading(true)

    try {
      const filterParams = {
        fecha_desde: fechaDesde || undefined,

        fecha_hasta: fechaHasta || undefined,

        cedula: cedula.trim() || undefined,

        institucion: institucion.trim() || undefined,
      }

      const res = await listPagosReportadosConKpis({
        page: effectivePage,

        per_page: 20,

        estado: effectiveEstado || undefined,

        incluir_exportados: incluirExportados,

        ...filterParams,
      })

      setData(res)

      setKpis(res.kpis)
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [page, incluirExportados])

  useEffect(() => {
    let cancelled = false

    ;(async () => {
      setTendenciaLoading(true)

      try {
        const r = await getTendenciaFallosGemini(diasTendencia)

        if (!cancelled) {
          setTendencia(r)
        }
      } catch {
        if (!cancelled) {
          setTendencia(null)

          toast.error('No se pudo cargar la tendencia de fallos (NO).')
        }
      } finally {
        if (!cancelled) {
          setTendenciaLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [diasTendencia])

  const handleKpiClick = (estadoKey: string) => {
    load({ estado: estadoKey, page: 1 })
  }

  const handleCambiarEstado = async (
    id: number,
    nuevoEstado: string,
    motivo?: string
  ) => {
    setChangingEstadoId(id)

    try {
      const data = await cambiarEstadoPago(id, nuevoEstado, motivo)

      if (nuevoEstado === 'rechazado') {
        toastAfterRechazoCobros(data)
      } else {
        toast.success(data.mensaje || 'Estado actualizado.')
      }

      // Al aprobar: el backend crea el pago en pagos, lo concilia y aplica a cuotas en cascada.
      // Invalidar queries para que prestamos, cuotas y notificaciones de mora se actualicen.
      if (nuevoEstado === 'aprobado') {
        queryClient.invalidateQueries({ queryKey: ['pagos'] })
        queryClient.invalidateQueries({ queryKey: ['cuotas-prestamo'] })
        queryClient.invalidateQueries({ queryKey: ['prestamos'] })
        void invalidateListasNotificacionesMora(queryClient)
      }

      // Quitar la fila al instante si la vista actual no lista aprobados (coincide con el API por defecto).
      if (nuevoEstado === 'aprobado' && estado !== 'aprobado') {
        setData(prev => {
          if (!prev) return prev

          return {
            ...prev,
            items: prev.items.filter(r => r.id !== id),
            total: Math.max(0, prev.total - 1),
          }
        })
      }

      await load()

      if (nuevoEstado === 'rechazado') {
        setRechazarModal({ open: false, row: null })

        setMotivoRechazo('')
      }
    } catch (e: any) {
      const detail =
        e?.response?.data?.detail ||
        e?.response?.data?.message ||
        e?.message ||
        'Error al actualizar.'
      toast.error(detail)
    } finally {
      setChangingEstadoId(null)
    }
  }

  const handleAbrirModalRechazo = (row: PagoReportadoItem) => {
    setMotivoRechazo(MENSAJE_RECHAZO_POR_DEFECTO)

    const rowToOpen = { ...row }

    setTimeout(() => setRechazarModal({ open: true, row: rowToOpen }), 0)
  }

  const handleConfirmarRechazo = () => {
    if (!rechazarModal.row || !motivoRechazo.trim()) {
      toast.error('El motivo de rechazo es obligatorio.')

      return
    }

    handleCambiarEstado(rechazarModal.row.id, 'rechazado', motivoRechazo.trim())
  }

  const handleEliminar = async (id: number, ref: string) => {
    if (
      !window.confirm(
        'Eliminar el pago reportado ' +
          ref +
          '? Esta acción no se puede deshacer.'
      )
    )
      return

    setDeletingId(id)

    try {
      await eliminarPagoReportado(id)

      toast.success('Pago reportado eliminado.')

      await load()
    } catch (e: any) {
      toast.error(e?.message || 'Error al eliminar.')
    } finally {
      setDeletingId(null)
    }
  }

  const handleVerComprobante = async (id: number) => {
    setViewingComprobanteId(id)

    try {
      await openComprobanteInNewTab(id)
    } catch (e: any) {
      toast.error(e?.message || 'No se pudo abrir el comprobante.')
    } finally {
      setViewingComprobanteId(null)
    }
  }

  const handleDescargarExcelAprobados = async () => {
    // Servidor: pendiente/en revisión que no validan, no exportados; cédula/institución; sin fechas.
    // El Excel y el marcado en BD son atómicos (un solo request).
    setDescargandoExcelAprobados(true)

    try {
      const stats = await exportarPagosReportadosAprobadosExcel({
        cedula: cedula.trim() || undefined,
        institucion: institucion.trim() || undefined,
      })

      toast.success(
        'Excel con ' +
          String(stats.totalFilas) +
          ' fila(s) sin validar. Nuevos exportados: ' +
          String(stats.marcados) +
          (stats.yaExportados > 0
            ? ' (ya constaban ' + String(stats.yaExportados) + ')'
            : '') +
          '. Cola temporal: quitados ' +
          String(stats.quitadosCola) +
          ' registro(s).'
      )

      await load({ page: 1 })
    } catch (e: any) {
      toast.error(e?.message || 'No se pudo exportar el Excel de corrección.')
    } finally {
      setDescargandoExcelAprobados(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <h1 className="text-2xl font-semibold">Pagos Reportados</h1>

          <p className="max-w-3xl text-xs leading-relaxed text-slate-600">
            {TEXTO_AVISO_PAGOS_REPORTADOS_ADMIN}
          </p>
        </div>

        <a
          href={
            (typeof window !== 'undefined' ? window.location.origin : '') +
            (import.meta.env.BASE_URL || '/').replace(/\/$/, '') +
            '/' +
            PUBLIC_REPORTE_PAGO_PATH
          }
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-sm text-blue-600 hover:underline"
        >
          Link al formulario público
        </a>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtros</CardTitle>
        </CardHeader>

        <CardContent className="flex flex-wrap gap-4">
          <div className="flex min-w-[min(100%,280px)] flex-col gap-1">
            <select
              className="rounded-md border px-3 py-2"
              value={estado}
              onChange={e => setEstado(e.target.value)}
              aria-label="Filtrar por estado del reporte"
            >
              <option value="">
                Por gestionar (excluye aprobados, importados y rechazados)
              </option>

              <option value="pendiente">Pendiente</option>

              <option value="en_revision">En revisión</option>

              <option value="aprobado">
                Aprobado (pendientes de exportar)
              </option>

              <option value="rechazado">Rechazado</option>

              <option value="importado">Importado a Pagos</option>
            </select>

            <p className="text-xs text-muted-foreground">
              Vista por defecto: cola sin filas ya exportadas al Excel de
              corrección; puede marcar &quot;Incluir ya exportados&quot; para
              seguir resolviendo desde esta pantalla (aprobar, editar,
              rechazar). &quot;Excel no validan&quot; solo vuelca quienes
              fallan validadores. Los rechazados no se listan aquí salvo filtro.
            </p>
          </div>

          <Input
            type="date"
            placeholder="Fecha desde"
            value={fechaDesde}
            onChange={e => setFechaDesde(e.target.value)}
            className="w-40"
          />

          <Input
            type="date"
            placeholder="Fecha hasta"
            value={fechaHasta}
            onChange={e => setFechaHasta(e.target.value)}
            className="w-40"
          />

          <Input
            placeholder="Cédula"
            value={cedula}
            onChange={e => setCedula(e.target.value)}
            className="w-40"
          />

          <Input
            placeholder="Institución"
            value={institucion}
            onChange={e => setInstitucion(e.target.value)}
            className="w-48"
          />

          <label
            htmlFor="cobros-incluir-exportados"
            className="flex max-w-xs cursor-pointer items-start gap-2 text-xs text-muted-foreground"
          >
            <input
              id="cobros-incluir-exportados"
              type="checkbox"
              className="mt-0.5 shrink-0 rounded border-input"
              checked={incluirExportados}
              onChange={e => {
                setIncluirExportados(e.target.checked)
                setPage(1)
              }}
            />
            <span>
              Incluir ya exportados a Excel: sigue viendo esas filas para
              aprobar, editar o rechazar desde Cobranzas con normalidad.
            </span>
          </label>

          <Button onClick={() => load()}>Buscar</Button>

          <Button
            variant="outline"
            onClick={handleDescargarExcelAprobados}
            disabled={descargandoExcelAprobados}
            title="Solo filas con falla de validadores. Al descargar van al Excel y salen de la cola por defecto; marque Incluir ya exportados para seguir gestionándolas aquí. Sin fechas; sí cédula/institución si las llenaste."
          >
            {descargandoExcelAprobados ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Excel no validan (carga masiva)
          </Button>
        </CardContent>
      </Card>

      {kpis != null && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleKpiClick('')}
            title="Cola operativa: pendiente y en revisión no exportados al Excel de corrección (sin aprobados, importados ni rechazados en la vista por defecto)."
            className={
              'min-w-28 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
              (estado === ''
                ? 'border-primary bg-primary/10 font-semibold'
                : 'border-muted hover:bg-muted/50')
            }
          >
            <span className="block text-xs uppercase tracking-wide text-muted-foreground">
              Por gestionar
            </span>

            <span className="text-2xl font-bold">
              {kpis.pendiente + kpis.en_revision}
            </span>
          </button>

          {(['pendiente', 'en_revision', 'aprobado', 'rechazado'] as const).map(
            key => {
              const cfg = ESTADO_CONFIG[key]

              const Icon = cfg.Icon

              const selected = estado === key

              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleKpiClick(key)}
                  className={
                    'flex min-w-28 flex-col gap-0.5 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
                    (selected
                      ? 'border-primary bg-primary/10 font-semibold'
                      : 'border-muted hover:bg-muted/50')
                  }
                >
                  <span className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />

                    {cfg.label}
                  </span>

                  <span className="text-2xl font-bold">{kpis[key]}</span>
                </button>
              )
            }
          )}
        </div>
      )}

      <Card className="overflow-hidden border-2 border-slate-200 shadow-lg">
        <CardHeader className="border-b border-rose-100 bg-gradient-to-r from-rose-50 via-white to-slate-50 pb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2 text-lg font-bold text-slate-800 sm:text-xl">
              <TrendingDown className="h-6 w-6 shrink-0 text-rose-600" />
              Tendencia: fallos verificacion (NO) por dia
            </CardTitle>

            <div className="flex flex-wrap items-center gap-2">
              <label
                htmlFor="cobros-tendencia-dias"
                className="text-xs text-slate-600"
              >
                Periodo
              </label>

              <select
                id="cobros-tendencia-dias"
                className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
                value={diasTendencia}
                onChange={e => setDiasTendencia(Number(e.target.value))}
                aria-label="Dias de la tendencia"
              >
                <option value={30}>Ultimos 30 dias</option>

                <option value={60}>Ultimos 60 dias</option>

                <option value={90}>Ultimos 90 dias</option>

                <option value={180}>Ultimos 180 dias</option>
              </select>
            </div>
          </div>

          <p className="mt-2 text-xs leading-relaxed text-slate-600">
            Cada punto es un dia calendario (
            {tendencia?.zona ?? 'America/Caracas'}
            ): cantidad de reportes donde la comprobacion automatica respondio{' '}
            <strong>NO</strong> (
            <code className="rounded bg-slate-100 px-1">
              gemini_coincide_exacto
            </code>{' '}
            = false). La zona sombreada muestra cuantos reportes tuvieron
            respuesta true/false ese dia (contexto). Si la linea baja, hay menos
            fallos NO por dia.
          </p>
        </CardHeader>

        <CardContent className="p-4 pt-5 sm:p-6">
          {tendenciaLoading ? (
            <div className="flex h-[320px] items-center justify-center gap-2 text-slate-500">
              <Loader2 className="h-8 w-8 animate-spin" />

              <span>Cargando serie...</span>
            </div>
          ) : tendencia?.puntos?.length ? (
            <ResponsiveContainer width="100%" height={360}>
              <ComposedChart
                data={tendencia.puntos}
                margin={{ top: 8, right: 12, left: 4, bottom: 8 }}
              >
                <defs>
                  <linearGradient
                    id="cobrosGeminiVerifFill"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="0%" stopColor="#64748b" stopOpacity={0.22} />

                    <stop
                      offset="100%"
                      stopColor="#64748b"
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                </defs>

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#e2e8f0"
                  vertical={false}
                />

                <XAxis
                  dataKey="fecha"
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#cbd5e1' }}
                  tickFormatter={(v: string) => {
                    const [y, m, d] = v.split('-')

                    return d && m ? `${d}/${m}` : v
                  }}
                  interval={
                    tendencia.puntos.length > 20
                      ? Math.floor(tendencia.puntos.length / 12)
                      : 0
                  }
                />

                <YAxis
                  yAxisId="fallos"
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: '#be123c' }}
                  tickLine={false}
                  axisLine={{ stroke: '#fecdd3' }}
                  width={40}
                  label={{
                    value: 'Fallos (NO)',
                    angle: -90,
                    position: 'insideLeft',
                    style: { fill: '#9f1239', fontSize: 11 },
                  }}
                />

                <YAxis
                  yAxisId="vol"
                  orientation="right"
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: '#475569' }}
                  tickLine={false}
                  axisLine={{ stroke: '#cbd5e1' }}
                  width={44}
                  label={{
                    value: 'Verificados',
                    angle: 90,
                    position: 'insideRight',
                    style: { fill: '#475569', fontSize: 11 },
                  }}
                />

                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) {
                      return null
                    }

                    const row = payload[0].payload as TendenciaFalloGeminiPunto

                    const fechaFmt = new Date(
                      `${row.fecha}T12:00:00`
                    ).toLocaleDateString('es-VE', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })

                    return (
                      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-xl">
                        <p className="text-xs font-medium text-slate-500">
                          {fechaFmt}
                        </p>

                        <p className="mt-1.5 text-sm text-rose-600">
                          Fallos (NO):{' '}
                          <span className="font-bold tabular-nums">
                            {row.fallos_no}
                          </span>
                        </p>

                        <p className="text-sm text-slate-700">
                          Verificados (Gemini):{' '}
                          <span className="font-semibold tabular-nums">
                            {row.verificados_gemini}
                          </span>
                        </p>

                        {row.pct_fallo != null ? (
                          <p className="mt-1 text-xs text-slate-500">
                            % fallo del dia:{' '}
                            <span className="font-medium tabular-nums">
                              {row.pct_fallo}%
                            </span>
                          </p>
                        ) : null}
                      </div>
                    )
                  }}
                />

                <Legend wrapperStyle={{ paddingTop: 16 }} />

                <Area
                  yAxisId="vol"
                  type="monotone"
                  dataKey="verificados_gemini"
                  name="Verificados (Gemini)"
                  stroke="#64748b"
                  strokeWidth={1}
                  fill="url(#cobrosGeminiVerifFill)"
                  dot={false}
                  activeDot={{ r: 4 }}
                />

                <Line
                  yAxisId="fallos"
                  type="monotone"
                  dataKey="fallos_no"
                  name="Fallos (NO)"
                  stroke="#be123c"
                  strokeWidth={2.5}
                  dot={{ r: 2, strokeWidth: 1, fill: '#fff' }}
                  activeDot={{ r: 6, strokeWidth: 2 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[200px] items-center justify-center text-slate-500">
              Sin datos de tendencia.
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p>Cargando...</p>
          ) : !data?.items?.length ? (
            <p className="text-gray-500">No hay registros.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[1180px] table-fixed text-sm">
                <colgroup>
                  <col style={{ width: '10%' }} />

                  <col style={{ width: '8%' }} />

                  <col style={{ width: '9%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '9%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '8%' }} />

                  <col style={{ width: '9%' }} />

                  <col style={{ width: '6%' }} />

                  <col style={{ width: '13%' }} />
                </colgroup>

                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-3 py-3 text-left font-semibold">
                      Nombre
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Cédula
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">Banco</th>

                    <th className="px-3 py-3 text-right font-semibold">
                      Monto
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Fecha pago
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Nº operación
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Fecha reporte
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Origen
                    </th>

                    <th className="px-3 py-3 text-center font-semibold">
                      Comprobante
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Observación
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Estado
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Acciones
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {data.items.map((row: PagoReportadoItem) => (
                    <tr
                      key={row.id}
                      className="border-b transition-colors hover:bg-muted/20"
                    >
                      <td className="min-w-0 px-3 py-3 align-top">
                        <span
                          className="block truncate"
                          title={
                            String(row.nombres) + ' ' + String(row.apellidos)
                          }
                        >
                          {row.nombres} {row.apellidos}
                        </span>
                      </td>

                      <td
                        className={
                          'whitespace-nowrap px-3 py-3 align-top ' +
                          (/c[eé]dula/i.test(row.observacion || '')
                            ? 'bg-destructive/10 font-medium text-destructive'
                            : '')
                        }
                        title={
                          /c[eé]dula/i.test(row.observacion || '')
                            ? 'Observación: ' + (row.observacion || '')
                            : undefined
                        }
                      >
                        {/c[eé]dula/i.test(row.observacion || '') && (
                          <AlertCircle
                            className="mr-1 inline-block h-4 w-4 align-middle"
                            aria-hidden
                          />
                        )}

                        {row.cedula_display}
                      </td>

                      <td className="min-w-0 px-3 py-3 align-top">
                        <span
                          className="block truncate"
                          title={row.institucion_financiera}
                        >
                          {row.institucion_financiera}
                        </span>
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 text-right align-top">
                        <span>
                          {row.monto} {row.moneda}
                        </span>
                        {row.moneda === 'BS' && row.equivalente_usd != null && (
                          <span
                            className="mt-0.5 block text-xs text-emerald-700"
                            title={
                              row.tasa_cambio_bs_usd != null
                                ? `Tasa: ${row.tasa_cambio_bs_usd.toLocaleString('es-VE')} Bs/USD`
                                : 'Equivalente en USD'
                            }
                          >
                            {'≈ '}
                            {row.equivalente_usd.toLocaleString('es-VE', {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}{' '}
                            USD
                          </span>
                        )}
                        {row.moneda === 'BS' && row.equivalente_usd == null && (
                          <span
                            className="mt-0.5 block text-xs text-amber-600"
                            title="No hay tasa registrada para esta fecha. Registre la tasa en Pagos antes de aprobar."
                          >
                            Sin tasa
                          </span>
                        )}
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 align-top">
                        {row.fecha_pago}
                      </td>

                      <td
                        className={
                          'min-w-0 px-3 py-3 align-top ' +
                          (/DUPLICADO/i.test(row.observacion || '')
                            ? 'bg-amber-500/15 font-medium text-amber-900 dark:text-amber-100'
                            : '')
                        }
                        title={
                          /DUPLICADO/i.test(row.observacion || '')
                            ? 'DUPLICADO: el número de operación / documento coincide con otro registro en pagos o con otro reporte en esta página.'
                            : row.numero_operacion
                        }
                      >
                        <span className="block truncate font-mono text-xs">
                          {row.numero_operacion}
                        </span>
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 align-top">
                        {new Date(row.fecha_reporte).toLocaleDateString()}
                      </td>

                      <td
                        className="min-w-0 px-3 py-3 align-top text-xs"
                        title="Infopagos y formulario publico comparten esta cola y las mismas reglas."
                      >
                        {etiquetaCanalReportado(row.canal_ingreso)}
                      </td>

                      <td className="px-2 py-3 align-middle">
                        {row.tiene_comprobante ? (
                          <button
                            type="button"
                            onClick={() => handleVerComprobante(row.id)}
                            disabled={viewingComprobanteId === row.id}
                            className="flex w-full min-w-0 flex-col items-center justify-center gap-1 rounded-lg border border-slate-200/80 bg-slate-50/80 px-2 py-2 text-center text-xs font-semibold text-[#1e3a5f] shadow-sm transition-colors hover:border-[#1e3a5f]/30 hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/25 disabled:opacity-60 sm:flex-row sm:text-left"
                            title="Abrir imagen o PDF del comprobante"
                          >
                            {viewingComprobanteId === row.id ? (
                              <Loader2
                                className="h-4 w-4 shrink-0 animate-spin"
                                aria-hidden
                              />
                            ) : (
                              <Eye
                                className="h-4 w-4 shrink-0 opacity-80"
                                aria-hidden
                              />
                            )}
                            <span className="leading-tight underline decoration-[#1e3a5f]/35 underline-offset-2">
                              Ver comprobante
                            </span>
                          </button>
                        ) : (
                          <div
                            className="flex min-h-[52px] flex-col items-center justify-center rounded-lg border border-dashed border-muted-foreground/25 bg-muted/20 px-2 py-2 text-center"
                            title="Sin archivo adjunto en este reporte"
                          >
                            <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                              No disponible
                            </span>
                          </div>
                        )}
                      </td>

                      <td
                        className="min-w-0 px-3 py-3 align-top"
                        title={
                          /NO CLIENTES/i.test(row.observacion || '')
                            ? 'NO CLIENTES: la cédula del reporte (' +
                              row.cedula_display +
                              ') no figura en la tabla clientes. Se compara normalizada (sin guión, sin ceros a la izquierda). Verifique en Préstamos > Clientes o registre al cliente.'
                            : /DUPLICADO/i.test(row.observacion || '')
                              ? 'DUPLICADO: ya existe en la tabla pagos (documento/referencia normalizado) o hay otro reporte con el mismo número en esta página. No se debe aprobar dos veces el mismo comprobante.'
                              : /No pag Bs|solo Bs|Bolívares/i.test(
                                    row.observacion || ''
                                  )
                                ? 'No pag Bs.: la cédula no está en la lista autorizada para bolívares (cedulas_reportar_bs). Use USD o agregue la cédula en Configuración > Pagos.'
                                : (row.observacion ?? '')
                        }
                      >
                        {row.observacion ? (
                          <span
                            className={
                              'line-clamp-2 text-xs ' +
                              (/NO CLIENTES/i.test(row.observacion || '')
                                ? 'font-medium text-destructive'
                                : /DUPLICADO/i.test(row.observacion || '')
                                  ? 'font-semibold text-amber-900 dark:text-amber-100'
                                  : 'text-muted-foreground')
                            }
                          >
                            {row.observacion}
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 align-top">
                        {(() => {
                          const cfg = ESTADO_CONFIG[row.estado] ?? {
                            label: row.estado,
                            short: row.estado,
                            variant: 'outline' as const,
                            Icon: Clock,
                          }

                          const Icon = cfg.Icon

                          return (
                            <Badge
                              variant={cfg.variant}
                              className="inline-flex items-center gap-1 font-normal"
                              title={cfg.label}
                            >
                              <Icon
                                className="h-3.5 w-3.5 shrink-0"
                                aria-hidden
                              />

                              <span>{cfg.short}</span>
                            </Badge>
                          )
                        })()}
                      </td>

                      <td className="px-3 py-3 align-top">
                        <div className="flex flex-wrap items-center justify-start gap-1">
                          {/* Estado envío recibo: X = no enviado, visto = entregado, triángulo = en revisión */}

                          <span
                            className="flex h-8 w-8 shrink-0 items-center justify-center text-muted-foreground"
                            title={
                              row.estado === 'aprobado'
                                ? row.tiene_recibo_pdf && row.correo_enviado_a
                                  ? 'Recibo enviado por correo'
                                  : 'No se envió recibo por correo'
                                : 'En revisión'
                            }
                          >
                            {row.estado === 'aprobado' ? (
                              row.tiene_recibo_pdf && row.correo_enviado_a ? (
                                <CheckCircle
                                  className="h-4 w-4 text-green-600"
                                  aria-hidden
                                />
                              ) : (
                                <XCircle
                                  className="h-4 w-4 text-muted-foreground"
                                  aria-hidden
                                />
                              )
                            ) : (
                              <AlertTriangle
                                className="h-4 w-4 text-blue-600"
                                aria-hidden
                              />
                            )}
                          </span>

                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            title="Ver detalle"
                            onClick={() =>
                              navigate(
                                '/cobros/pagos-reportados/' + String(row.id)
                              )
                            }
                          >
                            <FileText className="h-4 w-4" />
                          </Button>

                          {(row.estado === 'pendiente' ||
                            row.estado === 'en_revision' ||
                            row.estado === 'rechazado') && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 shrink-0"
                              title="Editar (monto, referencia, cédula, etc.)"
                              onClick={() =>
                                navigate(
                                  '/cobros/pagos-reportados/' +
                                    String(row.id) +
                                    '/editar'
                                )
                              }
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                          )}

                          {(row.estado === 'pendiente' ||
                            row.estado === 'en_revision') && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                              title="Rechazar (escribir mensaje y enviar correo)"
                              onClick={() => handleAbrirModalRechazo(row)}
                              disabled={changingEstadoId === row.id}
                            >
                              {changingEstadoId === row.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <XCircle className="h-4 w-4" />
                              )}
                            </Button>
                          )}

                          <div className="relative inline-block h-8 w-8">
                            <select
                              className="absolute inset-0 h-full w-full min-w-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
                              value=""
                              title="Estado"
                              onChange={e => {
                                const v = e.target.value

                                e.target.value = ''

                                if (!v) return

                                if (v === 'rechazado') {
                                  handleAbrirModalRechazo(row)

                                  return
                                }

                                handleCambiarEstado(row.id, v)
                              }}
                              disabled={changingEstadoId === row.id}
                            >
                              <option value="">Seleccionar estado</option>

                              <option value="en_revision">En revisión</option>

                              <option value="aprobado">Aprobar</option>

                              <option value="rechazado">Rechazar</option>
                            </select>

                            <span
                              className="pointer-events-none flex h-8 w-8 items-center justify-center rounded-md border border-input bg-background"
                              title="Estado"
                            >
                              {changingEstadoId === row.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Settings className="h-4 w-4" />
                              )}
                            </span>
                          </div>

                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:bg-destructive/10 hover:text-destructive"
                            title="Eliminar"
                            onClick={() =>
                              handleEliminar(row.id, row.referencia_interna)
                            }
                            disabled={deletingId === row.id}
                          >
                            {deletingId === row.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data && data.total > data.per_page && (
            <div className="mt-4 flex justify-between">
              <p className="text-sm text-gray-600">Total: {data.total}</p>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  Anterior
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  disabled={page * data.per_page >= data.total}
                  onClick={() => setPage(p => p + 1)}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal: interfaz rápida para escribir mensaje de rechazo y enviar correo al cliente */}

      <Dialog
        open={rechazarModal.open}
        onOpenChange={open => {
          if (!open) {
            setRechazarModal({ open: false, row: null })

            setMotivoRechazo('')
          }
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <XCircle className="h-5 w-5" /> Rechazar pago reportado
            </DialogTitle>

            <DialogDescription>
              {rechazarModal.row && (
                <>
                  Referencia:{' '}
                  <strong>
                    {rechazarModal.row.referencia_interna?.startsWith('#')
                      ? rechazarModal.row.referencia_interna
                      : '#' + String(rechazarModal.row.referencia_interna)}
                  </strong>
                  {rechazarModal.row.correo_enviado_a && (
                    <span className="mt-1 block">
                      Se enviará un correo automáticamente a{' '}
                      <strong>{rechazarModal.row.correo_enviado_a}</strong>{' '}
                      desde <strong>notificaciones@rapicreditca.com</strong> con
                      el mensaje y el comprobante adjunto.
                    </span>
                  )}
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            <label className="block text-sm font-medium">
              Mensaje para el cliente (obligatorio)
            </label>

            <textarea
              className="min-h-[100px] w-full resize-y rounded-md border px-3 py-2 text-sm"
              placeholder="Indique el motivo del rechazo. Este texto se enviará por correo al cliente."
              value={motivoRechazo}
              onChange={e => setMotivoRechazo(e.target.value)}
              autoFocus
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRechazarModal({ open: false, row: null })

                setMotivoRechazo('')
              }}
            >
              Cancelar
            </Button>

            <Button
              variant="destructive"
              onClick={handleConfirmarRechazo}
              disabled={
                !motivoRechazo.trim() ||
                changingEstadoId === rechazarModal.row?.id
              }
            >
              {changingEstadoId === rechazarModal.row?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Mail className="mr-2 h-4 w-4" />
              )}
              Rechazar y enviar correo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
