import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, BarChart3, LineChart } from 'lucide-react'
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  obtenerAnalisisUniversoCobranzas,
  type UniversoAnalisisResponse,
  type UniversoBucket,
} from '../../services/cobranzaService'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { formatCurrency } from '../../utils'

const DETALLE_BUCKET_KEYS = [
  ...Array.from({ length: 15 }, (_, i) => String(i + 1)),
] as const

const ATRASO_BIN_DIAS = 30
const ATRASO_N_BINS = 20
const ATRASO_MAX_DIAS = ATRASO_N_BINS * ATRASO_BIN_DIAS

const STALE_MS = 10 * 60 * 1000

function etiquetaBinAtraso(i: number): string {
  if (i >= ATRASO_N_BINS) return '>600 días'
  const desde = i * ATRASO_BIN_DIAS + 1
  const hasta = Math.min((i + 1) * ATRASO_BIN_DIAS, ATRASO_MAX_DIAS)
  return `${desde}–${hasta}`
}

function formatFechaCorta(v: string): string {
  const s = String(v || '')
  if (s.length >= 10) {
    const [y, m, d] = s.slice(0, 10).split('-')
    if (y && m && d) return `${d}/${m}`
  }
  return s
}

function formatAxisUsd(v: number): string {
  if (!Number.isFinite(v)) return ''
  const abs = Math.abs(v)
  if (abs >= 100000) return `$${(v / 1000).toFixed(1)}k`
  if (abs >= 1000) return `$${(v / 1000).toFixed(2)}k`
  return `$${Math.round(v)}`
}

function yDomainFromSeries(
  data: readonly object[],
  keys: string[]
): [number, number] {
  let min = Number.POSITIVE_INFINITY
  let max = Number.NEGATIVE_INFINITY
  for (const row of data) {
    const rec = row as Record<string, unknown>
    for (const k of keys) {
      const v = Number(rec[k])
      if (!Number.isFinite(v)) continue
      if (v < min) min = v
      if (v > max) max = v
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return [0, 1]
  }
  if (min === max) {
    const pad = Math.max(Math.abs(min) * 0.02, 100)
    return [Math.max(0, min - pad), max + pad]
  }
  const span = max - min
  const pad = Math.max(span * 0.2, Math.abs(max) * 0.008, 50)
  return [Math.max(0, min - pad), max + pad]
}

function serieConTendenciaLineal<T extends object>(
  serie: T[],
  valueKey: keyof T | string
): Array<T & { tendencia: number }> {
  const n = serie.length
  if (n === 0) return []
  const yAt = (row: T) =>
    Math.max(0, Number((row as Record<string, unknown>)[valueKey as string]) || 0)
  if (n === 1) {
    return [{ ...serie[0], tendencia: yAt(serie[0]) }]
  }
  let sumX = 0
  let sumY = 0
  let sumXY = 0
  let sumXX = 0
  for (let i = 0; i < n; i++) {
    const x = i
    const y = yAt(serie[i])
    sumX += x
    sumY += y
    sumXY += x * y
    sumXX += x * x
  }
  const denom = n * sumXX - sumX * sumX
  let b = 0
  let a = sumY / n
  if (Math.abs(denom) > 1e-9) {
    b = (n * sumXY - sumX * sumY) / denom
    a = (sumY - b * sumX) / n
  }
  return serie.map((row, i) => ({
    ...row,
    tendencia: Math.max(0, a + b * i),
  }))
}

function distribucionAtrasoDias(
  buckets: Record<string, UniversoBucket> | undefined
): Array<{ label: string; casos: number; monto_usd: number }> {
  const nBins = ATRASO_N_BINS + 1
  const casos = Array.from({ length: nBins }, () => 0)
  const montos = Array.from({ length: nBins }, () => 0)
  for (const k of DETALLE_BUCKET_KEYS) {
    const items = buckets?.[k]?.items || []
    for (const it of items) {
      const dias = Math.max(1, Number(it.dias_atraso_max) || 0)
      const idx =
        dias > ATRASO_MAX_DIAS
          ? ATRASO_N_BINS
          : Math.min(ATRASO_N_BINS - 1, Math.floor((dias - 1) / ATRASO_BIN_DIAS))
      casos[idx] += 1
      montos[idx] += Number(it.saldo_vencido_usd) || 0
    }
  }
  return Array.from({ length: nBins }, (_, i) => ({
    label: etiquetaBinAtraso(i),
    casos: casos[i],
    monto_usd: Math.round(montos[i] * 100) / 100,
  }))
}

const HIST_ATRASO_STROKES = ['#7c3aed', '#ea580c'] as const

function TooltipAtrasoDias({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{
    name?: string
    value?: number
    color?: string
    dataKey?: string
    payload?: { monto_usd?: number }
  }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  const montoHoy = Number(payload[0]?.payload?.monto_usd) || 0
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-semibold text-slate-700">{label} días</div>
      {payload.map(p => (
        <div key={String(p.dataKey || p.name)} className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: p.color }}
          />
          <span className="text-slate-600">{p.name}:</span>
          <span className="font-medium text-slate-900">
            {String(Math.round(Number(p.value) || 0))}
          </span>
        </div>
      ))}
      <div className="mt-1 text-slate-500">
        Saldo hoy: {formatCurrency(montoHoy)}
      </div>
    </div>
  )
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
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-semibold text-slate-700">
        {formatFechaCorta(String(label || ''))}
      </div>
      {payload.map(p => (
        <div key={String(p.name)} className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: p.color }}
          />
          <span className="text-slate-600">{p.name}:</span>
          <span className="font-medium text-slate-900">
            {formatCurrency(Number(p.value) || 0)}
          </span>
        </div>
      ))}
    </div>
  )
}

