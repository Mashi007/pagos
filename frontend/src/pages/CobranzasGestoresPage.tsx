import { useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Mail, RefreshCw, Users } from 'lucide-react'
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import {
  descargarExcelGestor,
  descargarInformeDiarioGestor,
  descargarInformeDiarioTodos,
  enviarListasGestoresAhora,
  obtenerDashboardGestores,
  triggerDownloadBlob,
} from '../services/cobranzaGestoresService'
import { formatCurrency } from '../utils'
import { getErrorDetail } from '../types/errors'
import { usePermissions } from '../hooks/usePermissions'

const COLORES_GESTORES = [
  '#1d4ed8',
  '#b91c1c',
  '#15803d',
  '#c2410c',
  '#7c3aed',
  '#0e7490',
  '#a16207',
  '#be185d',
  '#334155',
]

/** YYYY-MM-DD → "día/mes" (ej. 24/08) para ejes de gráficos. */
function formatoFechaDiaMes(iso: string | number | undefined): string {
  const raw = String(iso ?? '').slice(0, 10)
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw)
  if (!m) return raw || ''
  return `${m[3]}/${m[2]}`
}

function TooltipUsd({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ name?: string; value?: number; color?: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  const titulo = formatoFechaDiaMes(label) || label
  return (
    <div className="rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-lg backdrop-blur-sm">
      <p className="mb-1 text-xs font-semibold text-slate-700">{titulo}</p>
      <ul className="space-y-0.5">
        {payload.map(p => (
          <li
            key={String(p.name)}
            className="flex items-center justify-between gap-4 text-xs tabular-nums"
          >
            <span className="flex items-center gap-1.5 text-slate-600">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: p.color }}
              />
              {p.name}
            </span>
            <span className="font-medium text-slate-900">
              {formatCurrency(Number(p.value) || 0)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

const DASHBOARD_CACHE_MS = 15 * 60 * 1000
const GESTOR_TODOS = '__todos__'

export default function CobranzasGestoresPage() {
  const { isAdmin } = usePermissions()
  const [gestorSlug, setGestorSlug] = useState<string>('')
  const [descargando, setDescargando] = useState(false)
  const [descargandoInforme, setDescargandoInforme] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const forceRefreshRef = useRef(false)

  const esTodos = gestorSlug === GESTOR_TODOS
  const gestorIndividual = Boolean(gestorSlug) && !esTodos

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ['cobranzas-gestores-dashboard'],
    queryFn: ({ signal }) => {
      const force = forceRefreshRef.current
      forceRefreshRef.current = false
      return obtenerDashboardGestores({ signal, forceRefresh: force })
    },
    staleTime: DASHBOARD_CACHE_MS,
    refetchInterval: query =>
      query.state.data?.asignacion_en_progreso ? 5_000 : DASHBOARD_CACHE_MS,
    refetchOnWindowFocus: false,
    refetchIntervalInBackground: false,
  })

  const actualizarDashboard = () => {
    forceRefreshRef.current = true
    void refetch()
  }

  const gestores = data?.gestores ?? []
  const totales = data?.totales ?? []
  const tendencia = useMemo(
    () =>
      (data?.tendencia ?? []).map(row => ({
        ...row,
        fecha_label: formatoFechaDiaMes(row.fecha),
      })),
    [data?.tendencia]
  )

  /** Dominio Y acotado al rango de datos (no desde 0) para ver variaciones diarias. */
  const yDomainTendencia = useMemo((): [number, number] | ['auto', 'auto'] => {
    const slugs = gestores.map(g => g.slug)
    let min = Infinity
    let max = -Infinity
    for (const row of tendencia) {
      const rec = row as Record<string, unknown>
      for (const slug of slugs) {
        const v = Number(rec[slug])
        if (!Number.isFinite(v)) continue
        if (v < min) min = v
        if (v > max) max = v
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      return ['auto', 'auto']
    }
    if (min === max) {
      const pad = Math.max(Math.abs(min) * 0.08, 100)
      return [Math.max(0, min - pad), max + pad]
    }
    const span = max - min
    const pad = Math.max(span * 0.15, Math.abs(max) * 0.015, 50)
    return [Math.max(0, min - pad), max + pad]
  }, [tendencia, gestores])

  const yTickTendencia = useMemo(() => {
    const d = yDomainTendencia
    const span =
      Array.isArray(d) && typeof d[0] === 'number' && typeof d[1] === 'number'
        ? d[1] - d[0]
        : Infinity
    return (v: number) => {
      const n = Number(v)
      if (!Number.isFinite(n)) return ''
      if (n >= 1000) {
        const k = n / 1000
        return span < 8000 ? `${k.toFixed(1)}k` : `${k.toFixed(0)}k`
      }
      return String(Math.round(n))
    }
  }, [yDomainTendencia])

  const colorBySlug = useMemo(() => {
    const m: Record<string, string> = {}
    gestores.forEach((g, i) => {
      m[g.slug] = COLORES_GESTORES[i % COLORES_GESTORES.length]
    })
    return m
  }, [gestores])

  const onDescargar = async () => {
    if (!gestorIndividual) {
      toast.warning(
        esTodos
          ? 'La lista Excel es por gestor. Elija un gestor, o use el informe con Todos.'
          : 'Seleccione un gestor.'
      )
      return
    }
    setDescargando(true)
    try {
      const { blob, filename } = await descargarExcelGestor(gestorSlug)
      triggerDownloadBlob(blob, filename)
      toast.success('Excel descargado (montos al día con pagos del sistema).')
      void refetch()
    } catch (e) {
      toast.error(getErrorDetail(e) || 'No se pudo descargar el Excel.')
    } finally {
      setDescargando(false)
    }
  }

  const onDescargarInforme = async () => {
    if (!gestorSlug) {
      toast.warning('Seleccione un gestor o Todos.')
      return
    }
    setDescargandoInforme(true)
    try {
      if (esTodos) {
        const { blob, filename } = await descargarInformeDiarioTodos()
        triggerDownloadBlob(blob, filename)
        toast.success(
          'Informe resumido de los 9 gestores (Resumen_hoy + Por_dia).'
        )
      } else {
        const { blob, filename } = await descargarInformeDiarioGestor(gestorSlug)
        triggerDownloadBlob(blob, filename)
        toast.success(
          'Informe diario descargado (Resumen hoy + historial Por_dia + Cartera).'
        )
      }
      void refetch()
    } catch (e) {
      toast.error(getErrorDetail(e) || 'No se pudo descargar el informe.')
    } finally {
      setDescargandoInforme(false)
    }
  }

  const onEnviarManual = async () => {
    const okConfirm = window.confirm(
      '¿Enviar ahora las 9 listas Excel actualizadas a operaciones@rapicreditca.com (BCC itmaster@)?'
    )
    if (!okConfirm) return
    setEnviando(true)
    try {
      const res = await enviarListasGestoresAhora()
      if (!res?.ok) {
        toast.error(res?.error || 'No se pudo enviar el correo.')
        return
      }
      toast.success(
        `Enviado: ${res.adjuntos ?? 9} listas. Asunto: ${res.asunto || 'Listas actualizadas'}.`
      )
      void refetch()
    } catch (e) {
      toast.error(getErrorDetail(e) || 'Error al enviar las 9 listas.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Gestores de cobranza"
        icon={Users}
        actions={
          isAdmin ? (
            <Button
              type="button"
              onClick={() => void onEnviarManual()}
              disabled={enviando || isLoading}
              className="gap-2 bg-emerald-700 hover:bg-emerald-800"
            >
              <Mail className="h-4 w-4" />
              {enviando ? 'Enviando 9 listas…' : 'Enviar 9 listas ahora'}
            </Button>
          ) : undefined
        }
      />

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Descargas por gestor</CardTitle>
          <p className="text-xs text-slate-500">
            Universo: APROBADO con aprobación desde 1-abr-2026 y 2+ cuotas
            vencidas/mora. Elija un gestor (lista + informe) o Todos (informe
            resumido). Disponible para Cobranza (gerente) y admin.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="min-w-[240px] flex-1 space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Gestor</label>
            <Select value={gestorSlug} onValueChange={setGestorSlug}>
              <SelectTrigger>
                <SelectValue placeholder="Seleccione gestor…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={GESTOR_TODOS}>Todos (resumen)</SelectItem>
                {gestores.map(g => (
                  <SelectItem key={g.slug} value={g.slug}>
                    {g.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            type="button"
            onClick={() => void onDescargar()}
            disabled={
              descargando ||
              descargandoInforme ||
              !gestorIndividual ||
              isLoading
            }
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            {descargando ? 'Generando…' : 'Descargar lista Excel'}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => void onDescargarInforme()}
            disabled={descargando || descargandoInforme || !gestorSlug || isLoading}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            {descargandoInforme
              ? 'Generando…'
              : esTodos
                ? 'Descargar informe (todos)'
                : 'Descargar informe diario'}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={actualizarDashboard}
            disabled={isFetching}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar dashboard
          </Button>
        </CardContent>
        {data?.asignacion_en_progreso ? (
          <p className="px-6 pb-2 text-sm text-amber-700">
            Preparando asignación de listas en segundo plano… el dashboard se
            actualizará solo cuando termine.
          </p>
        ) : null}
        {error ? (
          <p className="px-6 pb-4 text-sm text-red-600">
            {getErrorDetail(error) || 'Error al cargar gestores.'}
          </p>
        ) : null}
        {data?.asignacion_cerrada ? (
          <p className="px-6 pb-4 text-xs text-slate-500">
            Asignación cerrada (listas fijas). Fecha negocio: {data.fecha_negocio}.
            Dashboard en caché ~15 min
            {data.desde_cache ? ' (sirviendo caché)' : ' (recién calculado)'}.
            Use «Actualizar dashboard» para forzar recálculo.
          </p>
        ) : null}
      </Card>

      <div className="grid grid-cols-1 gap-6">
        <Card className="overflow-hidden border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white pb-3">
            <CardTitle className="text-base tracking-tight text-slate-900">
              Tendencia diaria por gestor
            </CardTitle>
            <p className="text-xs text-slate-500">
              USD cobranza pendiente (vencido + mora). Una línea por gestor. El eje Y
              se ajusta al rango de los datos para resaltar variaciones día a día.
            </p>
          </CardHeader>
          <CardContent className="h-[480px] pt-4">
            {isLoading ? (
              <p className="text-sm text-slate-500">Cargando…</p>
            ) : tendencia.length === 0 ? (
              <p className="text-sm text-slate-500">
                Aún no hay puntos de tendencia. Se generan al abrir el módulo, tras pagos y a
                las 18:00 Caracas.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={tendencia}
                  margin={{ top: 8, right: 12, left: 4, bottom: 8 }}
                >
                  <defs>
                    {gestores.map(g => (
                      <linearGradient
                        key={`grad-${g.slug}`}
                        id={`grad-${g.slug}`}
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor={colorBySlug[g.slug]}
                          stopOpacity={0.28}
                        />
                        <stop
                          offset="100%"
                          stopColor={colorBySlug[g.slug]}
                          stopOpacity={0.02}
                        />
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis
                    dataKey="fecha_label"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    axisLine={{ stroke: '#cbd5e1' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={yDomainTendencia}
                    allowDecimals
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                    width={52}
                    tickFormatter={yTickTendencia}
                  />
                  <Tooltip content={<TooltipUsd />} />
                  <Legend
                    wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                    iconType="circle"
                  />
                  {gestores.map(g => (
                    <Area
                      key={g.slug}
                      type="monotone"
                      dataKey={g.slug}
                      name={g.nombre}
                      stroke={colorBySlug[g.slug]}
                      strokeWidth={2.5}
                      fill={`url(#grad-${g.slug})`}
                      dot={{ r: 2.5, strokeWidth: 0, fill: colorBySlug[g.slug] }}
                      activeDot={{ r: 5 }}
                      isAnimationActive
                      animationDuration={700}
                    />
                  ))}
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="overflow-hidden border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white pb-3">
            <CardTitle className="text-base tracking-tight text-slate-900">
              Total cobranza asignada por gestor
            </CardTitle>
            <p className="text-xs text-slate-500">
              Baja al instante cuando se registra un pago en cualquier préstamo de la lista.
            </p>
          </CardHeader>
          <CardContent className="h-[480px] pt-4">
            {isLoading ? (
              <p className="text-sm text-slate-500">Cargando…</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={totales}
                  margin={{ top: 8, right: 12, left: 4, bottom: 48 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis
                    dataKey="nombre"
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    interval={0}
                    angle={-28}
                    textAnchor="end"
                    height={72}
                    axisLine={{ stroke: '#cbd5e1' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={v =>
                      Number(v) >= 1000
                        ? `${(Number(v) / 1000).toFixed(0)}k`
                        : String(v)
                    }
                  />
                  <Tooltip content={<TooltipUsd />} />
                  <Bar
                    dataKey="total_cobranza_usd"
                    name="USD vencido + mora"
                    radius={[6, 6, 0, 0]}
                    maxBarSize={48}
                    isAnimationActive
                    animationDuration={650}
                  >
                    {totales.map(t => (
                      <Cell
                        key={t.slug}
                        fill={colorBySlug[t.slug] || '#1d4ed8'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
