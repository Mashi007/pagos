import { motion } from 'framer-motion'

import { Calendar } from 'lucide-react'

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatCurrency } from '../../utils'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

export type CuotasCubiertasPorMesRow = {
  mes: string
  monto_programado: number
  monto_cobrado: number
  monto_falta: number
  /** Igual a `monto_cobrado`; la API lo envía por compatibilidad. */
  monto_usd?: number
  cuotas_con_pago_aplicado: number
}

type Props = {
  loading: boolean
  datos: CuotasCubiertasPorMesRow[] | undefined
  /** Retraso de animación (framer), alineado al dashboard de pagos */
  motionDelay?: number
}

function rowProgramado(row: CuotasCubiertasPorMesRow): number {
  if (
    typeof row.monto_programado === 'number' &&
    !Number.isNaN(row.monto_programado)
  ) {
    return row.monto_programado
  }
  const cob =
    typeof row.monto_cobrado === 'number'
      ? row.monto_cobrado
      : Number(row.monto_usd ?? 0)
  const fal = typeof row.monto_falta === 'number' ? row.monto_falta : 0
  return cob + fal
}

function rowCobrado(row: CuotasCubiertasPorMesRow): number {
  if (
    typeof row.monto_cobrado === 'number' &&
    !Number.isNaN(row.monto_cobrado)
  ) {
    return row.monto_cobrado
  }
  return Number(row.monto_usd ?? 0)
}

function rowFalta(row: CuotasCubiertasPorMesRow): number {
  if (typeof row.monto_falta === 'number' && !Number.isNaN(row.monto_falta)) {
    return row.monto_falta
  }
  const prog = rowProgramado(row)
  return Math.max(0, prog - rowCobrado(row))
}

/**
 * Por mes de vencimiento: barra apilada cobrado + falta = programado (cartera de ese mes).
 * El cobrado incluye pagos aplicados en cualquier mes calendario.
 */
export function CuotasCubiertasVencimientoChartCard({
  loading,
  datos,
  motionDelay = 0.12,
}: Props) {
  const chartData =
    datos?.map(d => ({
      ...d,
      _programado: rowProgramado(d),
      _cobrado: rowCobrado(d),
      _falta: rowFalta(d),
    })) ?? []

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: motionDelay }}
    >
      <Card className="border-2 border-gray-200 shadow-lg">
        <CardHeader className="border-b-2 border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50">
          <CardTitle className="flex flex-col gap-1 text-xl font-bold text-gray-800 sm:flex-row sm:items-center sm:space-x-2">
            <span className="flex items-center space-x-2">
              <Calendar className="h-6 w-6 text-emerald-600" />
              <span>Programado vs cobrado y falta (USD)</span>
            </span>
          </CardTitle>
          <p className="text-sm font-normal text-gray-600">
            Por <span className="font-medium">mes de vencimiento</span> de la
            cuota (igual que la cartera azul de Evolución mensual): la altura
            total es lo programado para ese mes. La parte verde es lo ya cobrado
            hacia esas cuotas{' '}
            <span className="font-medium">sin importar en qué mes se pagó</span>
            (ej. cuota de abril cobrada en mayo suma en abril). La parte ámbar
            es lo que falta por cobrar de ese bucket. Si la cuota tiene{' '}
            <span className="font-medium">fecha de pago</span>, el monto
            aplicado se alinea con la barra verde de Evolución; si no, se usan
            abonos en <span className="font-medium">cuota_pagos</span> o{' '}
            <span className="font-medium">total_pagado</span>. Préstamos
            aprobados, sin filtrar clientes inactivos. La barra naranja de
            Evolución (cobro en el mes calendario del pago) no es esta vista:
            aquí todo va al mes de{' '}
            <span className="font-medium">vencimiento</span> de cada cuota.
          </p>
        </CardHeader>

        <CardContent className="p-6">
          {loading ? (
            <div className="flex h-[300px] items-center justify-center">
              <div className="animate-pulse text-gray-400">Cargando...</div>
            </div>
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="mes" stroke="#6b7280" />
                <YAxis
                  stroke="#6b7280"
                  tickFormatter={v => formatCurrency(Number(v))}
                  width={88}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) {
                      return null
                    }
                    const row = payload[0]?.payload as
                      | CuotasCubiertasPorMesRow
                      | undefined
                    if (!row) {
                      return null
                    }
                    const programado = rowProgramado(row)
                    const cobrado = rowCobrado(row)
                    const falta = rowFalta(row)
                    return (
                      <div className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm shadow-md">
                        <div className="font-semibold text-gray-800">
                          {String(label)}
                        </div>
                        <div className="mt-1 text-gray-900">
                          Programado:{' '}
                          <span className="font-medium">
                            {formatCurrency(programado)}
                          </span>
                        </div>
                        <div className="text-emerald-800">
                          Cobrado:{' '}
                          <span className="font-medium">
                            {formatCurrency(cobrado)}
                          </span>
                        </div>
                        <div className="text-amber-800">
                          Falta:{' '}
                          <span className="font-medium">
                            {formatCurrency(falta)}
                          </span>
                        </div>
                        <div className="mt-0.5 text-gray-600">
                          {Number(
                            row.cuotas_con_pago_aplicado
                          ).toLocaleString()}{' '}
                          cuotas con abono aplicado
                        </div>
                      </div>
                    )
                  }}
                />
                <Legend />
                <Bar
                  isAnimationActive={false}
                  dataKey="_cobrado"
                  name="Cobrado (hacia cuotas de ese vencimiento)"
                  stackId="venc"
                  fill="#059669"
                />
                <Bar
                  isAnimationActive={false}
                  dataKey="_falta"
                  name="Falta por cobrar"
                  stackId="venc"
                  fill="#f59e0b"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[300px] items-center justify-center text-gray-400">
              No hay datos disponibles
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}
