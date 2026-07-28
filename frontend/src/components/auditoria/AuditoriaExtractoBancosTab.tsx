import { useCallback, useEffect, useMemo, useState } from 'react'

import { Loader2, RefreshCw, FileText, DollarSign } from 'lucide-react'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
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

type Slice = {
  name: string
  value: number
  pct: number
  fill: string
}

function PastelSinBd({
  title,
  data,
  loading,
  valueKind,
}: {
  title: string
  data: Slice[]
  loading: boolean
  valueKind: 'cantidad' | 'usd'
}) {
  const renderLabel = (props: {
    cx?: number
    cy?: number
    midAngle?: number
    innerRadius?: number
    outerRadius?: number
    percent?: number
    name?: string
  }) => {
    const {
      cx = 0,
      cy = 0,
      midAngle = 0,
      innerRadius = 0,
      outerRadius = 0,
      percent = 0,
      name = '',
    } = props
    if (percent < 0.04) return null
    const RAD = Math.PI / 180
    const r = innerRadius + (outerRadius - innerRadius) * 0.55
    const x = cx + r * Math.cos(-midAngle * RAD)
    const y = cy + r * Math.sin(-midAngle * RAD)
    return (
      <text
        x={x}
        y={y}
        fill="#fff"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={12}
        fontWeight={600}
      >
        {name} {(percent * 100).toFixed(0)}%
      </text>
    )
  }

  return (
    <Card className="overflow-hidden border-border/60 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold tracking-tight">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="h-[380px] pt-0">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Sin SIN_BD. Conciliar un Excel para actualizar.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="46%"
                innerRadius={68}
                outerRadius={118}
                paddingAngle={2}
                stroke="#fff"
                strokeWidth={2}
                label={renderLabel}
                labelLine={false}
              >
                {data.map((d) => (
                  <Cell key={d.name} fill={d.fill} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number, _n, item) => {
                  const pct = Number(item?.payload?.pct || 0)
                  if (valueKind === 'usd') {
                    return [
                      formatCurrency(Number(value || 0)) +
                        ' (' +
                        pct.toFixed(1) +
                        '%)',
                      'USD',
                    ]
                  }
                  return [
                    fmtNum(Number(value || 0)) +
                      ' (' +
                      pct.toFixed(1) +
                      '%)',
                    'Cantidad',
                  ]
                }}
              />
              <Legend
                verticalAlign="bottom"
                height={48}
                formatter={(value: string) => (
                  <span className="text-sm text-foreground">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}

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
      setTotal(Number(res.total || 0))
      setMontoTotal(Number(res.monto_total || 0))
      setPorBanco(
        (res.por_banco || []).map((r) => ({
          banco: r.banco,
          filas: Number(r.filas || 0),
          monto_total: Number(r.monto_total || 0),
        }))
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

  const pastelCantidad = useMemo((): Slice[] => {
    const t = porBanco.reduce((a, r) => a + r.filas, 0) || 1
    return porBanco.map((r, i) => ({
      name: r.banco,
      value: r.filas,
      pct: (100 * r.filas) / t,
      fill: colorBanco(i),
    }))
  }, [porBanco])

  const pastelUsd = useMemo((): Slice[] => {
    const t = porBanco.reduce((a, r) => a + r.monto_total, 0) || 1
    return porBanco.map((r, i) => ({
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
          className="rounded-full px-4 py-1.5 text-base font-semibold tracking-wide"
        >
          SIN_BD: {fmtNum(total)}
        </Badge>
        <span className="text-sm text-muted-foreground">
          Actualizacion automatica por banco (cantidad y USD). Sin filtros.
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
          <span className="text-xs text-muted-foreground">
            Actualizado {actualizado}
          </span>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {porBanco.map((r, i) => (
          <Badge
            key={r.banco}
            variant="outline"
            className="rounded-full px-3 py-1 text-sm font-medium"
            style={{ borderColor: colorBanco(i) }}
          >
            {r.banco}: {fmtNum(r.filas)} · {formatCurrency(r.monto_total)}
          </Badge>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-border/60 shadow-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">
                  Cantidad de pagos SIN_BD
                </p>
                <p className="text-3xl font-bold tracking-tight">
                  {fmtNum(total)}
                </p>
              </div>
              <FileText className="h-9 w-9 text-teal-700" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/60 shadow-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total USD SIN_BD</p>
                <p className="text-3xl font-bold tracking-tight">
                  {formatCurrency(montoTotal)}
                </p>
              </div>
              <DollarSign className="h-9 w-9 text-blue-700" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <PastelSinBd
          title="SIN_BD por banco — cantidad de pagos"
          data={pastelCantidad}
          loading={loading}
          valueKind="cantidad"
        />
        <PastelSinBd
          title="SIN_BD por banco — dolares (USD)"
          data={pastelUsd}
          loading={loading}
          valueKind="usd"
        />
      </div>

      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Totales SIN_BD por banco
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Banco</TableHead>
                <TableHead className="text-right">Cantidad</TableHead>
                <TableHead className="text-right">USD</TableHead>
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
                    {formatCurrency(r.monto_total)}
                  </TableCell>
                </TableRow>
              ))}
              {!loading && porBanco.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={3}
                    className="text-center text-muted-foreground"
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