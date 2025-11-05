import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DollarSign,
  BarChart3,
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
  ComposedChart,
} from 'recharts'

// Submenús eliminados: financiamiento, cuotas, cobranza, analisis, pagos

export function DashboardMenu() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'
  const queryClient = useQueryClient()

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [periodo, setPeriodo] = useState('mes')
  const { construirParams, construirFiltrosObject } = useDashboardFiltros(filtros)


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
        clientes_por_estado?: {
          activos: { valor_actual: number; variacion_porcentual: number }
          inactivos: { valor_actual: number; variacion_porcentual: number }
          finalizados: { valor_actual: number; variacion_porcentual: number }
        }
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

  // Cargar financiamiento aprobado por mes (últimos 12 meses - 1 año)
  const { data: datosTendencia, isLoading: loadingTendencia } = useQuery({
    queryKey: ['financiamiento-tendencia', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses', '12') // Últimos 12 meses (1 año)
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/financiamiento-tendencia-mensual?${queryParams.toString()}`
      ) as { meses: Array<{ mes: string; cantidad_nuevos: number; monto_nuevos: number; total_acumulado: number; monto_cuotas_programadas: number; monto_pagado: number; monto_cuota: number; morosidad: number }> }
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

  // Cargar préstamos por modelo
  const { data: datosModelos, isLoading: loadingModelos } = useQuery({
    queryKey: ['prestamos-modelo', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/prestamos-por-modelo?${queryParams.toString()}`
      ) as { modelos: Array<{ modelo: string; total_prestamos: number; porcentaje: number }> }
      return response.modelos.slice(0, 10) // Top 10
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })

  // Cargar datos de pagos conciliados
  const { data: datosPagosConciliados, isLoading: loadingPagosConciliados } = useQuery({
    queryKey: ['pagos-conciliados', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/pagos-conciliados?${queryParams.toString()}`
      ) as {
        total_pagos: number
        total_pagos_conciliados: number
        total_pagos_no_conciliados: number
        monto_total: number
        monto_conciliado: number
        monto_no_conciliado: number
        porcentaje_conciliacion: number
        porcentaje_monto_conciliado: number
      }
      return response
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })

  // Cargar financiamiento por rangos para gráfico de pirámide
  const { data: datosFinanciamientoRangos, isLoading: loadingFinanciamientoRangos } = useQuery({
    queryKey: ['financiamiento-rangos', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/financiamiento-por-rangos?${queryParams.toString()}`
      ) as {
        rangos: Array<{
          categoria: string
          cantidad_prestamos: number
          monto_total: number
          porcentaje_cantidad: number
          porcentaje_monto: number
        }>
        total_prestamos: number
        total_monto: number
      }
      return response
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })

  // Cargar composición de morosidad por rangos de días
  const { data: datosComposicionMorosidad, isLoading: loadingComposicionMorosidad } = useQuery({
    queryKey: ['composicion-morosidad', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/composicion-morosidad?${queryParams.toString()}`
      ) as {
        composicion: Array<{
          categoria: string
          monto: number
          cantidad: number
          porcentaje: number
        }>
        total_morosidad: number
        total_cuotas: number
      }
      return response
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })

  // Cargar evolución general mensual (Morosidad, Total Activos, Total Financiamiento, Total Pagos)
  const { data: datosEvolucionGeneral, isLoading: loadingEvolucionGeneral } = useQuery({
    queryKey: ['evolucion-general-mensual', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/evolucion-general-mensual?${queryParams.toString()}`
      ) as {
        evolucion: Array<{
          mes: string
          morosidad: number
          total_activos: number
          total_financiamiento: number
          total_pagos: number
        }>
      }
      return response
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

  // Cargar resumen financiamiento vs pagado para gráfico de barras
  const { data: datosResumenFinanciamiento, isLoading: loadingResumenFinanciamiento } = useQuery({
    queryKey: ['resumen-financiamiento-pagado', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/resumen-financiamiento-pagado?${queryParams.toString()}`
      ) as {
        total_financiamiento: number
        total_pagado: number
      }
      return response
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
  
  // Invalidar queries cuando cambian los filtros o el período
  // React Query debería detectar automáticamente los cambios en queryKey,
  // pero invalidamos explícitamente para asegurar que se refresquen inmediatamente
  useEffect(() => {
    const filtrosKey = JSON.stringify(filtros)
    console.log('🔄 [DashboardMenu] Filtros o período cambiaron, invalidando queries...', { filtros, periodo, filtrosKey })
    // Invalidar todas las queries relacionadas con el dashboard
    // Usar exact: false para que invalide todas las variantes de las queries
    queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['financiamiento-tendencia'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['prestamos-concesionario'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['prestamos-modelo'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['pagos-conciliados'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['financiamiento-rangos'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['composicion-morosidad'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['evolucion-general-mensual'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['cobranzas-mensuales'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['morosidad-analista'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['evolucion-morosidad-menu'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['evolucion-pagos-menu'], exact: false })
  }, [filtros, periodo, queryClient])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      console.log('🔄 [DashboardMenu] Refrescando todas las queries del dashboard...')
      // Invalidar todas las queries relacionadas
      await queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['financiamiento-tendencia'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['prestamos-concesionario'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['prestamos-modelo'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-conciliados'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['financiamiento-rangos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['composicion-morosidad'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['evolucion-general-mensual'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['cobranzas-mensuales'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['morosidad-analista'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['evolucion-morosidad-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['evolucion-pagos-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['resumen-financiamiento-pagado'], exact: false })
      
      // Refrescar todas las queries activas
      await queryClient.refetchQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['dashboard-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['financiamiento-tendencia'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['prestamos-concesionario'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['prestamos-modelo'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['pagos-conciliados'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['financiamiento-rangos'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['composicion-morosidad'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['evolucion-general-mensual'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['cobranzas-mensuales'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['morosidad-analista'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['evolucion-morosidad-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['evolucion-pagos-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['resumen-financiamiento-pagado'], exact: false })
      
      // También refrescar la query de kpisPrincipales usando su refetch
      await refetch()
      console.log('✅ [DashboardMenu] Todas las queries refrescadas exitosamente')
    } catch (error) {
      console.error('❌ [DashboardMenu] Error al refrescar queries:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  const evolucionMensual = datosDashboard?.evolucion_mensual || []
  const COLORS_CONCESIONARIOS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1']

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
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
                {/* Botones de navegación rápida - Eliminados */}
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
                  title="Total Financiamiento de Préstamos Concedidos en el Mes en Curso"
                  value={kpisPrincipales.total_prestamos.valor_actual}
                  icon={FileText}
                  color="text-cyan-600"
                  bgColor="bg-cyan-100"
                  borderColor="border-cyan-500"
                  format="currency"
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
                {/* Card de Clientes por Estado */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ scale: 1.02, y: -4 }}
                  transition={{ duration: 0.2 }}
                  className="relative min-h-[180px] bg-white rounded-xl border-2 border-blue-500 shadow-[0_4px_20px_rgba(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgba(0,0,0,0.18)] transition-all duration-300 overflow-hidden group"
                >
                  <div className="absolute top-0 left-0 right-0 h-1 bg-blue-100 opacity-80"></div>
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 bg-blue-100"></div>
                  
                  <div className="relative z-10 p-6 h-full flex flex-col">
                    {/* Header */}
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="p-3 rounded-lg bg-blue-100 border-2 border-white/50 shadow-lg">
                        <Users className="h-6 w-6 text-blue-600" />
                      </div>
                      <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                        Clientes: Activos, Inactivos, Finalizados
                      </h3>
                    </div>

                    {/* Valores */}
                    {kpisPrincipales.clientes_por_estado ? (
                      <div className="grid grid-cols-3 gap-4 flex-1">
                        {/* Activos */}
                        <div className="flex flex-col justify-center">
                          <div className="text-3xl font-black text-green-600 mb-1">
                            {kpisPrincipales.clientes_por_estado.activos.valor_actual.toLocaleString('es-EC')}
                          </div>
                          <div className="text-xs font-semibold text-gray-600 uppercase mb-1">Activos</div>
                          <div className="flex items-center space-x-1">
                            <span
                              className={`text-xs font-bold ${
                                kpisPrincipales.clientes_por_estado.activos.variacion_porcentual >= 0
                                  ? 'text-green-600'
                                  : 'text-red-600'
                              }`}
                            >
                              {kpisPrincipales.clientes_por_estado.activos.variacion_porcentual >= 0 ? '+' : ''}
                              {kpisPrincipales.clientes_por_estado.activos.variacion_porcentual.toFixed(1)}%
                            </span>
                          </div>
                        </div>

                        {/* Inactivos */}
                        <div className="flex flex-col justify-center">
                          <div className="text-3xl font-black text-orange-600 mb-1">
                            {kpisPrincipales.clientes_por_estado.inactivos.valor_actual.toLocaleString('es-EC')}
                          </div>
                          <div className="text-xs font-semibold text-gray-600 uppercase mb-1">Inactivos</div>
                          <div className="flex items-center space-x-1">
                            <span
                              className={`text-xs font-bold ${
                                kpisPrincipales.clientes_por_estado.inactivos.variacion_porcentual >= 0
                                  ? 'text-green-600'
                                  : 'text-red-600'
                              }`}
                            >
                              {kpisPrincipales.clientes_por_estado.inactivos.variacion_porcentual >= 0 ? '+' : ''}
                              {kpisPrincipales.clientes_por_estado.inactivos.variacion_porcentual.toFixed(1)}%
                            </span>
                          </div>
                        </div>

                        {/* Finalizados */}
                        <div className="flex flex-col justify-center">
                          <div className="text-3xl font-black text-blue-600 mb-1">
                            {kpisPrincipales.clientes_por_estado.finalizados.valor_actual.toLocaleString('es-EC')}
                          </div>
                          <div className="text-xs font-semibold text-gray-600 uppercase mb-1">Finalizados</div>
                          <div className="flex items-center space-x-1">
                            <span
                              className={`text-xs font-bold ${
                                kpisPrincipales.clientes_por_estado.finalizados.variacion_porcentual >= 0
                                  ? 'text-green-600'
                                  : 'text-red-600'
                              }`}
                            >
                              {kpisPrincipales.clientes_por_estado.finalizados.variacion_porcentual >= 0 ? '+' : ''}
                              {kpisPrincipales.clientes_por_estado.finalizados.variacion_porcentual.toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <div className="text-gray-400">Cargando datos...</div>
                      </div>
                    )}
                  </div>
                </motion.div>
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
                  value={datosDashboard?.financieros?.totalCobrado || 0}
                  icon={CheckCircle}
                  color="text-emerald-600"
                  bgColor="bg-emerald-100"
                  borderColor="border-emerald-500"
                  format="currency"
                  variation={
                    datosDashboard?.financieros?.totalCobradoAnterior !== undefined &&
                    datosDashboard?.financieros?.totalCobradoAnterior !== null &&
                    datosDashboard?.financieros?.totalCobradoAnterior > 0
                      ? {
                          percent:
                            ((datosDashboard.financieros.totalCobrado - datosDashboard.financieros.totalCobradoAnterior) /
                              datosDashboard.financieros.totalCobradoAnterior) *
                            100,
                          label: 'vs mes anterior',
                        }
                      : undefined
                  }
                />
              </div>
            ) : null}
          </motion.div>

          {/* COLUMNA DERECHA: 6 GRÁFICOS PRINCIPALES (2x3) */}
          <div className="lg:col-span-9 space-y-6">
            {/* Fila 1: Gráfico de Financiamiento (Fila completa) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-cyan-50 to-blue-50 border-b-2 border-cyan-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <TrendingUp className="h-6 w-6 text-cyan-600" />
                    <span>MONITOREO FINANCIERO</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  {loadingTendencia ? (
                    <div className="h-[450px] flex items-center justify-center">
                      <div className="animate-pulse text-gray-400">Cargando...</div>
                    </div>
                    ) : datosTendencia && datosTendencia.length > 0 ? (
                    <ResponsiveContainer width="100%" height={450}>
                      <ComposedChart data={datosTendencia} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorMontoGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                            <stop offset="50%" stopColor="#06b6d4" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.1} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
                        <XAxis 
                          dataKey="mes" 
                          stroke="#6b7280" 
                          style={{ fontSize: '12px', fontWeight: 500 }}
                          tick={{ fill: '#6b7280' }}
                        />
                        <YAxis 
                          stroke="#6b7280"
                          style={{ fontSize: '12px', fontWeight: 500 }}
                          tick={{ fill: '#6b7280' }}
                          tickFormatter={(value) => formatCurrency(value)}
                        />
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: 'rgba(255, 255, 255, 0.98)',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                            padding: '12px',
                          }}
                          labelStyle={{
                            color: '#1f2937',
                            fontWeight: 600,
                            marginBottom: '8px',
                            fontSize: '14px',
                          }}
                          itemStyle={{
                            color: '#374151',
                            fontSize: '14px',
                            fontWeight: 500,
                          }}
                          formatter={(value: number, name: string) => [
                            formatCurrency(value),
                            name
                          ]}
                        />
                        <Legend 
                          wrapperStyle={{ paddingTop: '20px' }}
                          iconType="line"
                        />
                        <Area 
                          type="monotone" 
                          dataKey="monto_nuevos" 
                          stroke="#06b6d4" 
                          strokeWidth={3}
                          fillOpacity={1} 
                          fill="url(#colorMontoGradient)" 
                          name="Total Financiamiento por Mes"
                          dot={{ fill: '#06b6d4', strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: '#06b6d4', strokeWidth: 2 }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="monto_cuotas_programadas" 
                          stroke="#8b5cf6" 
                          strokeWidth={3}
                          dot={{ fill: '#8b5cf6', strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: '#8b5cf6', strokeWidth: 2 }}
                          name="Cuotas Programadas por Mes"
                          strokeDasharray="5 5"
                        />
                        <Line 
                          type="monotone" 
                          dataKey="monto_pagado" 
                          stroke="#10b981" 
                          strokeWidth={3}
                          dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: '#10b981', strokeWidth: 2 }}
                          name="Monto Pagado por Mes"
                        />
                        <Line 
                          type="monotone" 
                          dataKey="morosidad" 
                          stroke="#ef4444" 
                          strokeWidth={3}
                          dot={{ fill: '#ef4444', strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: '#ef4444', strokeWidth: 2 }}
                          name="Morosidad por Mes"
                          strokeDasharray="8 4"
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[450px] flex items-center justify-center text-gray-400">
                      No hay datos disponibles
                    </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

            {/* Gráfico de Barras: Financiamiento vs Pagado */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
            >
              <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b-2 border-blue-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <BarChart3 className="h-6 w-6 text-blue-600" />
                    <span>RESUMEN: FINANCIAMIENTO VS PAGADO</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  {loadingResumenFinanciamiento ? (
                    <div className="h-[350px] flex items-center justify-center">
                      <div className="animate-pulse text-gray-400">Cargando...</div>
                    </div>
                  ) : datosResumenFinanciamiento ? (
                    <ResponsiveContainer width="100%" height={350}>
                      <BarChart
                        data={[
                          {
                            nombre: 'Financiamiento',
                            valor: datosResumenFinanciamiento.total_financiamiento,
                          },
                          {
                            nombre: 'Pagado',
                            valor: datosResumenFinanciamiento.total_pagado,
                          },
                        ]}
                        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
                        <XAxis 
                          dataKey="nombre" 
                          stroke="#6b7280"
                          style={{ fontSize: '14px', fontWeight: 600 }}
                          tick={{ fill: '#6b7280' }}
                        />
                        <YAxis 
                          stroke="#6b7280"
                          style={{ fontSize: '12px', fontWeight: 500 }}
                          tick={{ fill: '#6b7280' }}
                          tickFormatter={(value) => formatCurrency(value)}
                        />
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: 'rgba(255, 255, 255, 0.98)',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                            padding: '12px',
                          }}
                          formatter={(value: number) => formatCurrency(value)}
                        />
                        <Legend />
                        <Bar 
                          dataKey="valor" 
                          name="Monto"
                          radius={[8, 8, 0, 0]}
                        >
                          {[
                            { nombre: 'Financiamiento', valor: datosResumenFinanciamiento.total_financiamiento },
                            { nombre: 'Pagado', valor: datosResumenFinanciamiento.total_pagado },
                          ].map((entry, index) => (
                            <Cell 
                              key={`cell-${index}`} 
                              fill={entry.nombre === 'Financiamiento' ? '#3b82f6' : '#10b981'} 
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[350px] flex items-center justify-center text-gray-400">
                      No hay datos disponibles
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Fila 2: 2 Gráficos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

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
                        <ResponsiveContainer width="100%" height={400}>
                          <RechartsPieChart>
                            <Pie
                              data={datosConcesionarios.map((c) => ({
                                name: c.concesionario.length > 20 ? c.concesionario.substring(0, 20) + '...' : c.concesionario,
                                value: c.porcentaje,
                                total: c.total_prestamos,
                                fullName: c.concesionario,
                              }))}
                              cx="50%"
                              cy="50%"
                              labelLine={true}
                              label={({ name, percent, fullName }) => {
                                const labelText = `${name}: ${(percent * 100).toFixed(1)}%`
                                return labelText
                              }}
                              outerRadius={120}
                              innerRadius={70}
                              fill="#8884d8"
                              dataKey="value"
                              paddingAngle={2}
                            >
                              {datosConcesionarios.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]} />
                              ))}
                            </Pie>
                            <Tooltip 
                              formatter={(value: number, name: string, props: any) => [
                                `${props.payload.fullName || props.payload.name}: ${(value as number).toFixed(1)}%`,
                                'Porcentaje'
                              ]}
                            />
                          </RechartsPieChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <div className="h-[400px] flex items-center justify-center text-gray-400">
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
                      <div className="h-[350px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosCobranzas && datosCobranzas.length > 0 ? (
                      <ResponsiveContainer width="100%" height={350}>
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
                      <div className="h-[350px] flex items-center justify-center text-gray-400">
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
                      <div className="h-[350px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosMorosidadAnalista && datosMorosidadAnalista.length > 0 ? (
                      <ResponsiveContainer width="100%" height={350}>
                        <BarChart 
                          data={[...datosMorosidadAnalista].sort((a, b) => b.total_morosidad - a.total_morosidad)} 
                          layout="vertical"
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis type="number" stroke="#6b7280" />
                          <YAxis dataKey="analista" type="category" stroke="#6b7280" width={120} />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Bar dataKey="total_morosidad" fill="#ef4444" radius={[0, 8, 8, 0]} name="Morosidad" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[350px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Fila 3: 2 Gráficos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico 5: Evolución Combinada de Morosidad y Pagos */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b-2 border-blue-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <LineChart className="h-6 w-6 text-blue-600" />
                      <span>Evolución de Morosidad y Pagos</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {(loadingEvolucionMorosidad || loadingEvolucionPagos) ? (
                      <div className="h-[350px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : (datosEvolucionMorosidad && datosEvolucionMorosidad.length > 0) || (datosEvolucionPagos && datosEvolucionPagos.length > 0) ? (
                      <ResponsiveContainer width="100%" height={350}>
                        <RechartsLineChart
                          data={(() => {
                            // Combinar datos de ambos gráficos por mes
                            const morosidadMap = new Map(datosEvolucionMorosidad?.map(item => [item.mes, item.morosidad]) || [])
                            const pagosMap = new Map(datosEvolucionPagos?.map(item => [item.mes, item.monto]) || [])
                            const allMonths = Array.from(new Set([...morosidadMap.keys(), ...pagosMap.keys()])).sort()
                            return allMonths.map(mes => ({
                              mes,
                              morosidad: morosidadMap.get(mes) || 0,
                              pagos: pagosMap.get(mes) || 0,
                            }))
                          })()}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="mes" stroke="#6b7280" />
                          <YAxis yAxisId="left" stroke="#6b7280" />
                          <YAxis yAxisId="right" orientation="right" stroke="#6b7280" />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Line yAxisId="left" type="monotone" dataKey="morosidad" stroke="#ef4444" strokeWidth={3} name="Morosidad" dot={{ r: 4 }} />
                          <Line yAxisId="right" type="monotone" dataKey="pagos" stroke="#8b5cf6" strokeWidth={3} name="Pagos" dot={{ r: 4 }} />
                        </RechartsLineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[350px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              {/* Gráfico 6: Préstamos por Modelo */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-violet-50 to-indigo-50 border-b-2 border-violet-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <PieChart className="h-6 w-6 text-violet-600" />
                      <span>Préstamos por Modelo</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingModelos ? (
                      <div className="h-[350px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosModelos && datosModelos.length > 0 ? (
                      <div className="relative">
                        <ResponsiveContainer width="100%" height={400}>
                          <RechartsPieChart>
                            <Pie
                              data={datosModelos.map((m) => ({
                                name: m.modelo.length > 20 ? m.modelo.substring(0, 20) + '...' : m.modelo,
                                value: m.porcentaje,
                                total: m.total_prestamos,
                                fullName: m.modelo,
                              }))}
                              cx="50%"
                              cy="50%"
                              labelLine={true}
                              label={({ name, percent, fullName }) => {
                                return `${name}: ${(percent * 100).toFixed(1)}%`
                              }}
                              outerRadius={120}
                              fill="#8884d8"
                              dataKey="value"
                            >
                              {datosModelos.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]} />
                              ))}
                            </Pie>
                            <Tooltip
                              formatter={(value: number, name: string, props: any) => [
                                `${value.toFixed(2)}%`,
                                `${formatCurrency(props.payload.total)}`,
                              ]}
                            />
                            <Legend />
                          </RechartsPieChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <div className="h-[350px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Fila 4: 2 Gráficos adicionales */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico 7: Modelos Financiados (Pastel mejorado) */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.9 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-teal-50 to-cyan-50 border-b-2 border-teal-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <PieChart className="h-6 w-6 text-teal-600" />
                      <span>Modelos Financiados</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingModelos ? (
                      <div className="h-[400px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosModelos && datosModelos.length > 0 ? (
                      <div className="relative">
                        <ResponsiveContainer width="100%" height={400}>
                          <RechartsPieChart>
                            <Pie
                              data={datosModelos.map((m) => ({
                                name: m.modelo.length > 25 ? m.modelo.substring(0, 25) + '...' : m.modelo,
                                value: m.porcentaje,
                                total: m.total_prestamos,
                                cantidad: m.cantidad_prestamos || 0,
                                fullName: m.modelo,
                              }))}
                              cx="50%"
                              cy="50%"
                              labelLine={false}
                              label={({ percent, fullName }) => {
                                return `${fullName.length > 20 ? fullName.substring(0, 20) + '...' : fullName}\n${(percent * 100).toFixed(1)}%`
                              }}
                              outerRadius={140}
                              fill="#8884d8"
                              dataKey="value"
                            >
                              {datosModelos.map((entry, index) => (
                                <Cell key={`cell-modelo-${index}`} fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]} />
                              ))}
                            </Pie>
                            <Tooltip
                              formatter={(value: number, name: string, props: any) => [
                                `${value.toFixed(2)}%`,
                                `Monto: ${formatCurrency(props.payload.total)}`,
                                `Cantidad: ${props.payload.cantidad || 0}`,
                              ]}
                            />
                            <Legend
                              formatter={(value, entry) => {
                                const item = datosModelos.find(m => (m.modelo.length > 25 ? m.modelo.substring(0, 25) + '...' : m.modelo) === value)
                                return item ? `${value} (${item.porcentaje.toFixed(1)}%)` : value
                              }}
                            />
                          </RechartsPieChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <div className="h-[400px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              {/* Gráfico 8: Total Pagos vs Total Conciliado */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.0 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b-2 border-blue-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <BarChart3 className="h-6 w-6 text-blue-600" />
                      <span>Total Pagos y Conciliados</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingPagosConciliados ? (
                      <div className="h-[400px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosPagosConciliados ? (
                      <ResponsiveContainer width="100%" height={400}>
                        <BarChart
                          data={[
                            {
                              categoria: 'Pagos',
                              total: datosPagosConciliados.monto_total,
                              conciliado: datosPagosConciliados.monto_conciliado,
                              noConciliado: datosPagosConciliados.monto_no_conciliado,
                            },
                          ]}
                          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="categoria" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Bar dataKey="total" fill="#3b82f6" radius={[8, 8, 0, 0]} name="Total Pagos" />
                          <Bar dataKey="conciliado" fill="#10b981" radius={[8, 8, 0, 0]} name="Total Conciliado" />
                          <Bar dataKey="noConciliado" fill="#ef4444" radius={[8, 8, 0, 0]} name="No Conciliado" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[400px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Fila 5: Gráfico de Pirámide y Gráfico de Pastel de Morosidad */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico de Pirámide */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.1 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-orange-50 to-amber-50 border-b-2 border-orange-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <BarChart3 className="h-6 w-6 text-orange-600" />
                      <span>Distribución de Financiamiento por Rangos</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingFinanciamientoRangos ? (
                      <div className="h-[450px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosFinanciamientoRangos && datosFinanciamientoRangos.rangos.length > 0 ? (
                      <ResponsiveContainer width="100%" height={450}>
                        <BarChart
                          data={datosFinanciamientoRangos.rangos}
                          layout="vertical"
                          margin={{ top: 20, right: 30, left: 120, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis type="number" stroke="#6b7280" />
                          <YAxis 
                            type="category" 
                            dataKey="categoria" 
                            stroke="#6b7280" 
                            width={110}
                            tick={{ fontSize: 12 }}
                          />
                          <Tooltip
                            formatter={(value: number, name: string, props: any) => {
                              if (name === 'monto_total') {
                                return [
                                  formatCurrency(value),
                                  `Porcentaje: ${props.payload.porcentaje_monto.toFixed(1)}%`,
                                  `Cantidad: ${props.payload.cantidad_prestamos} préstamos`,
                                ]
                              }
                              return value
                            }}
                            contentStyle={{
                              backgroundColor: 'rgba(255, 255, 255, 0.95)',
                              border: '1px solid #e5e7eb',
                              borderRadius: '8px',
                            }}
                          />
                          <Legend />
                          <Bar
                            dataKey="monto_total"
                            fill="#f97316"
                            radius={[0, 8, 8, 0]}
                            name="Total Financiamiento"
                          >
                            {datosFinanciamientoRangos.rangos.map((entry, index) => (
                              <Cell
                                key={`cell-rango-${index}`}
                                fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[450px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              {/* Gráfico de Pastel - Composición de Morosidad */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-red-50 to-pink-50 border-b-2 border-red-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <PieChart className="h-6 w-6 text-red-600" />
                      <span>Composición de Morosidad por Días de Atraso</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingComposicionMorosidad ? (
                      <div className="h-[450px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosComposicionMorosidad && datosComposicionMorosidad.composicion.length > 0 ? (
                      <div className="flex flex-col items-center">
                        <ResponsiveContainer width="100%" height={400}>
                          <RechartsPieChart>
                            <Pie
                              data={datosComposicionMorosidad.composicion}
                              cx="50%"
                              cy="50%"
                              labelLine={false}
                              label={({ categoria, porcentaje }) => `${categoria}: ${porcentaje.toFixed(1)}%`}
                              outerRadius={140}
                              fill="#8884d8"
                              dataKey="monto"
                            >
                              {datosComposicionMorosidad.composicion.map((entry, index) => {
                                // Colores específicos para rangos de morosidad
                                const colorsMorosidad = [
                                  '#10b981', // Verde claro - 1 día
                                  '#84cc16', // Verde amarillo - 3 días
                                  '#f59e0b', // Amarillo - 15 días
                                  '#f97316', // Naranja - 1 mes
                                  '#ef4444', // Rojo claro - 2 meses
                                  '#dc2626', // Rojo oscuro - 3+ meses
                                ]
                                return (
                                  <Cell
                                    key={`cell-morosidad-${index}`}
                                    fill={colorsMorosidad[index % colorsMorosidad.length]}
                                  />
                                )
                              })}
                            </Pie>
                            <Tooltip
                              formatter={(value: number, name: string, props: any) => {
                                return [
                                  formatCurrency(value),
                                  `Porcentaje: ${props.payload.porcentaje.toFixed(2)}%`,
                                  `Cantidad: ${props.payload.cantidad} cuotas`,
                                ]
                              }}
                              contentStyle={{
                                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                                border: '1px solid #e5e7eb',
                                borderRadius: '8px',
                              }}
                            />
                            <Legend
                              formatter={(value, entry) => {
                                const data = datosComposicionMorosidad.composicion.find((d) => d.categoria === value)
                                return `${value} (${data?.porcentaje.toFixed(1)}%)`
                              }}
                              wrapperStyle={{ paddingTop: '20px' }}
                            />
                          </RechartsPieChart>
                        </ResponsiveContainer>
                        <div className="mt-4 text-center">
                          <div className="text-sm text-gray-600">
                            <span className="font-semibold">Total Morosidad: </span>
                            {formatCurrency(datosComposicionMorosidad.total_morosidad)}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {datosComposicionMorosidad.total_cuotas} cuotas vencidas
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="h-[450px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Fila 6: Gráfico de Evolución General Mensual */}
            <div className="grid grid-cols-1 gap-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.3 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-purple-50 to-indigo-50 border-b-2 border-purple-200">
                    <CardTitle className="flex items-center space-x-2 text-2xl font-bold text-gray-800">
                      <LineChart className="h-7 w-7 text-purple-600" />
                      <span>Evolución General Mensual (Últimos 6 Meses)</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingEvolucionGeneral ? (
                      <div className="h-[500px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosEvolucionGeneral && datosEvolucionGeneral.evolucion.length > 0 ? (
                      <ResponsiveContainer width="100%" height={500}>
                        <RechartsLineChart
                          data={datosEvolucionGeneral.evolucion}
                          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis 
                            dataKey="mes" 
                            stroke="#6b7280"
                            tick={{ fontSize: 12 }}
                            angle={-45}
                            textAnchor="end"
                            height={80}
                          />
                          <YAxis 
                            yAxisId="left"
                            stroke="#6b7280"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => formatCurrency(value)}
                          />
                          <YAxis 
                            yAxisId="right"
                            orientation="right"
                            stroke="#6b7280"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => formatCurrency(value)}
                          />
                          <Tooltip
                            formatter={(value: number, name: string) => {
                              const labels: Record<string, string> = {
                                'morosidad': 'Morosidad por Día',
                                'total_activos': 'Total Activos',
                                'total_financiamiento': 'Total Financiamiento',
                                'total_pagos': 'Total Pagos'
                              }
                              return [formatCurrency(value), labels[name] || name]
                            }}
                            contentStyle={{
                              backgroundColor: 'rgba(255, 255, 255, 0.95)',
                              border: '1px solid #e5e7eb',
                              borderRadius: '8px',
                            }}
                          />
                          <Legend 
                            wrapperStyle={{ paddingTop: '20px' }}
                            formatter={(value) => {
                              const labels: Record<string, string> = {
                                'morosidad': 'Morosidad por Día',
                                'total_activos': 'Total Activos',
                                'total_financiamiento': 'Total Financiamiento',
                                'total_pagos': 'Total Pagos'
                              }
                              return labels[value] || value
                            }}
                          />
                          <Line
                            yAxisId="left"
                            type="monotone"
                            dataKey="morosidad"
                            stroke="#ef4444"
                            strokeWidth={3}
                            dot={{ r: 5 }}
                            activeDot={{ r: 8 }}
                            name="morosidad"
                          />
                          <Line
                            yAxisId="left"
                            type="monotone"
                            dataKey="total_activos"
                            stroke="#3b82f6"
                            strokeWidth={3}
                            dot={{ r: 5 }}
                            activeDot={{ r: 8 }}
                            name="total_activos"
                          />
                          <Line
                            yAxisId="left"
                            type="monotone"
                            dataKey="total_financiamiento"
                            stroke="#10b981"
                            strokeWidth={3}
                            dot={{ r: 5 }}
                            activeDot={{ r: 8 }}
                            name="total_financiamiento"
                          />
                          <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="total_pagos"
                            stroke="#f59e0b"
                            strokeWidth={3}
                            dot={{ r: 5 }}
                            activeDot={{ r: 8 }}
                            name="total_pagos"
                          />
                        </RechartsLineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[500px] flex items-center justify-center text-gray-400">
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
