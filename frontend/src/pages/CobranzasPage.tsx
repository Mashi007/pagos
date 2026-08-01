import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  FileSpreadsheet,
  Loader2,
  Minus,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Trash2,
  Upload,
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
  agregarCedulaUniverso,
  eliminarCedulaUniverso,
  limpiarUniversoCobranzas,
  listarCedulasUniverso,
  obtenerAnalisisUniversoCobranzas,
  obtenerUniversoCobranzas,
  uploadUniversoCobranzas,
  type UniversoAnalisisResponse,
  type UniversoBucket,
  type UniversoMeta,
} from '../services/cobranzaService'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
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

type SerieMontoKey = 'monto_1' | 'monto_2' | 'monto_3' | 'monto_4plus' | 'total'

const BUCKET_SERIE_KEY: Record<BucketKey, SerieMontoKey> = {
  '1': 'monto_1',
  '2': 'monto_2',
  '3': 'monto_3',
  '4plus': 'monto_4plus',
}

function montoSerieDia(
  d: { monto_1?: number; monto_2?: number; monto_3?: number; monto_4plus?: number } | null | undefined,
  key: SerieMontoKey
): number {
  if (!d) return 0
  if (key === 'total') {
    return (
      (Number(d.monto_1) || 0) +
      (Number(d.monto_2) || 0) +
      (Number(d.monto_3) || 0) +
      (Number(d.monto_4plus) || 0)
    )
  }
  return Number(d[key]) || 0
}

/** % cambio actual vs base. null = no comparable (base 0 y actual > 0). */
function pctVariacion(actual: number, base: number): number | null {
  if (!Number.isFinite(actual) || !Number.isFinite(base)) return null
  if (Math.abs(base) < 0.005) {
    if (Math.abs(actual) < 0.005) return 0
    return null
  }
  return ((actual - base) / Math.abs(base)) * 100
}

