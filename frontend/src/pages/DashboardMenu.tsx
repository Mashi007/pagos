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
import { toast } from 'sonner'
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
