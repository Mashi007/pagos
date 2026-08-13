import React, { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  Database,
  Download,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
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
  type UniversoAnalisisItem,
  type UniversoAnalisisResponse,
  type UniversoBucket,
  type UniversoMeta,
} from '../services/cobranzaService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { formatCurrency } from '../utils'
import { createAndDownloadExcel } from '../types/exceljs'

/** Tabla + detalle: solo segmentos exactos 1..15 cuotas. */
const DETALLE_BUCKET_KEYS = [
  ...Array.from({ length: 15 }, (_, i) => String(i + 1)),
] as const
type DetalleBucketKey = (typeof DETALLE_BUCKET_KEYS)[number]

function labelDetalleBucket(key: string): string {
  const n = Number(key)
  if (n === 1) return '1 cuota'
  if (n >= 2 && n <= 15) return `${n} cuotas`
  return key
}

/** Semáforo vs columna previa: cualquier alza = rojo, cualquier baja = verde. */
type SemaforoMonto = 'rojo' | 'verde'

function semaforoMontoVsAnterior(
  actual: number,
  anterior: number | undefined
): SemaforoMonto | null {
  if (anterior === undefined || !Number.isFinite(anterior) || !Number.isFinite(actual)) {
    return null
  }
  const delta = actual - anterior
  if (Math.abs(delta) < 0.005) return null
  return delta > 0 ? 'rojo' : 'verde'
}

function semaforoCeldaClass(tono: SemaforoMonto | null): string {
  if (tono === 'rojo') return 'bg-red-500 text-white'
  if (tono === 'verde') return 'bg-emerald-500 text-white'
  return ''
}

