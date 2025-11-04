import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp,
  Users,
  Building2,
  DollarSign,
  BarChart3,
  PieChart,
  LineChart,
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
import { TreemapMorosidadModal } from '@/components/dashboard/modals/TreemapMorosidadModal'
import { DonutConcesionariosModal } from '@/components/dashboard/modals/DonutConcesionariosModal'
import { BarrasDivergentesModal } from '@/components/dashboard/modals/BarrasDivergentesModal'
import { TendenciasModal } from '@/components/dashboard/modals/TendenciasModal'
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'

interface DashboardData {
  financieros?: {
    ingresosCapital: number
    ingresosInteres: number
    ingresosMora: number
  }
  evolucion_mensual?: Array<{
    mes: string
    cartera: number
    cobrado: number
    morosidad: number
  }>
}

interface CobroDiario {
  fecha: string
  dia: string
  dia_semana: string
  total_a_cobrar: number
  total_cobrado: number
}

export function DashboardAnalisis() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [periodo, setPeriodo] = useState('mes')
  const { construirParams, construirFiltrosObject } = useDashboardFiltros(filtros)

  const [isTreemapMorosidadOpen, setIsTreemapMorosidadOpen] = useState(false)
  const [isDonutConcesionariosOpen, setIsDonutConcesionariosOpen] = useState(false)
  const [isBarrasDivergentesOpen, setIsBarrasDivergentesOpen] = useState(false)
  const [isTendenciasOpen, setIsTendenciasOpen] = useState(false)

  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  // Cargar KPIs principales
  const { data: kpisPrincipales, isLoading: loadingKPIs } = useQuery({
    queryKey: ['kpis-principales', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/kpis-principales${queryString ? '?' + queryString : ''}`
      ) as {
        total_prestamos: number
        variacion_mes_anterior: number
        creditos_nuevos_mes: number
        total_clientes: number
        total_morosidad: number
      }
      return response
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar datos del dashboard
  const { data: dashboardData, isLoading: loadingDashboard, refetch } = useQuery({
    queryKey: ['dashboard-analisis', periodo, filtros],
    queryFn: async () => {
      try {
        const params = construirParams(periodo)
        const response = await apiClient.get(`/api/v1/dashboard/admin?${params}`) as DashboardData
        return response
      } catch (error) {
        console.warn('Error cargando dashboard:', error)
        return {} as DashboardData
      }
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar cobros diarios del mes
  const { data: cobrosDiariosData, isLoading: loadingCobrosDiarios } = useQuery({
    queryKey: ['cobros-diarios', filtros],
    queryFn: async () => {
      try {
        const params = construirFiltrosObject()
        const queryParams = new URLSearchParams()
        queryParams.append('dias', '31')
        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })
        const response = await apiClient.get(`/api/v1/dashboard/cobros-diarios?${queryParams.toString()}`) as {
          datos: CobroDiario[]
        }
        return response.datos
      } catch (error) {
        console.warn('Error cargando cobros diarios:', error)
        return [] as CobroDiario[]
      }
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar evolución mensual
  const evolucionMensual = dashboardData?.evolucion_mensual || []

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  const totalFinanciamiento = dashboardData?.financieros?.ingresosCapital || 0
  const carteraCobrada = dashboardData?.financieros?.ingresosInteres || 0
  const morosidad = dashboardData?.financieros?.ingresosMora || 0

  // Calcular variación mes anterior (simulado por ahora)
  const variacionMesAnterior = kpisPrincipales?.variacion_mes_anterior || 0
  const crecimientoAnual = variacionMesAnterior * 1.2 // Simulado

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
              className="hover:bg-amber-50"
            >
              ← Menú
            </Button>
            <div>
              <h1 className="text-4xl font-black text-gray-900 uppercase tracking-tight">Análisis</h1>
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
                    <Filter className="h-4 w-4 text-amber-600" />
                    <span>Filtros Rápidos</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <DashboardFiltrosPanel
                    filtros={filtros}
                    setFiltros={setFiltros}
                    periodo={periodo}
                    setPeriodo={setPeriodo}
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
        {loadingKPIs || loadingDashboard ? (
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
              title="Variación Mes Anterior"
              value={variacionMesAnterior}
              icon={TrendingUp}
              color="text-amber-600"
              bgColor="bg-amber-100"
              borderColor="border-amber-500"
              format="percentage"
              variation={{
                percent: variacionMesAnterior,
                label: 'vs mes anterior',
              }}
            />
            <KpiCardLarge
              title="Crecimiento Anual"
              value={crecimientoAnual}
              icon={TrendingUp}
              color="text-green-600"
              bgColor="bg-green-100"
              borderColor="border-green-500"
              format="percentage"
            />
            <KpiCardLarge
              title="Clientes Activos"
              value={kpisPrincipales?.total_clientes || 0}
              icon={Users}
              color="text-blue-600"
              bgColor="bg-blue-100"
              borderColor="border-blue-500"
              format="number"
            />
            <KpiCardLarge
              title="Cartera Total"
              value={totalFinanciamiento}
              icon={DollarSign}
              color="text-purple-600"
              bgColor="bg-purple-100"
              borderColor="border-purple-500"
              format="currency"
            />
          </div>
        )}

        {/* GRÁFICOS PRINCIPALES */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Gráfico 1: Cobros Diarios del Mes */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="shadow-lg border-2 border-gray-200">
              <CardHeader className="bg-gradient-to-r from-amber-50 to-orange-50 border-b-2 border-amber-200">
                <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                  <LineChart className="h-6 w-6 text-amber-600" />
                  <span>Cobros Diarios del Mes</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                {loadingCobrosDiarios ? (
                  <div className="h-[300px] flex items-center justify-center">
                    <div className="animate-pulse text-gray-400">Cargando...</div>
                  </div>
                ) : cobrosDiariosData && cobrosDiariosData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={cobrosDiariosData}>
                      <defs>
                        <linearGradient id="colorCobrado" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8} />
                          <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.1} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="dia" stroke="#6b7280" />
                      <YAxis stroke="#6b7280" />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="total_cobrado"
                        stroke="#f59e0b"
                        fillOpacity={1}
                        fill="url(#colorCobrado)"
                        name="Total Cobrado"
                      />
                      <Line
                        type="monotone"
                        dataKey="total_a_cobrar"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        name="Total a Cobrar"
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

          {/* Gráfico 2: Análisis Comparativo */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="shadow-lg border-2 border-gray-200">
              <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b-2 border-blue-200">
                <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                  <BarChart3 className="h-6 w-6 text-blue-600" />
                  <span>Análisis Comparativo</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                {loadingDashboard ? (
                  <div className="h-[300px] flex items-center justify-center">
                    <div className="animate-pulse text-gray-400">Cargando...</div>
                  </div>
                ) : evolucionMensual.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <RechartsLineChart data={evolucionMensual}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="mes" stroke="#6b7280" />
                      <YAxis stroke="#6b7280" />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="cartera"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        name="Cartera"
                      />
                      <Line
                        type="monotone"
                        dataKey="cobrado"
                        stroke="#10b981"
                        strokeWidth={2}
                        name="Cobrado"
                      />
                      <Line
                        type="monotone"
                        dataKey="morosidad"
                        stroke="#ef4444"
                        strokeWidth={2}
                        name="Morosidad"
                      />
                    </RechartsLineChart>
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
          <div className="bg-gradient-to-r from-amber-600 to-orange-600 rounded-xl p-6 shadow-xl">
            <h2 className="text-2xl font-bold text-white mb-4 flex items-center space-x-2">
              <span>🔍</span>
              <span>Explorar Análisis Detallados</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-amber-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => setIsTreemapMorosidadOpen(true)}
              >
                <PieChart className="h-6 w-6" />
                <span className="font-semibold">Morosidad por Analista</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-amber-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => setIsDonutConcesionariosOpen(true)}
              >
                <Building2 className="h-6 w-6" />
                <span className="font-semibold">Préstamos por Concesionario</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-amber-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => setIsBarrasDivergentesOpen(true)}
              >
                <BarChart3 className="h-6 w-6" />
                <span className="font-semibold">Distribución de Préstamos</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-amber-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => setIsTendenciasOpen(true)}
              >
                <LineChart className="h-6 w-6" />
                <span className="font-semibold">Tendencias y Proyecciones</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Modales */}
      <TreemapMorosidadModal
        isOpen={isTreemapMorosidadOpen}
        onClose={() => setIsTreemapMorosidadOpen(false)}
      />
      <DonutConcesionariosModal
        isOpen={isDonutConcesionariosOpen}
        onClose={() => setIsDonutConcesionariosOpen(false)}
      />
      <BarrasDivergentesModal
        isOpen={isBarrasDivergentesOpen}
        onClose={() => setIsBarrasDivergentesOpen(false)}
      />
      <TendenciasModal isOpen={isTendenciasOpen} onClose={() => setIsTendenciasOpen(false)} />
    </div>
  )
}
