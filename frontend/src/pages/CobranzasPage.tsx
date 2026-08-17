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
  if (tono === 'rojo') return 'bg-red-800 text-white font-semibold'
  if (tono === 'verde') return 'bg-emerald-800 text-white font-semibold'
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

function lecturasCobranzas(
  lecturas: Array<{
    fecha: string
    cantidad_cobrada?: number
    cobrado_usd?: number
  }>
) {
  return lecturas.map(L => ({
    fecha: L.fecha,
    cantidad: Number(L.cantidad_cobrada || 0),
    monto_usd: Number(L.cobrado_usd || 0),
  }))
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
    kind: 'vencidos' | 'cobranzas'
    lecturas: Array<{
      fecha: string
      cantidad: number
      monto_usd: number
      cantidad_cobrada?: number
      cobrado_usd?: number
    }>
  }> = []
  if (data.total?.lecturas?.length) {
    rows.push({
      key: 'total',
      label: 'Total vencidos',
      kind: 'vencidos',
      lecturas: data.total.lecturas,
    })
    rows.push({
      key: 'total-cobranzas',
      label: 'Total cobranzas',
      kind: 'cobranzas',
      lecturas: lecturasCobranzas(data.total.lecturas),
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
          cantidad_cobrada: 0,
          cobrado_usd: 0,
        }))
    rows.push({
      key: k,
      label: labelDetalleBucket(k),
      kind: 'vencidos',
      lecturas,
    })
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
        <p className="mt-1 text-xs text-slate-500">
          Total vencidos: foto al cierre de cada fecha. Acumulado del mes en
          curso = cierre de ayer (no el 1 del mes). Total cobranzas: pagos
          reales del 1 al ayer en Acumulado; hoy y ayer, solo ese día.
        </p>
      </CardHeader>
      <CardContent className="pt-2">
        <div className="max-h-[min(72vh,40rem)] overflow-auto">
          <table className="w-full min-w-[960px] border-separate border-spacing-0 text-sm">
            <thead className="sticky top-0 z-20 bg-white shadow-[0_2px_6px_rgba(15,23,42,0.08)]">
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th
                  rowSpan={2}
                  className="py-2 pr-3 align-bottom font-semibold border-r border-b border-slate-300 bg-white"
                >
                  Bucket
                </th>
                {columnas.map((col) => (
                  <th
                    key={col.fecha}
                    colSpan={2}
                    className={`py-2 px-2 text-center font-semibold border-b border-slate-200 ${bordeBloque} ${
                      col.es_hoy
                        ? 'bg-slate-100 text-slate-900'
                        : col.es_ayer
                          ? 'bg-slate-50 text-slate-800'
                          : 'bg-white text-slate-600'
                    }`}
                  >
                    {col.etiqueta}
                  </th>
                ))}
              </tr>
              <tr className="text-xs uppercase tracking-wide text-slate-500">
                {columnas.map((col) => (
                  <Fragment key={`${col.fecha}-sub`}>
                    <th
                      className={`py-1.5 px-2 font-semibold text-right border-b border-slate-200 ${bordeBloque} ${
                        col.es_hoy || col.es_ayer ? 'bg-slate-50' : 'bg-white'
                      }`}
                    >
                      Cantidad
                    </th>
                    <th
                      className={`py-1.5 px-2 font-semibold text-right border-b border-slate-200 ${
                        col.es_hoy || col.es_ayer ? 'bg-slate-50' : 'bg-white'
                      }`}
                    >
                      Monto
                    </th>
                  </Fragment>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(({ key, label, kind, lecturas }) => {
                const esCobranzas = kind === 'cobranzas'
                return (
                <tr
                  key={key}
                  className={`border-b border-slate-100 ${
                    key === 'total'
                      ? 'bg-slate-50 font-semibold'
                      : esCobranzas
                        ? 'bg-emerald-50 font-semibold'
                        : ''
                  }`}
                >
                  <td className="py-2.5 pr-3 text-slate-800 border-r border-slate-300">
                    {label}
                  </td>
                  {lecturas.map((L, i) => {
                    const esHoy = Boolean(columnas[i]?.es_hoy)
                    const resaltar = esHoy || columnas[i]?.es_ayer
                    const semaforoRaw = semaforoMontoVsAnterior(
                      Number(L.monto_usd),
                      i > 0 ? Number(lecturas[i - 1]?.monto_usd) : undefined
                    )
                    const semaforo =
                      esCobranzas && semaforoRaw
                        ? semaforoRaw === 'rojo'
                          ? 'verde'
                          : 'rojo'
                        : semaforoRaw
                    const celdaHoy = esHoy ? semaforoCeldaClass(semaforo) : ''
                    const titleHoy = esHoy
                      ? semaforo === 'rojo'
                        ? esCobranzas
                          ? 'Bajó vs columna anterior'
                          : 'Subió vs columna anterior'
                        : semaforo === 'verde'
                          ? esCobranzas
                            ? 'Subió vs columna anterior'
                            : 'Bajó vs columna anterior'
                          : undefined
                      : undefined
                    const cobradoCaso = Number(L.cobrado_usd || 0)
                    const esUltimaCol = i === lecturas.length - 1
                    const cobradoTextoCls = celdaHoy
                      ? 'text-[11px] font-semibold text-white'
                      : esUltimaCol
                        ? 'text-[11px] font-semibold text-emerald-950'
                        : 'text-[11px] font-normal text-emerald-800'
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
                          <span className="inline-flex flex-col items-end gap-0.5">
                            <span className="inline-flex items-center justify-end gap-1">
                              {semaforo ? (
                                <SemaforoMarca tono={semaforo} invert={esHoy} />
                              ) : null}
                              <span
                                className={
                                  key === 'total' || esCobranzas ? '' : 'font-normal'
                                }
                              >
                                {formatCurrency(L.monto_usd)}
                              </span>
                            </span>
                            {!esCobranzas && key !== 'total' ? (
                              <span className={cobradoTextoCls}>
                                cobrado {formatCurrency(cobradoCaso)}
                              </span>
                            ) : null}
                          </span>
                        </td>
                      </Fragment>
                    )
                  })}
                </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

type DetalleFila = UniversoAnalisisItem & {
  bucket: DetalleBucketKey
  bucket_label: string
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
        </>
      )}
    </div>
  )
}
