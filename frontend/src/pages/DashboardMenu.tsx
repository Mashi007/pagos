import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  DollarSign,
  CreditCard,
  Calendar,
  BarChart3,
  Activity,
  ChevronRight,
  Filter,
  TrendingUp,
  Users,
  Target,
  AlertTriangle,
  Shield,
  CheckCircle,
  Clock,
  FileText,
  PieChart,
  LineChart,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency } from '@/utils'
import { apiClient } from '@/services/api'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { DashboardFiltrosPanel } from '@/components/dashboard/DashboardFiltrosPanel'
import { KpiCardLarge } from '@/components/dashboard/KpiCardLarge'
import {
  BarChart,
  Bar,
  LineChart as RechartsLineChart,
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

interface KpiCategory {
  id: string
  title: string
  description: string
  icon: typeof DollarSign
  color: string
  hoverColor: string
  bgColor: string
  route: string
}

const categories: KpiCategory[] = [
  {
    id: 'financiamiento',
    title: 'Financiamiento',
    description: 'Total y por estado',
    icon: DollarSign,
    color: 'text-cyan-600',
    hoverColor: 'hover:border-cyan-500 hover:shadow-[0_8px_30px_rgba(6,182,212,0.3)] hover:bg-gradient-to-br hover:from-cyan-50 hover:to-blue-50',
    bgColor: 'bg-gradient-to-br from-cyan-100 to-blue-100',
    route: '/dashboard/financiamiento',
  },
  {
    id: 'cuotas',
    title: 'Cuotas y Amortizaciones',
    description: 'Gestión de cuotas y pagos',
    icon: Calendar,
    color: 'text-purple-600',
    hoverColor: 'hover:border-purple-500 hover:shadow-[0_8px_30px_rgba(168,85,247,0.3)] hover:bg-gradient-to-br hover:from-purple-50 hover:to-pink-50',
    bgColor: 'bg-gradient-to-br from-purple-100 to-pink-100',
    route: '/dashboard/cuotas',
  },
  {
    id: 'cobranza',
    title: 'Cobranza',
    description: 'Recaudación y metas',
    icon: CreditCard,
    color: 'text-emerald-600',
    hoverColor: 'hover:border-emerald-500 hover:shadow-[0_8px_30px_rgba(16,185,129,0.3)] hover:bg-gradient-to-br hover:from-emerald-50 hover:to-teal-50',
    bgColor: 'bg-gradient-to-br from-emerald-100 to-teal-100',
    route: '/dashboard/cobranza',
  },
  {
    id: 'analisis',
    title: 'Análisis y Gráficos',
    description: 'Visualizaciones detalladas',
    icon: BarChart3,
    color: 'text-amber-600',
    hoverColor: 'hover:border-amber-500 hover:shadow-[0_8px_30px_rgba(245,158,11,0.3)] hover:bg-gradient-to-br hover:from-amber-50 hover:to-orange-50',
    bgColor: 'bg-gradient-to-br from-amber-100 to-orange-100',
    route: '/dashboard/analisis',
  },
  {
    id: 'pagos',
    title: 'Pagos',
    description: 'KPIs de transacciones',
    icon: Activity,
    color: 'text-violet-600',
    hoverColor: 'hover:border-violet-500 hover:shadow-[0_8px_30px_rgba(139,92,246,0.3)] hover:bg-gradient-to-br hover:from-violet-50 hover:to-indigo-50',
    bgColor: 'bg-gradient-to-br from-violet-100 to-indigo-100',
    route: '/dashboard/pagos',
  },
]

export function DashboardMenu() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [periodo, setPeriodo] = useState('mes')
  const { construirParams, construirFiltrosObject } = useDashboardFiltros(filtros)

  // Verificar que el componente se está renderizando - NUEVO DISEÑO v2.0 (solo una vez)
  useEffect(() => {
    console.log('✅✅✅ DASHBOARD MENU - NUEVO DISEÑO v2.0 ACTIVO ✅✅✅')
    console.log('🎨 Elementos del diseño:', {
      badge: '✨ NUEVO DISEÑO v2.0',
      titulo: 'DASHBOARD EJECUTIVO',
      modulos: categories.length,
      usuario: userName
    })
  }, [])

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  // Cargar KPIs principales
  const { data: kpisPrincipales, isLoading: loadingKPIs, refetch } = useQuery({
    queryKey: ['kpis-principales-menu', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      console.log('🔍 [KPIs Principales] Filtros aplicados:', filtros)
      console.log('🔍 [KPIs Principales] Parámetros construidos:', params)
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      console.log('🔍 [KPIs Principales] Query string:', queryString)
      const response = await apiClient.get(
        `/api/v1/dashboard/kpis-principales${queryString ? '?' + queryString : ''}`
      ) as {
        total_prestamos: { valor_actual: number; variacion_porcentual: number }
        creditos_nuevos_mes: { valor_actual: number; variacion_porcentual: number }
        total_clientes: { valor_actual: number; variacion_porcentual: number }
        total_morosidad_usd: { valor_actual: number; variacion_porcentual: number }
      }
      return response
    },
    staleTime: 5 * 60 * 1000,
    enabled: true, // Asegurar que siempre esté habilitado
  })

  // Cargar datos para gráficos (con timeout extendido)
  const { data: datosDashboard, isLoading: loadingDashboard } = useQuery({
    queryKey: ['dashboard-menu', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      try {
        const params = construirParams(periodo)
        console.log('🔍 [Dashboard Admin] Filtros aplicados:', filtros)
        console.log('🔍 [Dashboard Admin] Parámetros construidos:', params)
        // Usar timeout extendido para endpoints lentos
        const response = await apiClient.get(`/api/v1/dashboard/admin?${params}`, { timeout: 60000 }) as {
          financieros?: { ingresosCapital: number; ingresosInteres: number; ingresosMora: number }
          evolucion_mensual?: Array<{ mes: string; cartera: number; cobrado: number; morosidad: number }>
        }
        return response
      } catch (error) {
        console.warn('Error cargando dashboard:', error)
        return {}
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: 1, // Solo un retry para evitar múltiples intentos
    enabled: true, // Asegurar que siempre esté habilitado
  })

  // Cargar tendencia mensual de financiamiento
  const { data: datosTendencia, isLoading: loadingTendencia } = useQuery({
    queryKey: ['financiamiento-tendencia', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses', '12')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/financiamiento-tendencia-mensual?${queryParams.toString()}`
      ) as { meses: Array<{ mes: string; cantidad_nuevos: number; monto_nuevos: number; total_acumulado: number }> }
      return response.meses
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })

  // Cargar préstamos por concesionario
  const { data: datosConcesionarios, isLoading: loadingConcesionarios } = useQuery({
    queryKey: ['prestamos-concesionario', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/prestamos-por-concesionario?${queryParams.toString()}`
      ) as { concesionarios: Array<{ concesionario: string; total_prestamos: number; porcentaje: number }> }
      return response.concesionarios.slice(0, 10) // Top 10
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })

  // Cargar cobranzas mensuales (con timeout extendido)
  const { data: datosCobranzas, isLoading: loadingCobranzas } = useQuery({
    queryKey: ['cobranzas-mensuales', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      // Usar timeout extendido para endpoints lentos
      const response = await apiClient.get(
        `/api/v1/dashboard/cobranzas-mensuales?${queryParams.toString()}`,
        { timeout: 60000 }
      ) as { meses: Array<{ nombre_mes: string; cobranzas_planificadas: number; pagos_reales: number; meta_mensual: number }> }
      return response.meses.slice(-12) // Últimos 12 meses
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
    enabled: true,
  })

  // Cargar morosidad por analista
  const { data: datosMorosidadAnalista, isLoading: loadingMorosidadAnalista } = useQuery({
    queryKey: ['morosidad-analista', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/morosidad-por-analista?${queryParams.toString()}`
      ) as { analistas: Array<{ analista: string; total_morosidad: number; cantidad_clientes: number }> }
      return response.analistas.slice(0, 10) // Top 10
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })

  // Cargar evolución de morosidad
  const { data: datosEvolucionMorosidad, isLoading: loadingEvolucionMorosidad } = useQuery({
    queryKey: ['evolucion-morosidad-menu', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses', '6')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/evolucion-morosidad?${queryParams.toString()}`
      ) as { meses: Array<{ mes: string; morosidad: number }> }
      return response.meses
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })

  // Cargar evolución de pagos (con timeout extendido)
  const { data: datosEvolucionPagos, isLoading: loadingEvolucionPagos } = useQuery({
    queryKey: ['evolucion-pagos-menu', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses', '6')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      // Usar timeout extendido para endpoints lentos
      const response = await apiClient.get(
        `/api/v1/dashboard/evolucion-pagos?${queryParams.toString()}`,
        { timeout: 60000 }
      ) as { meses: Array<{ mes: string; pagos: number; monto: number }> }
      return response.meses
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
    enabled: true,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  const evolucionMensual = datosDashboard?.evolucion_mensual || []
  const COLORS_CONCESIONARIOS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1']

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-4 py-8 space-y-8">
        {/* Header con Badge */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative"
        >
          {/* Badge de identificación del nuevo diseño - MÁS VISIBLE */}
          <div className="absolute top-0 right-0 bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-black shadow-2xl z-50 border-2 border-emerald-400 animate-pulse">
            ✨ NUEVO DISEÑO v2.0
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-5xl font-black text-gray-900 mb-3 tracking-tight">
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-600 via-blue-600 to-purple-600">
                  DASHBOARD
                </span>{' '}
                <span className="text-gray-800">EJECUTIVO</span>
              </h1>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
                  <div className="absolute inset-0 h-2 w-2 rounded-full bg-emerald-400 animate-ping opacity-75"></div>
                </div>
                <p className="text-gray-600 font-semibold text-sm tracking-wide">
                  Bienvenido, <span className="text-cyan-600 font-black">{userName}</span> • Monitoreo Estratégico
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* BARRA DE FILTROS Y BOTONES ARRIBA */}
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
                    <Filter className="h-4 w-4 text-cyan-600" />
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
                {/* Botones de navegación rápida */}
                <div className="flex items-center gap-2">
                  {categories.map((category) => {
                    const Icon = category.icon
                    return (
                      <Button
                        key={category.id}
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(category.route)}
                        className={`${category.color} border-2 hover:bg-opacity-10`}
                      >
                        <Icon className="h-4 w-4 mr-2" />
                        {category.title.split(' ')[0]}
                      </Button>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* LAYOUT PRINCIPAL: KPIs IZQUIERDA + GRÁFICOS DERECHA */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* COLUMNA IZQUIERDA: KPIs PRINCIPALES VERTICALES */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-3 space-y-4"
          >
            {loadingKPIs ? (
              <div className="space-y-4">
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
            ) : kpisPrincipales ? (
              <div className="space-y-4 sticky top-4">
                <KpiCardLarge
                  title="Total Préstamos"
                  value={kpisPrincipales.total_prestamos.valor_actual}
                  icon={FileText}
                  color="text-cyan-600"
                  bgColor="bg-cyan-100"
                  borderColor="border-cyan-500"
                  format="number"
                  variation={{
                    percent: kpisPrincipales.total_prestamos.variacion_porcentual,
                    label: 'vs mes anterior',
                  }}
                />
                <KpiCardLarge
                  title="Créditos Nuevos"
                  value={kpisPrincipales.creditos_nuevos_mes.valor_actual}
                  icon={TrendingUp}
                  color="text-green-600"
                  bgColor="bg-green-100"
                  borderColor="border-green-500"
                  format="number"
                  variation={{
                    percent: kpisPrincipales.creditos_nuevos_mes.variacion_porcentual,
                    label: 'vs mes anterior',
                  }}
                />
                <KpiCardLarge
                  title="Total Clientes"
                  value={kpisPrincipales.total_clientes.valor_actual}
                  icon={Users}
                  color="text-blue-600"
                  bgColor="bg-blue-100"
                  borderColor="border-blue-500"
                  format="number"
                  variation={{
                    percent: kpisPrincipales.total_clientes.variacion_porcentual,
                    label: 'vs mes anterior',
                  }}
                />
                <KpiCardLarge
                  title="Morosidad Total"
                  value={kpisPrincipales.total_morosidad_usd.valor_actual}
                  icon={AlertTriangle}
                  color="text-red-600"
                  bgColor="bg-red-100"
                  borderColor="border-red-500"
                  format="currency"
                  variation={{
                    percent: kpisPrincipales.total_morosidad_usd.variacion_porcentual,
                    label: 'vs mes anterior',
                  }}
                />
                <KpiCardLarge
                  title="Cartera Total"
                  value={datosDashboard?.financieros?.ingresosCapital || 0}
                  icon={DollarSign}
                  color="text-purple-600"
                  bgColor="bg-purple-100"
                  borderColor="border-purple-500"
                  format="currency"
                />
                <KpiCardLarge
                  title="Total Cobrado"
                  value={datosDashboard?.financieros?.ingresosInteres || 0}
                  icon={CheckCircle}
                  color="text-emerald-600"
                  bgColor="bg-emerald-100"
                  borderColor="border-emerald-500"
                  format="currency"
                />
              </div>
            ) : null}
          </motion.div>

          {/* COLUMNA DERECHA: 6 GRÁFICOS PRINCIPALES (2x3) */}
          <div className="lg:col-span-9 space-y-6">
            {/* Fila 1: 2 Gráficos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico 1: Tendencia Mensual Financiamiento */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-cyan-50 to-blue-50 border-b-2 border-cyan-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <TrendingUp className="h-6 w-6 text-cyan-600" />
                      <span>Tendencia Financiamiento</span>
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
                            <linearGradient id="colorMonto" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                              <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.1} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="mes" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Area type="monotone" dataKey="monto_nuevos" stroke="#06b6d4" fillOpacity={1} fill="url(#colorMonto)" name="Monto Nuevos" />
                          <Line type="monotone" dataKey="total_acumulado" stroke="#3b82f6" strokeWidth={2} name="Total Acumulado" />
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

              {/* Gráfico 2: Distribución por Concesionario */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 border-b-2 border-purple-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <PieChart className="h-6 w-6 text-purple-600" />
                      <span>Préstamos por Concesionario</span>
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
                                value: c.porcentaje,
                                total: c.total_prestamos,
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
                                <Cell key={`cell-${index}`} fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]} />
                              ))}
                            </Pie>
                            <Tooltip />
                          </RechartsPieChart>
                        </ResponsiveContainer>
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

            {/* Fila 2: 2 Gráficos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico 3: Cobranzas Mensuales */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-emerald-50 to-teal-50 border-b-2 border-emerald-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <BarChart3 className="h-6 w-6 text-emerald-600" />
                      <span>Cobranzas Mensuales</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingCobranzas ? (
                      <div className="h-[300px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosCobranzas && datosCobranzas.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={datosCobranzas}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="nombre_mes" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Bar dataKey="cobranzas_planificadas" fill="#10b981" radius={[8, 8, 0, 0]} name="Planificado" />
                          <Bar dataKey="pagos_reales" fill="#3b82f6" radius={[8, 8, 0, 0]} name="Recaudado" />
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

              {/* Gráfico 4: Morosidad por Analista */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-red-50 to-orange-50 border-b-2 border-red-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <AlertTriangle className="h-6 w-6 text-red-600" />
                      <span>Morosidad por Analista</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingMorosidadAnalista ? (
                      <div className="h-[300px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosMorosidadAnalista && datosMorosidadAnalista.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={datosMorosidadAnalista} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis type="number" stroke="#6b7280" />
                          <YAxis dataKey="analista" type="category" stroke="#6b7280" width={120} />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Bar dataKey="total_morosidad" fill="#ef4444" radius={[0, 8, 8, 0]} name="Morosidad" />
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
            </div>

            {/* Fila 3: 2 Gráficos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico 5: Evolución de Morosidad */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-red-50 to-orange-50 border-b-2 border-red-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <LineChart className="h-6 w-6 text-red-600" />
                      <span>Evolución de Morosidad</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingEvolucionMorosidad ? (
                      <div className="h-[300px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosEvolucionMorosidad && datosEvolucionMorosidad.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <RechartsLineChart data={datosEvolucionMorosidad}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="mes" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Line type="monotone" dataKey="morosidad" stroke="#ef4444" strokeWidth={3} name="Morosidad" />
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

              {/* Gráfico 6: Evolución de Pagos */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-violet-50 to-indigo-50 border-b-2 border-violet-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <Activity className="h-6 w-6 text-violet-600" />
                      <span>Evolución de Pagos</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingEvolucionPagos ? (
                      <div className="h-[300px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosEvolucionPagos && datosEvolucionPagos.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={datosEvolucionPagos}>
                          <defs>
                            <linearGradient id="colorEvolucionPagos" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="mes" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Area type="monotone" dataKey="monto" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorEvolucionPagos)" name="Monto Total" />
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
    </div>
  )
}