function formatPctVariacion(pct: number | null): string {
  if (pct == null) return 'n/d'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(1)}%`
}

function VariacionChip({
  etiqueta,
  pct,
}: {
  etiqueta: string
  pct: number | null
}) {
  // Deuda: subir = malo (rojo), bajar = bueno (verde)
  let tone =
    'border-slate-300 bg-slate-100 text-slate-800 ring-1 ring-slate-200'
  let Icon = Minus
  if (pct != null && Math.abs(pct) >= 0.05) {
    if (pct > 0) {
      tone =
        'border-rose-400 bg-rose-100 text-rose-900 ring-1 ring-rose-300'
      Icon = TrendingUp
    } else {
      tone =
        'border-emerald-400 bg-emerald-100 text-emerald-900 ring-1 ring-emerald-300'
      Icon = TrendingDown
    }
  }
  return (
    <div
      className={`flex min-w-0 flex-1 items-center gap-1.5 rounded-md border px-2 py-1.5 ${tone}`}
      title={
        pct == null
          ? `${etiqueta}: sin base comparable`
          : `${etiqueta}: ${formatPctVariacion(pct)}`
      }
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
      <div className="min-w-0 leading-tight">
        <div className="text-[10px] font-semibold uppercase tracking-wide opacity-80">
          {etiqueta}
        </div>
        <div className="text-sm font-bold tabular-nums">
          {formatPctVariacion(pct)}
        </div>
      </div>
    </div>
  )
}

function VariacionesTarjeta({
  diaPct,
  semanaPct,
}: {
  diaPct: number | null
  semanaPct: number | null
}) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2">
      <VariacionChip etiqueta="vs ayer" pct={diaPct} />
      <VariacionChip etiqueta="vs semana" pct={semanaPct} />
    </div>
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
  return (
    <Card className={`overflow-hidden border-t-4 ${BUCKET_ACCENT[bucketKey]}`}>
      <CardHeader className="space-y-1 pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{BUCKET_LABELS[bucketKey]}</CardTitle>
          <Badge className={BUCKET_SOFT[bucketKey]} variant="secondary">
            {bucket.cantidad} prestamos
          </Badge>
        </div>
        <p className="text-lg font-semibold tracking-tight text-slate-900">
          {formatCurrency(bucket.monto_usd)}
        </p>
        <CardDescription>Saldo vencido USD</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="max-h-64 overflow-y-auto rounded-md border border-slate-100">
          {bucket.items.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-slate-400">
              Sin casos
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {bucket.items.map(item => (
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
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [universoMeta, setUniversoMeta] = useState<UniversoMeta | null>(null)
  const [analisis, setAnalisis] = useState<UniversoAnalisisResponse | null>(
    null
  )
  const [cedulasUniverso, setCedulasUniverso] = useState<string[]>([])
  const [cedulaUniversoInput, setCedulaUniversoInput] = useState('')
  const [cargandoUniverso, setCargandoUniverso] = useState(false)
  const [subiendo, setSubiendo] = useState(false)
  const [limpiando, setLimpiando] = useState(false)
  const [editandoCedula, setEditandoCedula] = useState(false)

  const cargarAnalisis = useCallback(async (showToast = false) => {
    setCargandoUniverso(true)
    try {
      const meta = await obtenerUniversoCobranzas()
      setUniversoMeta(meta)
      const lista = await listarCedulasUniverso()
      setCedulasUniverso(lista.cedulas || [])
      if (meta.cantidad > 0) {
        const data = await obtenerAnalisisUniversoCobranzas()
        setAnalisis(data)
        if (data.meta) setUniversoMeta(data.meta)
      } else {
        setAnalisis(null)
      }
      if (showToast) toast.success('Universo actualizado')
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : 'Error al cargar universo'
      )
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

  const totalVencido = useMemo(
    () => buckets.reduce((acc, b) => acc + (b.monto_usd || 0), 0),
    [buckets]
  )

  const totalPrestamosVencidos = useMemo(
    () => buckets.reduce((acc, b) => acc + (b.cantidad || 0), 0),
    [buckets]
  )

  /** Variacion % vs ayer y vs hace 7 dias (serie diaria reconstruida). */
  const variacionesKpi = useMemo(() => {
    const serie = analisis?.serie_diaria || []
    const empty = {
      total: { dia: null as number | null, semana: null as number | null },
      '1': { dia: null as number | null, semana: null as number | null },
      '2': { dia: null as number | null, semana: null as number | null },
      '3': { dia: null as number | null, semana: null as number | null },
      '4plus': { dia: null as number | null, semana: null as number | null },
    }
    if (serie.length < 2) return empty
    const hoy = serie[serie.length - 1]
    const ayer = serie[serie.length - 2]
    const semana = serie.length >= 8 ? serie[serie.length - 8] : null
    const keys: Array<'total' | BucketKey> = ['total', '1', '2', '3', '4plus']
    const out = { ...empty }
    for (const k of keys) {
      const sk: SerieMontoKey = k === 'total' ? 'total' : BUCKET_SERIE_KEY[k]
      const a = montoSerieDia(hoy, sk)
      const d = montoSerieDia(ayer, sk)
      const s = semana ? montoSerieDia(semana, sk) : null
      out[k] = {
        dia: pctVariacion(a, d),
        semana: s == null ? null : pctVariacion(a, s),
      }
    }
    return out
  }, [analisis])

  const onFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setSubiendo(true)
    try {
      const res = await uploadUniversoCobranzas(file)
      setUniversoMeta(res.meta)
      toast.success(
        `Excel fusionado: ${res.agregadas} nuevas (${res.cantidad} total)`
      )
      await cargarAnalisis(false)
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : 'Error al subir Excel'
      )
    } finally {
      setSubiendo(false)
    }
  }

  const onLimpiar = async () => {
    if (!universoMeta?.cantidad) {
      toast.error('No hay universo cargado')
      return
    }
    if (
      !window.confirm(
        'Se eliminara toda la lista permanente de cedulas y los snapshots diarios. Continuar?'
      )
    ) {
      return
    }
    setLimpiando(true)
    try {
      const res = await limpiarUniversoCobranzas()
      setUniversoMeta({ cantidad: 0, cargado_en: null })
      setCedulasUniverso([])
      setAnalisis(null)
      toast.success(`Universo eliminado (${res.eliminados} filas)`)
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : 'Error al limpiar universo'
      )
    } finally {
      setLimpiando(false)
    }
  }

  const onAgregarCedula = async () => {
    const raw = cedulaUniversoInput.trim()
    if (!raw) {
      toast.error('Ingrese una cedula')
      return
    }
    setEditandoCedula(true)
    try {
      const res = await agregarCedulaUniverso(raw)
      setCedulaUniversoInput('')
      if (res.agregada) {
        toast.success(`Cedula agregada (${res.cantidad} total)`)
      } else {
        toast.success('La cedula ya estaba en la lista')
      }
      await cargarAnalisis(false)
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : 'Error al agregar cedula'
      )
    } finally {
      setEditandoCedula(false)
    }
  }

  const onEliminarCedula = async () => {
    const raw = cedulaUniversoInput.trim()
    if (!raw) {
      toast.error('Ingrese una cedula')
      return
    }
    setEditandoCedula(true)
    try {
      const res = await eliminarCedulaUniverso(raw)
      if (res.eliminada) {
        toast.success(`Cedula eliminada (${res.cantidad} total)`)
        setCedulaUniversoInput('')
      } else {
        toast.error('Cedula no encontrada en la lista')
      }
      await cargarAnalisis(false)
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : 'Error al eliminar cedula'
      )
    } finally {
      setEditandoCedula(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Cobranzas</h1>
        <p className="mt-1 text-sm text-slate-600">
          Universo permanente de cedulas y analisis de cuotas vencidas.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileSpreadsheet className="h-5 w-5" />
            Universo Excel
          </CardTitle>
          <CardDescription>
            Lista permanente de cedulas (BD). El Excel agrega sin borrar las
            existentes.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={onFileSelected}
            />
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={subiendo || cargandoUniverso}
            >
              {subiendo ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Subiendo...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Subir Excel
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => void cargarAnalisis(true)}
              disabled={cargandoUniverso || subiendo}
            >
              {cargandoUniverso ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Actualizar
            </Button>
            <Button
              variant="outline"
              className="text-red-700 hover:bg-red-50"
              onClick={() => void onLimpiar()}
              disabled={limpiando || !universoMeta?.cantidad}
            >
              {limpiando ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Limpiar
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              className="max-w-xs"
              placeholder="V12345678"
              value={cedulaUniversoInput}
              onChange={e => setCedulaUniversoInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  void onAgregarCedula()
                }
              }}
              disabled={editandoCedula || subiendo}
            />
            <Button
              variant="secondary"
              onClick={() => void onAgregarCedula()}
              disabled={editandoCedula || subiendo}
            >
              Agregar
            </Button>
            <Button
              variant="outline"
              className="text-red-700 hover:bg-red-50"
              onClick={() => void onEliminarCedula()}
              disabled={editandoCedula || subiendo}
            >
              Eliminar
            </Button>
          </div>
          <div className="flex flex-wrap gap-4 text-sm text-slate-600">
            <span>
              Cedulas:{' '}
              <strong className="text-slate-900">
                {universoMeta?.cantidad ?? cedulasUniverso.length}
              </strong>
            </span>
            <span>
              Cargado:{' '}
              <strong className="text-slate-900">
                {formatCargadoEn(universoMeta?.cargado_en)}
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

      {analisis && (universoMeta?.cantidad ?? 0) > 0 && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <Card className="border-slate-200 bg-slate-50 sm:col-span-2 xl:col-span-1">
              <CardHeader className="pb-2">
                <CardDescription>Resumen vencidos</CardDescription>
                <CardTitle className="text-xl">
                  {formatCurrency(totalVencido)}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-1 text-sm text-slate-700">
                <p className="font-medium text-slate-700">
                  {totalPrestamosVencidos} prestamos con cuotas vencidas
                </p>
                <VariacionesTarjeta
                  diaPct={variacionesKpi.total.dia}
                  semanaPct={variacionesKpi.total.semana}
                />
              </CardContent>
            </Card>
            {BUCKET_KEYS.map(k => {
              const b = bucketsByKey[k] || emptyBucket(k)
              const v = variacionesKpi[k]
              return (
                <Card key={k} className={`border-t-4 ${BUCKET_ACCENT[k]}`}>
                  <CardHeader className="pb-2">
                    <CardDescription>{BUCKET_LABELS[k]}</CardDescription>
                    <CardTitle className="text-lg">
                      {formatCurrency(b.monto_usd)}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-1 text-sm text-slate-700">
                    <p className="font-medium text-slate-700">
                      {b.cantidad} prestamos
                    </p>
                    <VariacionesTarjeta
                      diaPct={v.dia}
                      semanaPct={v.semana}
                    />
                  </CardContent>
                </Card>
              )
            })}
          </div>

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
              Saldo vencido USD reconstruido desde el universo Excel.
            </p>
            {chartData.length === 0 ? (
              <p className="py-6 text-center text-slate-500">
                Sin datos de serie diaria.
              </p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                  <SerieDiariaLineCard
                    title="1 cuota"
                    description="Saldo vencido USD; eje Y propio del segmento."
                    data={chartData}
                    dataKey="monto_1"
                    name="1 cuota"
                    color={LINE_COLORS.monto_1}
                    yDomain={yDomain1}
                  />
                  <SerieDiariaLineCard
                    title="2 cuotas"
                    description="Saldo vencido USD; eje Y propio del segmento."
                    data={chartData}
                    dataKey="monto_2"
                    name="2 cuotas"
                    color={LINE_COLORS.monto_2}
                    yDomain={yDomain2}
                  />
                  <SerieDiariaLineCard
                    title="3 cuotas"
                    description="Saldo vencido USD; eje Y propio del segmento."
                    data={chartData}
                    dataKey="monto_3"
                    name="3 cuotas"
                    color={LINE_COLORS.monto_3}
                    yDomain={yDomain3}
                  />
                  <SerieDiariaLineCard
                    title="4 o mas cuotas"
                    description="Saldo vencido USD; eje Y propio del segmento."
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
                Suma de 1 + 2 + 3 + 4 o mas cuotas vencidas (USD) por dia.
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
                      <linearGradient id="fillTotalDeuda" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0f766e" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#0f766e" stopOpacity={0.02} />
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
