import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Calendar,
  CheckCircle,
  Shield,
  AlertTriangle,
  Users,
  TrendingUp,
  BarChart3,
  PieChart,
  ChevronRight,
  Filter,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { formatCurrency } from '../utils'
import { apiClient } from '../services/api'
import { useDashboardFiltros, type DashboardFiltros } from '../hooks/useDashboardFiltros'
import { DashboardFiltrosPanel } from '../components/dashboard/DashboardFiltrosPanel'
import { useNavigate } from 'react-router-dom'
import { KpiCardLarge } from '../components/dashboard/KpiCardLarge'
import {
  BarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts'

interface KPIsData {
  total_cuotas_mes: number
  cuotas_pagadas: number
  porcentaje_cuotas_pagadas: number
  total_cuotas_conciliadas: number
  cuotas_atrasadas_mes: number
  total_cuotas_impagas_2mas: number
}

export function DashboardCuotas() {
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

  const { data: kpisData, isLoading: loadingKpis, refetch } = useQuery({
    queryKey: ['kpis-cuotas', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/kpis/dashboard${queryString ? '?' + queryString : ''}`
      ) as KPIsData

      return {
        total_cuotas_mes: response.total_cuotas_mes || 0,
        cuotas_pagadas: response.cuotas_pagadas || 0,
        porcentaje_cuotas_pagadas: response.porcentaje_cuotas_pagadas || 0,
        total_cuotas_conciliadas: response.total_cuotas_conciliadas || 0,
        cuotas_atrasadas_mes: response.cuotas_atrasadas_mes || 0,
        total_cuotas_impagas_2mas: response.total_cuotas_impagas_2mas || 0,
      } as KPIsData
    },
    staleTime: 2 * 60 * 1000, // âœ… ACTUALIZADO: 2 minutos para datos más frescos
    refetchOnWindowFocus: true, // âœ… ACTUALIZADO: Recargar al enfocar ventana para datos actualizados
  })

  // Cargar datos para gráfico de estado de cuotas
  const datosEstadoCuotas = kpisData
    ? [
        {
          estado: 'Pagadas',
          cantidad: kpisData.cuotas_pagadas,
          porcentaje: kpisData.porcentaje_cuotas_pagadas,
          color: '#10b981',
        },
        {
          estado: 'Atrasadas',
          cantidad: kpisData.cuotas_atrasadas_mes,
          porcentaje: kpisData.total_cuotas_mes > 0
            ? (kpisData.cuotas_atrasadas_mes / kpisData.total_cuotas_mes) * 100
            : 0,
          color: '#ef4444',
        },
        {
          estado: 'Pendientes',
          cantidad: kpisData.total_cuotas_mes - kpisData.cuotas_pagadas - kpisData.cuotas_atrasadas_mes,
          porcentaje: kpisData.total_cuotas_mes > 0
            ? ((kpisData.total_cuotas_mes - kpisData.cuotas_pagadas - kpisData.cuotas_atrasadas_mes) / kpisData.total_cuotas_mes) * 100
            : 0,
          color: '#f59e0b',
        },
      ]
    : []

  // Cargar datos para gráfico de conciliación
  const datosConciliacion = kpisData
    ? [
        {
          estado: 'Conciliadas',
          cantidad: kpisData.total_cuotas_conciliadas,
          porcentaje: kpisData.total_cuotas_mes > 0
            ? (kpisData.total_cuotas_conciliadas / kpisData.total_cuotas_mes) * 100
            : 0,
          color: '#3b82f6',
        },
        {
          estado: 'No Conciliadas',
          cantidad: kpisData.cuotas_pagadas - kpisData.total_cuotas_conciliadas,
          porcentaje: kpisData.cuotas_pagadas > 0
            ? ((kpisData.cuotas_pagadas - kpisData.total_cuotas_conciliadas) / kpisData.cuotas_pagadas) * 100
            : 0,
          color: '#f59e0b',
        },
        {
          estado: 'Pendientes',
          cantidad: kpisData.total_cuotas_mes - kpisData.cuotas_pagadas,
          porcentaje: kpisData.total_cuotas_mes > 0
            ? ((kpisData.total_cuotas_mes - kpisData.cuotas_pagadas) / kpisData.total_cuotas_mes) * 100
            : 0,
          color: '#9ca3af',
        },
      ]
    : []

  // Cargar evolución de morosidad (últimos 6 meses) - DATOS REALES
  const { data: datosEvolucionMorosidad, isLoading: loadingEvolucion } = useQuery({
    queryKey: ['evolucion-morosidad', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses', '6')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/evolucion-morosidad?${queryParams.toString()}`
      ) as {
        meses: Array<{ mes: string; morosidad: number }>
      }
      return response.meses
    },
    staleTime: 2 * 60 * 1000, // âœ… ACTUALIZADO: 2 minutos para datos más frescos
    refetchOnWindowFocus: true, // âœ… ACTUALIZADO: Recargar al enfocar ventana para datos actualizados
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  const COLORS_ESTADO = ['#10b981', '#ef4444', '#f59e0b']
  const COLORS_CONCILIACION = ['#3b82f6', '#f59e0b', '#9ca3af']

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
              className="hover:bg-purple-50"
            >
              â† Menú
            </Button>
            <div>
              <h1 className="text-4xl font-black text-gray-900 uppercase tracking-tight">Cuotas</h1>
              <p className="text-lg text-gray-600 font-medium mt-1">
                Monitoreo Estratégico • {userName}
              </p>
            </div>
          </div>
        </motion.div>

        {/* BARRA DE FILTROS HORIZONTAL */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="shadow-md border-2 border-gray-200 bg-gradient-to-r from-gray-50 to-white">
            <CardContent className="p-4">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center space-x-2">
                  <div className="flex items-center space-x-2 text-sm font-semibold text-gray-700">
                    <Filter className="h-4 w-4 text-purple-600" />
                    <span>Filtros Rápidos</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <DashboardFiltrosPanel
                    filtros={filtros}
                    setFiltros={setFiltros}
                    onRefresh={handleRefresh}
                    isRefreshing={isRefreshing}
                    opcionesFiltros={opcionesFiltros}
                    loadingOpcionesFiltros={loadingOpcionesFiltros}
                    errorOpcionesFiltros={errorOpcionesFiltros}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* KPIs PRINCIPALES */}
        {loadingKpis ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
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
        ) : kpisData ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
            <KpiCardLarge
              title="Total Cuotas del Mes"
              value={kpisData.total_cuotas_mes}
              icon={Calendar}
              color="text-purple-600"
              bgColor="bg-purple-100"
              borderColor="border-purple-500"
              format="number"
            />
            <KpiCardLarge
              title="Cuotas Pagadas"
              value={kpisData.cuotas_pagadas}
              subtitle={`${kpisData.porcentaje_cuotas_pagadas.toFixed(1)}% del total`}
              icon={CheckCircle}
              color="text-green-600"
              bgColor="bg-green-100"
              borderColor="border-green-500"
              format="number"
            />
            <KpiCardLarge
              title="Cuotas Conciliadas"
              value={kpisData.total_cuotas_conciliadas}
              subtitle={`${((kpisData.total_cuotas_conciliadas / kpisData.total_cuotas_mes) * 100 || 0).toFixed(1)}% del total`}
              icon={Shield}
              color="text-blue-600"
              bgColor="bg-blue-100"
              borderColor="border-blue-500"
              format="number"
            />
            <KpiCardLarge
              title="Cuotas Atrasadas"
              value={kpisData.cuotas_atrasadas_mes}
              subtitle={`${((kpisData.cuotas_atrasadas_mes / kpisData.total_cuotas_mes) * 100 || 0).toFixed(1)}% del total`}
              icon={AlertTriangle}
              color="text-red-600"
              bgColor="bg-red-100"
              borderColor="border-red-500"
              format="number"
            />
            <KpiCardLarge
              title="Saldo Pendiente"
              value={0}
              subtitle="Mes actual"
              icon={TrendingUp}
              color="text-orange-600"
              bgColor="bg-orange-100"
              borderColor="border-orange-500"
              format="currency"
            />
            <KpiCardLarge
              title="Tasa de Recuperación"
              value={kpisData.porcentaje_cuotas_pagadas}
              subtitle="Mes actual"
              icon={CheckCircle}
              color="text-teal-600"
              bgColor="bg-teal-100"
              borderColor="border-teal-500"
              format="percentage"
            />
          </div>
        ) : null}

        {/* LAYOUT: BOTONES IZQUIERDA + GRÁFICOS CENTRO */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* COLUMNA IZQUIERDA: BOTONES EXPLORAR DETALLES */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-3"
          >
            <Card className="shadow-lg border-2 border-purple-200 bg-gradient-to-br from-purple-50 to-pink-50 sticky top-4">
              <CardHeader className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-t-lg -m-0.5 mb-4">
                <CardTitle className="text-xl font-bold text-white flex items-center space-x-2">
                  <span>ðŸ”</span>
                  <span>Explorar Detalles</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-purple-50 text-gray-800 border-2 border-purple-200 hover:border-purple-400 h-auto py-3 px-4"
                  onClick={() => {
                    // TODO: Navegar a cuotas pendientes detalle
                    console.log('Cuotas Pendientes Detalle')
                  }}
                >
                  <Calendar className="h-5 w-5 mr-3 text-purple-600" />
                  <span className="font-semibold flex-1 text-left">Cuotas Pendientes</span>
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-purple-50 text-gray-800 border-2 border-purple-200 hover:border-purple-400 h-auto py-3 px-4"
                  onClick={() => {
                    // TODO: Navegar a análisis de morosidad
                    console.log('Análisis de Morosidad Avanzada')
                  }}
                >
                  <AlertTriangle className="h-5 w-5 mr-3 text-purple-600" />
                  <span className="font-semibold flex-1 text-left">Análisis de Morosidad</span>
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-purple-50 text-gray-800 border-2 border-purple-200 hover:border-purple-400 h-auto py-3 px-4"
                  onClick={() => {
                    // TODO: Navegar a cuotas por cliente
                    console.log('Cuotas por Cliente (2+ impagas)')
                  }}
                >
                  <Users className="h-5 w-5 mr-3 text-purple-600" />
                  <span className="font-semibold flex-1 text-left">Cuotas por Cliente</span>
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-purple-50 text-gray-800 border-2 border-purple-200 hover:border-purple-400 h-auto py-3 px-4"
                  onClick={() => {
                    // TODO: Navegar a historial de pagos
                    console.log('Historial de Pagos')
                  }}
                >
                  <CheckCircle className="h-5 w-5 mr-3 text-purple-600" />
                  <span className="font-semibold flex-1 text-left">Historial de Pagos</span>
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </Button>
              </CardContent>
            </Card>
          </motion.div>

          {/* COLUMNA CENTRO/DERECHA: GRÁFICOS PRINCIPALES */}
          <div className="lg:col-span-9 space-y-6">
            {/* Gráficos en Grid 2 Columnas */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico 1: Estado de Cuotas del Mes */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 border-b-2 border-purple-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <BarChart3 className="h-6 w-6 text-purple-600" />
                      <span>Estado de Cuotas del Mes</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingKpis ? (
                      <div className="h-[300px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosEstadoCuotas.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={datosEstadoCuotas}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="estado" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip />
                          <Legend />
                          <Bar dataKey="cantidad" radius={[8, 8, 0, 0]}>
                            {datosEstadoCuotas.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[300px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              {/* Gráfico 2: Cuotas por Estado de Conciliación */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-blue-50 to-cyan-50 border-b-2 border-blue-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <PieChart className="h-6 w-6 text-blue-600" />
                      <span>Cuotas por Estado de Conciliación</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingKpis ? (
                      <div className="h-[300px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosConciliacion.length > 0 ? (
                      <div className="relative">
                        <ResponsiveContainer width="100%" height={300}>
                          <RechartsPieChart>
                            <Pie
                              data={datosConciliacion.map((c) => ({
                                name: c.estado,
                                value: c.porcentaje,
                                cantidad: c.cantidad,
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
                              {datosConciliacion.map((entry, index) => (
                                <Cell
                                  key={`cell-${index}`}
                                  fill={COLORS_CONCILIACION[index % COLORS_CONCILIACION.length]}
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
                              {kpisData?.total_cuotas_mes.toLocaleString()}
                            </div>
                            <div className="text-xs text-gray-500">Total Cuotas</div>
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
            </div>

            {/* Gráfico 3: Evolución de Morosidad */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-red-50 to-orange-50 border-b-2 border-red-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <TrendingUp className="h-6 w-6 text-red-600" />
                    <span>Evolución de Morosidad (Ãšltimos 6 Meses)</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  {loadingEvolucion ? (
                    <div className="h-[300px] flex items-center justify-center">
                      <div className="animate-pulse text-gray-400">Cargando...</div>
                    </div>
                  ) : datosEvolucionMorosidad && datosEvolucionMorosidad.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={datosEvolucionMorosidad}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="mes" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" />
                        <Tooltip formatter={(value: number) => formatCurrency(value)} />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="morosidad"
                          stroke="#ef4444"
                          strokeWidth={3}
                          name="Morosidad"
                        />
                      </LineChart>
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
        </div>
      </div>
    </div>
  )
}
