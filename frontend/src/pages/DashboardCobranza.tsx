import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  CreditCard,
  Target,
  TrendingUp,
  Shield,
  Clock,
  Users,
  BarChart3,
  TrendingDown,
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
import { CobranzasMensualesModal } from '../components/dashboard/modals/CobranzasMensualesModal'
import { CobranzaPorDiaModal } from '../components/dashboard/modals/CobranzaPorDiaModal'
import { CobranzaPlanificadaRealModal } from '../components/dashboard/modals/CobranzaPlanificadaRealModal'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'

interface DashboardData {
  meta_mensual: number
  avance_meta: number
  financieros?: {
    totalCobrado: number
    tasaRecuperacion: number
  }
}

export function DashboardCobranza() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [periodo, setPeriodo] = useState('mes')
  const { construirParams, construirFiltrosObject } = useDashboardFiltros(filtros)

  const [isCobranzasMensualesOpen, setIsCobranzasMensualesOpen] = useState(false)
  const [isCobranzaPorDiaOpen, setIsCobranzaPorDiaOpen] = useState(false)
  const [isCobranzaPlanificadaRealOpen, setIsCobranzaPlanificadaRealOpen] = useState(false)

  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  const { data: dashboardData, isLoading: loadingDashboard, refetch } = useQuery({
    queryKey: ['dashboard-cobranza', periodo, filtros],
    queryFn: async () => {
      try {
        const params = construirParams(periodo)
        const response = await apiClient.get(`/api/v1/dashboard/admin?${params}`) as DashboardData
        return response
      } catch (error) {
        console.warn('Error cargando dashboard:', error)
        return {
          meta_mensual: 0,
          avance_meta: 0,
          financieros: { totalCobrado: 0, tasaRecuperacion: 0 },
        } as DashboardData
      }
    },
    staleTime: 2 * 60 * 1000, // âœ… ACTUALIZADO: 2 minutos para datos más frescos
    refetchOnWindowFocus: true, // âœ… ACTUALIZADO: Recargar al enfocar ventana para datos actualizados
  })

  // Cargar recaudación por día del mes
  const { data: datosRecaudacionDia, isLoading: loadingRecaudacionDia } = useQuery({
    queryKey: ['cobranza-por-dia-mes', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      queryParams.append('dias', '31') // Ãšltimos 31 días
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/cobranza-por-dia?${queryString}`
      ) as { dias: Array<{ fecha: string; total_a_cobrar: number; pagos: number; morosidad: number }> }

      // Filtrar solo días del mes actual
      const hoy = new Date()
      const primerDiaMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
      return response.dias.filter(d => new Date(d.fecha) >= primerDiaMes)
    },
    staleTime: 2 * 60 * 1000, // âœ… ACTUALIZADO: 2 minutos para datos más frescos
    refetchOnWindowFocus: true, // âœ… ACTUALIZADO: Recargar al enfocar ventana para datos actualizados
  })

  // Cargar distribución por analista
  const { data: datosAnalistas, isLoading: loadingAnalistas } = useQuery({
    queryKey: ['cobros-por-analista', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/cobros-por-analista${queryString ? '?' + queryString : ''}`
      ) as { analistas: Array<{ analista: string; total_cobrado: number; cantidad_pagos: number }> }
      return response.analistas
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

  const data = dashboardData || {
    meta_mensual: 0,
    avance_meta: 0,
    financieros: { totalCobrado: 0, tasaRecuperacion: 0 },
  }

  const porcentajeAvance = data.meta_mensual > 0 ? (data.avance_meta / data.meta_mensual) * 100 : 0

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
            <Button variant="ghost" size="sm" onClick={() => navigate('/dashboard/menu')} className="hover:bg-emerald-50">
              â† Menú
            </Button>
            <div>
              <h1 className="text-4xl font-black text-gray-900 uppercase tracking-tight">Cobranza</h1>
              <p className="text-lg text-gray-600 font-medium mt-1">Monitoreo Estratégico â€¢ {userName}</p>
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
                    <Filter className="h-4 w-4 text-emerald-600" />
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
        {loadingDashboard ? (
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
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
            <KpiCardLarge
              title="Total Cobrado"
              value={data.financieros?.totalCobrado || 0}
              icon={CreditCard}
              color="text-emerald-600"
              bgColor="bg-emerald-100"
              borderColor="border-emerald-500"
              format="currency"
            />
            <KpiCardLarge
              title="Meta Mensual"
              value={data.meta_mensual || 0}
              icon={Target}
              color="text-purple-600"
              bgColor="bg-purple-100"
              borderColor="border-purple-500"
              format="currency"
            />
            <KpiCardLarge
              title="Avance Meta"
              value={porcentajeAvance}
              subtitle={`${formatCurrency(data.avance_meta || 0)} de ${formatCurrency(data.meta_mensual || 0)}`}
              icon={TrendingUp}
              color="text-teal-600"
              bgColor="bg-teal-100"
              borderColor="border-teal-500"
              format="percentage"
            />
            <KpiCardLarge
              title="Tasa Recuperación"
              value={data.financieros?.tasaRecuperacion || 0}
              icon={TrendingDown}
              color="text-blue-600"
              bgColor="bg-blue-100"
              borderColor="border-blue-500"
              format="percentage"
            />
            <KpiCardLarge
              title="Pagos Conciliados"
              value={0}
              subtitle="Mes actual"
              icon={Shield}
              color="text-indigo-600"
              bgColor="bg-indigo-100"
              borderColor="border-indigo-500"
              format="number"
              // âš ï¸ TODO: Conectar con endpoint de pagos conciliados del mes actual
              // Debe consultar: COUNT(*) FROM pagos WHERE conciliado = TRUE AND fecha_pago >= primer_dia_mes
            />
            <KpiCardLarge
              title="Días Promedio Cobro"
              value="12"
              subtitle="días"
              icon={Clock}
              color="text-amber-600"
              bgColor="bg-amber-100"
              borderColor="border-amber-500"
              format="text"
              // âš ï¸ TODO: Calcular desde base de datos
              // Debe calcular: AVG(DATEDIFF(fecha_pago, fecha_vencimiento)) de cuotas pagadas
            />
          </div>
        )}

        {/* GRÁFICOS PRINCIPALES */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Gráfico 1: Progreso hacia Meta Mensual */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="shadow-lg border-2 border-gray-200">
              <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 border-b-2 border-purple-200">
                <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                  <Target className="h-6 w-6 text-purple-600" />
                  <span>Progreso hacia Meta Mensual</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-600">Recaudado</span>
                    <span className="text-2xl font-black text-purple-600">
                      {formatCurrency(data.avance_meta || 0)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-8">
                    <div
                      className="bg-gradient-to-r from-purple-600 to-pink-600 h-8 rounded-full transition-all flex items-center justify-end pr-2"
                      style={{ width: `${Math.min(porcentajeAvance, 100)}%` }}
                    >
                      <span className="text-white text-xs font-bold">{porcentajeAvance.toFixed(1)}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between text-sm text-gray-500">
                    <span>Meta: {formatCurrency(data.meta_mensual || 0)}</span>
                    <span>Faltan: {formatCurrency(Math.max(0, (data.meta_mensual || 0) - (data.avance_meta || 0)))}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Gráfico 2: Distribución por Analista */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card className="shadow-lg border-2 border-gray-200">
              <CardHeader className="bg-gradient-to-r from-teal-50 to-cyan-50 border-b-2 border-teal-200">
                <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                  <Users className="h-6 w-6 text-teal-600" />
                  <span>Distribución de Cobros por Analista</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                {loadingAnalistas ? (
                  <div className="h-[300px] flex items-center justify-center">
                    <div className="animate-pulse text-gray-400">Cargando...</div>
                  </div>
                ) : datosAnalistas && datosAnalistas.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={datosAnalistas} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis type="number" stroke="#6b7280" />
                      <YAxis dataKey="analista" type="category" stroke="#6b7280" width={120} />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Legend />
                      <Bar dataKey="total_cobrado" fill="#14b8a6" radius={[0, 8, 8, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-gray-400">No hay datos disponibles</div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Gráfico 3: Recaudación por Día del Mes (Full Width) */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
          <Card className="shadow-lg border-2 border-gray-200">
            <CardHeader className="bg-gradient-to-r from-emerald-50 to-green-50 border-b-2 border-emerald-200">
              <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                <BarChart3 className="h-6 w-6 text-emerald-600" />
                <span>Recaudación por Día del Mes</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {loadingRecaudacionDia ? (
                <div className="h-[300px] flex items-center justify-center">
                  <div className="animate-pulse text-gray-400">Cargando...</div>
                </div>
              ) : datosRecaudacionDia && datosRecaudacionDia.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={datosRecaudacionDia}>
                    <defs>
                      <linearGradient id="colorPagos" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="fecha" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    <Legend />
                    <Area type="monotone" dataKey="pagos" stroke="#10b981" fillOpacity={1} fill="url(#colorPagos)" name="Pagos" />
                    <Line type="monotone" dataKey="total_a_cobrar" stroke="#3b82f6" strokeWidth={2} name="Total a Cobrar" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-400">No hay datos disponibles</div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* BOTONES EXPLORAR DETALLES */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="mt-8">
          <div className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-xl p-6 shadow-xl">
            <h2 className="text-2xl font-bold text-white mb-4 flex items-center space-x-2">
              <span>ðŸ”</span>
              <span>Explorar Análisis Detallados</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-emerald-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => setIsCobranzasMensualesOpen(true)}
              >
                <BarChart3 className="h-6 w-6" />
                <span className="font-semibold">Cobranzas Mensuales</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-emerald-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => setIsCobranzaPorDiaOpen(true)}
              >
                <TrendingUp className="h-6 w-6" />
                <span className="font-semibold">Cobranza por Día</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-emerald-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => setIsCobranzaPlanificadaRealOpen(true)}
              >
                <LineChart className="h-6 w-6" />
                <span className="font-semibold">Planificada vs Real</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-emerald-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => {
                  // TODO: Navegar a desglose por analista
                  console.log('Desglose por Analista Completo')
                }}
              >
                <Users className="h-6 w-6" />
                <span className="font-semibold">Desglose por Analista</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                className="bg-white hover:bg-gray-50 text-gray-800 border-2 border-transparent hover:border-emerald-300 h-auto py-4 flex flex-col items-center space-y-2"
                onClick={() => {
                  // TODO: Navegar a análisis de metas
                  console.log('Análisis de Metas por Período')
                }}
              >
                <Target className="h-6 w-6" />
                <span className="font-semibold">Análisis de Metas</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Modales */}
      <CobranzasMensualesModal isOpen={isCobranzasMensualesOpen} onClose={() => setIsCobranzasMensualesOpen(false)} />
      <CobranzaPorDiaModal isOpen={isCobranzaPorDiaOpen} onClose={() => setIsCobranzaPorDiaOpen(false)} />
      <CobranzaPlanificadaRealModal isOpen={isCobranzaPlanificadaRealOpen} onClose={() => setIsCobranzaPlanificadaRealOpen(false)} />
    </div>
  )
}
