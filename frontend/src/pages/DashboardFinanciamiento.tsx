import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  DollarSign,
  Activity,
  Clock,
  CheckCircle,
  TrendingUp,
  FileText,
  BarChart3,
  PieChart,
  ChevronRight,
  Filter,
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
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'

interface KPIsData {
  total_financiamiento: number
  total_financiamiento_activo: number
  total_financiamiento_inactivo: number
  total_financiamiento_finalizado: number
  total_financiamientos: number
  monto_promedio: number
}

interface EstadoData {
  estado: string
  monto: number
  cantidad: number
  porcentaje: number
}

interface ConcesionarioData {
  concesionario: string
  cantidad_prestamos: number
  monto_total: number
  porcentaje_cantidad: number
  porcentaje_monto: number
}

interface TendenciaMensualData {
  mes: string
  cantidad_nuevos: number
  monto_nuevos: number
  total_acumulado: number
}

export function DashboardFinanciamiento() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  // Cargar KPIs
  const { data: kpisData, isLoading: loadingKpis, refetch } = useQuery({
    queryKey: ['kpis-financiamiento', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/kpis/dashboard${queryString ? '?' + queryString : ''}`
      ) as KPIsData & { total_prestamos?: number; promedio_financiamiento?: number }

      const total_financiamientos = response.total_prestamos || 0
      const monto_total = response.total_financiamiento || 0
      const monto_promedio = total_financiamientos > 0 ? monto_total / total_financiamientos : 0

      return {
        total_financiamiento: monto_total,
        total_financiamiento_activo: response.total_financiamiento_activo || 0,
        total_financiamiento_inactivo: response.total_financiamiento_inactivo || 0,
        total_financiamiento_finalizado: response.total_financiamiento_finalizado || 0,
        total_financiamientos: total_financiamientos,
        monto_promedio: monto_promedio,
      } as KPIsData
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar datos de gráfico por estado
  const { data: datosEstado, isLoading: loadingEstado } = useQuery({
    queryKey: ['financiamiento-por-estado', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = (await apiClient.get(
        `/api/v1/kpis/dashboard${queryString ? '?' + queryString : ''}`
      )) as {
        total_financiamiento?: number
        total_financiamiento_activo?: number
        total_financiamiento_inactivo?: number
        total_financiamiento_finalizado?: number
      }

      const total = response.total_financiamiento || 0
      const activo = response.total_financiamiento_activo || 0
      const inactivo = response.total_financiamiento_inactivo || 0
      const finalizado = response.total_financiamiento_finalizado || 0

      const datos: EstadoData[] = [
        {
          estado: 'Activo',
          monto: activo,
          cantidad: 0, // Se calcularía desde BD si es necesario
          porcentaje: total > 0 ? (activo / total) * 100 : 0,
        },
        {
          estado: 'Inactivo',
          monto: inactivo,
          cantidad: 0,
          porcentaje: total > 0 ? (inactivo / total) * 100 : 0,
        },
        {
          estado: 'Finalizado',
          monto: finalizado,
          cantidad: 0,
          porcentaje: total > 0 ? (finalizado / total) * 100 : 0,
        },
      ]

      return datos
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar datos de concesionarios
  const { data: datosConcesionarios, isLoading: loadingConcesionarios } = useQuery({
    queryKey: ['prestamos-por-concesionario', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/prestamos-por-concesionario${queryString ? '?' + queryString : ''}`
      ) as { concesionarios: ConcesionarioData[] }

      // Tomar top 10 y agrupar el resto como "Otros"
      const top10 = response.concesionarios.slice(0, 10)
      const otros = response.concesionarios.slice(10)
      const otrosSum = otros.reduce(
        (acc, c) => ({
          cantidad_prestamos: acc.cantidad_prestamos + c.cantidad_prestamos,
          monto_total: acc.monto_total + c.monto_total,
          porcentaje_cantidad: acc.porcentaje_cantidad + c.porcentaje_cantidad,
          porcentaje_monto: acc.porcentaje_monto + c.porcentaje_monto,
        }),
        {
          cantidad_prestamos: 0,
          monto_total: 0,
          porcentaje_cantidad: 0,
          porcentaje_monto: 0,
        }
      )

      const result = [...top10]
      if (otrosSum.cantidad_prestamos > 0) {
        result.push({
          concesionario: 'Otros',
          ...otrosSum,
        })
      }

      return result
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar tendencia mensual
  const { data: datosTendencia, isLoading: loadingTendencia } = useQuery({
    queryKey: ['financiamiento-tendencia-mensual', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      queryParams.append('meses', '12')
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/financiamiento-tendencia-mensual?${queryString}`
      ) as { meses: TendenciaMensualData[] }

      return response.meses
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  // Colores para gráficos
  const COLORS_POR_ESTADO = {
    Activo: '#10b981', // green-500
    Inactivo: '#f59e0b', // amber-500
    Finalizado: '#6366f1', // indigo-500
  }

  const COLORS_CONCESIONARIOS = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
  ]

  // Calcular totales para donut
  const totalConcesionarios = datosConcesionarios?.reduce(
    (acc, c) => ({
      cantidad: acc.cantidad + c.cantidad_prestamos,
      monto: acc.monto + c.monto_total,
    }),
    { cantidad: 0, monto: 0 }
  )

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
              className="hover:bg-cyan-50"
            >
              ← Menú
            </Button>
            <div>
              <h1 className="text-6xl font-black text-gray-900 uppercase tracking-tight">
                Financiamiento
              </h1>
              <p className="text-xl text-gray-600 font-medium mt-1">
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
                  <div className="flex items-center space-x-2 text-base font-semibold text-gray-700">
                    <Filter className="h-5 w-5 text-cyan-600" />
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

        {/* KPIs PRINCIPALES - Grid Grande */}
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
              title="Total Financiamiento"
              value={kpisData.total_financiamiento}
              icon={DollarSign}
              color="text-cyan-600"
              bgColor="bg-cyan-100"
              borderColor="border-cyan-500"
              format="currency"
            />
            <KpiCardLarge
              title="Activo"
              value={kpisData.total_financiamiento_activo}
              subtitle={`${((kpisData.total_financiamiento_activo / kpisData.total_financiamiento) * 100 || 0).toFixed(1)}% del total`}
              icon={Activity}
              color="text-green-600"
              bgColor="bg-green-100"
              borderColor="border-green-500"
              format="currency"
            />
            <KpiCardLarge
              title="Inactivo"
              value={kpisData.total_financiamiento_inactivo}
              subtitle={`${((kpisData.total_financiamiento_inactivo / kpisData.total_financiamiento) * 100 || 0).toFixed(1)}% del total`}
              icon={Clock}
              color="text-amber-600"
              bgColor="bg-amber-100"
              borderColor="border-amber-500"
              format="currency"
            />
            <KpiCardLarge
              title="Finalizado"
              value={kpisData.total_financiamiento_finalizado}
              subtitle={`${((kpisData.total_financiamiento_finalizado / kpisData.total_financiamiento) * 100 || 0).toFixed(1)}% del total`}
              icon={CheckCircle}
              color="text-indigo-600"
              bgColor="bg-indigo-100"
              borderColor="border-indigo-500"
              format="currency"
            />
            <KpiCardLarge
              title="Total Préstamos"
              value={kpisData.total_financiamientos}
              icon={FileText}
              color="text-blue-600"
              bgColor="bg-blue-100"
              borderColor="border-blue-500"
              format="number"
            />
            <KpiCardLarge
              title="Monto Promedio"
              value={kpisData.monto_promedio}
              icon={TrendingUp}
              color="text-purple-600"
              bgColor="bg-purple-100"
              borderColor="border-purple-500"
              format="currency"
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
            <Card className="shadow-lg border-2 border-cyan-200 bg-gradient-to-br from-cyan-50 to-blue-50 sticky top-4">
                  <CardHeader className="bg-gradient-to-r from-cyan-600 to-blue-600 rounded-t-lg -m-0.5 mb-4">
                <CardTitle className="text-2xl font-bold text-white flex items-center space-x-2">
                  <span>🔍</span>
                  <span>Explorar Detalles</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-cyan-50 text-gray-800 border-2 border-cyan-200 hover:border-cyan-400 h-auto py-3 px-4"
                  onClick={() => {
                    // TODO: Navegar a detalle de activos
                    console.log('Ver Financiamientos Activos Detalle')
                  }}
                >
                  <FileText className="h-6 w-6 mr-3 text-cyan-600" />
                  <span className="font-semibold text-base flex-1 text-left">Ver Financiamientos Activos</span>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-cyan-50 text-gray-800 border-2 border-cyan-200 hover:border-cyan-400 h-auto py-3 px-4"
                  onClick={() => {
                    // TODO: Navegar a análisis por estado
                    console.log('Análisis por Estado Completo')
                  }}
                >
                  <BarChart3 className="h-6 w-6 mr-3 text-cyan-600" />
                  <span className="font-semibold text-base flex-1 text-left">Análisis por Estado</span>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-cyan-50 text-gray-800 border-2 border-cyan-200 hover:border-cyan-400 h-auto py-3 px-4"
                  onClick={() => navigate('/dashboard/analisis')}
                >
                  <PieChart className="h-6 w-6 mr-3 text-cyan-600" />
                  <span className="font-semibold text-base flex-1 text-left">Distribución Concesionarios</span>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-cyan-50 text-gray-800 border-2 border-cyan-200 hover:border-cyan-400 h-auto py-3 px-4"
                  onClick={() => {
                    // TODO: Navegar a tendencias temporales
                    console.log('Tendencias Temporales Detalladas')
                  }}
                >
                  <TrendingUp className="h-6 w-6 mr-3 text-cyan-600" />
                  <span className="font-semibold text-base flex-1 text-left">Tendencias Temporales</span>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-white hover:bg-cyan-50 text-gray-800 border-2 border-cyan-200 hover:border-cyan-400 h-auto py-3 px-4"
                  onClick={() => navigate('/dashboard/analisis')}
                >
                  <PieChart className="h-6 w-6 mr-3 text-cyan-600" />
                  <span className="font-semibold text-base flex-1 text-left">Por Tipo Producto</span>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </Button>
              </CardContent>
            </Card>
          </motion.div>

          {/* COLUMNA CENTRO/DERECHA: GRÁFICOS PRINCIPALES */}
          <div className="lg:col-span-9 space-y-6">
            {/* Gráficos en Grid 2 Columnas */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico 1: Financiamiento por Estado (Bar Chart) */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-cyan-50 to-blue-50 border-b-2 border-cyan-200">
                    <CardTitle className="flex items-center space-x-2 text-2xl font-bold text-gray-800">
                      <BarChart3 className="h-7 w-7 text-cyan-600" />
                      <span>Financiamiento por Estado</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingEstado ? (
                      <div className="h-[300px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosEstado && datosEstado.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={datosEstado}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="estado" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip
                            formatter={(value: number) => formatCurrency(value)}
                            contentStyle={{
                              backgroundColor: 'rgba(255, 255, 255, 0.98)',
                              border: '1px solid #e5e7eb',
                              borderRadius: '8px',
                            }}
                          />
                          <Legend />
                          <Bar dataKey="monto" fill="#3b82f6" radius={[8, 8, 0, 0]}>
                            {datosEstado.map((entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={COLORS_POR_ESTADO[entry.estado as keyof typeof COLORS_POR_ESTADO] || '#3b82f6'}
                              />
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

              {/* Gráfico 2: Distribución por Concesionario (Donut) */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 border-b-2 border-purple-200">
                    <CardTitle className="flex items-center space-x-2 text-2xl font-bold text-gray-800">
                      <PieChart className="h-6 w-6 text-purple-600" />
                      <span>Distribución por Concesionario</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingConcesionarios ? (
                      <div className="h-[300px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosConcesionarios && datosConcesionarios.length > 0 ? (
                      <div className="relative">
                        <ResponsiveContainer width="100%" height={300}>
                          <RechartsPieChart>
                            <Pie
                              data={datosConcesionarios.map((c) => ({
                                name: c.concesionario,
                                value: c.porcentaje_cantidad,
                                monto: c.monto_total,
                                cantidad: c.cantidad_prestamos,
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
                              {datosConcesionarios.map((entry, index) => (
                                <Cell
                                  key={`cell-${index}`}
                                  fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]}
                                />
                              ))}
                            </Pie>
                            <Tooltip
                              formatter={(value: number, name: string, props: { payload?: { cantidad?: number; monto?: number } }) => {
                                const cantidad = props.payload?.cantidad ?? 0
                                const monto = props.payload?.monto ?? 0
                                return [
                                  `${(value * 100).toFixed(1)}% (${cantidad} préstamos, ${formatCurrency(monto)})`,
                                  'Porcentaje',
                                ]
                              }}
                            />
                          </RechartsPieChart>
                        </ResponsiveContainer>
                        {/* Centro del donut con totales */}
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                          <div className="text-center">
                            <div className="text-2xl font-black text-gray-800">
                              {totalConcesionarios?.cantidad.toLocaleString()}
                            </div>
                            <div className="text-xs text-gray-500">Préstamos</div>
                            <div className="text-lg font-bold text-gray-700 mt-1">
                              {formatCurrency(totalConcesionarios?.monto || 0)}
                            </div>
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

            {/* Gráfico 3: Tendencia Mensual (Full Width) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-emerald-50 to-teal-50 border-b-2 border-emerald-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <TrendingUp className="h-6 w-6 text-emerald-600" />
                    <span>Tendencia Mensual de Financiamientos</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  {loadingTendencia ? (
                    <div className="h-[300px] flex items-center justify-center">
                      <div className="animate-pulse text-gray-400">Cargando...</div>
                    </div>
                  ) : datosTendencia && datosTendencia.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <AreaChart data={datosTendencia}>
                        <defs>
                          <linearGradient id="colorMontoNuevos" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="mes" stroke="#6b7280" />
                        <YAxis stroke="#6b7280" />
                        <Tooltip
                          formatter={(value: number) => formatCurrency(value)}
                          contentStyle={{
                            backgroundColor: 'rgba(255, 255, 255, 0.98)',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                          }}
                        />
                        <Legend />
                        <Area
                          type="monotone"
                          dataKey="monto_nuevos"
                          stroke="#3b82f6"
                          fillOpacity={1}
                          fill="url(#colorMontoNuevos)"
                          name="Monto Nuevos Financiamientos"
                        />
                        <Line
                          type="monotone"
                          dataKey="total_acumulado"
                          stroke="#10b981"
                          strokeWidth={3}
                          name="Total Acumulado"
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
        </div>
      </div>
    </div>
  )
}
