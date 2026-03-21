import { useState } from 'react'

import { useQuery } from '@tanstack/react-query'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

import { BaseModal } from '../BaseModal'

import { DashboardFiltrosPanel } from '../DashboardFiltrosPanel'

import { KpiCardsPanel } from '../KpiCardsPanel'

import {
  useDashboardFiltros,
  type DashboardFiltros,
} from '../../../hooks/useDashboardFiltros'

import { apiClient } from '../../../services/api'

import { formatCurrency } from '../../../utils'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../../components/ui/card'

import { TrendingUp, DollarSign, Users, AlertTriangle } from 'lucide-react'

interface CobranzaPorDiaModalProps {
  isOpen: boolean

  onClose: () => void
}

interface DiaData {
  fecha: string

  total_a_cobrar: number

  pagos: number

  morosidad: number
}

interface MetricasAcumuladas {
  acumulado_mensual: number

  acumulado_anual: number

  clientes_1_pago_atrasado: number

  clientes_3mas_cuotas_atrasadas: number

  fecha_inicio_mes: string

  fecha_inicio_anio: string
}

interface CobranzaPorDiaResponse {
  dias: DiaData[]
}

interface MetricasAcumuladasResponse {
  acumulado_mensual: number

  acumulado_anual: number

  clientes_1_pago_atrasado: number

  clientes_3mas_cuotas_atrasadas: number

  fecha_inicio_mes: string

  fecha_inicio_anio: string
}

