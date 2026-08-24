import { useMemo, useState } from 'react'
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
  enviarListasGestoresAhora,
  obtenerDashboardGestores,
  triggerDownloadBlob,
} from '../services/cobranzaGestoresService'
import { formatCurrency } from '../utils'
import { getErrorDetail } from '../types/errors'

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
  return (
    <div className="rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-lg backdrop-blur-sm">
      <p className="mb-1 text-xs font-semibold text-slate-700">{label}</p>
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

export default function CobranzasGestoresPage() {
  const [gestorSlug, setGestorSlug] = useState<string>('')
  const [descargando, setDescargando] = useState(false)
  const [enviando, setEnviando] = useState(false)

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ['cobranzas-gestores-dashboard'],
    queryFn: ({ signal }) => obtenerDashboardGestores({ signal }),
    staleTime: 15_000,
    refetchInterval: 20_000,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: false,
  })

  const gestores = data?.gestores ?? []
  const totales = data?.totales ?? []
  const tendencia = data?.tendencia ?? []

  const colorBySlug = useMemo(() => {
    const m: Record<string, string> = {}
    gestores.forEach((g, i) => {
      m[g.slug] = COLORES_GESTORES[i % COLORES_GESTORES.length]
    })
    return m
  }, [gestores])

  const onDescargar = async () => {
    if (!gestorSlug) {
      toast.warning('Seleccione un gestor.')
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
          <Button
            type="button"
            onClick={() => void onEnviarManual()}
            disabled={enviando || isLoading}
            className="gap-2 bg-emerald-700 hover:bg-emerald-800"
          >
            <Mail className="h-4 w-4" />
            {enviando ? 'Enviando 9 listas…' : 'Enviar 9 listas ahora'}
          </Button>
        }
      />

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Descargar lista Excel</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="min-w-[240px] flex-1 space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Gestor</label>
            <Select value={gestorSlug} onValueChange={setGestorSlug}>
              <SelectTrigger>
                <SelectValue placeholder="Seleccione gestor…" />
              </SelectTrigger>
              <SelectContent>
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
            disabled={descargando || !gestorSlug || isLoading}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            {descargando ? 'Generando…' : 'Descargar Excel'}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => void refetch()}
            disabled={isFetching}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar dashboard
          </Button>
        </CardContent>
        {error ? (
          <p className="px-6 pb-4 text-sm text-red-600">
            {getErrorDetail(error) || 'Error al cargar gestores.'}
          </p>
        ) : null}
        {data?.asignacion_cerrada ? (
          <p className="px-6 pb-4 text-xs text-slate-500">
            Asignación cerrada (listas fijas). Fecha negocio: {data.fecha_negocio}.
            Gráficos se refrescan cada 8 s y tras cada pago en cascada.
          </p>
        ) : null}
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="overflow-hidden border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white pb-3">
            <CardTitle className="text-base tracking-tight text-slate-900">
              Tendencia diaria por gestor
            </CardTitle>
            <p className="text-xs text-slate-500">
              USD cobranza pendiente (vencido + mora). Una línea por gestor.
            </p>
          </CardHeader>
          <CardContent className="h-[420px] pt-4">
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
                    dataKey="fecha"
                    tick={{ fontSize: 11, fill: '#64748b' }}
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
          <CardContent className="h-[420px] pt-4">
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
