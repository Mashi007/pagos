import { motion } from 'framer-motion'

import { PieChart, BarChart3, Calendar } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { formatCurrency } from '../../utils'

import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
} from 'recharts'

type EstadoRow = {
  estado: string
  cantidad: number
  porcentaje: number
}

type EvolucionRow = { mes: string; pagos: number; monto: number }

type CuotasAplicadasMesRow = {
  mes: string
  monto_usd: number
  cuotas_con_pago_aplicado: number
}

type Props = {
  loadingCuotasPagoAplicadoPorMesCuota: boolean
  datosCuotasPagoAplicadoPorMesCuota: CuotasAplicadasMesRow[] | undefined
  loadingPagosEstado: boolean
  datosPagosEstado: EstadoRow[]
  totalPagos: number
  COLORS_ESTADO: string[]
  loadingEvolucion: boolean
  datosEvolucion: EvolucionRow[] | undefined
}

/**
 * Graficos pesados (Recharts) cargados con React.lazy para mejorar TTI del dashboard.
 */
export function DashboardPagosCharts({
  loadingCuotasPagoAplicadoPorMesCuota,
  datosCuotasPagoAplicadoPorMesCuota,
  loadingPagosEstado,
  datosPagosEstado,
  totalPagos,
  COLORS_ESTADO,
  loadingEvolucion,
  datosEvolucion,
}: Props) {
  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <Card className="border-2 border-gray-200 shadow-lg">
          <CardHeader className="border-b-2 border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50">
            <CardTitle className="flex flex-col gap-1 text-xl font-bold text-gray-800 sm:flex-row sm:items-center sm:space-x-2">
              <span className="flex items-center space-x-2">
                <Calendar className="h-6 w-6 text-emerald-600" />
                <span>Cuotas cubiertas (USD por mes de vencimiento)</span>
              </span>
            </CardTitle>
            <p className="text-sm font-normal text-gray-600">
              Suma en <span className="font-medium">USD</span> del monto
              aplicado en cascada (
              <span className="font-medium">cuota_pagos</span>
              ), agrupada por el mes de{' '}
              <span className="font-medium">vencimiento de la cuota</span>. No
              usa la fecha del pago: un abono aplicado en otro mes sigue
              contando en el mes de la cuota. En el detalle del gráfico verás
              también cuántas cuotas distintas recibieron abono en ese bucket.
            </p>
          </CardHeader>

          <CardContent className="p-6">
            {loadingCuotasPagoAplicadoPorMesCuota ? (
              <div className="flex h-[300px] items-center justify-center">
                <div className="animate-pulse text-gray-400">Cargando...</div>
              </div>
            ) : datosCuotasPagoAplicadoPorMesCuota &&
              datosCuotasPagoAplicadoPorMesCuota.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={datosCuotasPagoAplicadoPorMesCuota}>
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
                        | CuotasAplicadasMesRow
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
                            <span className="text-gray-500">
                              (USD cubierto)
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="border-2 border-gray-200 shadow-lg">
            <CardHeader className="border-b-2 border-violet-200 bg-gradient-to-r from-violet-50 to-purple-50">
              <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                <PieChart className="h-6 w-6 text-violet-600" />
                <span>Pagos por Estado</span>
              </CardTitle>
            </CardHeader>

            <CardContent className="p-6">
              {loadingPagosEstado ? (
                <div className="flex h-[300px] items-center justify-center">
                  <div className="animate-pulse text-gray-400">Cargando...</div>
                </div>
              ) : datosPagosEstado.length > 0 ? (
                <div className="relative">
                  <ResponsiveContainer width="100%" height={300}>
                    <RechartsPieChart>
                      <Pie
                        isAnimationActive={false}
                        data={datosPagosEstado.map(p => ({
                          name: p.estado,
                          value: p.porcentaje,
                          cantidad: p.cantidad,
                        }))}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) =>
                          `${name}: ${(percent * 100).toFixed(1)}%`
                        }
                        outerRadius={100}
                        innerRadius={60}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {datosPagosEstado.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={COLORS_ESTADO[index % COLORS_ESTADO.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </RechartsPieChart>
                  </ResponsiveContainer>

                  <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-2xl font-black text-gray-800">
                        {totalPagos.toLocaleString()}
                      </div>
                      <div className="text-xs text-gray-500">Total Pagos</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex h-[300px] items-center justify-center text-gray-400">
                  No hay datos disponibles
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="border-2 border-gray-200 shadow-lg">
            <CardHeader className="border-b-2 border-indigo-200 bg-gradient-to-r from-indigo-50 to-blue-50">
              <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                <BarChart3 className="h-6 w-6 text-indigo-600" />
                <span>Evolucion de Pagos</span>
              </CardTitle>
            </CardHeader>

            <CardContent className="p-6">
              {loadingEvolucion ? (
                <div className="flex h-[300px] items-center justify-center">
                  <div className="animate-pulse text-gray-400">Cargando...</div>
                </div>
              ) : datosEvolucion && datosEvolucion.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={datosEvolucion}>
                    <defs>
                      <linearGradient
                        id="colorEvolucion"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="#6366f1"
                          stopOpacity={0.8}
                        />
                        <stop
                          offset="95%"
                          stopColor="#6366f1"
                          stopOpacity={0.1}
                        />
                      </linearGradient>
                    </defs>

                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

                    <XAxis dataKey="mes" stroke="#6b7280" />

                    <YAxis stroke="#6b7280" />

                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                    />

                    <Legend />

                    <Area
                      isAnimationActive={false}
                      type="monotone"
                      dataKey="monto"
                      stroke="#6366f1"
                      fillOpacity={1}
                      fill="url(#colorEvolucion)"
                      name="Monto Total"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-[300px] items-center justify-center text-gray-400">
                  No hay datos disponibles
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
