import { useCallback, useEffect, useMemo, useState } from 'react'

import { Loader2, RefreshCw, FileText, DollarSign } from 'lucide-react'
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

function colorBanco(i: number): string {
  return COLORES[i % COLORES.length]
}

function fmtNum(n: number): string {
  return n.toLocaleString('es-VE')
}

const POLL_MS = 30000

export function AuditoriaExtractoBancosTab() {
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [montoTotal, setMontoTotal] = useState(0)
  const [porBanco, setPorBanco] = useState<Fila[]>([])
  const [actualizado, setActualizado] = useState('')

  const cargar = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true)
      const res = await conciliacionBancosService.resumenSinBd(null)
      const filas = (res.por_banco || []).map((r) => ({
        banco: r.banco,
        filas: Number(r.filas || 0),
        monto_total: Number(r.monto_total || 0),
      }))
      setTotal(Number(res.total || 0))
      setMontoTotal(Number(res.monto_total || 0))
      setPorBanco(filas)
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

  const dataBarras = useMemo(
    () =>
      [...porBanco]
        .sort((a, b) => b.filas - a.filas)
        .map((r, i) => ({
          banco: r.banco,
          cantidad: r.filas,
          usd: r.monto_total,
          fill: colorBanco(i),
        })),
    [porBanco]
  )

  const dataPastelCantidad = useMemo(() => {
    const t = porBanco.reduce((a, r) => a + r.filas, 0) || 1
    return [...porBanco]
      .sort((a, b) => b.filas - a.filas)
      .map((r, i) => ({
        name: r.banco,
        value: r.filas,
        pct: (100 * r.filas) / t,
        fill: colorBanco(i),
      }))
  }, [porBanco])

  const dataPastelUsd = useMemo(() => {
    const t = porBanco.reduce((a, r) => a + r.monto_total, 0)
    if (t <= 0) return []
    return [...porBanco]
      .filter((r) => r.monto_total > 0)
      .sort((a, b) => b.monto_total - a.monto_total)
      .map((r, i) => ({
        name: r.banco,
        value: r.monto_total,
        pct: (100 * r.monto_total) / t,
        fill: colorBanco(i),
      }))
  }, [porBanco])

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
          Cantidad de pagos y USD por banco. Sin filtros. Auto-actualiza.
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
            {r.banco}: {fmtNum(r.filas)}
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

      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-bold text-slate-900">
            Cantidad de pagos SIN_BD por banco
          </CardTitle>
        </CardHeader>
        <CardContent className="h-[360px]">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
          ) : dataBarras.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm font-medium text-slate-600">
              Sin SIN_BD. Conciliar un Excel para actualizar.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={dataBarras}
                layout="vertical"
                margin={{ top: 8, right: 28, left: 8, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                <XAxis
                  type="number"
                  tick={{ fill: '#0f172a', fontSize: 12, fontWeight: 600 }}
                  axisLine={{ stroke: '#64748b' }}
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
                    fmtNum(Number(value || 0)),
                    'Cantidad de pagos',
                  ]}
                />
                <Bar
                  dataKey="cantidad"
                  name="Cantidad de pagos"
                  radius={[0, 6, 6, 0]}
                  barSize={28}
                  label={{
                    position: 'right',
                    fill: '#0f172a',
                    fontSize: 12,
                    fontWeight: 700,
                    formatter: (v: number) => fmtNum(Number(v || 0)),
                  }}
                >
                  {dataBarras.map((d) => (
                    <Cell key={d.banco} fill={d.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold text-slate-900">
              Pastel — cantidad de pagos por banco
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[340px]">
            {loading ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
              </div>
            ) : dataPastelCantidad.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm font-medium text-slate-600">
                Sin datos
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dataPastelCantidad}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="48%"
                    innerRadius={62}
                    outerRadius={110}
                    paddingAngle={2}
                    stroke="#ffffff"
                    strokeWidth={3}
                  >
                    {dataPastelCantidad.map((d) => (
                      <Cell key={d.name} fill={d.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#fff',
                      border: '1px solid #334155',
                      borderRadius: 8,
                      color: '#0f172a',
                      fontWeight: 600,
                    }}
                    formatter={(value: number, _n, item) => {
                      const pct = Number(item?.payload?.pct || 0)
                      return [
                        fmtNum(Number(value || 0)) +
                          ' pagos (' +
                          pct.toFixed(1) +
                          '%)',
                        'Cantidad',
                      ]
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    formatter={(value: string) => (
                      <span className="text-sm font-semibold text-slate-900">
                        {value}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold text-slate-900">
              Pastel — dolares (USD) por banco
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[340px]">
            {loading ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
              </div>
            ) : dataPastelUsd.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-sm font-medium text-slate-700">
                <span>Sin montos USD en SIN_BD de este resumen.</span>
                <span className="text-xs text-slate-500">
                  La cantidad de pagos si aparece en el grafico de barras y en
                  el pastel de cantidad.
                </span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dataPastelUsd}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="48%"
                    innerRadius={62}
                    outerRadius={110}
                    paddingAngle={2}
                    stroke="#ffffff"
                    strokeWidth={3}
                  >
                    {dataPastelUsd.map((d) => (
                      <Cell key={d.name} fill={d.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#fff',
                      border: '1px solid #334155',
                      borderRadius: 8,
                      color: '#0f172a',
                      fontWeight: 600,
                    }}
                    formatter={(value: number, _n, item) => {
                      const pct = Number(item?.payload?.pct || 0)
                      return [
                        formatCurrency(Number(value || 0)) +
                          ' (' +
                          pct.toFixed(1) +
                          '%)',
                        'USD',
                      ]
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    formatter={(value: string) => (
                      <span className="text-sm font-semibold text-slate-900">
                        {value}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

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