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
  type UniversoSerieDia,
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

const SEG_COMPILADO = [
  { key: '1', dataKey: 'seg_1', name: '1 cuota', color: '#2563eb' },
  { key: '2', dataKey: 'seg_2', name: '2 cuotas', color: '#f97316' },
  { key: '3', dataKey: 'seg_3', name: '3 cuotas', color: '#0d9488' },
  { key: '4', dataKey: 'seg_4', name: '4 cuotas', color: '#eab308' },
  { key: '5', dataKey: 'seg_5', name: '5 cuotas', color: '#ec4899' },
  { key: '6plus', dataKey: 'seg_6plus', name: '6 o más', color: '#8b5cf6' },
] as const

function nMonto(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : 0
}

function serieCompiladaDiaria(serie: UniversoSerieDia[] | undefined) {
  return (serie || []).map(d => {
    const seg_1 = nMonto(d.cobrado_1)
    const seg_2 = nMonto(d.cobrado_2)
    const seg_3 = nMonto(d.cobrado_3)
    const seg_4 = nMonto(d.cobrado_4)
    const seg_5 = nMonto(d.cobrado_5)
    const seg_6plus = nMonto(d.cobrado_6plus)
    const cobrado_total =
      nMonto(d.cobrado_total) ||
      Math.round((seg_1 + seg_2 + seg_3 + seg_4 + seg_5 + seg_6plus) * 100) /
        100
    const a_conseguir = nMonto(d.monto_total)
    return {
      dia: formatFechaCorta(String(d.fecha)),
      fecha: String(d.fecha),
      seg_1,
      seg_2,
      seg_3,
      seg_4,
      seg_5,
      seg_6plus,
      cobrado_total,
      a_conseguir,
    }
  })
}

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

function yDomainFromMax(
  data: readonly object[],
  key: string
): [number, number] {
  let max = 0
  for (const row of data) {
    const v = Number((row as Record<string, unknown>)[key])
    if (!Number.isFinite(v) || v <= 0) continue
    if (v > max) max = v
  }
  if (max <= 0) return [0, 1]
  return [0, max * 1.08]
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

function etiquetaCurvaViernes(
  fecha: string | undefined,
  index: number,
  total: number
): string {
  const s = String(fecha || '')
  const m = s.length >= 7 ? Number(s.slice(5, 7)) : NaN
  const meses = [
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
  ]
  const mes = Number.isFinite(m) && m >= 1 && m <= 12 ? meses[m - 1] : ''
  if (!mes) return `Mes ${index + 1}`
  if (total >= 2 && index === 0) return `fin ${mes}`
  return mes
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
  payload?: Array<{
    name?: string
    value?: number
    color?: string
    dataKey?: string
    payload?: { cobrado_total?: number }
  }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  const cobrado = Number(row?.cobrado_total)
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-semibold text-slate-700">
        {formatFechaCorta(String(label || ''))}
      </div>
      {payload.map(p => (
        <div key={String(p.dataKey || p.name)} className="flex items-center gap-2">
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
      {Number.isFinite(cobrado) && cobrado >= 0 ? (
        <div className="mt-1 border-t border-slate-100 pt-1 text-slate-500">
          Cobrado del día: {formatCurrency(cobrado)}
        </div>
      ) : null}
    </div>
  )
}

export const COBRANZAS_ATRASO_DEUDA_QUERY_KEY =
  'cobranzas-universo-analisis-cobrado'

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

  const serieCompilada = useMemo(
    () => serieCompiladaDiaria(data?.serie_diaria),
    [data?.serie_diaria]
  )

  const yDomainCobrado = useMemo(
    () => yDomainFromMax(serieCompilada, 'cobrado_total'),
    [serieCompilada]
  )
  const yDomainPorCobrar = useMemo(
    () => yDomainFromMax(serieCompilada, 'a_conseguir'),
    [serieCompilada]
  )

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
      <div className="mt-6" id="dashboard-cobranzas-compilado-segmentos">
        <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
          <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-slate-50/90 to-indigo-50/90 pb-3">
            <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
              <BarChart3 className="h-5 w-5 shrink-0 text-indigo-600" />
              <span>Cobranzas compiladas por segmento</span>
            </CardTitle>
            <p className="mt-1 text-xs font-normal text-slate-500">
              Hoy y los 30 días anteriores. Las barras son el dinero cobrado
              ese día, apilado por segmento (1 a 6 o más). La línea es lo que
              aún debes cobrar (saldo vencido).
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
                  No se pudo cargar el compilado de cobranzas.
                </p>
              </div>
            ) : serieCompilada.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                Sin datos de los últimos 30 días.
              </div>
            ) : (
              <div className="h-[340px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={serieCompilada}
                    margin={{ top: 8, right: 8, left: 4, bottom: 8 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#e2e8f0"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="dia"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickMargin={8}
                      interval="preserveStartEnd"
                      minTickGap={16}
                    />
                    <YAxis
                      yAxisId="cobrado"
                      domain={yDomainCobrado}
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickFormatter={formatAxisUsd}
                      width={56}
                    />
                    <YAxis
                      yAxisId="porCobrar"
                      orientation="right"
                      domain={yDomainPorCobrar}
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickFormatter={formatAxisUsd}
                      width={56}
                    />
                    <Tooltip content={<TooltipUsd />} />
                    <Legend />
                    {SEG_COMPILADO.map((seg, idx) => (
                      <Bar
                        key={seg.dataKey}
                        yAxisId="cobrado"
                        dataKey={seg.dataKey}
                        name={seg.name}
                        stackId="segmentos"
                        fill={seg.color}
                        radius={
                          idx === SEG_COMPILADO.length - 1
                            ? [3, 3, 0, 0]
                            : [0, 0, 0, 0]
                        }
                        maxBarSize={22}
                      />
                    ))}
                    <Line
                      yAxisId="porCobrar"
                      type="monotone"
                      dataKey="a_conseguir"
                      name="Por cobrar"
                      stroke="#0f172a"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: '#0f172a' }}
                      activeDot={{ r: 5 }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

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
                      name="Hoy (mes actual)"
                      fill="#2563eb"
                      radius={[3, 3, 0, 0]}
                      maxBarSize={28}
                    />
                    {(distAtrasoViernes || []).map((serie, si) => (
                      <Line
                        key={serie.fecha || `hist_${si}`}
                        type="monotone"
                        dataKey={`hist_${si}`}
                        name={etiquetaCurvaViernes(
                          serie.fecha,
                          si,
                          (distAtrasoViernes || []).length
                        )}
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
