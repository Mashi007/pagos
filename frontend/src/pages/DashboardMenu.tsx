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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { formatCurrency } from '../utils'
import { apiClient } from '../services/api'
import { toast } from 'sonner'
import { useDashboardFiltros, type DashboardFiltros } from '../hooks/useDashboardFiltros'
import { getPeriodoEtiqueta, PERIODOS_VALORES } from '../constants/dashboard'
import type {
  KpisPrincipalesResponse,
  OpcionesFiltrosResponse,
  DashboardAdminResponse,
  FinanciamientoPorRangosResponse,
  ComposicionMorosidadResponse,
  CobranzasSemanalesResponse,
  MorosidadPorAnalistaItem,
} from '../types/dashboard'
import { DashboardFiltrosPanel } from '../components/dashboard/DashboardFiltrosPanel'
import { KpiCardLarge } from '../components/dashboard/KpiCardLarge'
import { ChartWithDateRangeSlider } from '../components/dashboard/ChartWithDateRangeSlider'
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
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts'

// Submenús eliminados: financiamiento, cuotas, cobranza, analisis, pagos

export function DashboardMenu() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'
  const queryClient = useQueryClient()

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [periodo, setPeriodo] = useState('ultimos_12_meses') // Por defecto últimos 12 meses para que los gráficos muestren datos recientes
  /** Período por gráfico: cada gráfico puede usar el general o uno propio. Key = id del gráfico, value = día|semana|mes|año o '' = usar general */
  const [periodoPorGrafico, setPeriodoPorGrafico] = useState<Record<string, string>>({})
  const { construirParams, construirFiltrosObject, tieneFiltrosActivos, cantidadFiltrosActivos } = useDashboardFiltros(filtros)

  /** Período efectivo para un gráfico: el del gráfico si está definido, si no el general */
  const getPeriodoGrafico = (chartId: string) => periodoPorGrafico[chartId] || periodo
  const setPeriodoGrafico = (chartId: string, value: string) => {
    setPeriodoPorGrafico((prev) => (value ? { ...prev, [chartId]: value } : { ...prev, [chartId]: '' }))
  }

  // âœ… OPTIMIZACIÓN PRIORIDAD 1: Carga por batches con priorización
  // Batch 1: CRÍTICO - Opciones de filtros y KPIs principales (carga inmediata)
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async (): Promise<OpcionesFiltrosResponse> => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as OpcionesFiltrosResponse
    },
    staleTime: 30 * 60 * 1000, // 30 minutos - cambian muy poco
    refetchOnWindowFocus: false, // No recargar automáticamente
    // âœ… Prioridad máxima - carga inmediatamente
  })

  // Batch 1: CRÍTICO - KPIs principales (visible primero para el usuario)
  // âœ… ACTUALIZADO: Incluye período en queryKey y aplica filtro de período
  const { data: kpisPrincipales, isLoading: loadingKPIs, isError: errorKPIs, refetch } = useQuery({
    queryKey: ['kpis-principales-menu', periodo, JSON.stringify(filtros)],
    queryFn: async (): Promise<KpisPrincipalesResponse> => {
      const params = construirFiltrosObject(periodo)
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/kpis-principales${queryString ? '?' + queryString : ''}`
      )
      return response as KpisPrincipalesResponse
    },
    staleTime: 4 * 60 * 60 * 1000, // 4 h: el backend actualiza caché a las 6:00, 13:00, 16:00
    refetchOnWindowFocus: false,
    refetchOnMount: false, // Usar caché; el backend refresca 3 veces al día
    enabled: true,
    retry: false,
  })

  // Batch 2: IMPORTANTE - Dashboard admin (gráfico principal). Siempre con período que incluya 2025 si hay datos.
  const periodoEvolucion = getPeriodoGrafico('evolucion') || periodo || 'ultimos_12_meses'
  const { data: datosDashboard, isLoading: loadingDashboard } = useQuery({
    queryKey: ['dashboard-menu', periodoEvolucion, JSON.stringify(filtros)],
    queryFn: async (): Promise<DashboardAdminResponse> => {
      try {
        const obj = construirFiltrosObject(periodoEvolucion)
        const params = new URLSearchParams()
        Object.entries(obj).forEach(([key, value]) => {
          if (value != null && value !== '') params.append(key, String(value))
        })
        if (!params.has('periodo') && periodoEvolucion) params.append('periodo', periodoEvolucion)
        const queryString = params.toString()
        const response = await apiClient.get(`/api/v1/dashboard/admin${queryString ? `?${queryString}` : ''}`, { timeout: 60000 })
        return response as DashboardAdminResponse
      } catch (error) {
        return {} as DashboardAdminResponse
      }
    },
    staleTime: 4 * 60 * 60 * 1000, // 4 h: backend actualiza caché a las 6:00, 13:00, 16:00
    retry: 1,
    refetchOnWindowFocus: false, // Evitar refetch al cambiar de pestaña (carga lenta)
    enabled: true,
  })

  // Batch 3: Morosidad por día (desde tabla cuotas). Respeta rango del período (ej. desde 2025).
  const periodoTendencia = getPeriodoGrafico('tendencia') || periodo || 'ultimos_12_meses'
  const diasMorosidad = (periodoTendencia === 'dia' || periodoTendencia === 'día') ? 7 : periodoTendencia === 'semana' ? 14 : periodoTendencia === 'mes' ? 30 : 90
  const { data: datosMorosidadPorDia, isLoading: loadingMorosidadPorDia } = useQuery({
    queryKey: ['morosidad-por-dia', periodoTendencia, diasMorosidad, JSON.stringify(filtros)],
    queryFn: async () => {
      const obj = construirFiltrosObject(periodoTendencia)
      const queryParams = new URLSearchParams()
      queryParams.append('dias', String(diasMorosidad))
      if (obj.fecha_inicio) queryParams.append('fecha_inicio', obj.fecha_inicio)
      if (obj.fecha_fin) queryParams.append('fecha_fin', obj.fecha_fin)
      const response = await apiClient.get<{ dias: Array<{ fecha: string; dia: string; morosidad: number }> }>(
        `/api/v1/dashboard/morosidad-por-dia?${queryParams.toString()}`
      )
      return response.dias ?? []
    },
    staleTime: 4 * 60 * 60 * 1000, // 4 h: alineado con refresh backend 6/13/16
    enabled: true,
    refetchOnWindowFocus: false,
  })

  // Batch 3: Gráficos secundarios rápidos. Período por gráfico; filtros (fecha_inicio/fecha_fin) se envían siempre.
  // Batch 4: BAJA - Gráficos menos críticos. Período con fallback para incluir 2025.
  const periodoRangos = getPeriodoGrafico('rangos') || periodo || 'ultimos_12_meses'
  const { data: datosFinanciamientoRangos, isLoading: loadingFinanciamientoRangos, isError: errorFinanciamientoRangos, error: errorFinanciamientoRangosDetail, refetch: refetchFinanciamientoRangos } = useQuery({
    queryKey: ['financiamiento-rangos', periodoRangos, JSON.stringify(filtros)],
    queryFn: async () => {
      try {
        const params = construirFiltrosObject(periodoRangos)
        const queryParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })
        const response = await apiClient.get(
          `/api/v1/dashboard/financiamiento-por-rangos?${queryParams.toString()}`,
          { timeout: 60000 }
        )
        return response as FinanciamientoPorRangosResponse
      } catch (error: unknown) {
        // Si el error es 500 o de red, lanzar el error para que React Query lo maneje
        // Si es otro error, retornar respuesta vacía para no romper el dashboard
        const err = error as { response?: { status?: number }; code?: string }
        const status = err?.response?.status
        if ((status != null && status >= 500) || err?.code === 'ERR_NETWORK' || err?.code === 'ECONNABORTED') {
          throw error
        }
        return {
          rangos: [],
          total_prestamos: 0,
          total_monto: 0.0,
        } satisfies FinanciamientoPorRangosResponse
      }
    },
    staleTime: 4 * 60 * 60 * 1000, // 4 h: alineado con refresh backend
    refetchOnWindowFocus: false,
    enabled: true,
    retry: 1, // âœ… Permitir 1 reintento para errores de red
    retryDelay: 2000, // Esperar 2 segundos antes de reintentar
  })

  const periodoComposicionMorosidad = getPeriodoGrafico('composicion-morosidad')
  const { data: datosComposicionMorosidad, isLoading: loadingComposicionMorosidad } = useQuery({
    queryKey: ['composicion-morosidad', periodoComposicionMorosidad, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodoComposicionMorosidad)
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/composicion-morosidad?${queryParams.toString()}`
      )
      return response as ComposicionMorosidadResponse
    },
    staleTime: 4 * 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    enabled: true,
  })


  const periodoCobranzasSemanales = getPeriodoGrafico('cobranzas-semanales')
  const { data: datosCobranzasSemanales, isLoading: loadingCobranzasSemanales } = useQuery({
    queryKey: ['cobranzas-semanales', periodoCobranzasSemanales, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodoCobranzasSemanales)
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      queryParams.append('semanas', '12') // Últimas 12 semanas
      const response = await apiClient.get(
        `/api/v1/dashboard/cobranzas-semanales?${queryParams.toString()}`,
        { timeout: 60000 }
      )
      return response as CobranzasSemanalesResponse
    },
    staleTime: 15 * 60 * 1000,
    enabled: true,
    refetchOnWindowFocus: false,
  })

  const periodoMorosidadAnalista = getPeriodoGrafico('morosidad-analista')
  const { data: datosMorosidadAnalista, isLoading: loadingMorosidadAnalista } = useQuery({
    queryKey: ['morosidad-analista', periodoMorosidadAnalista, JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject(periodoMorosidadAnalista)
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get<{ analistas: MorosidadPorAnalistaItem[] }>(
        `/api/v1/dashboard/morosidad-por-analista?${queryParams.toString()}`
      )
      return response.analistas ?? []
    },
    staleTime: 4 * 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    enabled: true,
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
      await queryClient.invalidateQueries({ queryKey: ['morosidad-por-dia'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['financiamiento-rangos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['composicion-morosidad'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['cobranzas-mensuales'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['cobranzas-semanales'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['morosidad-analista'], exact: false })

      // Refrescar todas las queries activas
      await queryClient.refetchQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['dashboard-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['morosidad-por-dia'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['financiamiento-rangos'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['composicion-morosidad'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['morosidad-analista'], exact: false })

      // También refrescar la query de kpisPrincipales usando su refetch
      await refetch()
      toast.success('Datos actualizados correctamente')
    } catch (error) {
      toast.error('Error al actualizar los datos. Intenta de nuevo.')
    } finally {
      setIsRefreshing(false)
    }
  }

  const evolucionMensual = datosDashboard?.evolucion_mensual || []
  const COLORS_CONCESIONARIOS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1']

  // Etiqueta del período activo (general)
  const rangoFechasLabel = useMemo(() => {
    const obj = construirFiltrosObject(periodo)
    if (obj.fecha_inicio && obj.fecha_fin) {
      const fIni = new Date(obj.fecha_inicio)
      const fFin = new Date(obj.fecha_fin)
      const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' }
      return `${fIni.toLocaleDateString('es-ES', opts)} – ${fFin.toLocaleDateString('es-ES', opts)}`
    }
    return getPeriodoEtiqueta(periodo)
  }, [periodo, filtros, construirFiltrosObject])

  /** Etiqueta de rango de fechas para un gráfico (usa período del gráfico o el general) */
  const getRangoFechasLabelGrafico = (chartId: string) => {
    const p = getPeriodoGrafico(chartId)
    const obj = construirFiltrosObject(p)
    if (obj.fecha_inicio && obj.fecha_fin) {
      const fIni = new Date(obj.fecha_inicio)
      const fFin = new Date(obj.fecha_fin)
      const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' }
      return `${fIni.toLocaleDateString('es-ES', opts)} – ${fFin.toLocaleDateString('es-ES', opts)}`
    }
    return getPeriodoEtiqueta(p)
  }

  /** Selector de período por gráfico (dropdown para cada tarjeta) */
  const SelectorPeriodoGrafico = ({ chartId }: { chartId: string }) => (
    <Select
      value={periodoPorGrafico[chartId] || 'general'}
      onValueChange={(v) => setPeriodoGrafico(chartId, v === 'general' ? '' : v)}
    >
      <SelectTrigger className="w-[160px] h-8 text-xs border-gray-200 bg-white/80">
        <SelectValue placeholder="Período" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="general">General (barra superior)</SelectItem>
        {PERIODOS_VALORES.map((p) => (
          <SelectItem key={p} value={p}>
            {getPeriodoEtiqueta(p)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )

  // Estilos de mayor calidad para todos los gráficos (tooltips, ejes, grid)
  const chartTooltipStyle = {
    contentStyle: { backgroundColor: 'rgba(255,255,255,0.98)', border: '1px solid #e5e7eb', borderRadius: '10px', boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: '14px 16px' },
    labelStyle: { fontWeight: 600, color: '#111827', marginBottom: 8, fontSize: 13 },
    itemStyle: { fontSize: '13px', color: '#4b5563' },
  }
  const chartCartesianGrid = { stroke: '#d1d5db', strokeDasharray: '4 4', strokeOpacity: 0.9 }
  const chartAxisTick = { fontSize: 13, fill: '#374151', fontWeight: 500 }
  const chartLegendStyle = { wrapperStyle: { paddingTop: 14 }, iconType: 'rect' as const, iconSize: 12 }

  // Bandas desde backend: $0-$200, $200-$400, ..., $800-$1000, $1000-$1200, Más de $1200 (cantidad de préstamos por banda)
  const datosBandas200 = useMemo(() => {
    try {
      if (!datosFinanciamientoRangos?.rangos || datosFinanciamientoRangos.rangos.length === 0) {
        return []
      }
      // Orden descendente (mayor banda arriba en el gráfico horizontal): Más de $1200 primero, luego $1000-$1200, etc.
      const orden = ['Más de $1,200', '$1,000 - $1,200', '$800 - $1,000', '$600 - $800', '$400 - $600', '$200 - $400', '$0 - $200']
      return [...datosFinanciamientoRangos.rangos]
        .sort((a, b) => orden.indexOf(b.categoria) - orden.indexOf(a.categoria))
        .map(r => ({
          ...r,
          categoriaFormateada: r.categoria.replace(/,/g, ''),
          cantidad: r.cantidad_prestamos,
        }))
    } catch (error) {
      console.error('Error procesando datos de financiamiento por rangos:', error)
      return []
    }
  }, [datosFinanciamientoRangos])

  // âœ… Asegurar que el componente siempre renderice, incluso si hay errores
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

        {/* Barra de filtros: período general (cada gráfico puede usar este o uno propio) */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="shadow-md border border-gray-200/80 bg-white/95 backdrop-blur-sm rounded-xl">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-cyan-600" />
                    <span className="text-sm font-semibold text-gray-700">Filtros</span>
                  </div>
                  <Select value={periodo} onValueChange={(v) => setPeriodo(v)}>
                    <SelectTrigger className="w-[180px] h-9 border-gray-200 bg-gray-50/80">
                      <SelectValue placeholder="Período" />
                    </SelectTrigger>
                    <SelectContent>
                      {PERIODOS_VALORES.map((p) => (
                        <SelectItem key={p} value={p}>
                          {getPeriodoEtiqueta(p)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-gray-100">
                    {rangoFechasLabel}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
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
        {(
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
                  format="currency"
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
            {/* Aviso cuando no hay datos en los gráficos */}
            {kpisPrincipales && Number(kpisPrincipales.total_prestamos?.valor_actual ?? 0) === 0 && (!datosDashboard?.evolucion_mensual?.length || datosDashboard.evolucion_mensual.every((e: { cartera: number; cobrado: number }) => !e.cartera && !e.cobrado)) ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
                <Card className="border-amber-200 bg-amber-50/80">
                  <CardContent className="p-4 flex items-center gap-3">
                    <Info className="h-5 w-5 text-amber-600 shrink-0" />
                    <p className="text-sm text-amber-800">
                      Los gráficos están vacíos porque no hay datos en el período. Cargue <strong>préstamos</strong> y <strong>cuotas</strong> en el sistema para ver la información. Puede usar la opción <strong>Últimos 12 meses</strong> si ya tiene datos de meses anteriores.
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ) : null}

            {/* Gráfico de Evolución Mensual */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white">
                  <CardHeader className="bg-gradient-to-r from-cyan-50/90 to-blue-50/90 border-b border-gray-200/80 pb-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                        <LineChart className="h-5 w-5 text-cyan-600" />
                        <span>Evolución Mensual</span>
                      </CardTitle>
                      <div className="flex items-center gap-2 flex-wrap">
                        <SelectorPeriodoGrafico chartId="evolucion" />
                        <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                          {getRangoFechasLabelGrafico('evolucion')}
                        </Badge>
                        {datosDashboard?.evolucion_origen === 'demo' && (
                          <Badge variant="outline" className="text-xs font-medium text-amber-700 bg-amber-50 border-amber-300">
                            Datos de ejemplo
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-6 pt-4">
                    {evolucionMensual.length > 0 ? (
                      <ChartWithDateRangeSlider data={evolucionMensual} dataKey="mes" chartHeight={320}>
                        {(filteredData) => (
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={filteredData} margin={{ top: 12, right: 20, left: 12, bottom: 12 }}>
                              <CartesianGrid {...chartCartesianGrid} />
                              <XAxis dataKey="mes" tick={chartAxisTick} />
                              <YAxis 
                                tick={chartAxisTick}
                                tickFormatter={(value) => {
                                  if (value >= 1000) {
                                    return `$${(value / 1000).toFixed(0)}K`
                                  }
                                  return `$${value}`
                                }}
                                label={{ value: 'Monto (USD)', angle: -90, position: 'insideLeft', style: { fill: '#374151', fontSize: 13 } }}
                              />
                              <Tooltip 
                                contentStyle={chartTooltipStyle.contentStyle}
                                labelStyle={chartTooltipStyle.labelStyle}
                                formatter={(value: number, name: string) => [formatCurrency(value), name]}
                              />
                              <Legend {...chartLegendStyle} />
                              <Bar dataKey="cartera" fill="#3b82f6" name="Cartera" radius={[4, 4, 0, 0]} />
                              <Bar dataKey="cobrado" fill="#10b981" name="Cobrado" radius={[4, 4, 0, 0]} />
                              <Line type="monotone" dataKey="morosidad" stroke="#ef4444" strokeWidth={2} name="Morosidad" dot={{ r: 4 }} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        )}
                      </ChartWithDateRangeSlider>
                    ) : (
                      <div className="flex items-center justify-center py-16 text-gray-500">No hay datos para el período seleccionado</div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

            {/* Morosidad por día - desde tabla cuotas (cartera - cobrado por día) */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
              >
                <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white">
                  <CardHeader className="bg-gradient-to-r from-red-50/90 to-orange-50/90 border-b border-gray-200/80 pb-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                        <AlertTriangle className="h-5 w-5 text-red-600" />
                        <span>Morosidad por día</span>
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        <SelectorPeriodoGrafico chartId="tendencia" />
                        <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                          {(periodoTendencia === 'dia' || periodoTendencia === 'día') ? '7 días' : periodoTendencia === 'semana' ? '14 días' : periodoTendencia === 'mes' ? '30 días' : '90 días'}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-6 pt-4">
                    {loadingMorosidadPorDia ? (
                      <div className="flex items-center justify-center py-16 text-gray-500">Cargando morosidad por día...</div>
                    ) : datosMorosidadPorDia && datosMorosidadPorDia.length > 0 ? (
                      <ChartWithDateRangeSlider data={datosMorosidadPorDia} dataKey="fecha" chartHeight={400}>
                        {(filteredData) => (
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={filteredData} margin={{ top: 14, right: 24, left: 12, bottom: 14 }}>
                              <CartesianGrid {...chartCartesianGrid} />
                              <XAxis dataKey="dia" angle={-45} textAnchor="end" tick={chartAxisTick} height={80} />
                              <YAxis tick={chartAxisTick} tickFormatter={(value) => `$${value >= 1000 ? (value / 1000).toFixed(1) + 'K' : value}`} label={{ value: 'Morosidad (USD)', angle: -90, position: 'insideLeft', style: { fill: '#374151', fontSize: 13 } }} />
                              <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [formatCurrency(value), 'Morosidad']} labelFormatter={(label, payload) => payload?.[0]?.payload?.fecha ? `Fecha: ${payload[0].payload.fecha}` : label} />
                              <Legend {...chartLegendStyle} />
                              <Bar dataKey="morosidad" fill="#ef4444" name="Morosidad" radius={[4, 4, 0, 0]} maxBarSize={48} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        )}
                      </ChartWithDateRangeSlider>
                    ) : (
                      <div className="flex items-center justify-center py-16 text-gray-500">No hay datos de morosidad por día para el período seleccionado</div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

          </div>
        ) : null}

        {/* GRÁFICOS: BANDAS DE $200 USD Y COBRANZA PLANIFICADA VS REAL */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* GRÁFICO DE BANDAS DE $200 USD */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            >
              <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white h-full flex flex-col">
                <CardHeader className="bg-gradient-to-r from-indigo-50/90 to-purple-50/90 border-b border-gray-200/80 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-indigo-600" />
                      <span>Distribución por Bandas de $200 USD</span>
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="rangos" />
                      <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                        {getRangoFechasLabelGrafico('rangos')}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  {datosBandas200 && datosBandas200.length > 0 ? (
                  <ChartWithDateRangeSlider data={datosBandas200} dataKey="categoriaFormateada" chartHeight={450}>
                    {(filteredData) => (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={filteredData} layout="vertical" margin={{ top: 14, right: 24, left: 120, bottom: 24 }}>
                          <CartesianGrid {...chartCartesianGrid} />
                          <XAxis type="number" domain={[0, 'dataMax']} tick={chartAxisTick} tickFormatter={(value) => value.toLocaleString('es-EC')} label={{ value: 'Cantidad de Préstamos', position: 'insideBottom', offset: -10, style: { textAnchor: 'middle', fill: '#374151', fontSize: 13, fontWeight: 600 } }} allowDecimals={false} />
                          <YAxis type="category" dataKey="categoriaFormateada" width={115} tick={{ fontSize: 11, fill: '#4b5563', fontWeight: 500 }} interval={0} tickLine={false} />
                          <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [`${value.toLocaleString('es-EC')} préstamos`, 'Cantidad']} labelFormatter={(label) => `Banda: ${label}`} cursor={{ fill: 'rgba(99, 102, 241, 0.08)' }} />
                          <Legend {...chartLegendStyle} />
                          <Bar dataKey="cantidad" radius={[0, 6, 6, 0]} name="Cantidad de Préstamos">
                            {filteredData.map((entry, index) => {
                              const maxCant = Math.max(...filteredData.map(d => d.cantidad))
                              const intensity = maxCant > 0 ? entry.cantidad / maxCant : 0
                              const opacity = 0.6 + (intensity * 0.4)
                              return <Cell key={`cell-${index}`} fill={`rgba(99, 102, 241, ${opacity})`} />
                            })}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </ChartWithDateRangeSlider>
                  ) : (
                    <div className="flex items-center justify-center py-16 text-gray-500">No hay datos para mostrar</div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

        </div>

        {/* GRÁFICOS DE MOROSIDAD */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Composición de Morosidad */}
          <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="h-full"
            >
              <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white h-full flex flex-col">
                <CardHeader className="bg-gradient-to-r from-red-50/90 to-rose-50/90 border-b border-gray-200/80 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-red-600" />
                      <span>Composición de Morosidad</span>
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="composicion-morosidad" />
                      <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                        {getRangoFechasLabelGrafico('composicion-morosidad')}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  {datosComposicionMorosidad?.puntos?.length ? (
                  <ChartWithDateRangeSlider data={datosComposicionMorosidad.puntos} dataKey="categoria" chartHeight={400}>
                    {(filteredData) => (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={filteredData} margin={{ top: 12, right: 24, left: 12, bottom: 12 }}>
                          <CartesianGrid {...chartCartesianGrid} />
                          <XAxis dataKey="categoria" tick={chartAxisTick} />
                          <YAxis tick={chartAxisTick} />
                          <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} />
                          <Legend {...chartLegendStyle} />
                          <Bar dataKey="monto" fill="#ef4444" name="Monto en Morosidad" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </ChartWithDateRangeSlider>
                  ) : (
                    <div className="flex items-center justify-center py-16 text-gray-500">No hay datos para mostrar</div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

          {/* Morosidad por Analista - Red tela de araña: cuotas vencidas y dólares vencidos por analista */}
          <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
              className="h-full lg:col-span-2"
            >
              <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white h-full flex flex-col">
                <CardHeader className="bg-gradient-to-r from-orange-50/90 to-amber-50/90 border-b border-gray-200/80 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <Users className="h-5 w-5 text-orange-600" />
                      <span>Morosidad por Analista</span>
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="morosidad-analista" />
                      <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                        {getRangoFechasLabelGrafico('morosidad-analista')}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  {loadingMorosidadAnalista ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">Cargando...</div>
                  ) : datosMorosidadAnalista && datosMorosidadAnalista.length > 0 ? (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* Red tela de araña: cuántas cuotas vencidas por analista */}
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 text-center">Cuotas vencidas por analista</h4>
                        <ResponsiveContainer width="100%" height={320}>
                          <RadarChart data={datosMorosidadAnalista} margin={{ top: 16, right: 24, left: 24, bottom: 16 }}>
                            <PolarGrid stroke="#e5e7eb" />
                            <PolarAngleAxis dataKey="analista" tick={{ fontSize: 11 }} />
                            <PolarRadiusAxis angle={90} tick={{ fontSize: 10 }} />
                            <Radar name="Cuotas vencidas" dataKey="cantidad_cuotas_vencidas" stroke="#f97316" fill="#f97316" fillOpacity={0.5} />
                            <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [value.toLocaleString('es-EC'), 'Cuotas vencidas']} labelFormatter={(label) => `Analista: ${label}`} />
                            <Legend />
                          </RadarChart>
                        </ResponsiveContainer>
                      </div>
                      {/* Red tela de araña: dólares vencidos por analista */}
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 text-center">Dólares vencidos por analista</h4>
                        <ResponsiveContainer width="100%" height={320}>
                          <RadarChart data={datosMorosidadAnalista} margin={{ top: 16, right: 24, left: 24, bottom: 16 }}>
                            <PolarGrid stroke="#e5e7eb" />
                            <PolarAngleAxis dataKey="analista" tick={{ fontSize: 11 }} />
                            <PolarRadiusAxis angle={90} tick={{ fontSize: 10 }} tickFormatter={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`} />
                            <Radar name="Dólares vencidos" dataKey="monto_vencido" stroke="#ea580c" fill="#ea580c" fillOpacity={0.5} />
                            <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [formatCurrency(value), 'Dólares vencidos']} labelFormatter={(label) => `Analista: ${label}`} />
                            <Legend />
                          </RadarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center py-16 text-gray-500">No hay datos para mostrar</div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
        </div>

      </div>
    </div>
  )
}

export default DashboardMenu
