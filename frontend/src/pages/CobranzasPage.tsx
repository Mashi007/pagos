import React, { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import {
  Database,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  obtenerAnalisisUniversoCobranzas,
  type UniversoAnalisisResponse,
  type UniversoBucket,
  type UniversoMeta,
} from '../services/cobranzaService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { formatCurrency } from '../utils'

const BUCKET_KEYS = ['1', '2', '3', '4plus'] as const
type BucketKey = (typeof BUCKET_KEYS)[number]

const BUCKET_LABELS: Record<BucketKey, string> = {
  '1': '1 cuota',
  '2': '2 cuotas',
  '3': '3 cuotas',
  '4plus': '4 o mas',
}

/** Texto corto: buckets excluyentes (exactamente N; sin solape). */
const BUCKET_HINT: Record<BucketKey, string> = {
  '1': 'Solo exactamente 1 cuota vencida',
  '2': 'Solo exactamente 2 cuotas vencidas',
  '3': 'Solo exactamente 3 cuotas vencidas',
  '4plus': 'Solo 4 o mas cuotas vencidas',
}

const BUCKET_ACCENT: Record<BucketKey, string> = {
  '1': 'border-t-blue-500',
  '2': 'border-t-amber-500',
  '3': 'border-t-rose-500',
  '4plus': 'border-t-violet-600',
}

const BUCKET_SOFT: Record<BucketKey, string> = {
  '1': 'bg-blue-50 text-blue-800',
  '2': 'bg-amber-50 text-amber-900',
  '3': 'bg-rose-50 text-rose-900',
  '4plus': 'bg-violet-50 text-violet-900',
}

const LINE_COLORS = {
  monto_1: '#2563eb',
  monto_2: '#d97706',
  monto_3: '#e11d48',
  monto_4plus: '#7c3aed',
}

function emptyBucket(clave: string): UniversoBucket {
  return { clave, cantidad: 0, monto_usd: 0, items: [] }
}

function formatCargadoEn(v?: string | null): string {
  if (!v) return '-'
  try {
    return new Date(v).toLocaleString('es-VE', {
      dateStyle: 'short',
      timeStyle: 'short',
    })
  } catch {
    return v
  }
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

function DesempenoLecturasLunes({
  data,
}: {
  data: NonNullable<UniversoAnalisisResponse['desempeno_lecturas']>
}) {
  const columnas = data.columnas || []
  const rows: Array<{
    key: string
    label: string
    lecturas: Array<{ fecha: string; cantidad: number; monto_usd: number }>
  }> = []
  if (data.total?.lecturas?.length) {
    rows.push({
      key: 'total',
      label: 'Total vencidos',
      lecturas: data.total.lecturas,
    })
  }
  for (const k of BUCKET_KEYS) {
    const b = data.buckets?.[k]
    if (b?.lecturas?.length) {
      rows.push({ key: k, label: BUCKET_LABELS[k], lecturas: b.lecturas })
    }
  }
  const bordeBloque = 'border-l border-slate-300'
  return (
    <Card className="border-slate-200">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Desempeño de cobranzas</CardTitle>
        <CardDescription>
          Buckets excluyentes (exactamente 1 / 2 / 3 / 4+). Saldo as-of por
          dia: cobros posteriores no reescriben el pasado (asi se ve la
          mejoria). Columnas: 3 lunes + ayer + hoy.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-2">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                <th
                  rowSpan={2}
                  className="py-2 pr-3 align-bottom font-semibold border-r border-slate-300"
                >
                  Bucket
                </th>
                {columnas.map((col) => (
                  <th
                    key={col.fecha}
                    colSpan={2}
                    className={`py-2 px-2 text-center font-semibold ${bordeBloque} ${
                      col.es_hoy
                        ? 'bg-slate-100 text-slate-900'
                        : col.es_ayer
                          ? 'bg-slate-50 text-slate-800'
                          : 'text-slate-600'
                    }`}
                  >
                    {col.etiqueta}
                  </th>
                ))}
              </tr>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                {columnas.map((col) => (
                  <Fragment key={`${col.fecha}-sub`}>
                    <th
                      className={`py-1.5 px-2 font-semibold text-right ${bordeBloque} ${
                        col.es_hoy || col.es_ayer ? 'bg-slate-50' : ''
                      }`}
                    >
                      Cantidad
                    </th>
                    <th
                      className={`py-1.5 px-2 font-semibold text-right ${
                        col.es_hoy || col.es_ayer ? 'bg-slate-50' : ''
                      }`}
                    >
                      Monto
                    </th>
                  </Fragment>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(({ key, label, lecturas }) => (
                <tr
                  key={key}
                  className={`border-b border-slate-100 ${
                    key === 'total' ? 'bg-slate-50 font-semibold' : ''
                  }`}
                >
                  <td className="py-2.5 pr-3 text-slate-800 border-r border-slate-300">
                    {label}
                  </td>
                  {lecturas.map((L, i) => {
                    const resaltar =
                      columnas[i]?.es_hoy || columnas[i]?.es_ayer
                    return (
                      <Fragment key={`${key}-${L.fecha}`}>
                        <td
                          className={`py-2.5 px-2 text-right tabular-nums text-slate-900 ${bordeBloque} ${
                            resaltar ? 'bg-slate-50/80' : ''
                          }`}
                        >
                          {L.cantidad}
                        </td>
                        <td
                          className={`py-2.5 px-2 text-right tabular-nums text-slate-700 ${
                            resaltar ? 'bg-slate-50/80' : ''
                          }`}
                        >
                          <span className={key === 'total' ? '' : 'font-normal'}>
                            {formatCurrency(L.monto_usd)}
                          </span>
                        </td>
                      </Fragment>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

/** Zoom del eje Y al rango real de las series (evita linea plana desde $0). */
function yDomainFromSeries(
  data: Array<Record<string, unknown>>,
  keys: string[]
): [number, number] {
  let min = Number.POSITIVE_INFINITY
  let max = Number.NEGATIVE_INFINITY
  for (const row of data) {
    for (const k of keys) {
      const v = Number(row[k])
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

function SerieDiariaLineCard({
  title,
  description,
  data,
  dataKey,
  name,
  color,
  yDomain,
}: {
  title: string
  description: string
  data: Array<{ fecha_label?: string; [key: string]: unknown }>
  dataKey: string
  name: string
  color: string
  yDomain: [number, number]
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[260px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
            >
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
                domain={yDomain}
                allowDataOverflow
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={formatAxisUsd}
                width={56}
              />
              <Tooltip content={<TooltipUsd />} />
              <Legend />
              <Line
                type="monotone"
                dataKey={dataKey}
                name={name}
                stroke={color}
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

function BucketListCard({
  bucketKey,
  bucket,
}: {
  bucketKey: BucketKey
  bucket: UniversoBucket
}) {
  const [filtroCedula, setFiltroCedula] = useState('')
  const q = filtroCedula.trim().toLowerCase()
  const itemsFiltrados = useMemo(() => {
    if (!q) return bucket.items
    return bucket.items.filter(item => {
      const ced = String(item.cedula || '').toLowerCase()
      const nom = String(item.nombres || '').toLowerCase()
      return ced.includes(q) || nom.includes(q)
    })
  }, [bucket.items, q])

  return (
    <Card className={`overflow-hidden border-t-4 ${BUCKET_ACCENT[bucketKey]}`}>
      <CardHeader className="space-y-1 pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">
            {BUCKET_LABELS[bucketKey]}
          </CardTitle>
          <Badge className={BUCKET_SOFT[bucketKey]} variant="secondary">
            {q
              ? `${itemsFiltrados.length}/${bucket.cantidad} prestamos`
              : `${bucket.cantidad} prestamos`}
          </Badge>
        </div>
        <p className="text-lg font-semibold tracking-tight text-slate-900">
          {formatCurrency(bucket.monto_usd)}
        </p>
        <CardDescription>
          Saldo vencido USD - {BUCKET_HINT[bucketKey]}
        </CardDescription>
        <Input
          className="mt-2 h-8 font-mono text-sm"
          placeholder="Filtrar por cedula..."
          value={filtroCedula}
          onChange={e => setFiltroCedula(e.target.value)}
          aria-label={`Filtrar ${BUCKET_LABELS[bucketKey]} por cedula`}
        />
      </CardHeader>
      <CardContent className="pt-0">
        <div className="max-h-64 overflow-y-auto rounded-md border border-slate-100">
          {itemsFiltrados.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-slate-400">
              {bucket.items.length === 0 ? 'Sin casos' : 'Sin coincidencias'}
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {itemsFiltrados.map(item => (
                <li
                  key={`${item.prestamo_id}-${item.cedula}`}
                  className="flex items-center justify-between gap-2 px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <div className="truncate font-mono text-slate-800">
                      {item.cedula}
                    </div>
                    {item.nombres ? (
                      <div className="truncate text-xs text-slate-500">
                        {item.nombres}
                      </div>
                    ) : null}
                  </div>
                  <div className="shrink-0 font-medium text-amber-800">
                    {formatCurrency(item.saldo_vencido_usd)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function CobranzasPage() {
  const [universoMeta, setUniversoMeta] = useState<UniversoMeta | null>(null)
  const [analisis, setAnalisis] = useState<UniversoAnalisisResponse | null>(
    null
  )
  const [cargandoUniverso, setCargandoUniverso] = useState(false)

  const cargarAnalisis = useCallback(async (showToast = false) => {
    setCargandoUniverso(true)
    try {
      const data = await obtenerAnalisisUniversoCobranzas()
      setAnalisis(data)
      if (data.meta) setUniversoMeta(data.meta)
      if (showToast) toast.success('Analisis actualizado desde BD')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al cargar analisis')
    } finally {
      setCargandoUniverso(false)
    }
  }, [])

  useEffect(() => {
    void cargarAnalisis(false)
  }, [cargarAnalisis])

  const buckets = useMemo(() => {
    const raw = analisis?.buckets || {}
    return BUCKET_KEYS.map(k => raw[k] || emptyBucket(k))
  }, [analisis])

  const bucketsByKey = useMemo(() => {
    const map = {} as Record<BucketKey, UniversoBucket>
    for (const b of buckets) {
      map[b.clave as BucketKey] = b
    }
    return map
  }, [buckets])

  const chartData = useMemo(() => {
    return (analisis?.serie_diaria || []).map(d => {
      const m1 = Number(d.monto_1) || 0
      const m2 = Number(d.monto_2) || 0
      const m3 = Number(d.monto_3) || 0
      const m4 = Number(d.monto_4plus) || 0
      return {
        ...d,
        fecha_label: formatFechaCorta(String(d.fecha)),
        total_deuda: Math.round((m1 + m2 + m3 + m4) * 100) / 100,
      }
    })
  }, [analisis])

  const yDomain1 = useMemo(
    () => yDomainFromSeries(chartData, ['monto_1']),
    [chartData]
  )
  const yDomain2 = useMemo(
    () => yDomainFromSeries(chartData, ['monto_2']),
    [chartData]
  )
  const yDomain3 = useMemo(
    () => yDomainFromSeries(chartData, ['monto_3']),
    [chartData]
  )
  const yDomain4plus = useMemo(
    () => yDomainFromSeries(chartData, ['monto_4plus']),
    [chartData]
  )
  const yDomainTotal = useMemo(
    () => yDomainFromSeries(chartData, ['total_deuda']),
    [chartData]
  )

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Cobranzas</h1>
        <p className="mt-1 text-sm text-slate-600">
          Analisis de cuotas vencidas sobre cartera APROBADO en base de datos.
          No incluye LIQUIDADO ni DESISTIMIENTO (desestimados).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Database className="h-5 w-5" />
            Cartera completa (BD)
          </CardTitle>
          <CardDescription>
            Solo prestamos APROBADO (sin liquidados ni desestimados). Actualice
            para recalcular buckets y desempeno.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              onClick={() => void cargarAnalisis(true)}
              disabled={cargandoUniverso}
            >
              {cargandoUniverso ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Actualizar
            </Button>
          </div>
          <div className="flex flex-wrap gap-4 text-sm text-slate-600">
            <span>
              Prestamos APROBADO:{' '}
              <strong className="text-slate-900">
                {universoMeta?.cantidad ?? '-'}
              </strong>
            </span>
            {analisis != null && (
              <span>
                Sin vencidas:{' '}
                <strong className="text-slate-900">
                  {analisis.sin_vencidas}
                </strong>
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {analisis && (

        <>
          {analisis.desempeno_lecturas && (
            <DesempenoLecturasLunes data={analisis.desempeno_lecturas} />
          )}

          <div>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">
              Detalle por bucket
            </h2>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {BUCKET_KEYS.map(k => (
                <BucketListCard
                  key={k}
                  bucketKey={k}
                  bucket={bucketsByKey[k] || emptyBucket(k)}
                />
              ))}
            </div>
          </div>

          <div>
            <h2 className="mb-1 text-lg font-semibold text-slate-900">
              Desempeno diario (30 dias)
            </h2>
            <p className="mb-4 text-sm text-slate-500">
              Saldo as-of USD por bucket (cobros del dia bajan ese dia y
              siguientes, no el pasado). Misma logica que la tabla de lecturas.
            </p>
            {chartData.length === 0 ? (
              <p className="py-6 text-center text-slate-500">
                Sin datos de serie diaria.
              </p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                <SerieDiariaLineCard
                  title="1 cuota"
                  description="Solo exactamente 1 cuota vencida (excluyente). Eje Y propio."
                  data={chartData}
                  dataKey="monto_1"
                  name="1 cuota"
                  color={LINE_COLORS.monto_1}
                  yDomain={yDomain1}
                />
                <SerieDiariaLineCard
                  title="2 cuotas"
                  description="Solo exactamente 2 cuotas vencidas (excluyente). Eje Y propio."
                  data={chartData}
                  dataKey="monto_2"
                  name="2 cuotas"
                  color={LINE_COLORS.monto_2}
                  yDomain={yDomain2}
                />
                <SerieDiariaLineCard
                  title="3 cuotas"
                  description="Solo exactamente 3 cuotas vencidas (excluyente). Eje Y propio."
                  data={chartData}
                  dataKey="monto_3"
                  name="3 cuotas"
                  color={LINE_COLORS.monto_3}
                  yDomain={yDomain3}
                />
                <SerieDiariaLineCard
                  title="4 o mas cuotas"
                  description="Solo 4 o mas cuotas vencidas (excluyente). Eje Y propio."
                  data={chartData}
                  dataKey="monto_4plus"
                  name="4 o mas"
                  color={LINE_COLORS.monto_4plus}
                  yDomain={yDomain4plus}
                />
              </div>
            )}
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">
                Deuda total diaria (30 dias)
              </CardTitle>
              <CardDescription>
                Suma de buckets excluyentes (1 + 2 + 3 + 4 o mas) por dia. Sin
                doble conteo.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={chartData}
                    margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient
                        id="fillTotalDeuda"
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
                      fill="url(#fillTotalDeuda)"
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
