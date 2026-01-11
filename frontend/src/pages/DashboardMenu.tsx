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
  DollarSign,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
        cuotas_programadas?: { valor_actual: number }
        porcentaje_cuotas_pagadas?: number
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

      // ✅ CORRECCIÓN: Para este gráfico específico, NO pasar fecha_inicio del período
      // En su lugar, usar el parámetro 'meses' para mostrar los últimos 12 meses
      // Esto asegura que siempre se muestren múltiples meses independientemente del período seleccionado
      // Solo pasar fecha_inicio si viene de filtros explícitos del usuario (no del período)
      const fechaInicioExplicita = filtros.fecha_inicio && filtros.fecha_inicio !== ''
      
      if (fechaInicioExplicita) {
        // Si el usuario especificó fecha_inicio explícitamente en filtros, usarla
        const fechaInicioFiltro = new Date(filtros.fecha_inicio)
        const fechaMinima = new Date('2024-09-01')
        if (fechaInicioFiltro < fechaMinima) {
          queryParams.append('fecha_inicio', '2024-09-01')
        } else {
          queryParams.append('fecha_inicio', filtros.fecha_inicio)
        }
      } else {
        // Si no hay fecha_inicio explícita, usar septiembre 2024 como fecha de inicio mínima
        queryParams.append('fecha_inicio', '2024-09-01') // Desde septiembre 2024
      }

      // ✅ Pasar solo filtros de analista, concesionario y modelo (NO fecha_inicio ni fecha_fin del período)
      Object.entries(params).forEach(([key, value]) => {
        // No pasar fecha_inicio ni fecha_fin del período (ya se manejan arriba o se ignoran)
        // Solo pasar filtros de analista, concesionario y modelo
        if (key !== 'fecha_inicio' && key !== 'fecha_fin' && value) {
          queryParams.append(key, value.toString())
        }
      })
      
      // ✅ SIEMPRE agregar parámetro meses=12 para mostrar últimos 12 meses
      // Esto asegura que se muestren múltiples meses independientemente del período
      queryParams.append('meses', '12')

      const response = await apiClient.get(
        `/api/v1/dashboard/financiamiento-tendencia-mensual?${queryParams.toString()}`
      ) as { meses: Array<{ mes: string; cantidad_nuevos: number; monto_nuevos: number; total_acumulado: number; monto_cuotas_programadas: number; monto_pagado: number; morosidad: number; morosidad_mensual: number }> }
      const meses = response.meses
      return meses
    },
    staleTime: 15 * 60 * 1000, // 15 minutos - optimizado para datos históricos
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
      ) as { concesionarios: Array<{ concesionario: string; total_prestamos: number; cantidad_prestamos: number; porcentaje: number }> }
      // ✅ Ordenar de mayor a menor por cantidad_prestamos (cantidad real, no monto)
      const concesionariosOrdenados = response.concesionarios
        .sort((a, b) => b.cantidad_prestamos - a.cantidad_prestamos)
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
      ) as { modelos: Array<{ modelo: string; total_prestamos: number; cantidad_prestamos: number; porcentaje: number }> }
      // ✅ Ordenar de mayor a menor por cantidad_prestamos (cantidad real, no monto)
      const modelosOrdenados = response.modelos
        .sort((a, b) => b.cantidad_prestamos - a.cantidad_prestamos)
        .slice(0, 10) // Top 10
      return modelosOrdenados
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
    staleTime: 10 * 60 * 1000, // 10 minutos - optimizado para reducir carga
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

  // Datos de cobranza para fechas específicas (mañana, hoy, 3 días atrás)
  const { data: datosCobranzaFechas, isLoading: loadingCobranzaFechas } = useQuery({
    queryKey: ['cobranza-fechas-especificas', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get<{
        dias: Array<{
          fecha: string
          nombre_fecha: string
          cobranza_planificada: number
          cobranza_real: number
        }>
      }>(`/api/v1/dashboard/cobranza-fechas-especificas?${queryParams.toString()}`)
      return response
    },
    staleTime: 2 * 60 * 1000, // 2 minutos - datos más dinámicos
    refetchOnWindowFocus: true, // Recargar al enfocar ventana para datos actuales
    enabled: true,
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
    staleTime: 15 * 60 * 1000, // 15 minutos - optimizado para datos históricos
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
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
      // ✅ Ordenar de mayor a menor por total_morosidad
      const analistasOrdenados = response.analistas
        .sort((a, b) => b.total_morosidad - a.total_morosidad)
        .slice(0, 10) // Top 10
      return analistasOrdenados
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
      
      // ✅ CORRECCIÓN: NO pasar fecha_inicio del período para este gráfico
      // En su lugar, usar el parámetro 'meses' para mostrar los últimos 12 meses
      // Solo pasar fecha_inicio si viene de filtros explícitos del usuario
      const fechaInicioExplicita = filtros.fecha_inicio && filtros.fecha_inicio !== ''
      if (fechaInicioExplicita) {
        queryParams.append('fecha_inicio', filtros.fecha_inicio)
      }
      
      Object.entries(params).forEach(([key, value]) => {
        // No pasar fecha_inicio ni fecha_fin del período
        if (key !== 'fecha_inicio' && key !== 'fecha_fin' && value) {
          queryParams.append(key, value.toString())
        }
      })
      
      // ✅ SIEMPRE agregar parámetro meses=12 para mostrar últimos 12 meses
      queryParams.append('meses', '12')
      
      const response = await apiClient.get(
        `/api/v1/dashboard/evolucion-morosidad?${queryParams.toString()}`
      ) as { meses: Array<{ mes: string; morosidad: number }> }
      return response.meses
    },
    staleTime: 15 * 60 * 1000, // 15 minutos - optimizado para datos históricos
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
    enabled: !!datosDashboard, // ✅ Lazy loading - carga después de dashboard admin
  })

  const { data: datosEvolucionPagos, isLoading: loadingEvolucionPagos } = useQuery({
    queryKey: ['evolucion-pagos-menu', periodo, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodo) // ✅ Pasar período
      const queryParams = new URLSearchParams()
      
      // ✅ CORRECCIÓN: NO pasar fecha_inicio del período para este gráfico
      // En su lugar, usar el parámetro 'meses' para mostrar los últimos 12 meses
      // Solo pasar fecha_inicio si viene de filtros explícitos del usuario
      const fechaInicioExplicita = filtros.fecha_inicio && filtros.fecha_inicio !== ''
      if (fechaInicioExplicita) {
        queryParams.append('fecha_inicio', filtros.fecha_inicio)
      }
      
      Object.entries(params).forEach(([key, value]) => {
        // No pasar fecha_inicio ni fecha_fin del período
        if (key !== 'fecha_inicio' && key !== 'fecha_fin' && value) {
          queryParams.append(key, value.toString())
        }
      })
      
      // ✅ SIEMPRE agregar parámetro meses=12 para mostrar últimos 12 meses
      queryParams.append('meses', '12')
      
      // Usar timeout extendido para endpoints lentos
      const response = await apiClient.get(
        `/api/v1/dashboard/evolucion-pagos?${queryParams.toString()}`,
        { timeout: 60000 }
      ) as { meses: Array<{ mes: string; pagos: number; monto: number }> }
      return response.meses
    },
    staleTime: 15 * 60 * 1000, // 15 minutos - optimizado para datos históricos
    retry: 1,
    refetchOnWindowFocus: false, // Reducir peticiones automáticas
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

  // Procesar datos de financiamiento por rangos en bandas de $200 USD
  const datosBandas200 = useMemo(() => {
    try {
      if (!datosFinanciamientoRangos?.rangos || datosFinanciamientoRangos.rangos.length === 0) {
        return []
      }

      // Crear bandas de $200 USD
      const bandas: Record<string, number> = {}
      const montosExtraidos = datosFinanciamientoRangos.rangos.map(r => {
        // Extraer el monto máximo del rango
        const match = r.categoria.match(/\$(\d+)/g)
        if (match) {
          const montos = match.map(m => parseInt(m.replace('$', '').replace(/,/g, '')))
          return Math.max(...montos)
        }
        return 0
      }).filter(m => !isNaN(m) && m > 0) // Filtrar valores inválidos
      
      // Si no hay montos válidos, retornar array vacío
      if (montosExtraidos.length === 0) {
        return []
      }
      
      const maxMonto = Math.max(...montosExtraidos)

    // Inicializar todas las bandas de $200 desde $0 hasta el máximo
    for (let i = 0; i <= maxMonto; i += 200) {
      const bandaMax = i + 200
      const etiqueta = bandaMax > maxMonto && i > 0
        ? `$${i.toLocaleString()}+`
        : `$${i.toLocaleString()} - $${bandaMax.toLocaleString()}`
      bandas[etiqueta] = 0
    }

    // Distribuir los préstamos de los rangos existentes en las nuevas bandas de $200
    datosFinanciamientoRangos.rangos.forEach(rango => {
      const cantidad = rango.cantidad_prestamos
      const montoPromedio = rango.monto_total / (cantidad || 1)

      // Extraer límites del rango
      const match = rango.categoria.match(/\$(\d+)/g)
      if (match) {
        const montos = match.map(m => parseInt(m.replace('$', '').replace(/,/g, '')))
        const minRango = montos[0] || 0
        const maxRango = rango.categoria.includes('+') ? maxMonto : (montos[1] || montos[0] + 300)

        // Distribuir proporcionalmente en las bandas de $200
        for (let i = 0; i <= maxMonto; i += 200) {
          const bandaMin = i
          const bandaMax = i + 200

          // Calcular intersección entre el rango y la banda
          const interseccionMin = Math.max(bandaMin, minRango)
          const interseccionMax = Math.min(bandaMax, maxRango)

          if (interseccionMin < interseccionMax) {
            const porcentaje = (interseccionMax - interseccionMin) / (maxRango - minRango)
            const cantidadAsignada = Math.round(cantidad * porcentaje)

            const etiqueta = bandaMax > maxMonto && i > 0
              ? `$${i.toLocaleString()}+`
              : `$${i.toLocaleString()} - $${bandaMax.toLocaleString()}`

            if (bandas[etiqueta] !== undefined) {
              bandas[etiqueta] += cantidadAsignada
            }
          }
        }
      }
    })

    // Convertir a array y ordenar por monto (descendente)
    const bandasArray = Object.entries(bandas)
      .map(([categoria, cantidad]) => {
        // Extraer el monto mínimo para ordenar (capturar todos los dígitos y comas después del $)
        const match = categoria.match(/\$([\d,]+)/)
        const montoMin = match ? parseInt(match[1].replace(/,/g, '')) : 0
        return {
          categoria,
          cantidad,
          montoMin
        }
      })
      .filter(item => item.cantidad > 0) // Solo mostrar bandas con datos
      .sort((a, b) => b.montoMin - a.montoMin) // Ordenar de mayor a menor (valores grandes arriba)

      // Formatear etiquetas de manera más legible
      // El orden es descendente (mayor a menor), así los valores más grandes aparecen arriba en el gráfico vertical
      return bandasArray.map(item => ({
        ...item,
        categoriaFormateada: item.categoria.replace(/,/g, '') // Remover comas para mejor visualización
      }))
    } catch (error) {
      console.error('Error procesando datos de financiamiento por rangos:', error)
      return [] // Retornar array vacío en caso de error
    }
  }, [datosFinanciamientoRangos])

  // ✅ Asegurar que el componente siempre renderice, incluso si hay errores
  // Si hay un error crítico en las queries principales, mostrar mensaje pero no bloquear
  const hasCriticalError = errorOpcionesFiltros || errorKPIs
  
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
        
        {/* Mensaje de error si hay problemas críticos */}
        {hasCriticalError && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-yellow-50 border border-yellow-200 rounded-lg p-4"
          >
            <div className="flex items-center gap-2 text-yellow-800">
              <AlertTriangle className="h-5 w-5" />
              <p className="text-sm font-medium">
                Algunos datos no se pudieron cargar. Por favor, recarga la página o intenta más tarde.
              </p>
            </div>
          </motion.div>
        )}

        {/* BARRA DE FILTROS Y BOTONES ARRIBA - OCULTA */}
        {false && (
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
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* KPIs PRINCIPALES - OCULTAS */}
        {false && (
          <>
            {loadingKPIs ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-[180px] bg-gray-100 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : errorKPIs ? (
              <Card className="border-red-200 bg-red-50">
                <CardContent className="p-6">
                  <div className="flex items-center gap-3 text-red-700">
                    <AlertTriangle className="h-5 w-5" />
                    <p>Error al cargar los KPIs principales. Por favor, intente nuevamente.</p>
                  </div>
                </CardContent>
              </Card>
            ) : kpisPrincipales ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
              >
                <KpiCardLarge
                  title="Total Préstamos"
                  value={kpisPrincipales.total_prestamos.valor_actual}
                  variation={kpisPrincipales.total_prestamos.variacion_porcentual !== undefined ? {
                    percent: kpisPrincipales.total_prestamos.variacion_porcentual,
                    label: 'vs mes anterior'
                  } : undefined}
                  icon={FileText}
                  color="text-cyan-600"
                  bgColor="bg-cyan-100"
                  borderColor="border-cyan-500"
                  format="number"
                />
                <KpiCardLarge
                  title="Créditos Nuevos"
                  value={kpisPrincipales.creditos_nuevos_mes.valor_actual}
                  variation={kpisPrincipales.creditos_nuevos_mes.variacion_porcentual !== undefined ? {
                    percent: kpisPrincipales.creditos_nuevos_mes.variacion_porcentual,
                    label: 'vs mes anterior'
                  } : undefined}
                  icon={TrendingUp}
                  color="text-green-600"
                  bgColor="bg-green-100"
                  borderColor="border-green-500"
                  format="number"
                />
                <KpiCardLarge
                  title="Cuotas Programadas"
                  value={kpisPrincipales.cuotas_programadas?.valor_actual || 0}
                  subtitle={kpisPrincipales.porcentaje_cuotas_pagadas !== undefined
                    ? `% Cuotas pagadas: ${kpisPrincipales.porcentaje_cuotas_pagadas.toFixed(1)}%`
                    : undefined}
                  icon={FileText}
                  color="text-blue-600"
                  bgColor="bg-blue-100"
                  borderColor="border-blue-500"
                  format="currency"
                />
                <KpiCardLarge
                  title="Morosidad Total"
                  value={kpisPrincipales.total_morosidad_usd.valor_actual}
                  variation={kpisPrincipales.total_morosidad_usd.variacion_porcentual !== undefined ? {
                    percent: kpisPrincipales.total_morosidad_usd.variacion_porcentual,
                    label: 'vs mes anterior'
                  } : undefined}
                  icon={AlertTriangle}
                  color="text-red-600"
                  bgColor="bg-red-100"
                  borderColor="border-red-500"
                  format="currency"
                />
              </motion.div>
            ) : null}
          </>
        )}

        {/* GRÁFICOS PRINCIPALES */}
        {loadingDashboard ? (
          <div className="space-y-6">
            <div className="h-[400px] bg-gray-100 rounded-xl animate-pulse" />
            <div className="h-[400px] bg-gray-100 rounded-xl animate-pulse" />
          </div>
        ) : datosDashboard ? (
          <div className="space-y-6">
            {/* Gráfico de Evolución Mensual */}
            {evolucionMensual.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-cyan-50 to-blue-50 border-b-2 border-cyan-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <LineChart className="h-6 w-6 text-cyan-600" />
                      <span>Evolución Mensual</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    <ResponsiveContainer width="100%" height={300}>
                      <ComposedChart data={evolucionMensual}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="mes" />
                        <YAxis 
                          tickFormatter={(value) => {
                            if (value >= 1000) {
                              return `$${(value / 1000).toFixed(0)}K`
                            }
                            return `$${value}`
                          }}
                          label={{ value: 'Monto (USD)', angle: -90, position: 'insideLeft' }}
                        />
                        <Tooltip 
                          formatter={(value: number, name: string) => {
                            if (name === 'Morosidad') {
                              return [formatCurrency(value), name]
                            }
                            return [formatCurrency(value), name]
                          }}
                        />
                        <Legend />
                        <Bar dataKey="cartera" fill="#3b82f6" name="Cartera" />
                        <Bar dataKey="cobrado" fill="#10b981" name="Cobrado" />
                        <Line type="monotone" dataKey="morosidad" stroke="#ef4444" strokeWidth={2} name="Morosidad" />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Gráfico de Áreas - Indicadores Financieros - Ancho Completo */}
            {datosTendencia && datosTendencia.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 border-b-2 border-green-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <DollarSign className="h-6 w-6 text-green-600" />
                      <span>Indicadores Financieros</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    <ResponsiveContainer width="100%" height={400}>
                      <AreaChart data={datosTendencia} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorFinanciamiento" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                          </linearGradient>
                          <linearGradient id="colorPagosProgramados" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
                          </linearGradient>
                          <linearGradient id="colorPagosReales" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.1}/>
                          </linearGradient>
                          <linearGradient id="colorMorosidad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="mes"
                          tick={{ fontSize: 12 }}
                          angle={-45}
                          textAnchor="end"
                          height={80}
                        />
                        <YAxis
                          tick={{ fontSize: 12 }}
                          tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                          label={{ value: 'Monto (USD)', angle: -90, position: 'insideLeft' }}
                        />
                        <Tooltip
                          formatter={(value: number, name: string) => {
                            const labels: Record<string, string> = {
                              'monto_nuevos': 'Total Financiamiento',
                              'monto_cuotas_programadas': 'Total Pagos Programados',
                              'monto_pagado': 'Total Pagos Reales',
                              'morosidad_mensual': 'Morosidad'
                            }
                            return [formatCurrency(value), labels[name] || name]
                          }}
                          labelFormatter={(label) => `Mes: ${label}`}
                        />
                        <Legend />
                        <Area
                          type="monotone"
                          dataKey="monto_nuevos"
                          stroke="#3b82f6"
                          fillOpacity={0.6}
                          fill="url(#colorFinanciamiento)"
                          name="Total Financiamiento"
                        />
                        <Area
                          type="monotone"
                          dataKey="monto_cuotas_programadas"
                          stroke="#10b981"
                          fillOpacity={0.6}
                          fill="url(#colorPagosProgramados)"
                          name="Total Pagos Programados"
                        />
                        <Area
                          type="monotone"
                          dataKey="monto_pagado"
                          stroke="#f59e0b"
                          fillOpacity={0.6}
                          fill="url(#colorPagosReales)"
                          name="Total Pagos Reales"
                        />
                        <Area
                          type="monotone"
                          dataKey="morosidad_mensual"
                          stroke="#ef4444"
                          fillOpacity={0.6}
                          fill="url(#colorMorosidad)"
                          name="Morosidad"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Gráfico de Líneas - Morosidad, Cuotas Programadas y Pagos Realizados - Ancho Completo */}
            {datosTendencia && datosTendencia.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.36 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-cyan-50 to-blue-50 border-b-2 border-cyan-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <LineChart className="h-6 w-6 text-cyan-600" />
                      <span>Evolución Mensual: Morosidad, Cuotas Programadas y Pagos Realizados</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    <ResponsiveContainer width="100%" height={400}>
                      <RechartsLineChart data={datosTendencia} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis
                          dataKey="mes"
                          tick={{ fontSize: 12, fill: '#6b7280' }}
                          angle={-45}
                          textAnchor="end"
                          height={80}
                        />
                        <YAxis
                          tick={{ fontSize: 12, fill: '#6b7280' }}
                          tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                          label={{ value: 'Monto (USD)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: '#374151', fontSize: 12, fontWeight: 600 } }}
                        />
                        <Tooltip
                          formatter={(value: number, name: string) => {
                            const labels: Record<string, string> = {
                              'morosidad_mensual': 'Morosidad',
                              'monto_cuotas_programadas': 'Cuotas Programadas',
                              'monto_pagado': 'Pagos Realizados'
                            }
                            return [formatCurrency(value), labels[name] || name]
                          }}
                          labelFormatter={(label) => `Mes: ${label}`}
                          contentStyle={{
                            backgroundColor: 'rgba(255, 255, 255, 0.95)',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                          }}
                        />
                        <Legend 
                          wrapperStyle={{ paddingTop: '10px' }}
                          iconType="line"
                        />
                        <Line
                          type="monotone"
                          dataKey="morosidad_mensual"
                          stroke="#ef4444"
                          strokeWidth={3}
                          dot={{ r: 5, fill: '#ef4444' }}
                          activeDot={{ r: 7 }}
                          name="Morosidad"
                        />
                        <Line
                          type="monotone"
                          dataKey="monto_cuotas_programadas"
                          stroke="#10b981"
                          strokeWidth={3}
                          dot={{ r: 5, fill: '#10b981' }}
                          activeDot={{ r: 7 }}
                          name="Cuotas Programadas"
                        />
                        <Line
                          type="monotone"
                          dataKey="monto_pagado"
                          stroke="#f59e0b"
                          strokeWidth={3}
                          dot={{ r: 5, fill: '#f59e0b' }}
                          activeDot={{ r: 7 }}
                          name="Pagos Realizados"
                        />
                      </RechartsLineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </div>
        ) : null}

        {/* GRÁFICOS: BANDAS DE $200 USD Y COBRANZA PLANIFICADA VS REAL */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* GRÁFICO DE BANDAS DE $200 USD */}
          {datosBandas200 && datosBandas200.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card className="shadow-lg border-2 border-gray-200 h-full flex flex-col">
                <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50 border-b-2 border-indigo-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <BarChart3 className="h-6 w-6 text-indigo-600" />
                    <span>Distribución por Bandas de $200 USD</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  <ResponsiveContainer width="100%" height={450}>
                    <BarChart
                      data={datosBandas200}
                      layout="vertical"
                      margin={{ top: 10, right: 40, left: 120, bottom: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
                      <XAxis
                        type="number"
                        domain={[0, 'dataMax']}
                        tick={{ fontSize: 11, fill: '#6b7280' }}
                        tickFormatter={(value) => value.toLocaleString('es-EC')}
                        label={{
                          value: 'Cantidad de Préstamos',
                          position: 'insideBottom',
                          offset: -10,
                          style: { textAnchor: 'middle', fill: '#374151', fontSize: 12, fontWeight: 600 }
                        }}
                        allowDecimals={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="categoriaFormateada"
                        width={115}
                        tick={{ fontSize: 10, fill: '#4b5563', fontWeight: 500 }}
                        interval={0}
                        tickLine={false}
                      />
                      <Tooltip
                        formatter={(value: number) => [
                          `${value.toLocaleString('es-EC')} préstamos`,
                          'Cantidad'
                        ]}
                        labelFormatter={(label) => `Banda: ${label}`}
                        contentStyle={{
                          backgroundColor: 'rgba(255, 255, 255, 0.95)',
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                        }}
                        cursor={{ fill: 'rgba(99, 102, 241, 0.1)' }}
                      />
                      <Legend
                        wrapperStyle={{ paddingTop: '10px' }}
                        iconType="rect"
                      />
                      <Bar
                        dataKey="cantidad"
                        radius={[0, 6, 6, 0]}
                        name="Cantidad de Préstamos"
                      >
                        {datosBandas200.map((entry, index) => {
                          // Gradiente de color según la posición (más oscuro para valores más altos)
                          const intensity = entry.cantidad / Math.max(...datosBandas200.map(d => d.cantidad))
                          const opacity = 0.6 + (intensity * 0.4)
                          return (
                            <Cell
                              key={`cell-${index}`}
                              fill={`rgba(99, 102, 241, ${opacity})`}
                            />
                          )
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* GRÁFICO DE COBRANZA FECHAS ESPECÍFICAS */}
          {datosCobranzaFechas && datosCobranzaFechas.dias && datosCobranzaFechas.dias.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45 }}
              className="h-full"
            >
              <Card className="shadow-lg border-2 border-gray-200 h-full flex flex-col">
                <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b-2 border-blue-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <BarChart3 className="h-6 w-6 text-blue-600" />
                    <span>Cobranza Planificada vs Real</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  {loadingCobranzaFechas ? (
                    <div className="h-[450px] flex items-center justify-center">
                      <div className="animate-pulse text-gray-400">Cargando...</div>
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={450}>
                      <BarChart data={datosCobranzaFechas.dias} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="nombre_fecha"
                          tick={{ fontSize: 12 }}
                        />
                        <YAxis
                          domain={[0, 'dataMax']}
                          tickCount={6}
                          tick={{ fontSize: 11 }}
                          tickFormatter={(value) => {
                            if (value >= 1000) {
                              return `$${(value / 1000).toFixed(1)}K`
                            }
                            return `$${value}`
                          }}
                          label={{
                            value: 'Monto (USD)',
                            angle: -90,
                            position: 'insideLeft',
                            style: { textAnchor: 'middle', fontSize: 12, fontWeight: 600 }
                          }}
                        />
                        <Tooltip
                          formatter={(value: number) => [formatCurrency(value), '']}
                          labelFormatter={(label) => `Fecha: ${label}`}
                          contentStyle={{
                            backgroundColor: 'rgba(255, 255, 255, 0.95)',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                          }}
                        />
                        <Legend />
                        <Bar dataKey="cobranza_planificada" fill="#3b82f6" name="Planificado" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="cobranza_real" fill="#10b981" name="Real" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}
        </div>

        {/* GRÁFICOS DE DISTRIBUCIÓN */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Préstamos por Concesionario */}
          {datosConcesionarios && datosConcesionarios.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 border-b-2 border-purple-200">
                    <CardTitle className="flex items-center justify-center space-x-2 text-xl font-bold text-gray-800">
                    <BarChart3 className="h-6 w-6 text-purple-600" />
                    <span>Préstamos por Concesionario</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6 flex items-center justify-center">
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={datosConcesionarios} layout="vertical" margin={{ top: 5, right: 30, left: 150, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        type="number"
                        allowDecimals={false}
                        tickFormatter={(value) => value.toLocaleString('es-EC')}
                      />
                      <YAxis
                        type="category"
                        dataKey="concesionario"
                        width={140}
                        tick={{ fontSize: 12 }}
                      />
                      <Tooltip
                        formatter={(value: number, name: string) => [
                          `${Math.round(value).toLocaleString('es-EC')} préstamos`,
                          'Cantidad'
                        ]}
                        labelFormatter={(label) => `Concesionario: ${label}`}
                      />
                      <Bar
                        dataKey="cantidad_prestamos"
                        fill="#8b5cf6"
                        radius={[0, 4, 4, 0]}
                      >
                        {datosConcesionarios.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]} />
                        ))}
                      </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                  </CardContent>
                </Card>
              </motion.div>
          )}

          {/* Préstamos por Modelo */}
          {datosModelos && datosModelos.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-amber-50 to-orange-50 border-b-2 border-amber-200">
                    <CardTitle className="flex items-center justify-center space-x-2 text-xl font-bold text-gray-800">
                    <BarChart3 className="h-6 w-6 text-amber-600" />
                    <span>Préstamos por Modelo</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6 flex items-center justify-center">
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={datosModelos} layout="vertical" margin={{ top: 5, right: 30, left: 150, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        type="number"
                        allowDecimals={false}
                        tickFormatter={(value) => value.toLocaleString('es-EC')}
                      />
                        <YAxis
                        type="category"
                        dataKey="modelo"
                        width={140}
                        tick={{ fontSize: 12 }}
                        />
                            <Tooltip
                        formatter={(value: number, name: string) => [
                          `${Math.round(value).toLocaleString('es-EC')} préstamos`,
                          'Cantidad'
                        ]}
                        labelFormatter={(label) => `Modelo: ${label}`}
                      />
                      <Bar
                        dataKey="cantidad_prestamos"
                        fill="#f59e0b"
                        radius={[0, 4, 4, 0]}
                      >
                        {datosModelos.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS_CONCESIONARIOS[index % COLORS_CONCESIONARIOS.length]} />
                            ))}
                        </Bar>
                      </BarChart>
                        </ResponsiveContainer>
                  </CardContent>
                </Card>
              </motion.div>
          )}
        </div>

        {/* GRÁFICO DE COBRANZAS MENSUALES - FILA COMPLETA */}
        {datosCobranzas && datosCobranzas.meses && datosCobranzas.meses.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <Card className="shadow-lg border-2 border-gray-200">
              <CardHeader className="bg-gradient-to-r from-emerald-50 to-teal-50 border-b-2 border-emerald-200">
                <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                  <BarChart3 className="h-6 w-6 text-emerald-600" />
                  <span>Cobranzas Mensuales</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={datosCobranzas.meses}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="nombre_mes" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="cobranzas_planificadas" fill="#3b82f6" name="Planificadas" />
                    <Bar dataKey="pagos_reales" fill="#10b981" name="Reales" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        )}


        {/* GRÁFICOS DE MOROSIDAD */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Composición de Morosidad */}
          {datosComposicionMorosidad && datosComposicionMorosidad.puntos && datosComposicionMorosidad.puntos.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="h-full"
            >
              <Card className="shadow-lg border-2 border-gray-200 h-full flex flex-col">
                <CardHeader className="bg-gradient-to-r from-red-50 to-rose-50 border-b-2 border-red-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <BarChart3 className="h-6 w-6 text-red-600" />
                    <span>Composición de Morosidad</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={datosComposicionMorosidad.puntos}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="categoria" />
                      <YAxis />
                      <Tooltip />
                        <Legend />
                      <Bar dataKey="monto" fill="#ef4444" name="Monto en Morosidad" />
                      </BarChart>
                    </ResponsiveContainer>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Morosidad por Analista */}
          {datosMorosidadAnalista && datosMorosidadAnalista.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
              className="h-full"
            >
              <Card className="shadow-lg border-2 border-gray-200 h-full flex flex-col">
                <CardHeader className="bg-gradient-to-r from-orange-50 to-amber-50 border-b-2 border-orange-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <Users className="h-6 w-6 text-orange-600" />
                    <span>Morosidad por Analista</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={datosMorosidadAnalista} margin={{ top: 5, right: 30, left: 20, bottom: 60 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="analista"
                        angle={-45}
                        textAnchor="end"
                        height={80}
                        tick={{ fontSize: 12 }}
                      />
                      <YAxis
                        label={{ value: 'Morosidad Total', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip
                        formatter={(value: number) => [`${formatCurrency(value)}`, 'Morosidad Total']}
                        labelFormatter={(label) => `Analista: ${label}`}
                      />
                      <Legend />
                      <Bar
                        dataKey="total_morosidad"
                        fill="#f97316"
                        name="Morosidad Total"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </div>

        {/* GRÁFICOS DE EVOLUCIÓN */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Evolución de Morosidad */}
          {datosEvolucionMorosidad && datosEvolucionMorosidad.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.0 }}
            >
              <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-red-50 to-pink-50 border-b-2 border-red-200">
                  <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <LineChart className="h-6 w-6 text-red-600" />
                    <span>Evolución de Morosidad</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <ResponsiveContainer width="100%" height={300}>
                    <RechartsLineChart data={datosEvolucionMorosidad}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="mes" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="morosidad" stroke="#ef4444" strokeWidth={2} name="Morosidad" />
                    </RechartsLineChart>
                  </ResponsiveContainer>
                  </CardContent>
                </Card>
              </motion.div>
          )}

          {/* Evolución de Pagos */}
          {datosEvolucionPagos && datosEvolucionPagos.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.1 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 border-b-2 border-green-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                    <LineChart className="h-6 w-6 text-green-600" />
                    <span>Evolución de Pagos</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                  <ResponsiveContainer width="100%" height={300}>
                    <ComposedChart data={datosEvolucionPagos}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="mes" />
                      <YAxis yAxisId="left" />
                      <YAxis yAxisId="right" orientation="right" />
                      <Tooltip />
                            <Legend />
                      <Bar yAxisId="left" dataKey="pagos" fill="#10b981" name="Cantidad Pagos" />
                      <Line yAxisId="right" type="monotone" dataKey="monto" stroke="#3b82f6" strokeWidth={2} name="Monto Total" />
                    </ComposedChart>
                        </ResponsiveContainer>
                  </CardContent>
                </Card>
              </motion.div>
          )}
            </div>

      </div>
    </div>
  )
}
