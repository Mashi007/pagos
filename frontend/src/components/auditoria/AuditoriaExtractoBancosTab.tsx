import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  Building2,
  Loader2,
  RefreshCw,
  BarChart3,
  FileText,
  DollarSign,
  Calendar,
} from 'lucide-react'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { toast } from 'sonner'

import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import {
  conciliacionBancosService,
  CONCILIACION_BANCOS_CATEGORIAS,
  type ConciliacionBancosMoneda,
} from '../../services/conciliacionBancosService'
import { formatCurrency } from '../../utils'

const COLORES = [
  '#0f766e',
  '#1d4ed8',
  '#b45309',
  '#7c3aed',
  '#be123c',
  '#047857',
  '#0369a1',
  '#a16207',
]

type FilaBanco = {
  banco: string
  filas: number
  monto_total: number
  pct_filas?: number
  pct_monto?: number
  fecha_min?: string | null
  fecha_max?: string | null
}

function colorBanco(idx: number): string {
  return COLORES[idx % COLORES.length]
}

function fmtNum(n: number): string {
  return n.toLocaleString('es-VE')
}

function fmtFecha(s?: string | null): string {
  if (!s) return '-'
  return s.slice(0, 10)
}

export function AuditoriaExtractoBancosTab() {
  const [loading, setLoading] = useState(true)
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')
  const [moneda, setMoneda] = useState<ConciliacionBancosMoneda | 'ALL'>('ALL')
  const [total, setTotal] = useState(0)
  const [montoTotal, setMontoTotal] = useState(0)
  const [nBancos, setNBancos] = useState(0)
  const [porBanco, setPorBanco] = useState<FilaBanco[]>([])

  const cargar = useCallback(async () => {
    try {
      setLoading(true)
      const res = await conciliacionBancosService.resumenExtracto({
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
        moneda: moneda === 'ALL' ? undefined : moneda,
      })
      setTotal(Number(res.total || 0))
      setMontoTotal(Number(res.monto_total || 0))
      setNBancos(Number(res.bancos || res.por_banco?.length || 0))
      setPorBanco(
        (res.por_banco || []).map((r) => ({
          banco: r.banco,
          filas: Number(r.filas || 0),
          monto_total: Number(r.monto_total || 0),
          pct_filas: Number(r.pct_filas || 0),
          pct_monto: Number(r.pct_monto || 0),
          fecha_min: r.fecha_min,
          fecha_max: r.fecha_max,
        }))
      )
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'No se pudo cargar el resumen'
      toast.error(msg)
      setPorBanco([])
      setTotal(0)
      setMontoTotal(0)
      setNBancos(0)
    } finally {
      setLoading(false)
    }
  }, [fechaDesde, fechaHasta, moneda])

  useEffect(() => {
    void cargar()
  }, [cargar])

  const dataPastelFilas = useMemo(
    () =>
      porBanco.map((r) => ({
        name: r.banco,
        value: r.filas,
      })),
    [porBanco]
  )

  const dataPastelMonto = useMemo(
    () =>
      porBanco.map((r) => ({
        name: r.banco,
        value: r.monto_total,
      })),
    [porBanco]
  )

  const dataBarras = useMemo(
    () =>
      [...porBanco]
        .sort((a, b) => b.filas - a.filas)
        .map((r) => ({
          banco: r.banco,
          pagos: r.filas,
          monto: r.monto_total,
        })),
    [porBanco]
  )

  const rangoFechas = useMemo(() => {
    const mins = porBanco.map((r) => r.fecha_min).filter(Boolean) as string[]
    const maxs = porBanco.map((r) => r.fecha_max).filter(Boolean) as string[]
    if (!mins.length && !maxs.length) return '-'
    const min = mins.sort()[0]
    const max = maxs.sort().slice(-1)[0]
    return `${fmtFecha(min)} - ${fmtFecha(max)}`
  }, [porBanco])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Desde</label>
          <Input
            type="date"
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
            className="w-[160px]"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Hasta</label>
          <Input
            type="date"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
            className="w-[160px]"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Moneda</label>
          <Select
            value={moneda}
            onValueChange={(v) => setMoneda(v as ConciliacionBancosMoneda | 'ALL')}
          >
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Todas</SelectItem>
              <SelectItem value="USD">USD</SelectItem>
              <SelectItem value="BS">BS</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={() => void cargar()}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Actualizar
        </Button>
        <p className="text-xs text-muted-foreground max-w-md">
          Datos de BD historica (`conciliacion_banco_extracto`). Cada Excel
          subido en Conciliacion Bancos se integra y actualiza este resumen por
          variable Banco.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {porBanco.map((r, i) => (
          <Badge
            key={r.banco}
            variant="outline"
            className="rounded-full px-3 py-1 text-sm font-medium"
            style={{ borderColor: colorBanco(i) }}
          >
            {r.banco}: {fmtNum(r.filas)}
          </Badge>
        ))}
        {!loading && porBanco.length === 0 ? (
          <span className="text-sm text-muted-foreground">
            Sin filas en extracto historico. Suba un Excel en Conciliacion Bancos.
          </span>
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pagos (filas)</p>
                <p className="text-2xl font-bold">{fmtNum(total)}</p>
              </div>
              <FileText className="h-8 w-8 text-teal-700" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Monto total</p>
                <p className="text-2xl font-bold">{formatCurrency(montoTotal)}</p>
              </div>
              <DollarSign className="h-8 w-8 text-blue-700" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Bancos</p>
                <p className="text-2xl font-bold">{fmtNum(nBancos)}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {CONCILIACION_BANCOS_CATEGORIAS.length} categorias posibles
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-amber-700" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Rango fechas</p>
                <p className="text-lg font-semibold">{rangoFechas}</p>
              </div>
              <Calendar className="h-8 w-8 text-violet-700" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 className="h-4 w-4" />
              Distribucion por cantidad
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[320px]">
            {loading ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : dataPastelFilas.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                Sin datos
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dataPastelFilas}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={95}
                    paddingAngle={2}
                  >
                    {dataPastelFilas.map((_, i) => (
                      <Cell key={`c-f-${i}`} fill={colorBanco(i)} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => [
                      `${fmtNum(Number(value || 0))} pagos`,
                      'Cantidad',
                    ]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <DollarSign className="h-4 w-4" />
              Distribucion por monto
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[320px]">
            {loading ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : dataPastelMonto.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                Sin datos
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dataPastelMonto}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={95}
                    paddingAngle={2}
                  >
                    {dataPastelMonto.map((_, i) => (
                      <Cell key={`c-m-${i}`} fill={colorBanco(i)} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => [
                      formatCurrency(Number(value || 0)),
                      'Monto',
                    ]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pagos por banco (barras)</CardTitle>
        </CardHeader>
        <CardContent className="h-[280px]">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : dataBarras.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Sin datos
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dataBarras}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="banco" />
                <YAxis />
                <Tooltip
                  formatter={(value: number, name: string) =>
                    name === 'monto'
                      ? [formatCurrency(Number(value || 0)), 'Monto']
                      : [fmtNum(Number(value || 0)), 'Pagos']
                  }
                />
                <Legend />
                <Bar dataKey="pagos" name="Pagos" fill="#0f766e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Detalle por banco</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Banco</TableHead>
                <TableHead className="text-right">Pagos</TableHead>
                <TableHead className="text-right">% pagos</TableHead>
                <TableHead className="text-right">Monto total</TableHead>
                <TableHead className="text-right">% monto</TableHead>
                <TableHead>Fecha min</TableHead>
                <TableHead>Fecha max</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {porBanco.map((r, i) => (
                <TableRow key={r.banco}>
                  <TableCell>
                    <span className="inline-flex items-center gap-2">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: colorBanco(i) }}
                      />
                      {r.banco}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {fmtNum(r.filas)}
                  </TableCell>
                  <TableCell className="text-right">
                    {(r.pct_filas ?? 0).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(r.monto_total)}
                  </TableCell>
                  <TableCell className="text-right">
                    {(r.pct_monto ?? 0).toFixed(1)}%
                  </TableCell>
                  <TableCell>{fmtFecha(r.fecha_min)}</TableCell>
                  <TableCell>{fmtFecha(r.fecha_max)}</TableCell>
                </TableRow>
              ))}
              {!loading && porBanco.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground">
                    Sin datos
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