export const COBRANZAS_ATRASO_DEUDA_QUERY_KEY = 'cobranzas-universo-analisis'

export function CobranzasAtrasoDeudaCharts({
  enabled,
}: {
  enabled: boolean
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: [COBRANZAS_ATRASO_DEUDA_QUERY_KEY],
    queryFn: (): Promise<UniversoAnalisisResponse> =>
      obtenerAnalisisUniversoCobranzas(),
    staleTime: STALE_MS,
    gcTime: STALE_MS * 3,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    retry: 1,
    enabled,
  })

  const distAtrasoViernes = data?.dist_atraso_viernes_cierre

  const distAtrasoDias = useMemo(() => {
    const hoy = distribucionAtrasoDias(data?.buckets)
    const hist = distAtrasoViernes || []
    return hoy.map((bin, i) => {
      const row: Record<string, string | number> = {
        label: bin.label,
        casos: bin.casos,
        monto_usd: bin.monto_usd,
      }
      hist.forEach((serie, si) => {
        row[`hist_${si}`] = Number(serie.bins?.[i]?.casos) || 0
      })
      return row
    })
  }, [data?.buckets, distAtrasoViernes])

  const chartDataTotalTendencia = useMemo(() => {
    const rows = (data?.serie_diaria || []).map(d => {
      const totalTabla = Number(d.monto_total)
      const total_deuda = Number.isFinite(totalTabla)
        ? Math.round(totalTabla * 100) / 100
        : Math.round(
            ((Number(d.monto_1) || 0) +
              (Number(d.monto_2) || 0) +
              (Number(d.monto_3) || 0) +
              (Number(d.monto_4) || 0) +
              (Number(d.monto_5) || 0) +
              (Number(d.monto_6plus) || 0)) *
              100
          ) / 100
      return {
        ...d,
        fecha_label: formatFechaCorta(String(d.fecha)),
        total_deuda,
      }
    })
    return serieConTendenciaLineal(rows, 'total_deuda')
  }, [data?.serie_diaria])

  const yDomainTotal = useMemo(
    () =>
      yDomainFromSeries(chartDataTotalTendencia, ['total_deuda', 'tendencia']),
    [chartDataTotalTendencia]
  )

  const sinAtraso = distAtrasoDias.every(d => d.casos === 0)

  return (
    <>
      <div className="mt-6" id="dashboard-distribucion-atraso-dias">
        <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
          <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-blue-50/90 to-indigo-50/90 pb-3">
            <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
              <BarChart3 className="h-5 w-5 shrink-0 text-blue-600" />
              <span>Distribución del atraso en días</span>
            </CardTitle>
            <p className="mt-1 text-xs font-normal text-slate-500">
              Cada barra agrupa préstamos según cuántos días llevan de atraso
              (hoy − vencimiento más antiguo), en tramos de 30 días, hasta 600
              días. Las curvas son el último viernes de los dos meses anteriores.
            </p>
          </CardHeader>
          <CardContent className="p-6 pt-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                Cargando…
              </div>
            ) : isError ? (
              <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-red-700">
                <AlertTriangle className="h-8 w-8" />
                <p className="text-sm font-medium">
                  No se pudo cargar la distribución de atraso.
                </p>
              </div>
            ) : sinAtraso ? (
              <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                Sin casos para graficar.
              </div>
            ) : (
              <div className="h-[320px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={distAtrasoDias}
                    margin={{ top: 8, right: 12, left: 0, bottom: 28 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#e2e8f0"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 10, fill: '#64748b' }}
                      tickMargin={10}
                      interval={0}
                      angle={-40}
                      textAnchor="end"
                      height={56}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      width={40}
                      allowDecimals={false}
                      label={{
                        value: 'Casos',
                        angle: -90,
                        position: 'insideLeft',
                        style: { fill: '#374151', fontSize: 13 },
                      }}
                    />
                    <Tooltip content={<TooltipAtrasoDias />} />
                    <Legend />
                    <Bar
                      dataKey="casos"
                      name="Hoy"
                      fill="#2563eb"
                      radius={[3, 3, 0, 0]}
                      maxBarSize={28}
                    />
                    {(distAtrasoViernes || []).map((serie, si) => (
                      <Line
                        key={serie.fecha || `hist_${si}`}
                        type="monotone"
                        dataKey={`hist_${si}`}
                        name={serie.etiqueta || `Mes ${si + 1}`}
                        stroke={HIST_ATRASO_STROKES[si] || '#64748b'}
                        strokeWidth={2.25}
                        dot={false}
                        activeDot={{ r: 3 }}
                      />
                    ))}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6" id="dashboard-deuda-total-diaria">
        <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
          <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-teal-50/90 to-emerald-50/90 pb-3">
            <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
              <LineChart className="h-5 w-5 shrink-0 text-teal-700" />
              <span>Desempeño diario (30 días)</span>
            </CardTitle>
            <p className="mt-1 text-xs font-normal text-slate-500">
              Deuda total diaria (30 días)
            </p>
          </CardHeader>
          <CardContent className="p-6 pt-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                Cargando…
              </div>
            ) : isError ? (
              <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-red-700">
                <AlertTriangle className="h-8 w-8" />
                <p className="text-sm font-medium">
                  No se pudo cargar la deuda total diaria.
                </p>
              </div>
            ) : chartDataTotalTendencia.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                Sin datos de serie diaria.
              </div>
            ) : (
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={chartDataTotalTendencia}
                    margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient
                        id="fillTotalDeudaDashboard"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="#0f766e"
                          stopOpacity={0.35}
                        />
                        <stop
                          offset="95%"
                          stopColor="#0f766e"
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
                      dataKey="fecha_label"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickMargin={8}
                      minTickGap={18}
                    />
                    <YAxis
                      domain={yDomainTotal}
                      allowDataOverflow
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickFormatter={formatAxisUsd}
                      width={56}
                    />
                    <Tooltip content={<TooltipUsd />} />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="total_deuda"
                      name="Deuda total"
                      stroke="#0f766e"
                      strokeWidth={2.5}
                      fill="url(#fillTotalDeudaDashboard)"
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                    <Line
                      type="linear"
                      dataKey="tendencia"
                      name="Tendencia"
                      stroke="#64748b"
                      strokeWidth={2}
                      strokeDasharray="6 4"
                      dot={false}
                      isAnimationActive={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
