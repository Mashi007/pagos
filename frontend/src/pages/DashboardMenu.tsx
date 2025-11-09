import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BarChart3,
  ChevronRight,
  Filter,
  TrendingUp,
  TrendingDown,
  Users,
  Target,
  AlertTriangle,
  Shield,
  Clock,
  FileText,
  PieChart,
  LineChart,
  Database,
  RefreshCw,
  Info,
  XCircle,
  X,
  Settings,
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
  ScatterChart,
  Scatter,
} from 'recharts'

// Submenús eliminados: financiamiento, cuotas, cobranza, analisis, pagos

export function DashboardMenu() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'
  const queryClient = useQueryClient()

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [periodo, setPeriodo] = useState('año') // ✅ Por defecto: "Este año"
  const { construirParams, construirFiltrosObject, tieneFiltrosActivos, cantidadFiltrosActivos } = useDashboardFiltros(filtros)

  // ✅ OPTIMIZACIÓN PRIORIDAD 1: Carga por batches con priorización
  // Batch 1: CRÍTICO - Opciones de filtros y KPIs principales (carga inmediata)
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
    staleTime: 30 * 60 * 1000, // 30 minutos - cambian muy poco
    refetchOnWindowFocus: false, // No recargar automáticamente
    // ✅ Prioridad máxima - carga inmediatamente
  })

  // Batch 1: CRÍTICO - KPIs principales (visible primero para el usuario)
  // ✅ ACTUALIZADO: Incluye período en queryKey y aplica filtro de período
  const { data: kpisPrincipales, isLoading: loadingKPIs, isError: errorKPIs, refetch } = useQuery({
    queryKey: ['kpis-principales-menu', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período para calcular fechas
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
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
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: true, // ✅ Prioridad máxima - carga inmediatamente
    retry: false, // No reintentar automáticamente en caso de error 401
  })

  // Batch 2: IMPORTANTE - Dashboard admin (gráfico principal, carga después de KPIs)
  const { data: datosDashboard, isLoading: loadingDashboard } = useQuery({
    queryKey: ['dashboard-menu', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      try {
        const params = construirParams(periodo)
        // Usar timeout extendido para endpoints lentos
        const response = await apiClient.get(`/api/v1/dashboard/admin?${params}`, { timeout: 60000 }) as {
          financieros?: { 
            ingresosCapital: number
            ingresosInteres: number
            ingresosMora: number
            totalCobrado: number
            totalCobradoAnterior: number
          }
          meta_mensual?: number
          avance_meta?: number
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
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: true, // ✅ Carga después de Batch 1
  })

  // Batch 3: MEDIA - Gráficos secundarios rápidos (cargar después de Batch 2, en paralelo limitado)
  // ✅ Lazy loading: Solo cargar cuando KPIs estén listos para reducir carga inicial
  // ✅ ACTUALIZADO: Incluye período en queryKey y aplica filtro de período
  // ✅ ACTUALIZADO: Muestra datos desde septiembre 2024
  const { data: datosTendencia, isLoading: loadingTendencia } = useQuery({
    queryKey: ['financiamiento-tendencia', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período para calcular fechas
      const queryParams = new URLSearchParams()
      
      // ✅ Si no hay fecha_inicio en filtros, usar septiembre 2024 como fecha de inicio
      if (!params.fecha_inicio) {
        queryParams.append('fecha_inicio', '2024-09-01') // Desde septiembre 2024
      } else {
        // Si hay fecha_inicio en filtros, usarla (pero asegurar que no sea anterior a sept 2024)
        const fechaInicioFiltro = new Date(params.fecha_inicio)
        const fechaMinima = new Date('2024-09-01')
        if (fechaInicioFiltro < fechaMinima) {
          queryParams.append('fecha_inicio', '2024-09-01')
        } else {
          queryParams.append('fecha_inicio', params.fecha_inicio)
        }
      }
      
      Object.entries(params).forEach(([key, value]) => {
        // No agregar fecha_inicio dos veces
        if (key !== 'fecha_inicio' && value) {
          queryParams.append(key, value.toString())
        }
      })
      
      const response = await apiClient.get(
        `/api/v1/dashboard/financiamiento-tendencia-mensual?${queryParams.toString()}`
      ) as { meses: Array<{ mes: string; cantidad_nuevos: number; monto_nuevos: number; total_acumulado: number; monto_cuotas_programadas: number; monto_pagado: number; morosidad: number; morosidad_mensual: number }> }
      const meses = response.meses
      return meses
    },
    staleTime: 5 * 60 * 1000, // 5 minutos - balance entre frescura y rendimiento
    enabled: !!kpisPrincipales, // ✅ Solo carga después de KPIs (lazy loading)
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
  })

  // Batch 3: Gráficos secundarios rápidos
  // ✅ ACTUALIZADO: Incluye período en queryKey y aplica filtro de período
  const { data: datosConcesionarios, isLoading: loadingConcesionarios } = useQuery({
    queryKey: ['prestamos-concesionario', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/prestamos-por-concesionario?${queryParams.toString()}`
      ) as { concesionarios: Array<{ concesionario: string; total_prestamos: number; porcentaje: number }> }
      // ✅ Ordenar de mayor a menor por total_prestamos
      const concesionariosOrdenados = response.concesionarios
        .sort((a, b) => b.total_prestamos - a.total_prestamos)
        .slice(0, 10) // Top 10
      return concesionariosOrdenados
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: !!kpisPrincipales, // ✅ Lazy loading - carga después de KPIs
  })

  const { data: datosModelos, isLoading: loadingModelos } = useQuery({
    queryKey: ['prestamos-modelo', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
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
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: !!kpisPrincipales, // ✅ Lazy loading - carga después de KPIs
  })

  // Batch 4: BAJA - Gráficos menos críticos (cargar después de Batch 3, lazy loading)
  // ✅ ACTUALIZADO: Incluye período en queryKey y aplica filtro de período
  const { data: datosFinanciamientoRangos, isLoading: loadingFinanciamientoRangos, isError: errorFinanciamientoRangos, error: errorFinanciamientoRangosDetail, refetch: refetchFinanciamientoRangos } = useQuery({
    queryKey: ['financiamiento-rangos', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      try {
        const params = construirFiltrosObject(periodo) // ✅ Pasar período
        const queryParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })
        const response = await apiClient.get(
          `/api/v1/dashboard/financiamiento-por-rangos?${queryParams.toString()}`,
          { timeout: 60000 } // ✅ Timeout extendido para queries pesadas
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
      } catch (error: any) {
        console.error('❌ [DashboardMenu] Error cargando financiamiento por rangos:', error)
        // Si el error es 500 o de red, lanzar el error para que React Query lo maneje
        // Si es otro error, retornar respuesta vacía para no romper el dashboard
        if (error?.response?.status >= 500 || error?.code === 'ERR_NETWORK' || error?.code === 'ECONNABORTED') {
          throw error // Lanzar para que React Query muestre el error
        }
        // Para otros errores, retornar respuesta vacía
        return {
          rangos: [],
          total_prestamos: 0,
          total_monto: 0.0,
        }
      }
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
    retry: 1, // ✅ Permitir 1 reintento para errores de red
    retryDelay: 2000, // Esperar 2 segundos antes de reintentar
  })

  const { data: datosComposicionMorosidad, isLoading: loadingComposicionMorosidad } = useQuery({
    queryKey: ['composicion-morosidad', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/composicion-morosidad?${queryParams.toString()}`
      ) as {
        puntos: Array<{
          categoria: string
          monto: number
          cantidad_cuotas: number
        }>
        total_morosidad: number
        total_cuotas: number
      }
      return response
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
  })

  const { data: datosCobranzas, isLoading: loadingCobranzas } = useQuery({
    queryKey: ['cobranzas-mensuales', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      // Usar timeout extendido para endpoints lentos
      const response = await apiClient.get<{
        meses: Array<{
          mes: string
          nombre_mes: string
          cobranzas_planificadas: number
          pagos_reales: number
          meta_mensual: number
        }>
        meta_actual: number
      }>(
        `/api/v1/dashboard/cobranzas-mensuales?${queryParams.toString()}`,
        { timeout: 60000 }
      )
      return response
    },
    staleTime: 5 * 60 * 1000, // 5 minutos
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
  })

  const { data: datosCobranzasSemanales, isLoading: loadingCobranzasSemanales } = useQuery({
    queryKey: ['cobranzas-semanales', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      queryParams.append('semanas', '12') // Últimas 12 semanas
      const response = await apiClient.get<{
        semanas: Array<{
          semana_inicio: string
          nombre_semana: string
          cobranzas_planificadas: number
          pagos_reales: number
        }>
        fecha_inicio: string
        fecha_fin: string
      }>(
        `/api/v1/dashboard/cobranzas-semanales?${queryParams.toString()}`,
        { timeout: 60000 }
      )
      // ✅ Logging para diagnóstico
      if (response && response.semanas) {
        const semanasConDatos = response.semanas.filter(
          s => s.cobranzas_planificadas > 0 || s.pagos_reales > 0
        )
        console.log(
          `📊 [CobranzasSemanales] Total semanas: ${response.semanas.length}, ` +
          `Semanas con datos: ${semanasConDatos.length}`,
          semanasConDatos.length > 0 ? semanasConDatos : 'Sin datos'
        )
      }
      return response
    },
    staleTime: 5 * 60 * 1000, // 5 minutos
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
  })

  const { data: datosMorosidadAnalista, isLoading: loadingMorosidadAnalista } = useQuery({
    queryKey: ['morosidad-analista', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
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
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
  })

  const { data: datosEvolucionMorosidad, isLoading: loadingEvolucionMorosidad } = useQuery({
    queryKey: ['evolucion-morosidad-menu', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
      const queryParams = new URLSearchParams()
      // ✅ Pasar fecha_inicio desde enero 2025 en lugar de meses
      queryParams.append('fecha_inicio', '2025-01-01')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/evolucion-morosidad?${queryParams.toString()}`
      ) as { meses: Array<{ mes: string; morosidad: number }> }
      return response.meses
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
  })

  const { data: datosEvolucionPagos, isLoading: loadingEvolucionPagos } = useQuery({
    queryKey: ['evolucion-pagos-menu', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
      const queryParams = new URLSearchParams()
      // ✅ Pasar fecha_inicio desde enero 2025 en lugar de meses
      queryParams.append('fecha_inicio', '2025-01-01')
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
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  
  // NOTA: No necesitamos invalidar queries manualmente aquí
  // React Query detecta automáticamente los cambios en queryKey (que incluye JSON.stringify(filtros))
  // y refetch automáticamente cuando cambian los filtros o el período

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      // Invalidar y refrescar todas las queries relacionadas con el dashboard
      await queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['financiamiento-tendencia'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['prestamos-concesionario'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['prestamos-modelo'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['financiamiento-rangos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['composicion-morosidad'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['cobranzas-mensuales'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['cobranzas-semanales'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['morosidad-analista'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['evolucion-morosidad-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['evolucion-pagos-menu'], exact: false })
      
      // Refrescar todas las queries activas
      await queryClient.refetchQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['dashboard-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['financiamiento-tendencia'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['prestamos-concesionario'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['prestamos-modelo'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['financiamiento-rangos'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['composicion-morosidad'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['cobranzas-mensuales'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['morosidad-analista'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['evolucion-morosidad-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['evolucion-pagos-menu'], exact: false })
      
      // También refrescar la query de kpisPrincipales usando su refetch
      await refetch()
    } catch (error) {
      console.error('❌ [DashboardMenu] Error al refrescar queries:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  const evolucionMensual = datosDashboard?.evolucion_mensual || []
  const COLORS_CONCESIONARIOS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1']

  // Calcular el dominio del eje Y para el gráfico de tendencia
  const yAxisDomainTendencia = useMemo(() => {
    if (!datosTendencia || datosTendencia.length === 0) {
      return [0, 'auto'] as [number, 'auto']
    }
    const allValues = datosTendencia.flatMap(d => [
      d.monto_nuevos || 0,
      d.monto_cuotas_programadas || 0,
      d.monto_pagado || 0,
      d.morosidad_mensual || 0
    ])
    const maxValue = allValues.length > 0 ? Math.max(...allValues, 0) : 0
    return maxValue > 0 ? [0, maxValue * 1.1] as [number, number] : [0, 'auto'] as [number, 'auto']
  }, [datosTendencia])

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
            ) : errorKPIs ? (
              <Card>
                <CardContent className="p-6">
                  <div className="text-center text-gray-500">
                    <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-red-500" />
                    <p className="text-sm">Error al cargar los datos. Por favor, intenta nuevamente.</p>
                    <Button 
                      onClick={() => refetch()} 
                      variant="outline" 
                      className="mt-4"
                      size="sm"
                    >
                      Reintentar
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : kpisPrincipales && kpisPrincipales.total_prestamos && kpisPrincipales.creditos_nuevos_mes ? (
              <div className="space-y-4 sticky top-4">
                {/* Tarjeta de Financiamiento con múltiples métricas */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ scale: 1.02, y: -4 }}
                  transition={{ duration: 0.2 }}
                  className="relative min-h-[280px] bg-white rounded-xl border-2 border-cyan-500 shadow-[0_4px_20px_rgba(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgba(0,0,0,0.18)] transition-all duration-300 overflow-hidden group"
                >
                  <div className="absolute top-0 left-0 right-0 h-1.5 bg-cyan-100 opacity-90"></div>
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300 bg-gradient-to-br bg-cyan-100 to-transparent"></div>
                  
                  <div className="relative z-10 p-5 md:p-6 h-full flex flex-col">
                    {/* Header */}
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="p-2.5 md:p-3 rounded-xl bg-cyan-100 border-2 border-white/50 shadow-lg flex-shrink-0">
                        <FileText className="h-6 w-6 md:h-7 md:w-7 text-cyan-600" />
                      </div>
                      <h3 className="text-sm md:text-base font-bold text-gray-700 uppercase tracking-tight leading-tight">
                        FINANCIAMIENTO
                      </h3>
                    </div>

                    {/* Métricas */}
                    <div className="flex-1 flex flex-col justify-center space-y-4">
                      {/* 1. Monto de Financiamiento */}
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Monto de Financiamiento</p>
                        <p className="text-2xl md:text-3xl font-black text-cyan-600 leading-tight">
                          {formatCurrency(datosDashboard?.financieros?.ingresosCapital || 0)}
                        </p>
                      </div>

                      {/* 2. Cartera Recobrada */}
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Cartera Recobrada</p>
                        <p className="text-2xl md:text-3xl font-black text-green-600 leading-tight">
                          {(() => {
                            const carteraTotal = datosDashboard?.financieros?.ingresosCapital || 0
                            const totalCobrado = datosDashboard?.financieros?.totalCobrado || 0
                            const porcentaje = carteraTotal > 0 ? (totalCobrado / carteraTotal) * 100 : 0
                            return `${porcentaje.toFixed(1)}%`
                          })()}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          {formatCurrency(datosDashboard?.financieros?.totalCobrado || 0)} cobrado
                        </p>
                      </div>

                      {/* 3. Morosidad */}
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Morosidad</p>
                        <p className="text-2xl md:text-3xl font-black text-red-600 leading-tight">
                          {(() => {
                            const carteraTotal = datosDashboard?.financieros?.ingresosCapital || 0
                            const morosidadTotal = kpisPrincipales.total_morosidad_usd?.valor_actual || 0
                            const porcentaje = carteraTotal > 0 ? (morosidadTotal / carteraTotal) * 100 : 0
                            return `${porcentaje.toFixed(1)}%`
                          })()}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          {formatCurrency(kpisPrincipales.total_morosidad_usd?.valor_actual || 0)} en mora
                        </p>
                      </div>
                    </div>

                    {/* Decoración sutil */}
                    <div className="absolute bottom-0 right-0 w-20 h-20 bg-cyan-100 opacity-5 rounded-tl-full -mr-10 -mb-10"></div>
                  </div>
                </motion.div>
                <KpiCardLarge
                  title="Créditos Aprobados"
                  value={kpisPrincipales.creditos_nuevos_mes?.valor_actual ?? 0}
                  icon={TrendingUp}
                  color="text-green-600"
                  bgColor="bg-green-100"
                  borderColor="border-green-500"
                  format="number"
                />
                {/* Card de Clientes por Estado */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ scale: 1.02, y: -4 }}
                  transition={{ duration: 0.2 }}
                  className="relative min-h-[200px] bg-white rounded-xl border-2 border-blue-500 shadow-[0_4px_20px_rgba(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgba(0,0,0,0.18)] transition-all duration-300 overflow-hidden group"
                >
                  <div className="absolute top-0 left-0 right-0 h-1.5 bg-blue-100 opacity-90"></div>
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300 bg-gradient-to-br bg-blue-100 to-transparent"></div>
                  
                  <div className="relative z-10 p-5 md:p-6 h-full flex flex-col">
                    {/* Header mejorado */}
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="p-2.5 md:p-3 rounded-xl bg-blue-100 border-2 border-white/50 shadow-lg flex-shrink-0">
                        <Users className="h-6 w-6 md:h-7 md:w-7 text-blue-600" />
                      </div>
                      <h3 className="text-sm md:text-base font-bold text-gray-700 uppercase tracking-tight leading-tight">
                        Clientes: Activos, Inactivos, Finalizados
                      </h3>
                    </div>

                    {/* Valores mejorados */}
                    {kpisPrincipales.clientes_por_estado ? (
                      <div className="grid grid-cols-3 gap-3 md:gap-4 flex-1">
                        {/* Activos */}
                        <div className="flex flex-col justify-center items-center text-center min-w-0 w-full overflow-hidden">
                          <div className="text-xl md:text-2xl font-black text-green-600 mb-2 leading-tight w-full">
                            {kpisPrincipales.clientes_por_estado.activos.valor_actual.toLocaleString('es-EC')}
                          </div>
                          <div className="text-xs md:text-sm font-bold text-gray-700 uppercase mb-2">Activos</div>
                          <div className="flex items-center justify-center gap-1">
                            {kpisPrincipales.clientes_por_estado.activos.variacion_porcentual >= 0 ? (
                              <TrendingUp className="h-3 w-3 text-green-600" />
                            ) : (
                              <TrendingDown className="h-3 w-3 text-red-600" />
                            )}
                            <span
                              className={`text-xs md:text-sm font-semibold ${
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
                        <div className="flex flex-col justify-center items-center text-center min-w-0 w-full overflow-hidden">
                          <div className="text-xl md:text-2xl font-black text-orange-600 mb-2 leading-tight w-full">
                            {kpisPrincipales.clientes_por_estado.inactivos.valor_actual.toLocaleString('es-EC')}
                          </div>
                          <div className="text-xs md:text-sm font-bold text-gray-700 uppercase mb-2">Inactivos</div>
                          <div className="flex items-center justify-center gap-1">
                            {kpisPrincipales.clientes_por_estado.inactivos.variacion_porcentual >= 0 ? (
                              <TrendingUp className="h-3 w-3 text-green-600" />
                            ) : (
                              <TrendingDown className="h-3 w-3 text-red-600" />
                            )}
                            <span
                              className={`text-xs md:text-sm font-semibold ${
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
                        <div className="flex flex-col justify-center items-center text-center min-w-0 w-full overflow-hidden">
                          <div className="text-xl md:text-2xl font-black text-blue-600 mb-2 leading-tight w-full">
                            {kpisPrincipales.clientes_por_estado.finalizados.valor_actual.toLocaleString('es-EC')}
                          </div>
                          <div className="text-xs md:text-sm font-bold text-gray-700 uppercase mb-2">Finalizados</div>
                          <div className="flex items-center justify-center gap-1">
                            {kpisPrincipales.clientes_por_estado.finalizados.variacion_porcentual >= 0 ? (
                              <TrendingUp className="h-3 w-3 text-green-600" />
                            ) : (
                              <TrendingDown className="h-3 w-3 text-red-600" />
                            )}
                            <span
                              className={`text-xs md:text-sm font-semibold ${
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
                    {/* Decoración sutil */}
                    <div className="absolute bottom-0 right-0 w-20 h-20 bg-blue-100 opacity-5 rounded-tl-full -mr-10 -mb-10"></div>
                  </div>
                </motion.div>
                {kpisPrincipales.total_morosidad_usd && (
                  <KpiCardLarge
                    title="Morosidad Total"
                    value={kpisPrincipales.total_morosidad_usd?.valor_actual ?? 0}
                    icon={AlertTriangle}
                    color="text-red-600"
                    bgColor="bg-red-100"
                    borderColor="border-red-500"
                    format="currency"
                    variation={{
                      percent: kpisPrincipales.total_morosidad_usd?.variacion_porcentual ?? 0,
                      label: 'vs mes anterior',
                    }}
                  />
                )}
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
                      <ComposedChart data={datosTendencia} margin={{ top: 20, right: 30, left: 80, bottom: 20 }}>
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
                          angle={-45}
                          textAnchor="end"
                          height={60}
                        />
                        <YAxis 
                          yAxisId="left"
                          stroke="#6b7280"
                          width={90}
                          style={{ fontSize: '12px', fontWeight: 500 }}
                          tick={{ fill: '#6b7280', fontSize: 11 }}
                          tickFormatter={(value) => {
                            // Formato compacto para números grandes en el eje Y
                            if (value >= 1000000) {
                              return `$${(value / 1000000).toFixed(1)}M`
                            } else if (value >= 1000) {
                              return `$${(value / 1000).toFixed(0)}K`
                            }
                            return formatCurrency(value)
                          }}
                          domain={yAxisDomainTendencia}
                          allowDataOverflow={false}
                          allowDecimals={false}
                          label={{ 
                            value: 'Monto ($)', 
                            angle: -90, 
                            position: 'insideLeft',
                            style: { textAnchor: 'middle', fill: '#6b7280', fontSize: '12px', fontWeight: 600 }
                          }}
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
                          yAxisId="left"
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
                          yAxisId="left"
                          type="monotone" 
                          dataKey="monto_cuotas_programadas" 
                          stroke="#8b5cf6" 
                          strokeWidth={3}
                          dot={{ fill: '#8b5cf6', strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: '#8b5cf6', strokeWidth: 2 }}
                          name="Cuotas Programadas por Mes"
                          strokeDasharray="5 5"
                          connectNulls={true}
                          isAnimationActive={true}
                        />
                        <Line 
                          yAxisId="left"
                          type="monotone" 
                          dataKey="monto_pagado" 
                          stroke="#10b981" 
                          strokeWidth={3}
                          dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: '#10b981', strokeWidth: 2 }}
                          name="Monto Pagado por Mes"
                          connectNulls={true}
                          isAnimationActive={true}
                        />
                        <Line 
                          yAxisId="left"
                          type="monotone" 
                          dataKey="morosidad_mensual" 
                          stroke="#ef4444" 
                          strokeWidth={3}
                          dot={{ fill: '#ef4444', strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: '#ef4444', strokeWidth: 2 }}
                          name="Morosidad Mensual"
                          connectNulls={true}
                          isAnimationActive={true}
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

            {/* Fila: Gráfico de Evolución de Morosidad y Pagos (Toda la fila) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
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
                      <div className="h-[450px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : (datosEvolucionMorosidad && datosEvolucionMorosidad.length > 0) || (datosEvolucionPagos && datosEvolucionPagos.length > 0) ? (
                      <ResponsiveContainer width="100%" height={450}>
                        <RechartsLineChart
                          data={(() => {
                            // ✅ Combinar datos de ambos gráficos por mes y ordenar correctamente por fecha
                            const morosidadMap = new Map(datosEvolucionMorosidad?.map(item => [item.mes, item.morosidad]) || [])
                            const pagosMap = new Map(datosEvolucionPagos?.map(item => [item.mes, item.monto]) || [])
                            
                            // Obtener todos los meses únicos
                            const allMonths = Array.from(new Set([...morosidadMap.keys(), ...pagosMap.keys()]))
                            
                            // ✅ Ordenar meses por fecha (parsear formato "Ene 2025", "Feb 2025", etc.)
                            const mesesOrdenados = allMonths.sort((a, b) => {
                              const parseMes = (mesStr: string) => {
                                const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
                                const partes = mesStr.split(' ')
                                const mesNombre = partes[0] || ''
                                const añoStr = partes[1] || '2025'
                                const año = parseInt(añoStr, 10)
                                const mesIndex = meses.indexOf(mesNombre)
                                return año * 12 + mesIndex
                              }
                              return parseMes(String(a)) - parseMes(String(b))
                            })
                            
                            // ✅ Calcular valores acumulados por mes
                            let morosidadAcumulada = 0
                            let pagosAcumulados = 0
                            
                            return mesesOrdenados.map(mes => {
                              const morosidadMensual: number = (morosidadMap.get(mes) as number) || 0
                              const pagosMensuales: number = (pagosMap.get(mes) as number) || 0
                              
                              // Acumular valores
                              morosidadAcumulada += morosidadMensual
                              pagosAcumulados += pagosMensuales
                              
                              return {
                                mes,
                                morosidad: morosidadAcumulada,
                                pagos: pagosAcumulados,
                              }
                            })
                          })()}
                          margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis 
                            dataKey="mes" 
                            stroke="#6b7280"
                            tick={{ fontSize: 11 }}
                            angle={-45}
                            textAnchor="end"
                            height={60}
                          />
                          <YAxis 
                            stroke="#6b7280"
                            tickFormatter={(value) => formatCurrency(value)}
                            label={{ 
                              value: 'Monto ($)', 
                              angle: -90, 
                              position: 'insideLeft',
                              style: { textAnchor: 'middle', fill: '#6b7280', fontSize: '12px', fontWeight: 600 }
                            }}
                          />
                          <Tooltip 
                            formatter={(value: number, name: string) => [
                              formatCurrency(value),
                              name === 'morosidad' ? 'Morosidad (Acumulado)' : 'Pagos (Acumulado)'
                            ]}
                            contentStyle={{
                              backgroundColor: 'rgba(255, 255, 255, 0.98)',
                              border: '1px solid #e5e7eb',
                              borderRadius: '8px',
                              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                              padding: '12px',
                            }}
                          />
                          <Legend />
                          <Line 
                            type="monotone" 
                            dataKey="morosidad" 
                            stroke="#ef4444" 
                            strokeWidth={3} 
                            name="Morosidad" 
                            dot={{ r: 5, fill: '#ef4444' }}
                            activeDot={{ r: 7 }}
                          />
                          <Line 
                            type="monotone" 
                            dataKey="pagos" 
                            stroke="#8b5cf6" 
                            strokeWidth={3} 
                            name="Pagos" 
                            dot={{ r: 5, fill: '#8b5cf6' }}
                            activeDot={{ r: 7 }}
                          />
                        </RechartsLineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[450px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
            </motion.div>

            {/* Fila: Cobranzas Mensuales y Cobranzas Semanales */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico: Cobranzas Mensuales */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
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
                    ) : datosCobranzas && datosCobranzas.meses && datosCobranzas.meses.length > 0 ? (
                      <ResponsiveContainer width="100%" height={350}>
                        <BarChart data={datosCobranzas.meses}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="nombre_mes" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" tickFormatter={(value) => formatCurrency(value)} />
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

              {/* Gráfico: Cobranzas Semanales (Lunes a Viernes) */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-teal-50 to-cyan-50 border-b-2 border-teal-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <BarChart3 className="h-6 w-6 text-teal-600" />
                      <span>Cobranzas Semanales (Lunes a Viernes)</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingCobranzasSemanales ? (
                      <div className="h-[350px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosCobranzasSemanales && datosCobranzasSemanales.semanas && datosCobranzasSemanales.semanas.length > 0 ? (
                      <ResponsiveContainer width="100%" height={350}>
                        <BarChart data={datosCobranzasSemanales.semanas} margin={{ top: 5, right: 30, left: 20, bottom: 60 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis 
                            dataKey="nombre_semana" 
                            stroke="#6b7280" 
                            angle={-45}
                            textAnchor="end"
                            height={80}
                            tick={{ fontSize: 11 }}
                          />
                          <YAxis stroke="#6b7280" tickFormatter={(value) => formatCurrency(value)} />
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
            </div>

            {/* Gráfico de Barras: Préstamos por Concesionario (Fila completa) */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 border-b-2 border-purple-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <BarChart3 className="h-6 w-6 text-purple-600" />
                      <span>Préstamos por Concesionario</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingConcesionarios ? (
                    <div className="h-[350px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosConcesionarios && datosConcesionarios.length > 0 ? (
                    <ResponsiveContainer width="100%" height={350}>
                      <BarChart
                        data={[...datosConcesionarios]
                          .sort((a, b) => b.porcentaje - a.porcentaje) // ✅ Ordenar de mayor a menor por porcentaje
                          .map((c) => ({
                            concesionario: c.concesionario.length > 30 ? c.concesionario.substring(0, 30) + '...' : c.concesionario,
                            porcentaje: c.porcentaje,
                            total_prestamos: c.total_prestamos,
                                fullName: c.concesionario,
                              }))}
                        margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
                        <XAxis 
                          dataKey="concesionario"
                          stroke="#6b7280"
                          style={{ fontSize: '11px', fontWeight: 500 }}
                          tick={{ fill: '#6b7280' }}
                          angle={-45}
                          textAnchor="end"
                          height={80}
                        />
                        <YAxis 
                          stroke="#6b7280"
                          style={{ fontSize: '12px', fontWeight: 500 }}
                          tick={{ fill: '#6b7280' }}
                          label={{ value: 'Porcentaje (%)', angle: -90, position: 'insideLeft' }}
                          tickFormatter={(value) => `${value}%`}
                        />
                            <Tooltip 
                          contentStyle={{
                            backgroundColor: 'rgba(255, 255, 255, 0.98)',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                            padding: '12px',
                          }}
                          formatter={(value: number, name: string, props: any) => {
                            return [
                              `${value.toFixed(1)}% (${props.payload.total_prestamos.toLocaleString('es-EC')} préstamos)`,
                                'Porcentaje'
                            ]
                          }}
                          labelFormatter={(label) => {
                            const data = datosConcesionarios?.find(c => 
                              (c.concesionario.length > 30 ? c.concesionario.substring(0, 30) + '...' : c.concesionario) === label
                            )
                            return data?.concesionario || label
                          }}
                            />
                        <Legend />
                        <Bar 
                          dataKey="porcentaje" 
                          name="Porcentaje"
                          radius={[8, 8, 0, 0]}
                        >
                          {[...datosConcesionarios]
                            .sort((a, b) => b.porcentaje - a.porcentaje)
                            .map((entry, index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]} 
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

            {/* Fila 2: Morosidad por Analista */}
            <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
              {/* Gráfico: Morosidad por Analista */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
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
                          margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis 
                            dataKey="analista" 
                            type="category" 
                            stroke="#6b7280" 
                            angle={-45}
                            textAnchor="end"
                            height={80}
                            tick={{ fontSize: 11 }}
                          />
                          <YAxis 
                            type="number" 
                            stroke="#6b7280" 
                            tickFormatter={(value) => formatCurrency(value)}
                          />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Bar dataKey="total_morosidad" fill="#ef4444" radius={[8, 8, 0, 0]} name="Morosidad" />
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

            {/* Fila 4: Préstamos por Modelo (Fila completa) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-violet-50 to-indigo-50 border-b-2 border-violet-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <BarChart3 className="h-6 w-6 text-violet-600" />
                    <span>Préstamos por Modelo</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  {loadingModelos ? (
                    <div className="h-[350px] flex items-center justify-center">
                      <div className="animate-pulse text-gray-400">Cargando...</div>
                    </div>
                  ) : datosModelos && datosModelos.length > 0 ? (
                    <ResponsiveContainer width="100%" height={350}>
                      <BarChart
                        data={[...datosModelos]
                          .sort((a, b) => b.porcentaje - a.porcentaje) // ✅ Ordenar de mayor a menor por porcentaje
                          .map((m) => ({
                            modelo: m.modelo.length > 30 ? m.modelo.substring(0, 30) + '...' : m.modelo,
                            porcentaje: m.porcentaje,
                            total_prestamos: m.total_prestamos,
                            fullName: m.modelo,
                          }))}
                        margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
                        <XAxis 
                          dataKey="modelo"
                          stroke="#6b7280"
                          style={{ fontSize: '11px', fontWeight: 500 }}
                          tick={{ fill: '#6b7280' }}
                          angle={-45}
                          textAnchor="end"
                          height={80}
                        />
                        <YAxis 
                          stroke="#6b7280"
                          style={{ fontSize: '12px', fontWeight: 500 }}
                          tick={{ fill: '#6b7280' }}
                          label={{ value: 'Porcentaje (%)', angle: -90, position: 'insideLeft' }}
                          tickFormatter={(value) => `${value}%`}
                        />
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: 'rgba(255, 255, 255, 0.98)',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                            padding: '12px',
                          }}
                          formatter={(value: number, name: string, props: any) => {
                            return [
                              `${value.toFixed(1)}% (${formatCurrency(props.payload.total_prestamos)})`,
                              'Porcentaje'
                            ]
                          }}
                          labelFormatter={(label) => {
                            const data = datosModelos?.find(m => 
                              (m.modelo.length > 30 ? m.modelo.substring(0, 30) + '...' : m.modelo) === label
                            )
                            return data?.modelo || label
                          }}
                        />
                        <Legend />
                        <Bar 
                          dataKey="porcentaje" 
                          name="Porcentaje"
                          radius={[8, 8, 0, 0]}
                        >
                          {[...datosModelos]
                            .sort((a, b) => b.porcentaje - a.porcentaje)
                            .map((entry, index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]} 
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
                    ) : errorFinanciamientoRangos ? (
                      <div className="h-[450px] flex flex-col items-center justify-center text-gray-500">
                        <AlertTriangle className="h-8 w-8 mb-2 text-red-500" />
                        <p className="text-sm font-semibold mb-1">Error al cargar los datos</p>
                        <p className="text-xs text-gray-400 mb-2 text-center px-4">
                          {(() => {
                            const error: any = errorFinanciamientoRangosDetail
                            if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network')) {
                              return 'Error de conexión. Verifica tu conexión a internet.'
                            }
                            if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
                              return 'La solicitud tardó demasiado. El servidor puede estar sobrecargado.'
                            }
                            if (error?.response?.status >= 500) {
                              return 'Error del servidor. Por favor, contacta al administrador.'
                            }
                            return error?.response?.data?.detail || error?.message || 'Por favor, verifica la conexión con el servidor'
                          })()}
                        </p>
                        <Button 
                          onClick={() => refetchFinanciamientoRangos()} 
                          variant="outline" 
                          className="mt-4"
                          size="sm"
                        >
                          Reintentar
                        </Button>
                      </div>
                    ) : datosFinanciamientoRangos?.rangos && Array.isArray(datosFinanciamientoRangos.rangos) && datosFinanciamientoRangos.rangos.length > 0 ? (
                      (() => {
                        // ✅ Filtrar solo rangos con datos (cantidad_prestamos > 0)
                        const rangosConDatos = datosFinanciamientoRangos.rangos.filter(r => (r.cantidad_prestamos || 0) > 0)
                        
                        // ✅ Calcular suma de todos los rangos mostrados
                        const sumaRangosMostrados = rangosConDatos.reduce((sum, r) => sum + (r.cantidad_prestamos || 0), 0)
                        const totalBackend = datosFinanciamientoRangos.total_prestamos || 0
                        const diferencia = totalBackend - sumaRangosMostrados
                        
                        if (rangosConDatos.length === 0) {
                          const filtrosAplicados = construirFiltrosObject(periodo)
                          const filtrosInfo: string[] = []
                          if (filtrosAplicados.analista) filtrosInfo.push(`Analista: ${filtrosAplicados.analista}`)
                          if (filtrosAplicados.concesionario) filtrosInfo.push(`Concesionario: ${filtrosAplicados.concesionario}`)
                          if (filtrosAplicados.modelo) filtrosInfo.push(`Modelo: ${filtrosAplicados.modelo}`)
                          if (filtrosAplicados.fecha_inicio) filtrosInfo.push(`Desde: ${new Date(filtrosAplicados.fecha_inicio).toLocaleDateString('es-EC')}`)
                          if (filtrosAplicados.fecha_fin) filtrosInfo.push(`Hasta: ${new Date(filtrosAplicados.fecha_fin).toLocaleDateString('es-EC')}`)
                          
                          return (
                            <div className="h-[450px] flex flex-col items-center justify-center">
                              <div className="flex flex-col items-center space-y-4 px-6 max-w-lg">
                                <div className="relative">
                                  <div className="absolute inset-0 bg-orange-100 rounded-full blur-xl opacity-50"></div>
                                  <Database className="h-16 w-16 text-orange-400 relative z-10" strokeWidth={1.5} />
                                </div>
                                <div className="text-center space-y-3">
                                  <p className="text-base font-semibold text-gray-700">No hay datos disponibles</p>
                                  {totalBackend > 0 ? (
                                    <div className="space-y-3">
                                      <p className="text-sm text-gray-500">
                                        Se encontraron <span className="font-semibold text-orange-600">{totalBackend.toLocaleString('es-EC')}</span> préstamos en el backend, pero no hay datos en los rangos configurados.
                                      </p>
                                      <div className="flex items-center justify-center gap-2 text-xs text-gray-400 bg-orange-50 rounded-lg px-3 py-2">
                                        <Info className="h-4 w-4" />
                                        <span>Los préstamos pueden estar fuera del rango de $0 - $50,000</span>
                                      </div>
                                    </div>
                                  ) : (
                                    <div className="space-y-3">
                                      <p className="text-sm text-gray-500">
                                        No se encontraron préstamos aprobados con los filtros aplicados.
                                      </p>
                                      {tieneFiltrosActivos && (
                                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-left">
                                          <div className="flex items-center gap-2 mb-2">
                                            <Filter className="h-4 w-4 text-blue-600" />
                                            <span className="text-xs font-semibold text-blue-800">
                                              Filtros activos ({cantidadFiltrosActivos}):
                                            </span>
                                          </div>
                                          <ul className="text-xs text-blue-700 space-y-1 ml-6">
                                            {filtrosInfo.map((info, idx) => (
                                              <li key={idx} className="list-disc">{info}</li>
                                            ))}
                                          </ul>
                                          <p className="text-xs text-blue-600 mt-2 italic">
                                            Período: {periodo === 'año' ? 'Este año' : periodo === 'mes' ? 'Este mes' : periodo === 'semana' ? 'Esta semana' : periodo}
                                          </p>
                                        </div>
                                      )}
                                      <p className="text-xs text-gray-400 italic">
                                        💡 Sugerencia: Intenta ajustar los filtros o cambiar el período seleccionado
                                      </p>
                                    </div>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 mt-2">
                                  <Button 
                                    onClick={() => refetchFinanciamientoRangos()} 
                                    variant="outline" 
                                    size="sm"
                                    className="border-orange-200 text-orange-600 hover:bg-orange-50"
                                  >
                                    <RefreshCw className="h-4 w-4 mr-2" />
                                    Recargar datos
                                  </Button>
                                  {tieneFiltrosActivos && (
                                    <Button 
                                      onClick={() => {
                                        setFiltros({})
                                        refetchFinanciamientoRangos()
                                      }} 
                                      variant="outline" 
                                      size="sm"
                                      className="border-blue-200 text-blue-600 hover:bg-blue-50"
                                    >
                                      <X className="h-4 w-4 mr-2" />
                                      Limpiar filtros
                                    </Button>
                                  )}
                                </div>
                              </div>
                            </div>
                          )
                        }
                        
                        // ✅ Calcular el máximo dinámicamente basado en los datos reales
                        // Encontrar el valor máximo de cantidad_prestamos en los rangos con datos
                        // ✅ BUGFIX: Validar que haya datos antes de calcular max
                        const maxCantidad = rangosConDatos.length > 0 
                          ? Math.max(...rangosConDatos.map(r => r.cantidad_prestamos || 0))
                          : 0
                        // Agregar un 10% de margen para mejor visualización
                        const dominioMin = 0
                        const dominioMax = maxCantidad > 0 ? Math.ceil(maxCantidad * 1.1) : 100
                        
                        // Ordenar rangos por valor numérico del rango (de menor a mayor - invertido)
                        const rangosOrdenados = [...rangosConDatos].sort((a, b) => {
                          // Extraer el valor mínimo del rango para ordenar
                          const getMinValue = (categoria: string) => {
                            // Limpiar formato: remover puntos y comas
                            const cleanCategoria = categoria.replace(/[.,]/g, '')
                            if (cleanCategoria.includes('+')) {
                              // Formato: $50000+
                              const match = cleanCategoria.match(/\$(\d+)\+/)
                              return match ? parseInt(match[1]) : 999999
                            }
                            // Formato: $6000 - $6500
                            const match = cleanCategoria.match(/\$(\d+)\s*-\s*\$\d+/)
                            return match ? parseInt(match[1]) : 0
                          }
                          return getMinValue(a.categoria) - getMinValue(b.categoria)
                        })
                        
                        return (
                          <ResponsiveContainer width="100%" height={450}>
                            <BarChart
                              data={rangosOrdenados}
                              layout="vertical"
                              margin={{ top: 20, right: 30, left: 120, bottom: 5 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                              <XAxis 
                                type="number" 
                                stroke="#6b7280"
                                domain={[dominioMin, dominioMax]}
                                tickFormatter={(value) => value.toLocaleString('es-EC')}
                                style={{ fontSize: '12px', fontWeight: 500 }}
                                tick={{ fill: '#6b7280' }}
                                allowDataOverflow={false}
                                label={{ value: 'Cantidad de Créditos Aprobados', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle', fill: '#6b7280', fontSize: '12px', fontWeight: 600 } }}
                              />
                              <YAxis 
                                type="category" 
                                dataKey="categoria" 
                                stroke="#6b7280" 
                                width={110}
                                tick={{ fontSize: 12 }}
                                reversed={true}
                              />
                          <Tooltip
                            formatter={(value: number, name: string, props: any) => {
                              if (name === 'cantidad_prestamos') {
                                return [
                                  `${value.toLocaleString('es-EC')} créditos`,
                                  `Monto Total: ${formatCurrency(props.payload.monto_total)}`,
                                  `Porcentaje: ${props.payload.porcentaje_cantidad.toFixed(1)}%`,
                                ]
                              }
                              return value
                            }}
                            contentStyle={{
                              backgroundColor: 'rgba(255, 255, 255, 0.95)',
                              border: '1px solid #e5e7eb',
                              borderRadius: '8px',
                            }}
                            labelStyle={{
                              fontWeight: 600,
                              marginBottom: '4px',
                            }}
                          />
                              <Legend />
                              <Bar
                                dataKey="cantidad_prestamos"
                                fill="#f97316"
                                radius={[0, 8, 8, 0]}
                                name="Créditos Aprobados"
                              >
                                {rangosOrdenados.map((entry, index) => (
                                  <Cell
                                    key={`cell-rango-${index}`}
                                    fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]}
                                  />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        )
                      })()
                    ) : (
                      <div className="h-[450px] flex flex-col items-center justify-center">
                        <div className="flex flex-col items-center space-y-4 px-6 max-w-lg">
                          <div className="relative">
                            <div className="absolute inset-0 bg-orange-100 rounded-full blur-xl opacity-50"></div>
                            <XCircle className="h-16 w-16 text-orange-400 relative z-10" strokeWidth={1.5} />
                          </div>
                          <div className="text-center space-y-3">
                            <p className="text-base font-semibold text-gray-700">No hay datos disponibles</p>
                            {datosFinanciamientoRangos && datosFinanciamientoRangos.total_prestamos === 0 ? (
                              <div className="space-y-3">
                                <p className="text-sm text-gray-500">
                                  No se encontraron préstamos aprobados con los filtros aplicados.
                                </p>
                                {tieneFiltrosActivos && (() => {
                                  const filtrosAplicados = construirFiltrosObject(periodo)
                                  const filtrosInfo: string[] = []
                                  if (filtrosAplicados.analista) filtrosInfo.push(`Analista: ${filtrosAplicados.analista}`)
                                  if (filtrosAplicados.concesionario) filtrosInfo.push(`Concesionario: ${filtrosAplicados.concesionario}`)
                                  if (filtrosAplicados.modelo) filtrosInfo.push(`Modelo: ${filtrosAplicados.modelo}`)
                                  if (filtrosAplicados.fecha_inicio) filtrosInfo.push(`Desde: ${new Date(filtrosAplicados.fecha_inicio).toLocaleDateString('es-EC')}`)
                                  if (filtrosAplicados.fecha_fin) filtrosInfo.push(`Hasta: ${new Date(filtrosAplicados.fecha_fin).toLocaleDateString('es-EC')}`)
                                  
                                  return (
                                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-left">
                                      <div className="flex items-center gap-2 mb-2">
                                        <Filter className="h-4 w-4 text-blue-600" />
                                        <span className="text-xs font-semibold text-blue-800">
                                          Filtros activos ({cantidadFiltrosActivos}):
                                        </span>
                                      </div>
                                      <ul className="text-xs text-blue-700 space-y-1 ml-6">
                                        {filtrosInfo.map((info, idx) => (
                                          <li key={idx} className="list-disc">{info}</li>
                                        ))}
                                      </ul>
                                      <p className="text-xs text-blue-600 mt-2 italic">
                                        Período: {periodo === 'año' ? 'Este año' : periodo === 'mes' ? 'Este mes' : periodo === 'semana' ? 'Esta semana' : periodo}
                                      </p>
                                    </div>
                                  )
                                })()}
                                <p className="text-xs text-gray-400 italic">
                                  💡 Sugerencia: Intenta ajustar los filtros o cambiar el período seleccionado
                                </p>
                              </div>
                            ) : (
                              <p className="text-sm text-gray-500">
                                No se pudieron cargar los datos. Verifica tu conexión e intenta nuevamente.
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-2">
                            <Button 
                              onClick={() => refetchFinanciamientoRangos()} 
                              variant="outline" 
                              size="sm"
                              className="border-orange-200 text-orange-600 hover:bg-orange-50"
                            >
                              <RefreshCw className="h-4 w-4 mr-2" />
                              Recargar datos
                            </Button>
                            {tieneFiltrosActivos && (
                              <Button 
                                onClick={() => {
                                  setFiltros({})
                                  refetchFinanciamientoRangos()
                                }} 
                                variant="outline" 
                                size="sm"
                                className="border-blue-200 text-blue-600 hover:bg-blue-50"
                              >
                                <X className="h-4 w-4 mr-2" />
                                Limpiar filtros
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                    {/* ✅ Mostrar resumen de totales si hay datos */}
                    {datosFinanciamientoRangos && datosFinanciamientoRangos.rangos && (
                      <div className="mt-4 pt-4 border-t text-sm text-gray-600">
                        <div className="flex justify-between items-center">
                          <span>Total de préstamos (backend):</span>
                          <span className="font-semibold">{datosFinanciamientoRangos.total_prestamos.toLocaleString('es-EC')}</span>
                        </div>
                        {(() => {
                          const rangosConDatos = datosFinanciamientoRangos.rangos.filter(r => (r.cantidad_prestamos || 0) > 0)
                          const sumaRangosMostrados = rangosConDatos.reduce((sum, r) => sum + (r.cantidad_prestamos || 0), 0)
                          const diferencia = datosFinanciamientoRangos.total_prestamos - sumaRangosMostrados
                          if (diferencia !== 0) {
                            return (
                              <>
                                <div className="flex justify-between items-center mt-1">
                                  <span>Suma de rangos mostrados:</span>
                                  <span className="font-semibold">{sumaRangosMostrados.toLocaleString('es-EC')}</span>
                                </div>
                                <div className="flex justify-between items-center mt-1 text-orange-600">
                                  <span>⚠️ Diferencia:</span>
                                  <span className="font-semibold">{diferencia.toLocaleString('es-EC')} préstamos no mostrados</span>
                                </div>
                              </>
                            )
                          }
                          return null
                        })()}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              {/* Gráfico de Barras - Morosidad por Categorías de Días de Atraso */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-red-50 to-pink-50 border-b-2 border-red-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <BarChart3 className="h-6 w-6 text-red-600" />
                      <span>Composición de Morosidad por Días de Atraso</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingComposicionMorosidad ? (
                      <div className="h-[450px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosComposicionMorosidad && datosComposicionMorosidad.puntos && datosComposicionMorosidad.puntos.length > 0 ? (
                      <div className="flex flex-col">
                        <ResponsiveContainer width="100%" height={400}>
                          <BarChart
                            data={datosComposicionMorosidad.puntos}
                            margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
                            <XAxis 
                              dataKey="categoria"
                              stroke="#6b7280"
                              style={{ fontSize: '11px', fontWeight: 500 }}
                              tick={{ fill: '#6b7280' }}
                              angle={-45}
                              textAnchor="end"
                              height={80}
                            />
                            <YAxis 
                              stroke="#6b7280"
                              style={{ fontSize: '12px', fontWeight: 500 }}
                              tick={{ fill: '#6b7280' }}
                              label={{ value: 'Monto de Morosidad', angle: -90, position: 'insideLeft' }}
                              tickFormatter={(value) => formatCurrency(value)}
                              domain={[0, 'dataMax']}
                            />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: 'rgba(255, 255, 255, 0.98)',
                                border: '1px solid #e5e7eb',
                                borderRadius: '8px',
                                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                                padding: '12px',
                              }}
                              formatter={(value: number, name: string, props: any) => {
                                return [
                                  formatCurrency(value),
                                  `Cuotas: ${props.payload.cantidad_cuotas}`,
                                ]
                              }}
                              labelFormatter={(label) => `Categoría: ${label}`}
                            />
                            <Legend />
                            <Bar
                              dataKey="monto"
                              name="Monto de Morosidad"
                              fill="#ef4444"
                              radius={[8, 8, 0, 0]}
                            >
                              {datosComposicionMorosidad.puntos.map((entry, index) => (
                                <Cell
                                  key={`cell-morosidad-${index}`}
                                  fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]}
                                />
                              ))}
                            </Bar>
                          </BarChart>
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

          </div>
        </div>
      </div>
    </div>
  )
}
