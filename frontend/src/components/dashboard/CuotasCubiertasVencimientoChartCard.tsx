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
  monto_usd: number
  cuotas_con_pago_aplicado: number
}

type Props = {
  loading: boolean
  datos: CuotasCubiertasPorMesRow[] | undefined
  /** Retraso de animación (framer), alineado al dashboard de pagos */
  motionDelay?: number
}

/**
 * Cuotas programadas: suma USD aplicados (cuota_pagos) por mes de vencimiento;
 * incluye pagos conciliados y no conciliados. No agrupa por fecha del pago.
 */
export function CuotasCubiertasVencimientoChartCard({
  loading,
  datos,
  motionDelay = 0.12,
}: Props) {
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
              <span>Cuotas programadas cubiertas (USD)</span>
            </span>
          </CardTitle>
          <p className="text-sm font-normal text-gray-600">
            Total en <span className="font-medium">USD</span> de todo lo
            aplicado a cuotas vía{' '}
            <span className="font-medium">cuota_pagos</span>, por{' '}
            <span className="font-medium">mes calendario de vencimiento</span>{' '}
            de la cuota. Incluye pagos{' '}
            <span className="font-medium">conciliados y no conciliados</span>.
            Si la cuota es de enero y el abono cae en abril, el monto se muestra
            en <span className="font-medium">enero</span>. El detalle indica
            cuántas cuotas distintas recibieron abono en ese mes de vencimiento.
          </p>
        </CardHeader>

        <CardContent className="p-6">
          {loading ? (
            <div className="flex h-[300px] items-center justify-center">
              <div className="animate-pulse text-gray-400">Cargando...</div>
            </div>
          ) : datos && datos.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={datos}>
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
                    return (
                      <div className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm shadow-md">
                        <div className="font-semibold text-gray-800">
                          {String(label)}
                        </div>
                        <div className="mt-1 text-gray-900">
                          {formatCurrency(Number(row.monto_usd))}{' '}
                          <span className="text-gray-500">(USD cubierto)</span>
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
                  dataKey="monto_usd"
                  name="USD cubierto (por vencimiento de cuota)"
                  fill="#059669"
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
