import { useCallback, useEffect, useMemo, useState } from 'react'

import { Loader2, RefreshCw, FileText, DollarSign } from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  Cell,
} from 'recharts'
import { toast } from 'sonner'

import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'
import { conciliacionBancosService } from '../../services/conciliacionBancosService'
import { formatCurrency } from '../../utils'

const COLORES = [
  '#0d9488',
  '#2563eb',
  '#d97706',
  '#7c3aed',
  '#e11d48',
  '#059669',
  '#0284c7',
  '#ca8a04',
]

type Fila = {
  banco: string
  filas: number
  monto_total: number
}

type PuntoSerie = {
  fecha: string
  label: string
  cantidad: number
  monto_usd: number
}

function colorBanco(i: number): string {
  return COLORES[i % COLORES.length]
}

function fmtNum(n: number): string {
  return n.toLocaleString('es-VE')
}

/** Regla: solo montos USD > 0 en resumenes SIN_BD. */
function montoPositivo(n: number): number {
  const v = Number(n || 0)
  return v > 0 ? v : 0
}

const POLL_MS = 30000

export function AuditoriaExtractoBancosTab() {
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [montoTotal, setMontoTotal] = useState(0)
  const [porBanco, setPorBanco] = useState<Fila[]>([])
  const [serie, setSerie] = useState<PuntoSerie[]>([])
  const [actualizado, setActualizado] = useState('')

  const cargar = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true)
      const res = await conciliacionBancosService.resumenSinBd(null)
      setTotal(Number(res.total || 0))
      setMontoTotal(montoPositivo(Number(res.monto_total || 0)))
      setPorBanco(
        (res.por_banco || []).map((r) => ({
          banco: r.banco,
          filas: Number(r.filas || 0),
          monto_total: montoPositivo(Number(r.monto_total || 0)),
        }))
      )
      setSerie(
        (res.serie_diaria || []).map(
          (p) => ({
            fecha: p.fecha,
            label: p.label,
            cantidad: Number(p.cantidad || 0),
            monto_usd: montoPositivo(Number(p.monto_usd || 0)),
          })
        )
      )
      setActualizado(new Date().toLocaleTimeString('es-VE'))
    } catch (err: unknown) {
      if (!silent) {
        toast.error(
          err instanceof Error ? err.message : 'No se pudo cargar SIN_BD'
        )
      }
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    void cargar(false)
    const id = window.setInterval(() => void cargar(true), POLL_MS)
    return () => window.clearInterval(id)
  }, [cargar])

  const dataBarrasUsd = useMemo(
    () =>
      [...porBanco]
        .sort((a, b) => b.monto_total - a.monto_total)
        .map((r, i) => ({
          banco: r.banco,
          usd: r.monto_total,
          fill: colorBanco(i),
        })),
    [porBanco]
  )

  const dataBarrasCantidad = useMemo(
    () =>
      [...porBanco]
        .sort((a, b) => b.filas - a.filas)
        .map((r, i) => ({
          banco: r.banco,
          cantidad: r.filas,
          fill: colorBanco(i),
        })),
    [porBanco]
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Badge
          variant="outline"
          className="rounded-full border-slate-400 px-4 py-1.5 text-base font-semibold text-slate-900"
        >
          SIN_BD: {fmtNum(total)}
        </Badge>
        <span className="text-sm font-medium text-slate-700">
          Pagos no reportados (SIN_BD) por banco. Auto-actualiza al conciliar.
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void cargar(false)}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Actualizar
        </Button>
        {actualizado ? (
          <span className="text-xs font-medium text-slate-600">
            Actualizado {actualizado}
          </span>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {porBanco.map((r, i) => (
          <Badge
            key={r.banco}
            variant="outline"
            className="rounded-full border-2 px-3 py-1 text-sm font-semibold text-slate-900"
            style={{ borderColor: colorBanco(i) }}
          >
            {r.banco}: {fmtNum(r.filas)} · {formatCurrency(r.monto_total)}
          </Badge>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-700">
                  Cantidad de pagos SIN_BD
                </p>
                <p className="text-3xl font-bold text-slate-900">
                  {fmtNum(total)}
                </p>
              </div>
              <FileText className="h-9 w-9 text-teal-700" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-700">
                  Total USD SIN_BD
                </p>
                <p className="text-3xl font-bold text-slate-900">
                  {formatCurrency(montoTotal)}
                </p>
              </div>
              <DollarSign className="h-9 w-9 text-blue-700" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold text-slate-900">
              Totales USD SIN_BD - hoy y 5 dias atras
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[360px]">
            {loading ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
              </div>
            ) : serie.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm font-medium text-slate-700">
                Sin serie diaria aun. Conciliar para registrar el total de hoy.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={serie}
                  margin={{ top: 12, right: 20, left: 8, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: '#0f172a', fontSize: 12, fontWeight: 700 }}
                    axisLine={{ stroke: '#64748b' }}
                  />
                  <YAxis
                    domain={[0, 'dataMax']}
                    tick={{ fill: '#0f172a', fontSize: 12, fontWeight: 600 }}
                    axisLine={{ stroke: '#64748b' }}
                    tickFormatter={(v) => {
                      const n = montoPositivo(Number(v || 0))
                      if (n >= 1000000) return '$' + (n / 1000000).toFixed(1) + 'M'
                      if (n >= 1000) return '$' + (n / 1000).toFixed(0) + 'k'
                      return '$' + String(n)
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#fff',
                      border: '1px solid #334155',
                      borderRadius: 8,
                      color: '#0f172a',
                      fontWeight: 600,
                    }}
                    formatter={(value: number) => [
                      formatCurrency(montoPositivo(Number(value || 0))),
                      'USD',
                    ]}
                  />
                  <Legend
                    formatter={() => (
                      <span className="font-semibold text-slate-900">USD</span>
                    )}
                  />
                  <Line
                    type="monotone"
                    dataKey="monto_usd"
                    name="USD"
                    stroke="#2563eb"
                    strokeWidth={3}
                    dot={{ r: 5, fill: '#1d4ed8', stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 7 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold text-slate-900">
              Pagos no reportados por banco
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[360px]">
            {loading ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
              </div>
            ) : dataBarrasUsd.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm font-medium text-slate-700">
                Sin montos USD por banco
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={dataBarrasUsd}
                  layout="vertical"
                  margin={{ top: 8, right: 36, left: 8, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                  <XAxis
                    type="number"
                    domain={[0, 'dataMax']}
                    allowDataOverflow={false}
                    tick={{ fill: '#0f172a', fontSize: 12, fontWeight: 600 }}
                    axisLine={{ stroke: '#64748b' }}
                    tickFormatter={(v) => {
                      const n = montoPositivo(Number(v || 0))
                      if (n >= 1000000) return '$' + (n / 1000000).toFixed(1) + 'M'
                      if (n >= 1000) return '$' + (n / 1000).toFixed(0) + 'k'
                      return '$' + String(n)
                    }}
                  />
                  <YAxis
                    type="category"
                    dataKey="banco"
                    width={100}
                    tick={{ fill: '#0f172a', fontSize: 13, fontWeight: 700 }}
                    axisLine={{ stroke: '#64748b' }}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(15, 23, 42, 0.06)' }}
                    contentStyle={{
                      background: '#fff',
                      border: '1px solid #334155',
                      borderRadius: 8,
                      color: '#0f172a',
                      fontWeight: 600,
                    }}
                    formatter={(value: number) => [
                      formatCurrency(Number(value || 0)),
                      'USD',
                    ]}
                  />
                  <Bar
                    dataKey="usd"
                    name="USD"
                    radius={[0, 6, 6, 0]}
                    barSize={28}
                    label={{
                      position: 'right',
                      fill: '#0f172a',
                      fontSize: 11,
                      fontWeight: 700,
                      formatter: (v: number) => formatCurrency(Number(v || 0)),
                    }}
                  >
                    {dataBarrasUsd.map((d) => (
                      <Cell key={d.banco} fill={d.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-bold text-slate-900">
            Cantidad de pagos SIN_BD por banco
          </CardTitle>
        </CardHeader>
        <CardContent className="h-[300px]">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
          ) : dataBarrasCantidad.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm font-medium text-slate-700">
              Sin datos
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={dataBarrasCantidad}
                layout="vertical"
                margin={{ top: 8, right: 28, left: 8, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                <XAxis
                  type="number"
                  tick={{ fill: '#0f172a', fontSize: 12, fontWeight: 600 }}
                />
                <YAxis
                  type="category"
                  dataKey="banco"
                  width={100}
                  tick={{ fill: '#0f172a', fontSize: 13, fontWeight: 700 }}
                />
                <Tooltip
                  contentStyle={{
                    background: '#fff',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    color: '#0f172a',
                    fontWeight: 600,
                  }}
                  formatter={(value: number) => [
                    fmtNum(Number(value || 0)),
                    'Cantidad',
                  ]}
                />
                <Bar
                  dataKey="cantidad"
                  name="Cantidad"
                  radius={[0, 6, 6, 0]}
                  barSize={24}
                  label={{
                    position: 'right',
                    fill: '#0f172a',
                    fontSize: 12,
                    fontWeight: 700,
                    formatter: (v: number) => fmtNum(Number(v || 0)),
                  }}
                >
                  {dataBarrasCantidad.map((d) => (
                    <Cell key={d.banco} fill={d.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg font-bold text-slate-900">
            Totales SIN_BD por banco
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-bold text-slate-800">Banco</TableHead>
                <TableHead className="text-right font-bold text-slate-800">
                  Cantidad
                </TableHead>
                <TableHead className="text-right font-bold text-slate-800">
                  USD
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {porBanco.map((r, i) => (
                <TableRow key={r.banco}>
                  <TableCell>
                    <span className="inline-flex items-center gap-2 font-semibold text-slate-900">
                      <span
                        className="inline-block h-3 w-3 rounded-full"
                        style={{ backgroundColor: colorBanco(i) }}
                      />
                      {r.banco}
                    </span>
                  </TableCell>
                  <TableCell className="text-right text-base font-bold text-slate-900">
                    {fmtNum(r.filas)}
                  </TableCell>
                  <TableCell className="text-right font-semibold text-slate-800">
                    {formatCurrency(r.monto_total)}
                  </TableCell>
                </TableRow>
              ))}
              {!loading && porBanco.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={3}
                    className="text-center font-medium text-slate-600"
                  >
                    Sin SIN_BD pendientes
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