import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  CreditCard,
  Shield,
  Clock,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  PieChart,
  BarChart3,
  ChevronRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency } from '@/utils'
import { apiClient } from '@/services/api'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { DashboardFiltrosPanel } from '@/components/dashboard/DashboardFiltrosPanel'
import { useNavigate } from 'react-router-dom'
import { KpiCardLarge } from '@/components/dashboard/KpiCardLarge'
import { pagoService } from '@/services/pagoService'
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'

export function DashboardPagos() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  // Cargar estadísticas de pagos
  const { data: pagosStats, isLoading: pagosStatsLoading, refetch } = useQuery({
    queryKey: ['pagos-stats', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      return await pagoService.getStats(params)
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar KPIs de pagos
  const { data: kpisPagos, isLoading: loadingKPIs } = useQuery({
    queryKey: ['kpis-pagos', filtros],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/pagos/kpis') as {
        montoCobradoMes: number
        saldoPorCobrar: number
        clientesEnMora: number
        clientesAlDia: number
      }
      return response
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar pagos por estado
  const { data: pagosPorEstado, isLoading: loadingPagosEstado } = useQuery({
    queryKey: ['pagos-por-estado', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/pagos/stats${queryString ? '?' + queryString : ''}`
      ) as {
        total_pagos: number
        total_pagado: number
        pagos_por_estado: Array<{ estado: string; count: number }>
      }
      return response
    },
    staleTime: 5 * 60 * 1000,
  })

  // Datos para gráfico de pagos por estado
  const datosPagosEstado = pagosPorEstado?.pagos_por_estado.map((item) => ({
    estado: item.estado,
    cantidad: item.count,
    porcentaje: pagosPorEstado.total_pagos > 0 ? (item.count / pagosPorEstado.total_pagos) * 100 : 0,
  })) || []

  // Cargar evolución de pagos (últimos 6 meses)
  const { data: datosEvolucion, isLoading: loadingEvolucion } = useQuery({
    queryKey: ['evolucion-pagos', filtros],
    queryFn: async () => {
      // Datos simulados - se puede crear endpoint específico
      const hoy = new Date()
      const meses: Array<{ mes: string; pagos: number; monto: number }> = []
      for (let i = 5; i >= 0; i--) {
        const fecha = new Date(hoy.getFullYear(), hoy.getMonth() - i, 1)
        meses.push({
          mes: fecha.toLocaleDateString('es-ES', { month: 'short', year: 'numeric' }),
          pagos: Math.random() * 500 + 100,
          monto: Math.random() * 1000000 + 500000,
        })
      }
      return meses
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  const totalPagos = pagosStats?.total_pagos || 0
  const totalPagado = pagosStats?.total_pagado || 0
  const pagosConciliados = pagosStats?.cuotas_pagadas || 0
  const pagosPendientes = pagosStats?.cuotas_pendientes || 0
  const promedioPorPago = totalPagos > 0 ? totalPagado / totalPagos : 0

  const porcentajeConciliados = totalPagos > 0 ? (pagosConciliados / totalPagos) * 100 : 0
  const porcentajePendientes = totalPagos > 0 ? (pagosPendientes / totalPagos) * 100 : 0

  const COLORS_ESTADO = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#9ca3af']

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-4 py-8 space-y-8">
        {/* Header Estratégico */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/dashboard/menu')}
              className="hover:bg-violet-50"
            >
              ← Menú
            </Button>
            <div>
              <h1 className="text-4xl font-black text-gray-900 uppercase tracking-tight">Pagos</h1>
              <p className="text-lg text-gray-600 font-medium mt-1">
                Monitoreo Estratégico • {userName}
              </p>
            </div>
          </div>
          <DashboardFiltrosPanel
            filtros={filtros}
            setFiltros={setFiltros}
            onRefresh={handleRefresh}
            isRefreshing={isRefreshing}
            opcionesFiltros={opcionesFiltros}
            loadingOpcionesFiltros={loadingOpcionesFiltros}
            errorOpcionesFiltros={errorOpcionesFiltros}
          />
        </motion.div>

        {/* KPIs PRINCIPALES */}
        {pagosStatsLoading || loadingKPIs ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
                    <div className="h-10 bg-gray-200 rounded w-1/2"></div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <KpiCardLarge
              title="Total Pagos Mes"
              value={totalPagado}
              subtitle={`${totalPagos.toLocaleString()} pagos`}
              icon={CreditCard}
              color="text-violet-600"
              bgColor="bg-violet-100"
              borderColor="border-violet-500"
              format="currency"
            />
            <KpiCardLarge
              title="Pagos Conciliados"
              value={pagosConciliados}
              subtitle={`${porcentajeConciliados.toFixed(1)}% del total`}
              icon={Shield}
              color="text-blue-600"
              bgColor="bg-blue-100"
              borderColor="border-blue-500"
              format="number"
            />
            <KpiCardLarge
              title="Pagos Pendientes"
              value={pagosPendientes}
              subtitle={`${porcentajePendientes.toFixed(1)}% del total`}
              icon={Clock}
              color="text-amber-600"
              bgColor="bg-amber-100"
              borderColor="border-amber-500"
              format="number"
            />
            <KpiCardLarge
              title="Promedio por Pago"
              value={promedioPorPago}
              subtitle="Mes actual"
              icon={TrendingUp}
              color="text-indigo-600"
              bgColor="bg-indigo-100"
              borderColor="border-indigo-500"
              format="currency"
            />
          </div>
        )}

        {/* GRÁFICOS PRINCIPALES */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Gráfico 1: Pagos por Estado */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="shadow-lg border-2 border-gray-200">
              <CardHeader className="bg-gradient-to-r from-violet-50 to-purple-50 border-b-2 border-violet-200">
                <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                  <PieChart className="h-6 w-6 text-violet-600" />
                  <span>Pagos por Estado</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                {loadingPagosEstado ? (
                  <div className="h-[300px] flex items-center justify-center">
                    <div className="animate-pulse text-gray-400">Cargando...</div>
                  </div>
                ) : datosPagosEstado.length > 0 ? (
                  <div className="relative">
                    <ResponsiveContainer width="100%" height={300}>
                      <RechartsPieChart>
                        <Pie
                          data={datosPagosEstado.map((p) => ({
                            name: p.estado,
                            value: p.porcentaje,
                            cantidad: p.cantidad,
                          }))}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
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
                    {/* Centro del donut */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="text-center">
                        <div className="text-2xl font-black text-gray-800">
                          {totalPagos.toLocaleString()}
                        </div>
                        <div className="text-xs text-gray-500">Total Pagos</div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-gray-400">
                    No hay datos disponibles
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Gráfico 2: Evolución de Pagos */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="shadow-lg border-2 border-gray-200">
              <CardHeader className="bg-gradient-to-r from-indigo-50 to-blue-50 border-b-2 border-indigo-200">
                <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                  <BarChart3 className="h-6 w-6 text-indigo-600" />
                  <span>Evolución de Pagos</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                {loadingEvolucion ? (
                  <div className="h-[300px] flex items-center justify-center">
                    <div className="animate-pulse text-gray-400">Cargando...</div>
                  </div>
                ) : datosEvolucion && datosEvolucion.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={datosEvolucion}>
                      <defs>
                        <linearGradient id="colorEvolucion" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8} />
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0.1} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="mes" stroke="#6b7280" />
                      <YAxis stroke="#6b7280" />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Legend />
                      <Area
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
                  <div className="h-[300px] flex items-center justify-center text-gray-400">
                    No hay datos disponibles
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* BOTONES EXPLORAR DETALLES */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-8"
        >
          <div className="bg-gradient-to-r from-violet-600 to-indigo-600 rounded-xl p-6 shadow-xl">
            <h2 className="text-2xl font-bold text-white mb-4 flex items-center space-x-2">
              <span>🔍</span>
              <span>Explorar Análisis Detallados</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-violet-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => {
                  // TODO: Navegar a detalles de transacciones
                  console.log('Detalles de Transacciones')
                }}
              >
                <CreditCard className="h-6 w-6" />
                <span className="font-semibold">Detalles de Transacciones</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-violet-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => {
                  // TODO: Navegar a análisis de conciliaciones
                  console.log('Análisis de Conciliaciones')
                }}
              >
                <Shield className="h-6 w-6" />
                <span className="font-semibold">Análisis de Conciliaciones</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-violet-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => {
                  // TODO: Navegar a reportes de pagos
                  console.log('Reportes de Pagos')
                }}
              >
                <CheckCircle className="h-6 w-6" />
                <span className="font-semibold">Reportes de Pagos</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
