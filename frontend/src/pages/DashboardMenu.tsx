import { useState, useMemo, useEffect } from 'react'
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
  PrestamosPorModeloResponse,
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
  // Los KPIs siempre reflejan solo el mes actual (ej. febrero) - independiente del período de los gráficos
  const mesActualKey = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
  const { data: kpisPrincipales, isLoading: loadingKPIs, isError: errorKPIs, refetch } = useQuery({
    queryKey: ['kpis-principales-menu', 'mes', mesActualKey, JSON.stringify(filtros)],
    queryFn: async (): Promise<KpisPrincipalesResponse> => {
      const params = construirFiltrosObject('mes')
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
  const { data: datosDashboard, isLoading: loadingDashboard, isError: errorDashboardAdmin } = useQuery({
    queryKey: ['dashboard-menu', periodoEvolucion, JSON.stringify(filtros)],
    queryFn: async (): Promise<DashboardAdminResponse> => {
      const obj = construirFiltrosObject(periodoEvolucion)
      const params = new URLSearchParams()
      Object.entries(obj).forEach(([key, value]) => {
        if (value != null && value !== '') params.append(key, String(value))
      })
      if (!params.has('periodo') && periodoEvolucion) params.append('periodo', periodoEvolucion)
      const queryString = params.toString()
      const response = await apiClient.get(`/api/v1/dashboard/admin${queryString ? `?${queryString}` : ''}`, { timeout: 60000 })
      return response as DashboardAdminResponse
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
      const queryParams = new URLSearchParams()
      queryParams.append('dias', String(diasMorosidad))
      // No enviar fecha_inicio/fecha_fin: el backend siempre usa hoy y hacia atrás
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

  const { data: datosPrestamosPorModelo, isLoading: loadingPrestamosPorModelo } = useQuery({
    queryKey: ['prestamos-por-modelo', periodoRangos, JSON.stringify(filtros)],
    queryFn: async (): Promise<PrestamosPorModeloResponse> => {
      const params = construirFiltrosObject(periodoRangos)
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/prestamos-por-modelo?${queryParams.toString()}`
      )
      return response as PrestamosPorModeloResponse
    },
    staleTime: 4 * 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    enabled: true,
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

  const { data: datosMontoProgramadoSemana, isLoading: loadingMontoProgramadoSemana } = useQuery({
    queryKey: ['monto-programado-proxima-semana'],
    queryFn: async () => {
      const response = await apiClient.get<{ dias: { fecha: string; dia: string; monto_programado: number }[] }>(
        '/api/v1/dashboard/monto-programado-proxima-semana'
      )
      return response.dias ?? []
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    enabled: true,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)

  // Mostrar toast cuando falla la carga del gráfico principal (auditoría: no fallar en silencio)
  useEffect(() => {
    if (errorDashboardAdmin) {
      toast.error('No se pudo cargar el gráfico de evolución mensual. Intenta de nuevo o recarga la página.')
    }
  }, [errorDashboardAdmin])

  // NOTA: No necesitamos invalidar queries manualmente aquí
  // React Query detecta automáticamente los cambios en queryKey (que incluye JSON.stringify(filtros))
  // y refetch automáticamente cuando cambian los filtros o el período

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      // Invalidar y refrescar solo las queries usadas por esta página (auditoría: alinear con queryKeys reales)
      await queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['morosidad-por-dia'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['financiamiento-rangos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['composicion-morosidad'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['cobranzas-semanales'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['morosidad-analista'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['monto-programado-proxima-semana'], exact: false })

      // Refrescar todas las queries activas del dashboard
      await queryClient.refetchQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['dashboard-menu'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['morosidad-por-dia'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['financiamiento-rangos'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['composicion-morosidad'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['cobranzas-semanales'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['morosidad-analista'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['monto-programado-proxima-semana'], exact: false })

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

  // Bandas desde backend: $0-$200 ... $1000-$1200, $1200-$1400, Más de $1400 (cantidad de préstamos por banda)
  const datosBandas200 = useMemo(() => {
    try {
      if (!datosFinanciamientoRangos?.rangos || datosFinanciamientoRangos.rangos.length === 0) {
        return []
      }
      // Orden descendente (mayor banda arriba): Más de $1400, $1200-$1400, $1000-$1200, ...
      const orden = ['Más de $1,400', '$1,200 - $1,400', '$1,000 - $1,200', '$800 - $1,000', '$600 - $800', '$400 - $600', '$200 - $400', '$0 - $200']
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

  // Asegurar que el componente siempre renderice, incluso si hay errores
  // Si hay un error crítico en las queries principales, mostrar mensaje pero no bloquear
  const hasCriticalError = errorOpcionesFiltros || errorKPIs || errorDashboardAdmin
  
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
                  title="Préstamos (mensual)"
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
                  title="Créditos nuevos (mensual)"
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
                  title="Cuotas programadas (mensual)"
                  value={kpisPrincipales.cuotas_programadas?.valor_actual || 0}
                  subtitle={kpisPrincipales.porcentaje_cuotas_pagadas !== undefined
                    ? `% Cuotas pagadas en el mes: ${kpisPrincipales.porcentaje_cuotas_pagadas.toFixed(1)}%`
                    : undefined}
                  icon={FileText}
                  color="text-blue-600"
                  bgColor="bg-blue-100"
                  borderColor="border-blue-500"
                  format="currency"
                />
                <KpiCardLarge
                  title="Pago vencido (mensual)"
                  subtitle="Cuotas vencidas sin pagar (solo si ya pasó la fecha de vencimiento)"
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
        ) : errorDashboardAdmin ? (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 text-red-700">
                <AlertTriangle className="h-5 w-5 shrink-0" />
                <div>
                  <p className="font-medium">Error al cargar el gráfico de evolución mensual</p>
                  <p className="text-sm mt-1">Usa el botón «Actualizar» en la barra de filtros o recarga la página.</p>
                </div>
              </div>
            </CardContent>
          </Card>
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
                              <Bar dataKey="cartera" fill="#3b82f6" name="Pagos programados" radius={[4, 4, 0, 0]} />
                              <Bar dataKey="cobrado" fill="#10b981" name="Pagos conciliados" radius={[4, 4, 0, 0]} />
                              <Line type="monotone" dataKey="morosidad" stroke="#ef4444" strokeWidth={2} name="Pago vencido" dot={{ r: 4 }} />
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

            {/* Pago vencido por día - desde tabla cuotas */}
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
                        <span>Pago vencido por día</span>
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
                      <div className="flex items-center justify-center py-16 text-gray-500">Cargando pago vencido por día...</div>
                    ) : datosMorosidadPorDia && datosMorosidadPorDia.length > 0 ? (
                      <ChartWithDateRangeSlider data={datosMorosidadPorDia} dataKey="fecha" chartHeight={400}>
                        {(filteredData) => (
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={filteredData} margin={{ top: 14, right: 24, left: 12, bottom: 14 }}>
                              <CartesianGrid {...chartCartesianGrid} />
                              <XAxis dataKey="dia" angle={-45} textAnchor="end" tick={chartAxisTick} height={80} />
                              <YAxis tick={chartAxisTick} tickFormatter={(value) => `$${value >= 1000 ? (value / 1000).toFixed(1) + 'K' : value}`} label={{ value: 'Pago vencido (USD)', angle: -90, position: 'insideLeft', style: { fill: '#374151', fontSize: 13 } }} />
                              <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [formatCurrency(value), 'Pago vencido']} labelFormatter={(label, payload) => payload?.[0]?.payload?.fecha ? `Fecha: ${payload[0].payload.fecha}` : label} />
                              <Legend {...chartLegendStyle} />
                              <Bar dataKey="morosidad" fill="#ef4444" name="Pago vencido" radius={[4, 4, 0, 0]} maxBarSize={48} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        )}
                      </ChartWithDateRangeSlider>
                    ) : (
                      <div className="flex items-center justify-center py-16 text-gray-500">No hay datos de pago vencido por día para el período seleccionado</div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

            {/* Monto programado por día: hoy hasta una semana después */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.36 }}
              >
                <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white">
                  <CardHeader className="bg-gradient-to-r from-emerald-50/90 to-teal-50/90 border-b border-gray-200/80 pb-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                        <DollarSign className="h-5 w-5 text-emerald-600" />
                        <span>Monto programado por día</span>
                      </CardTitle>
                      <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                        Hoy hasta 1 semana
                      </Badge>
                    </div>
                    <CardDescription className="text-gray-600 text-sm">
                      Suma de monto_cuota (cuotas con vencimiento cada día) desde hoy hasta 7 días después
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6 pt-4">
                    {loadingMontoProgramadoSemana ? (
                      <div className="flex items-center justify-center py-16 text-gray-500">Cargando...</div>
                    ) : datosMontoProgramadoSemana && datosMontoProgramadoSemana.length > 0 ? (
                      <ResponsiveContainer width="100%" height={340}>
                        <BarChart data={datosMontoProgramadoSemana} margin={{ top: 14, right: 24, left: 12, bottom: 14 }}>
                          <CartesianGrid {...chartCartesianGrid} />
                          <XAxis dataKey="dia" angle={-35} textAnchor="end" tick={chartAxisTick} height={72} />
                          <YAxis tick={chartAxisTick} tickFormatter={(value) => `$${value >= 1000 ? (value / 1000).toFixed(1) + 'K' : value}`} label={{ value: 'Monto (USD)', angle: -90, position: 'insideLeft', style: { fill: '#374151', fontSize: 13 } }} />
                          <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [formatCurrency(value), 'Monto programado']} labelFormatter={(_, payload) => payload?.[0]?.payload?.fecha ? `Fecha: ${payload[0].payload.fecha}` : ''} />
                          <Legend {...chartLegendStyle} />
                          <Bar dataKey="monto_programado" name="Monto programado" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={56} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex items-center justify-center py-16 text-gray-500">No hay datos de monto programado para los próximos 7 días</div>
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
                          <XAxis type="number" domain={[600, 'auto']} tick={chartAxisTick} tickFormatter={(value) => value.toLocaleString('es-EC')} label={{ value: 'Cantidad de Préstamos', position: 'insideBottom', offset: -10, style: { textAnchor: 'middle', fill: '#374151', fontSize: 13, fontWeight: 600 } }} allowDecimals={false} />
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

          {/* Préstamos aprobados por modelo de vehículo (barras horizontales) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.42 }}
            className="h-full"
          >
            <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white h-full flex flex-col">
              <CardHeader className="bg-gradient-to-r from-violet-50/90 to-purple-50/90 border-b border-gray-200/80 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                    <BarChart3 className="h-5 w-5 text-violet-600" />
                    <span>Préstamos aprobados por modelo de vehículo</span>
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <SelectorPeriodoGrafico chartId="rangos" />
                    <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                      {getRangoFechasLabelGrafico('rangos')}
                    </Badge>
                    {filtros.modelo && filtros.modelo !== '__ALL__' && (
                      <Badge variant="outline" className="text-xs font-medium text-violet-600 border-violet-300 bg-violet-50">
                        Modelo: {filtros.modelo}
                      </Badge>
                    )}
                  </div>
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  Distribución en porcentaje (acumulado). Usa el filtro Modelo en la barra superior para filtrar por vehículo.
                </p>
              </CardHeader>
              <CardContent className="p-6 flex-1">
                {loadingPrestamosPorModelo ? (
                  <div className="flex items-center justify-center py-16 text-gray-500">Cargando...</div>
                ) : datosPrestamosPorModelo?.acumulado?.length ? (
                  (() => {
                    const acumulado = datosPrestamosPorModelo.acumulado
                    const total = acumulado.reduce((s, d) => s + d.cantidad_acumulada, 0)
                    const dataBarras = acumulado.map((d) => ({
                      modelo: d.modelo || 'Sin modelo',
                      cantidad: d.cantidad_acumulada,
                      porcentaje: total > 0 ? (d.cantidad_acumulada / total) * 100 : 0,
                    }))
                    const numItems = dataBarras.length
                    const chartHeight = Math.max(380, Math.min(620, numItems * 26))
                    return (
                      <ResponsiveContainer width="100%" height={chartHeight}>
                        <BarChart data={dataBarras} layout="vertical" margin={{ top: 12, right: 48, left: 16, bottom: 12 }} barCategoryGap="10%" barGap={4}>
                          <CartesianGrid {...chartCartesianGrid} horizontal={false} />
                          <XAxis
                            type="number"
                            domain={[0, 100]}
                            tickFormatter={(v) => `${v}%`}
                            tick={chartAxisTick}
                            axisLine={{ stroke: '#e5e7eb' }}
                            label={{ value: '% del total', position: 'insideBottom', offset: -8, style: { fill: '#6b7280', fontSize: 12 } }}
                          />
                          <YAxis
                            type="category"
                            dataKey="modelo"
                            width={140}
                            tick={{ fontSize: 11, fill: '#374151', fontWeight: 500 }}
                            interval={0}
                            tickLine={false}
                            axisLine={{ stroke: '#e5e7eb' }}
                            tickFormatter={(name) => (name && name.length > 22 ? `${name.slice(0, 20)}…` : name)}
                          />
                          <Tooltip
                            contentStyle={chartTooltipStyle.contentStyle}
                            labelStyle={chartTooltipStyle.labelStyle}
                            formatter={(value: number, _name: string, props: { payload?: { cantidad: number; porcentaje: number } }) => [
                              `${props.payload?.cantidad?.toLocaleString('es-EC') ?? value} préstamos (${(value ?? props.payload?.porcentaje ?? 0).toFixed(1)}%)`,
                              '% del total',
                            ]}
                            labelFormatter={(label) => `Modelo: ${label}`}
                            cursor={{ fill: 'rgba(99, 102, 241, 0.06)' }}
                          />
                          <Legend {...chartLegendStyle} />
                          <Bar dataKey="porcentaje" name="% del total" fill="#6366f1" radius={[0, 4, 4, 0]} maxBarSize={22} />
                        </BarChart>
                      </ResponsiveContainer>
                    )
                  })()
                ) : (
                  <div className="flex items-center justify-center py-16 text-gray-500">No hay datos para mostrar</div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* GRÁFICOS DE MOROSIDAD */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Composición de Pago vencido (monto en USD) */}
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
                      <span>Composición de Pago vencido (USD)</span>
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="composicion-morosidad" />
                      <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                        Al día de hoy
                      </Badge>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                  Cuotas vencidas sin pagar. 1-30 y 31-60 días = Vencido; 61-90 y 90+ días = Moroso (snapshot al día de hoy).
                </p>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  {datosComposicionMorosidad?.puntos?.length ? (
                  <ChartWithDateRangeSlider data={datosComposicionMorosidad.puntos} dataKey="categoria" chartHeight={400}>
                    {(filteredData) => (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={filteredData} margin={{ top: 12, right: 24, left: 12, bottom: 12 }}>
                          <CartesianGrid {...chartCartesianGrid} />
                          <XAxis dataKey="categoria" tick={chartAxisTick} />
                          <YAxis tick={chartAxisTick} tickFormatter={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`)} label={{ value: 'Monto (USD)', angle: -90, position: 'insideLeft', style: { fill: '#374151', fontSize: 12 } }} />
                          <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [typeof value === 'number' ? `$${value.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : value, 'Monto (USD)']} />
                          <Legend {...chartLegendStyle} />
                          <Bar dataKey="monto" fill="#ef4444" name="Monto en Pago vencido (USD)" radius={[4, 4, 0, 0]} />
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

          {/* Cantidad de préstamos en mora por rango de días */}
          <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.82 }}
              className="h-full"
            >
              <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white h-full flex flex-col">
                <CardHeader className="bg-gradient-to-r from-rose-50/90 to-red-50/90 border-b border-gray-200/80 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-rose-600" />
                      <span>Cantidad de préstamos con pago vencido</span>
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="composicion-morosidad" />
                      <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                        Al día de hoy
                      </Badge>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    Préstamos con cuotas vencidas sin pagar. 1-30 y 31-60 días = Vencido; 61-90 y 90+ días = Moroso (snapshot al día de hoy).
                  </p>
                </CardHeader>
                <CardContent className="p-6 flex-1">
                  {datosComposicionMorosidad?.puntos?.length ? (
                  <ChartWithDateRangeSlider data={datosComposicionMorosidad.puntos} dataKey="categoria" chartHeight={400}>
                    {(filteredData) => (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={filteredData} margin={{ top: 12, right: 24, left: 12, bottom: 12 }}>
                          <CartesianGrid {...chartCartesianGrid} />
                          <XAxis dataKey="categoria" tick={chartAxisTick} />
                          <YAxis tick={chartAxisTick} allowDecimals={false} label={{ value: 'Cantidad de préstamos', angle: -90, position: 'insideLeft', style: { fill: '#374151', fontSize: 12 } }} />
                          <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [typeof value === 'number' ? value.toLocaleString('es-EC') : value, 'Préstamos']} />
                          <Legend {...chartLegendStyle} />
                          <Bar dataKey="cantidad_prestamos" fill="#be123c" name="Cantidad de préstamos" radius={[4, 4, 0, 0]} />
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

        {/* Pago vencido por Analista: 1 gráfico por fila, bloques independientes */}
        <div className="flex flex-col gap-6 mt-6">
          {/* Fila 1: solo Cuotas vencidas por analista (radar) */}
          <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
              className="w-full"
            >
              <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white w-full">
                <CardHeader className="bg-gradient-to-r from-orange-50/90 to-amber-50/90 border-b border-gray-200/80 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <Users className="h-5 w-5 text-orange-600" />
                      <span>Pago vencido por Analista — Cuotas vencidas</span>
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="morosidad-analista" />
                      <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                        Al día de hoy
                      </Badge>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-1 px-6">Cuotas vencidas sin pagar (fecha_vencimiento &lt; hoy), snapshot actual por analista</p>
                </CardHeader>
                <CardContent className="p-6">
                  {loadingMorosidadAnalista ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">Cargando...</div>
                  ) : datosMorosidadAnalista && datosMorosidadAnalista.length > 0 ? (
                    <>
                      <h4 className="text-sm font-semibold text-gray-700 mb-3 text-center">Cuotas vencidas por analista</h4>
                      <ResponsiveContainer width="100%" height={400}>
                        <RadarChart data={datosMorosidadAnalista} margin={{ top: 24, right: 32, left: 32, bottom: 24 }} cx="50%" cy="50%" outerRadius="75%">
                          <PolarGrid stroke="#e5e7eb" strokeWidth={1} />
                          <PolarAngleAxis
                            dataKey="analista"
                            tick={{ fontSize: 11, fill: '#374151', fontWeight: 500 }}
                            tickFormatter={(name) => (name && name.length > 18 ? `${name.slice(0, 16)}…` : name)}
                          />
                          <PolarRadiusAxis angle={90} tick={{ fontSize: 11, fill: '#6b7280' }} domain={[0, 'auto']} />
                          <Radar name="Cuotas vencidas" dataKey="cantidad_cuotas_vencidas" stroke="#ea580c" strokeWidth={2} fill="#f97316" fillOpacity={0.4} />
                          <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [value.toLocaleString('es-EC'), 'Cuotas vencidas']} labelFormatter={(label) => `Analista: ${label}`} />
                          <Legend {...chartLegendStyle} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </>
                  ) : (
                    <div className="flex items-center justify-center py-16 text-gray-500">No hay datos para mostrar</div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

          {/* Fila 2: solo Dólares vencidos por analista (barras) */}
          <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.95 }}
              className="w-full"
            >
              <Card className="shadow-lg border border-gray-200/90 rounded-xl overflow-hidden bg-white w-full">
                <CardHeader className="bg-gradient-to-r from-amber-50/90 to-orange-50/90 border-b border-gray-200/80 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <DollarSign className="h-5 w-5 text-amber-600" />
                      <span>Pago vencido por Analista — Dólares vencidos</span>
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="morosidad-analista" />
                      <Badge variant="secondary" className="text-xs font-medium text-gray-600 bg-white/80 border border-gray-200">
                        Al día de hoy
                      </Badge>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-1 px-6">Suma de monto_cuota de cuotas vencidas (fecha_vencimiento &lt; hoy, sin pagar), snapshot actual por analista</p>
                </CardHeader>
                <CardContent className="p-6">
                  {loadingMorosidadAnalista ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">Cargando...</div>
                  ) : datosMorosidadAnalista && datosMorosidadAnalista.length > 0 ? (
                    <>
                      <h4 className="text-sm font-semibold text-gray-700 mb-1 text-center">Dólares vencidos por analista</h4>
                      <ResponsiveContainer width="100%" height={Math.max(380, Math.min(620, datosMorosidadAnalista.length * 28))}>
                        <BarChart data={datosMorosidadAnalista} layout="vertical" margin={{ top: 12, right: 32, left: 16, bottom: 12 }} barCategoryGap="12%">
                          <CartesianGrid {...chartCartesianGrid} horizontal={false} />
                          <XAxis type="number" tickFormatter={(v) => `$${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`} tick={chartAxisTick} axisLine={{ stroke: '#e5e7eb' }} />
                          <YAxis
                            type="category"
                            dataKey="analista"
                            width={200}
                            tick={{ fontSize: 12, fill: '#374151', fontWeight: 500 }}
                            interval={0}
                            tickLine={false}
                            axisLine={{ stroke: '#e5e7eb' }}
                            tickFormatter={(name) => (name && name.length > 24 ? `${name.slice(0, 22)}…` : name)}
                          />
                          <Tooltip contentStyle={chartTooltipStyle.contentStyle} labelStyle={chartTooltipStyle.labelStyle} formatter={(value: number) => [formatCurrency(value), 'Dólares vencidos']} labelFormatter={(label) => `Analista: ${label}`} cursor={{ fill: 'rgba(234, 88, 12, 0.06)' }} />
                          <Legend {...chartLegendStyle} />
                          <Bar dataKey="monto_vencido" name="Dólares vencidos" fill="#ea580c" radius={[0, 4, 4, 0]} maxBarSize={28} />
                        </BarChart>
                      </ResponsiveContainer>
                    </>
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
