import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  FileSpreadsheet,
  Loader2,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
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
  type UniversoAnalisisItem,
  type UniversoAnalisisResponse,
  type UniversoBucket,
  type UniversoMeta,
} from '../services/cobranzaService'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import { formatCurrency } from '../utils'

const BUCKET_KEYS = ['1', '2', '3', '4plus'] as const
const BUCKET_LABELS: Record<(typeof BUCKET_KEYS)[number], string> = {
  '1': '1 cuota',
  '2': '2 cuotas',
  '3': '3 cuotas',
  '4plus': '4+ cuotas',
}
const LINE_COLORS = {
  monto_1: '#2563eb',
  monto_2: '#d97706',
  monto_3: '#dc2626',
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

  const maxRows = useMemo(
    () => Math.max(0, ...buckets.map(b => b.items.length)),
    [buckets]
  )

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

  const renderItemCell = (item?: UniversoAnalisisItem) => {
    if (!item) {
      return <span className="text-slate-300">-</span>
    }
    return (
      <div className="space-y-0.5">
        <div className="font-medium text-slate-800">{item.cedula}</div>
        <div className="text-xs text-amber-800">
          {formatCurrency(item.saldo_vencido_usd)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Cobranzas</h1>
        <p className="mt-1 text-sm text-slate-600">
          Cargue el universo Excel y analice vencidos por cuotas.
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
          {cedulasUniverso.length > 0 && (
            <div className="max-h-28 overflow-y-auto rounded border border-slate-200 bg-slate-50 p-2">
              <div className="flex flex-wrap gap-1.5">
                {cedulasUniverso.map(c => (
                  <Badge
                    key={c}
                    variant="secondary"
                    className="cursor-pointer font-mono text-xs"
                    title="Usar en el campo"
                    onClick={() => setCedulaUniversoInput(c)}
                  >
                    {c}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {analisis && (universoMeta?.cantidad ?? 0) > 0 && (
        <>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">
                Comparativo por cuotas vencidas
              </CardTitle>
              <p className="text-sm text-slate-500">
                Cedula y saldo vencido USD por bucket (1 / 2 / 3 / 4+)
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {BUCKET_KEYS.map(k => (
                        <TableHead key={k} className="min-w-[160px]">
                          {BUCKET_LABELS[k]}
                          <span className="ml-1 font-normal text-slate-500">
                            ({buckets.find(b => b.clave === k)?.cantidad ?? 0})
                          </span>
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {maxRows === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={4}
                          className="py-8 text-center text-slate-500"
                        >
                          Sin prestamos con cuotas vencidas en el universo.
                        </TableCell>
                      </TableRow>
                    ) : (
                      Array.from({ length: maxRows }).map((_, rowIdx) => (
                        <TableRow key={rowIdx}>
                          {buckets.map(b => (
                            <TableCell key={b.clave} className="align-top">
                              {renderItemCell(b.items[rowIdx])}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))
                    )}
                    <TableRow className="bg-slate-50 font-semibold">
                      {buckets.map(b => (
                        <TableCell key={b.clave}>
                          <div className="text-xs text-slate-500">
                            {b.cantidad} prestamos
                          </div>
                          <div className="text-amber-900">
                            {formatCurrency(b.monto_usd)}
                          </div>
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">
                Desempeno diario (saldo vencido por bucket)
              </CardTitle>
              <CardDescription>
                Ultimos 30 dias hasta hoy, reconstruido desde el universo Excel.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {(analisis.serie_diaria?.length ?? 0) === 0 ? (
                <p className="py-6 text-center text-slate-500">
                  Sin datos de serie diaria (ultimos 30 dias hasta hoy).
                </p>
              ) : (
                <>
                  <div className="h-[320px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={analisis.serie_diaria}>
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="#e5e7eb"
                        />
                        <XAxis dataKey="fecha" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" />
                        <Tooltip
                          formatter={(value: number) => formatCurrency(value)}
                        />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="monto_1"
                          name="1 cuota"
                          stroke={LINE_COLORS.monto_1}
                          strokeWidth={2}
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="monto_2"
                          name="2 cuotas"
                          stroke={LINE_COLORS.monto_2}
                          strokeWidth={2}
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="monto_3"
                          name="3 cuotas"
                          stroke={LINE_COLORS.monto_3}
                          strokeWidth={2}
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="monto_4plus"
                          name="4+ cuotas"
                          stroke={LINE_COLORS.monto_4plus}
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="overflow-x-auto rounded-lg border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Fecha</TableHead>
                          <TableHead>1 cuota</TableHead>
                          <TableHead>2 cuotas</TableHead>
                          <TableHead>3 cuotas</TableHead>
                          <TableHead>4+ cuotas</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {analisis.serie_diaria.map(d => (
                          <TableRow key={d.fecha}>
                            <TableCell>{d.fecha}</TableCell>
                            <TableCell>
                              {formatCurrency(d.monto_1)}
                            </TableCell>
                            <TableCell>
                              {formatCurrency(d.monto_2)}
                            </TableCell>
                            <TableCell>
                              {formatCurrency(d.monto_3)}
                            </TableCell>
                            <TableCell>
                              {formatCurrency(d.monto_4plus)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}

    </div>
  )
}