export function CobranzaPorDiaModal({
  isOpen,
  onClose,
}: CobranzaPorDiaModalProps) {
  const [filtros, setFiltros] = useState<DashboardFiltros>({})

  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  // Cargar opciones de filtros

  const {
    data: opcionesFiltros,
    isLoading: loadingOpcionesFiltros,
    isError: errorOpcionesFiltros,
  } = useQuery({
    queryKey: ['opciones-filtros'],

    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')

      return response as {
        analistas: string[]
        concesionarios: string[]
        modelos: string[]
      }
    },
  })

  // Cargar datos por día

  const {
    data: cobranzaPorDiaData,
    isLoading: loadingPorDia,
    refetch,
  } = useQuery({
    queryKey: ['cobranza-por-dia', filtros],

    queryFn: async (): Promise<CobranzaPorDiaResponse> => {
      const params = construirFiltrosObject()

      const queryParams = new URLSearchParams()

      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })

      const queryString = queryParams.toString()

      const response = (await apiClient.get(
        `/api/v1/dashboard/cobranza-por-dia${queryString ? '?' + queryString : ''}`
      )) as CobranzaPorDiaResponse

      return response || { dias: [] }
    },

    staleTime: 5 * 60 * 1000,
  })

  // Cargar métricas acumuladas

  const { data: metricasData, isLoading: loadingMetricas } = useQuery({
    queryKey: ['metricas-acumuladas', filtros],

    queryFn: async (): Promise<MetricasAcumuladasResponse> => {
      const params = construirFiltrosObject()

      const queryParams = new URLSearchParams()

      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })

      const queryString = queryParams.toString()

      const response = (await apiClient.get(
        `/api/v1/dashboard/metricas-acumuladas${queryString ? '?' + queryString : ''}`
      )) as MetricasAcumuladasResponse

      return (
        response || {
          acumulado_mensual: 0,

          acumulado_anual: 0,

          clientes_1_pago_atrasado: 0,

          clientes_3mas_cuotas_atrasadas: 0,

          fecha_inicio_mes: '',

          fecha_inicio_anio: '',
        }
      )
    },

    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)

    await refetch()

    setIsRefreshing(false)
  }

  // Formatear fechas para el gráfico

  const datosGrafico =
    cobranzaPorDiaData?.dias.map(d => ({
      ...d,

      fechaFormateada: new Date(d.fecha).toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
      }),
    })) || []

  // Tooltip personalizado

  const CustomTooltip = ({
    active,
    payload,
    label,
  }: {
    active?: boolean
    payload?: Array<{ name?: string; value?: number; color?: string }>
    label?: string | number
  }) => {
    if (active && payload && payload.length) {
      return (
        <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
          <p className="mb-2 font-semibold">{label}</p>

          {payload.map((entry, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {formatCurrency(entry.value ?? 0)}
            </p>
          ))}
        </div>
      )
    }

    return null
  }

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      title="Total a Cobrar, Pagos y Pago vencido por Día"
      size="xlarge"
    >
      <div className="space-y-6">
        {/* Filtros */}

        <DashboardFiltrosPanel
          filtros={filtros}
          setFiltros={setFiltros}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
          opcionesFiltros={opcionesFiltros}
          loadingOpcionesFiltros={loadingOpcionesFiltros}
          errorOpcionesFiltros={errorOpcionesFiltros}
        />

        {/* Layout: Tarjetas KPI Izquierda + Gráfico Centro + Métricas Derecha */}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Tarjetas KPI - Izquierda */}

          <div className="lg:col-span-2">
            <KpiCardsPanel filtros={filtros} />
          </div>

          {/* Gráfico - Centro */}

          <div className="lg:col-span-7">
            <Card>
              <CardHeader>
                <CardTitle>
                  Total a Cobrar, Pagos y Pago vencido por Día
                </CardTitle>
              </CardHeader>

              <CardContent>
                {loadingPorDia ? (
                  <div className="flex h-[400px] items-center justify-center">
                    <div className="animate-pulse text-gray-400">
                      Cargando gráfico...
                    </div>
                  </div>
                ) : datosGrafico.length === 0 ? (
                  <div className="flex h-[400px] items-center justify-center text-gray-500">
                    No hay datos disponibles para el período seleccionado
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart
                      data={datosGrafico}
                      margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

                      <XAxis
                        dataKey="fechaFormateada"
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                      />

                      <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                        tickFormatter={value =>
                          `$${(value / 1000).toFixed(0)}K`
                        }
                      />

                      <Tooltip content={<CustomTooltip />} />

                      <Legend />

                      <Bar
                        dataKey="total_a_cobrar"
                        name="Total a Cobrar"
                        fill="#3b82f6"
                      />

                      <Bar dataKey="pagos" name="Pagos" fill="#10b981" />

                      <Bar
                        dataKey="morosidad"
                        name="Pago vencido"
                        fill="#ef4444"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Métricas Acumuladas - Derecha */}

          <div className="space-y-4 lg:col-span-3">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <TrendingUp className="h-5 w-5 text-emerald-600" />
                  Acumulado Mensual
                </CardTitle>
              </CardHeader>

              <CardContent>
                <div className="mb-2 text-3xl font-bold text-emerald-600">
                  {formatCurrency(metricasData?.acumulado_mensual || 0)}
                </div>

                <p className="text-sm text-gray-500">
                  Desde{' '}
                  {metricasData?.fecha_inicio_mes
                    ? new Date(
                        metricasData.fecha_inicio_mes
                      ).toLocaleDateString('es-ES')
                    : 'inicio del mes'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <DollarSign className="h-5 w-5 text-blue-600" />
                  Acumulado Anual
                </CardTitle>
              </CardHeader>

              <CardContent>
                <div className="mb-2 text-3xl font-bold text-blue-600">
                  {formatCurrency(metricasData?.acumulado_anual || 0)}
                </div>

                <p className="text-sm text-gray-500">
                  Desde{' '}
                  {metricasData?.fecha_inicio_anio
                    ? new Date(
                        metricasData.fecha_inicio_anio
                      ).toLocaleDateString('es-ES')
                    : 'inicio del año'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Users className="h-5 w-5 text-orange-600" />
                  Clientes 1 Pago Atrasado
                </CardTitle>
              </CardHeader>

              <CardContent>
                <div className="mb-2 text-3xl font-bold text-orange-600">
                  {metricasData?.clientes_1_pago_atrasado || 0}
                </div>

                <p className="text-sm text-gray-500">Clientes únicos</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                  Clientes 3+ Cuotas Atrasadas
                </CardTitle>
              </CardHeader>

              <CardContent>
                <div className="mb-2 text-3xl font-bold text-red-600">
                  {metricasData?.clientes_3mas_cuotas_atrasadas || 0}
                </div>

                <p className="text-sm text-gray-500">Clientes únicos</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </BaseModal>
  )
}