function SemaforoMarca({
  tono,
  invert = false,
}: {
  tono: SemaforoMonto
  invert?: boolean
}) {
  const color = invert
    ? 'text-white'
    : tono === 'rojo'
      ? 'text-red-500'
      : 'text-emerald-500'
  const cls = `inline-block h-3.5 w-3.5 shrink-0 ${color}`
  if (tono === 'rojo') return <ArrowUp className={cls} strokeWidth={3} aria-hidden />
  return <ArrowDown className={cls} strokeWidth={3} aria-hidden />
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
  for (const k of DETALLE_BUCKET_KEYS) {
    const b = data.buckets?.[k]
    const lecturas = b?.lecturas?.length
      ? b.lecturas
      : (data.columnas || []).map(col => ({
          fecha: col.fecha,
          cantidad: 0,
          monto_usd: 0,
        }))
    rows.push({ key: k, label: labelDetalleBucket(k), lecturas })
  }
  const bordeBloque = 'border-l border-slate-300'
  return (
    <Card className="border-slate-200">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Desempeño de cobranzas</CardTitle>
        <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1">
            <ArrowUp className="h-3.5 w-3.5 text-red-500" strokeWidth={3} />
            subió
          </span>
          <span className="inline-flex items-center gap-1">
            <ArrowDown className="h-3.5 w-3.5 text-emerald-500" strokeWidth={3} />
            bajó
          </span>
          <span className="text-slate-400">(cualquier cambio vs columna anterior)</span>
        </p>
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
                    const esHoy = Boolean(columnas[i]?.es_hoy)
                    const resaltar = esHoy || columnas[i]?.es_ayer
                    const semaforo = semaforoMontoVsAnterior(
                      Number(L.monto_usd),
                      i > 0 ? Number(lecturas[i - 1]?.monto_usd) : undefined
                    )
                    const celdaHoy = esHoy ? semaforoCeldaClass(semaforo) : ''
                    const titleHoy = esHoy
                      ? semaforo === 'rojo'
                        ? 'Subió vs columna anterior'
                        : semaforo === 'verde'
                          ? 'Bajó vs columna anterior'
                          : undefined
                      : undefined
                    return (
                      <Fragment key={`${key}-${L.fecha}`}>
                        <td
                          className={`py-2.5 px-2 text-right tabular-nums ${bordeBloque} ${
                            celdaHoy ||
                            (resaltar ? 'bg-slate-50/80 text-slate-900' : 'text-slate-900')
                          }`}
                          title={titleHoy}
                        >
                          {L.cantidad}
                        </td>
                        <td
                          className={`py-2.5 px-2 text-right tabular-nums ${
                            celdaHoy ||
                            (resaltar ? 'bg-slate-50/80 text-slate-700' : 'text-slate-700')
                          }`}
                          title={titleHoy}
                        >
                          <span className="inline-flex items-center justify-end gap-1">
                            {semaforo ? (
                              <SemaforoMarca tono={semaforo} invert={esHoy} />
                            ) : null}
                            <span className={key === 'total' ? '' : 'font-normal'}>
                              {formatCurrency(L.monto_usd)}
                            </span>
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

/**
 * Añade `tendencia`: regresión lineal por índice (0..n-1) sobre `valueKey`.
 * Valores mostrados no negativos. Con menos de 2 puntos, coincide con el dato.
 */
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

type DetalleFila = UniversoAnalisisItem & {
  bucket: DetalleBucketKey
  bucket_label: string
}

const ATRASO_BIN_DIAS = 30
const ATRASO_N_BINS = 20
const ATRASO_MAX_DIAS = ATRASO_N_BINS * ATRASO_BIN_DIAS

function etiquetaBinAtraso(i: number): string {
  if (i >= ATRASO_N_BINS) return '>600 días'
  const desde = i * ATRASO_BIN_DIAS + 1
  const hasta = Math.min((i + 1) * ATRASO_BIN_DIAS, ATRASO_MAX_DIAS)
  return `${desde}–${hasta}`
}

function distribucionAtrasoDias(
  bucketsByKey: Record<string, UniversoBucket>
): Array<{
  label: string
  casos: number
  monto_usd: number
}> {
  const nBins = ATRASO_N_BINS + 1
  const casos = Array.from({ length: nBins }, () => 0)
  const montos = Array.from({ length: nBins }, () => 0)
  for (const k of DETALLE_BUCKET_KEYS) {
    const items = bucketsByKey[k]?.items || []
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

function TooltipAtrasoDias({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ name?: string; value?: number; color?: string; payload?: { monto_usd?: number } }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  const monto = Number(payload[0]?.payload?.monto_usd) || 0
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-semibold text-slate-700">{label} días</div>
      {payload.map(p => (
        <div key={String(p.name)} className="flex items-center gap-2">
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
      <div className="mt-1 text-slate-500">Saldo: {formatCurrency(monto)}</div>
    </div>
  )
}

function DetalleBucketsPanel({
  bucketsByKey,
}: {
  bucketsByKey: Record<string, UniversoBucket>
}) {
  const [filtroCuotas, setFiltroCuotas] = useState<string>('todas')
  const [diasDesde, setDiasDesde] = useState('')
  const [diasHasta, setDiasHasta] = useState('')
  const [exportando, setExportando] = useState(false)

  const filasBase = useMemo(() => {
    const out: DetalleFila[] = []
    for (const k of DETALLE_BUCKET_KEYS) {
      const bucket = bucketsByKey[k] || emptyBucket(k)
      for (const item of bucket.items || []) {
        out.push({
          ...item,
          bucket: k,
          bucket_label: labelDetalleBucket(k),
        })
      }
    }
    return out
  }, [bucketsByKey])

  const filas = useMemo(() => {
    const dMinRaw = diasDesde.trim()
    const dMaxRaw = diasHasta.trim()
    const dMin = dMinRaw === '' ? null : Number(dMinRaw)
    const dMax = dMaxRaw === '' ? null : Number(dMaxRaw)
    const hasMin = dMin !== null && Number.isFinite(dMin)
    const hasMax = dMax !== null && Number.isFinite(dMax)
    return filasBase.filter(row => {
      if (filtroCuotas !== 'todas' && row.bucket !== filtroCuotas) return false
      const dias = Number(row.dias_atraso_max ?? 0)
      if (hasMin && dias < (dMin as number)) return false
      if (hasMax && dias > (dMax as number)) return false
      return true
    })
  }, [filasBase, filtroCuotas, diasDesde, diasHasta])

  const hayFiltroActivo =
    filtroCuotas !== 'todas' ||
    diasDesde.trim() !== '' ||
    diasHasta.trim() !== ''

  const filasVisibles = useMemo(() => {
    if (hayFiltroActivo) return filas
    return filas.slice(0, 5)
  }, [filas, hayFiltroActivo])

  const montoFiltrado = useMemo(
    () =>
      Math.round(
        filas.reduce((s, r) => s + (Number(r.saldo_vencido_usd) || 0), 0) * 100
      ) / 100,
    [filas]
  )

  const descargarExcel = async () => {
    if (filas.length === 0) {
      toast.error('No hay filas con los filtros actuales')
      return
    }
    setExportando(true)
    try {
      const rows = filas.map(r => ({
        Segmento: r.bucket_label,
        'Cuotas atrasadas': r.cuotas_vencidas,
        'Dias atraso min': Number(r.dias_atraso_min) || 0,
        'Dias atraso max': Number(r.dias_atraso_max) || 0,
        Cedula: r.cedula,
        Nombre: r.nombres || '',
        'Saldo vencido USD': Number(r.saldo_vencido_usd) || 0,
        'Prestamo ID': r.prestamo_id,
      }))
      const stamp = new Date().toISOString().slice(0, 10)
      await createAndDownloadExcel(
        rows,
        'Detalle',
        `cobranzas_detalle_segmentos_${stamp}.xlsx`
      )
      toast.success(`Excel: ${filas.length} filas`)
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al exportar Excel')
    } finally {
      setExportando(false)
    }
  }

  return (
    <Card>
      <CardHeader className="space-y-3 pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-lg">Detalle por segmento</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              {filas.length} / {filasBase.length} prestamos
            </Badge>
            <span className="text-sm font-semibold text-slate-900">
              {formatCurrency(montoFiltrado)}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={exportando || filas.length === 0}
              onClick={() => void descargarExcel()}
            >
              {exportando ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Excel
            </Button>
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <Select value={filtroCuotas} onValueChange={setFiltroCuotas}>
            <SelectTrigger className="h-9" aria-label="Filtrar por segmento">
              <SelectValue placeholder="Segmento" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todas">Todos los segmentos</SelectItem>
              {DETALLE_BUCKET_KEYS.map(k => (
                <SelectItem key={k} value={k}>
                  {labelDetalleBucket(k)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            className="h-9 text-sm"
            type="number"
            min={0}
            inputMode="numeric"
            placeholder="Días atraso desde…"
            value={diasDesde}
            onChange={e => setDiasDesde(e.target.value)}
            aria-label="Días de atraso desde"
          />
          <Input
            className="h-9 text-sm"
            type="number"
            min={0}
            inputMode="numeric"
            placeholder="Días atraso hasta…"
            value={diasHasta}
            onChange={e => setDiasHasta(e.target.value)}
            aria-label="Días de atraso hasta"
          />
        </div>
        <p className="text-xs text-slate-500">
          Días de atraso = hoy − fecha de vencimiento (usa el máximo del
          préstamo). Excel exporta el resultado filtrado.
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        {!hayFiltroActivo && filas.length > 5 ? (
          <p className="mb-2 text-xs text-slate-500">
            Mostrando 5 de {filas.length}. Use filtros para buscar.
          </p>
        ) : null}
        <div
          className={`overflow-auto rounded-md border border-slate-100 ${
            hayFiltroActivo ? 'max-h-[420px]' : 'max-h-[220px]'
          }`}
        >
          {filas.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-slate-400">
              {filasBase.length === 0 ? 'Sin casos' : 'Sin coincidencias'}
            </p>
          ) : (
            <table className="w-full min-w-[720px] border-collapse text-sm">
              <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr className="border-b border-slate-200">
                  <th className="px-3 py-2 font-semibold">Segmento</th>
                  <th className="px-3 py-2 font-semibold">Cédula</th>
                  <th className="px-3 py-2 font-semibold">Nombre</th>
                  <th className="px-3 py-2 font-semibold text-right">
                    Días atraso
                  </th>
                  <th className="px-3 py-2 font-semibold text-right">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {filasVisibles.map(row => (
                  <tr
                    key={`${row.bucket}-${row.prestamo_id}-${row.cedula}`}
                    className="border-b border-slate-100"
                  >
                    <td className="px-3 py-2 text-slate-600">
                      {row.bucket_label}
                    </td>
                    <td className="px-3 py-2 font-mono text-slate-800">
                      {row.cedula}
                    </td>
                    <td className="max-w-[240px] truncate px-3 py-2 text-slate-600">
                      {row.nombres || '—'}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-slate-700">
                      {Number(row.dias_atraso_max) || 0}
                    </td>
                    <td className="px-3 py-2 text-right font-medium text-amber-800">
                      {formatCurrency(row.saldo_vencido_usd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
    return DETALLE_BUCKET_KEYS.map(k => raw[k] || emptyBucket(k))
  }, [analisis])

  const bucketsByKey = useMemo(() => {
    const map: Record<string, UniversoBucket> = {}
    for (const b of buckets) {
      map[b.clave] = b
    }
    return map
  }, [buckets])

  const chartData = useMemo(() => {
    return (analisis?.serie_diaria || []).map(d => {
      const m1 = Number(d.monto_1) || 0
      const m2 = Number(d.monto_2) || 0
      const m3 = Number(d.monto_3) || 0
      const m4 = Number(d.monto_4) || 0
      const m5 = Number(d.monto_5) || 0
      const m6 = Number(d.monto_6plus) || 0
      return {
        ...d,
        fecha_label: formatFechaCorta(String(d.fecha)),
        total_deuda: Math.round((m1 + m2 + m3 + m4 + m5 + m6) * 100) / 100,
      }
    })
  }, [analisis])

  const chartDataTotalTendencia = useMemo(
    () => serieConTendenciaLineal(chartData, 'total_deuda'),
    [chartData]
  )
  const yDomainTotal = useMemo(
    () =>
      yDomainFromSeries(
        chartDataTotalTendencia as Array<Record<string, unknown>>,
        ['total_deuda', 'tendencia']
      ),
    [chartDataTotalTendencia]
  )

  const distAtrasoDias = useMemo(
    () => distribucionAtrasoDias(bucketsByKey),
    [bucketsByKey]
  )

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Cobranzas</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Database className="h-5 w-5" />
            Cartera completa (BD)
          </CardTitle>
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

          <DetalleBucketsPanel bucketsByKey={bucketsByKey} />

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">
                Distribución del atraso en días
              </CardTitle>
              <p className="text-xs text-slate-500">
                Cada barra agrupa préstamos según cuántos días llevan de atraso
                (hoy − vencimiento más antiguo), en tramos de 30 días, hasta 600
                días.
              </p>
            </CardHeader>
            <CardContent>
              {distAtrasoDias.every(d => d.casos === 0) ? (
                <p className="py-6 text-center text-slate-500">
                  Sin casos para graficar.
                </p>
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
                      />
                      <Tooltip content={<TooltipAtrasoDias />} />
                      <Legend />
                      <Bar
                        dataKey="casos"
                        name="Casos"
                        fill="#2563eb"
                        radius={[3, 3, 0, 0]}
                        maxBarSize={28}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          <div>
            <h2 className="mb-4 text-lg font-semibold text-slate-900">
              Desempeño diario (30 días)
            </h2>
            {chartData.length === 0 ? (
              <p className="py-6 text-center text-slate-500">
                Sin datos de serie diaria.
              </p>
            ) : (
              <div>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">
                      Deuda total diaria (30 días)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart
                          data={chartDataTotalTendencia}
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
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
