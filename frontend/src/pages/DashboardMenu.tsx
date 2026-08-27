import { useState, useMemo, useEffect, useLayoutEffect } from 'react'

import { motion } from 'framer-motion'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  BarChart3,
  ChevronRight,
  Filter,
  AlertTriangle,
  Shield,
  PieChart,
  LineChart,
  Database,
  RefreshCw,
  Info,
  XCircle,
  X,
  Settings,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'

import { Button } from '../components/ui/button'

import { Badge } from '../components/ui/badge'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'

import { useSimpleAuth } from '../store/simpleAuthStore'

import { formatCurrency } from '../utils'

import { apiClient } from '../services/api'

import {
  DASHBOARD_MENU_CACHE_TTL_MS,
  DASHBOARD_MENU_QUERY_OPTIONS,
  dashboardMenuCacheKey,
  hasWarmDashboardMenuCache,
  invalidateDashboardMenuCache,
  peekDashboardMenuCache,
  peekDashboardMenuCacheMeta,
  peekDashboardMenuCacheStale,
  putDashboardMenuCache,
} from '../services/dashboardMenuCache'

import { toast } from 'sonner'

import {
  useDashboardFiltros,
  type DashboardFiltros,
} from '../hooks/useDashboardFiltros'

import {
  DASHBOARD_STAGGER,
  useStaggeredEnable,
} from '../hooks/useStaggeredEnable'

import { getPeriodoEtiqueta, PERIODOS_VALORES } from '../constants/dashboard'

import type {
  OpcionesFiltrosResponse,
  DashboardAdminResponse,
  CobranzasSemanalesResponse,
  EvolucionMensualItem,
  PagosIngresadosPorDiaResponse,
  ResumenCobranzasMensualResponse,
  CobranzasPorBancoMensualResponse,
} from '../types/dashboard'

import { DashboardFiltrosPanel } from '../components/dashboard/DashboardFiltrosPanel'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { ChartWithDateRangeSlider } from '../components/dashboard/ChartWithDateRangeSlider'

import {
  CobranzasAtrasoDeudaCharts,
  COBRANZAS_ATRASO_DEUDA_QUERY_KEY,
} from '../components/dashboard/CobranzasAtrasoDeudaCharts'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
} from 'recharts'

// Submenús eliminados: financiamiento, cuotas, cobranza, analisis, pagos

export function DashboardMenu() {
  const { user } = useSimpleAuth()

  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const queryClient = useQueryClient()

  useEffect(() => {
    const run = async () => {
      try {
        await queryClient.prefetchQuery({
          queryKey: ['dashboard-financiamiento-inicial', {}],
          queryFn: async () =>
            apiClient.get(
              '/api/v1/dashboard/financiamiento-inicial?meses_tendencia=12'
            ),
          staleTime: DASHBOARD_MENU_CACHE_TTL_MS,
        })
      } catch {
        /* prefetch opcional */
      }
    }
    void run()
  }, [queryClient])

  useLayoutEffect(() => {
    const main = document.querySelector('main.flex-1.overflow-auto')
    if (main instanceof HTMLElement) main.scrollTop = 0
  }, [])

  const [filtros, setFiltros] = useState<DashboardFiltros>({})

  const [periodo, setPeriodo] = useState('ultimos_12_meses') // Por defecto últimos 12 meses para que los gráficos muestren datos recientes

  /** Período por gráfico: cada gráfico puede usar el general o uno propio. Key = id del gráfico, value = día|semana|mes|año o '' = usar general */

  const [periodoPorGrafico, setPeriodoPorGrafico] = useState<
    Record<string, string>
  >({})

  const {
    construirParams,
    construirFiltrosObject,
    tieneFiltrosActivos,
    cantidadFiltrosActivos,
  } = useDashboardFiltros(filtros)

  /** Si ya hay caché de módulo o RQ, no retrasar gráficos secundarios al volver. */
  const skipStagger =
    hasWarmDashboardMenuCache() ||
    queryClient
      .getQueriesData({ queryKey: ['dashboard-menu'] })
      .some(([, d]) => d != null)

  const enableSecondaryCharts = useStaggeredEnable(
    DASHBOARD_STAGGER.secondary,
    skipStagger
  )
  const enableTertiaryCharts = useStaggeredEnable(
    DASHBOARD_STAGGER.tertiary,
    skipStagger
  )

  /** Período efectivo para un gráfico: el del gráfico si está definido, si no el general */

  const getPeriodoGrafico = (chartId: string) =>
    periodoPorGrafico[chartId] || periodo

  const setPeriodoGrafico = (chartId: string, value: string) => {
    setPeriodoPorGrafico(prev =>
      value ? { ...prev, [chartId]: value } : { ...prev, [chartId]: '' }
    )
  }

  // Así. OPTIMIZACIÓN PRIORIDAD 1: Carga por batches con priorización

  // Batch 1: CRÍTICO - Opciones de filtros y KPIs principales (carga inmediata)

  const opcionesCacheKey = dashboardMenuCacheKey(['opciones-filtros'])
  const opcionesCached =
    peekDashboardMenuCache<OpcionesFiltrosResponse>(opcionesCacheKey) ??
    peekDashboardMenuCacheStale<OpcionesFiltrosResponse>(opcionesCacheKey)
  const opcionesMeta = peekDashboardMenuCacheMeta(opcionesCacheKey)

  const {
    data: opcionesFiltros,
    isLoading: loadingOpcionesFiltros,
    isError: errorOpcionesFiltros,
  } = useQuery({
    queryKey: ['opciones-filtros'],

    queryFn: async (): Promise<OpcionesFiltrosResponse> => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      const data = response as OpcionesFiltrosResponse
      putDashboardMenuCache(opcionesCacheKey, data)
      return data
    },

    initialData: opcionesCached ?? undefined,
    initialDataUpdatedAt: opcionesMeta?.storedAt,

    ...DASHBOARD_MENU_QUERY_OPTIONS,
  })

  // Batch 2: IMPORTANTE - Dashboard admin (gráfico principal). Siempre con período que incluya 2025 si hay datos.

  const periodoEvolucion =
    getPeriodoGrafico('evolucion') || periodo || 'ultimos_12_meses'

  const adminCacheKey = dashboardMenuCacheKey([
    'dashboard-menu',
    periodoEvolucion,
    filtros,
  ])
  const adminCached =
    peekDashboardMenuCache<DashboardAdminResponse>(adminCacheKey) ??
    peekDashboardMenuCacheStale<DashboardAdminResponse>(adminCacheKey)
  const adminMeta = peekDashboardMenuCacheMeta(adminCacheKey)

  const {
    data: datosDashboard,
    isLoading: loadingDashboardRaw,
    isError: errorDashboardAdmin,
  } = useQuery({
    queryKey: ['dashboard-menu', periodoEvolucion, JSON.stringify(filtros)],

    queryFn: async (): Promise<DashboardAdminResponse> => {
      const obj = construirFiltrosObject(periodoEvolucion)

      const params = new URLSearchParams()

      Object.entries(obj).forEach(([key, value]) => {
        if (value != null && value !== '') params.append(key, String(value))
      })

      if (!params.has('periodo') && periodoEvolucion)
        params.append('periodo', periodoEvolucion)

      const queryString = params.toString()

      const response = await apiClient.get(
        `/api/v1/dashboard/admin${queryString ? `?${queryString}` : ''}`,
        { timeout: 60000 }
      )

      const data = response as DashboardAdminResponse
      putDashboardMenuCache(adminCacheKey, data)
      return data
    },

    initialData: adminCached ?? undefined,
    initialDataUpdatedAt: adminMeta?.storedAt,

    ...DASHBOARD_MENU_QUERY_OPTIONS,

    enabled: true,
  })

  /** Skeleton solo sin datos; con caché se pinta al instante. */
  const loadingDashboard = loadingDashboardRaw && !datosDashboard

  // Batch 3: Gráficos secundarios rápidos. Período por gráfico; filtros (fecha_inicio/fecha_fin) se envían siempre.

  const periodoCobranzasSemanales = getPeriodoGrafico('cobranzas-semanales')

  const cobranzasCacheKey = dashboardMenuCacheKey([
    'cobranzas-semanales',
    periodoCobranzasSemanales,
    filtros,
  ])
  const cobranzasCached =
    peekDashboardMenuCache<CobranzasSemanalesResponse>(cobranzasCacheKey) ??
    peekDashboardMenuCacheStale<CobranzasSemanalesResponse>(cobranzasCacheKey)
  const cobranzasMeta = peekDashboardMenuCacheMeta(cobranzasCacheKey)

  const {
    data: datosCobranzasSemanales,
    isLoading: loadingCobranzasSemanalesRaw,
  } = useQuery({
    queryKey: [
      'cobranzas-semanales',
      periodoCobranzasSemanales,
      JSON.stringify(filtros),
    ],

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

      const data = response as CobranzasSemanalesResponse
      putDashboardMenuCache(cobranzasCacheKey, data)
      return data
    },

    initialData: cobranzasCached ?? undefined,
    initialDataUpdatedAt: cobranzasMeta?.storedAt,

    ...DASHBOARD_MENU_QUERY_OPTIONS,

    enabled: enableSecondaryCharts,
  })

  const loadingCobranzasSemanales =
    loadingCobranzasSemanalesRaw && !datosCobranzasSemanales

  const PAGOS_POR_BANCO_DIAS = 31

  const pagosBancoCacheKey = dashboardMenuCacheKey([
    'pagos-ingresados-por-dia',
    PAGOS_POR_BANCO_DIAS,
  ])
  const pagosBancoCached =
    peekDashboardMenuCache<PagosIngresadosPorDiaResponse>(pagosBancoCacheKey) ??
    peekDashboardMenuCacheStale<PagosIngresadosPorDiaResponse>(
      pagosBancoCacheKey
    )
  const pagosBancoMeta = peekDashboardMenuCacheMeta(pagosBancoCacheKey)

  const {
    data: datosPagosPorBancoDia,
    isLoading: loadingPagosPorBancoDiaRaw,
    isError: errorPagosPorBancoDia,
  } = useQuery({
    queryKey: ['pagos-ingresados-por-dia', PAGOS_POR_BANCO_DIAS],
    queryFn: async (): Promise<PagosIngresadosPorDiaResponse> => {
      const params = new URLSearchParams({
        dias: String(PAGOS_POR_BANCO_DIAS),
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/pagos-ingresados-por-dia?${params.toString()}`,
        { timeout: 60000 }
      )
      const data = response as PagosIngresadosPorDiaResponse
      putDashboardMenuCache(pagosBancoCacheKey, data)
      return data
    },
    initialData: pagosBancoCached ?? undefined,
    initialDataUpdatedAt: pagosBancoMeta?.storedAt,
    ...DASHBOARD_MENU_QUERY_OPTIONS,
    enabled: enableSecondaryCharts,
  })

  const loadingPagosPorBancoDia =
    loadingPagosPorBancoDiaRaw && !datosPagosPorBancoDia

  const resumenCobranzasCacheKey = dashboardMenuCacheKey([
    'resumen-cobranzas-mensual',
    '2025-05',
  ])
  const resumenCobranzasCached =
    peekDashboardMenuCache<ResumenCobranzasMensualResponse>(
      resumenCobranzasCacheKey
    ) ??
    peekDashboardMenuCacheStale<ResumenCobranzasMensualResponse>(
      resumenCobranzasCacheKey
    )
  const resumenCobranzasMeta = peekDashboardMenuCacheMeta(
    resumenCobranzasCacheKey
  )

  const {
    data: datosResumenCobranzas,
    isLoading: loadingResumenCobranzasRaw,
  } = useQuery({
    queryKey: ['resumen-cobranzas-mensual', '2025-05'],
    queryFn: async (): Promise<ResumenCobranzasMensualResponse> => {
      const params = new URLSearchParams({ fecha_inicio: '2025-05-01' })
      const response = await apiClient.get(
        `/api/v1/dashboard/resumen-cobranzas-mensual?${params.toString()}`,
        { timeout: 60000 }
      )
      const data = response as ResumenCobranzasMensualResponse
      putDashboardMenuCache(resumenCobranzasCacheKey, data)
      return data
    },
    initialData: resumenCobranzasCached ?? undefined,
    initialDataUpdatedAt: resumenCobranzasMeta?.storedAt,
    ...DASHBOARD_MENU_QUERY_OPTIONS,
    enabled: true,
  })

  const loadingResumenCobranzas =
    loadingResumenCobranzasRaw && !datosResumenCobranzas

  const serieResumenCobranzas = useMemo(
    () => datosResumenCobranzas?.meses ?? [],
    [datosResumenCobranzas?.meses]
  )

  const mesesPagoResumen = useMemo(
    () => datosResumenCobranzas?.meses_pago ?? [],
    [datosResumenCobranzas?.meses_pago]
  )

  const cobranzasBancoCacheKey = dashboardMenuCacheKey([
    'cobranzas-por-banco-mensual',
    '2025-05',
  ])
  const cobranzasBancoCached =
    peekDashboardMenuCache<CobranzasPorBancoMensualResponse>(
      cobranzasBancoCacheKey
    ) ??
    peekDashboardMenuCacheStale<CobranzasPorBancoMensualResponse>(
      cobranzasBancoCacheKey
    )
  const cobranzasBancoMeta = peekDashboardMenuCacheMeta(cobranzasBancoCacheKey)

  const {
    data: datosCobranzasPorBancoMes,
    isLoading: loadingCobranzasPorBancoMesRaw,
    isError: errorCobranzasPorBancoMes,
  } = useQuery({
    queryKey: ['cobranzas-por-banco-mensual', '2025-05'],
    queryFn: async (): Promise<CobranzasPorBancoMensualResponse> => {
      const params = new URLSearchParams({ fecha_inicio: '2025-05-01' })
      const response = await apiClient.get(
        `/api/v1/dashboard/cobranzas-por-banco-mensual?${params.toString()}`,
        { timeout: 60000 }
      )
      const data = response as CobranzasPorBancoMensualResponse
      putDashboardMenuCache(cobranzasBancoCacheKey, data)
      return data
    },
    initialData: cobranzasBancoCached ?? undefined,
    initialDataUpdatedAt: cobranzasBancoMeta?.storedAt,
    ...DASHBOARD_MENU_QUERY_OPTIONS,
    enabled: enableSecondaryCharts,
  })

  const loadingCobranzasPorBancoMes =
    loadingCobranzasPorBancoMesRaw && !datosCobranzasPorBancoMes

  const serieCobranzasPorBancoMes = useMemo(
    () => datosCobranzasPorBancoMes?.meses ?? [],
    [datosCobranzasPorBancoMes?.meses]
  )

  const categoriasCobranzasPorBancoMes = useMemo(
    () =>
      datosCobranzasPorBancoMes?.categorias?.length
        ? datosCobranzasPorBancoMes.categorias
        : ['Mercantil', 'BNC', 'Binance', 'Zelle', 'BNV', 'Recibos', 'Otros'],
    [datosCobranzasPorBancoMes?.categorias]
  )

  /** Colores por mes de cobro (apilado); el pendiente usa sólido aparte. */
  const COLORES_MES_COBRO = [
    '#0ea5e9',
    '#8b5cf6',
    '#ec4899',
    '#14b8a6',
    '#f97316',
    '#6366f1',
    '#84cc16',
    '#06b6d4',
    '#eab308',
    '#a855f7',
    '#22c55e',
    '#3b82f6',
  ] as const
  const COLOR_POR_COBRAR = '#64748b'

  const [isRefreshing, setIsRefreshing] = useState(false)

  // Mostrar toast cuando falla la carga del gráfico principal (auditoría: no fallar en silencio)

  useEffect(() => {
    if (errorDashboardAdmin) {
      toast.error(
        'No se pudo cargar el gráfico de evolución mensual. Intenta de nuevo o recarga la página.'
      )
    }
  }, [errorDashboardAdmin])

  // NOTA: No necesitamos invalidar queries manualmente aquí

  // React Query detecta automáticamente los cambios en queryKey (que incluye JSON.stringify(filtros))

  // y refetch automáticamente cuando cambian los filtros o el período

  const handleRefresh = async () => {
    setIsRefreshing(true)

    try {
      invalidateDashboardMenuCache()

      // Invalidar y refrescar solo las queries usadas por esta página (auditoría: alinear con queryKeys reales)

      await queryClient.invalidateQueries({
        queryKey: ['opciones-filtros'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['dashboard-menu'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['cobranzas-semanales'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: [COBRANZAS_ATRASO_DEUDA_QUERY_KEY],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['pagos-ingresados-por-dia'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['resumen-cobranzas-mensual'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['cobranzas-por-banco-mensual'],
        exact: false,
      })

      // Refrescar todas las queries activas del dashboard

      await queryClient.refetchQueries({
        queryKey: ['opciones-filtros'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['dashboard-menu'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['cobranzas-semanales'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: [COBRANZAS_ATRASO_DEUDA_QUERY_KEY],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['pagos-ingresados-por-dia'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['resumen-cobranzas-mensual'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['cobranzas-por-banco-mensual'],
        exact: false,
      })

      toast.success('Datos actualizados correctamente')
    } catch (error) {
      toast.error('Error al actualizar los datos. Intenta de nuevo.')
    } finally {
      setIsRefreshing(false)
    }
  }

  const evolucionMensual = useMemo(() => {
    const raw = datosDashboard?.evolucion_mensual ?? []
    let acumProgramadas = 0
    let acumCobros = 0

    return raw.map((e: EvolucionMensualItem) => {
      const cobrado = e.cobrado ?? 0
      const pagos_atrasos = e.pagos_atrasos ?? 0
      const pagos_anticipados = e.pagos_anticipados ?? 0
      const pagos_no_conciliados_a_tiempo = e.pagos_no_conciliados_a_tiempo ?? 0
      const pagos_no_conciliados_atrasados =
        e.pagos_no_conciliados_atrasados ?? 0
      /** Solo cuotas (mes + anticipos); sin pendientes de conciliar */
      const cuotas_a_tiempo = cobrado + pagos_anticipados
      /**
       * Cartera vencida y pagada: atrasos de cuotas + todos los pendientes
       * de conciliar (a tiempo y atrasados).
       */
      const cartera_vencida_pagada =
        pagos_atrasos +
        pagos_no_conciliados_a_tiempo +
        pagos_no_conciliados_atrasados
      const cobros = cuotas_a_tiempo + cartera_vencida_pagada

      acumProgramadas += e.cartera ?? 0
      acumCobros += cobros

      return {
        ...e,
        cobrado,
        pagos_atrasos,
        pagos_anticipados,
        pagos_no_conciliados_a_tiempo,
        pagos_no_conciliados_atrasados,
        cuotas_a_tiempo,
        cartera_vencida_pagada,
        cobros,
        /** Acumulados desde el primer mes de la serie hasta este mes */
        programadas_acumuladas: acumProgramadas,
        cobros_acumulados: acumCobros,
        cuentas_por_cobrar: acumProgramadas - acumCobros,
      }
    })
  }, [datosDashboard?.evolucion_mensual])

  const seriePagosPorBancoDia = useMemo(
    () => datosPagosPorBancoDia?.serie ?? [],
    [datosPagosPorBancoDia?.serie]
  )

  const categoriasPagosPorBanco = useMemo(
    () =>
      datosPagosPorBancoDia?.categorias?.length
        ? datosPagosPorBancoDia.categorias
        : ['Mercantil', 'BNC', 'Binance', 'Zelle', 'BNV', 'Recibos', 'Otros'],
    [datosPagosPorBancoDia?.categorias]
  )

  const etiquetaRangoPagosPorBanco = useMemo(() => {
    const s = seriePagosPorBancoDia
    if (!s.length) return '-'
    const a = s[0]?.fecha
    const b = s[s.length - 1]?.fecha
    if (!a || !b) return '-'
    return `${a} - ${b}`
  }, [seriePagosPorBancoDia])

  const COLORS_CONCESIONARIOS = [
    '#3b82f6',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#8b5cf6',
    '#06b6d4',
    '#ec4899',
    '#84cc16',
    '#f97316',
    '#6366f1',
  ]

  // Etiqueta del período activo (general)

  const rangoFechasLabel = useMemo(() => {
    const obj = construirFiltrosObject(periodo)

    if (obj.fecha_inicio && obj.fecha_fin) {
      const fIni = new Date(obj.fecha_inicio)

      const fFin = new Date(obj.fecha_fin)

      const opts: Intl.DateTimeFormatOptions = {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      }

      return `${fIni.toLocaleDateString('es-ES', opts)}  \u2013  ${fFin.toLocaleDateString('es-ES', opts)}`
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

      const opts: Intl.DateTimeFormatOptions = {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      }

      return `${fIni.toLocaleDateString('es-ES', opts)}  \u2013  ${fFin.toLocaleDateString('es-ES', opts)}`
    }

    return getPeriodoEtiqueta(p)
  }

  /** Selector de período por gráfico (dropdown para cada tarjeta) */

  const SelectorPeriodoGrafico = ({ chartId }: { chartId: string }) => (
    <Select
      value={periodoPorGrafico[chartId] || 'general'}
      onValueChange={v => setPeriodoGrafico(chartId, v === 'general' ? '' : v)}
    >
      <SelectTrigger className="h-8 w-[160px] border-gray-200 bg-white/80 text-xs">
        <SelectValue placeholder="Período" />
      </SelectTrigger>

      <SelectContent>
        <SelectItem value="general">General (barra superior)</SelectItem>

        {PERIODOS_VALORES.map(p => (
          <SelectItem key={p} value={p}>
            {getPeriodoEtiqueta(p)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )

  // Estilos de mayor calidad para todos los gráficos (tooltips, ejes, grid)

  const chartTooltipStyle = {
    contentStyle: {
      backgroundColor: 'rgba(255,255,255,0.98)',
      border: '1px solid #e5e7eb',
      borderRadius: '10px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
      padding: '14px 16px',
    },

    labelStyle: {
      fontWeight: 600,
      color: '#111827',
      marginBottom: 8,
      fontSize: 13,
    },

    itemStyle: { fontSize: '13px', color: '#4b5563' },
  }

  const chartCartesianGrid = {
    stroke: '#d1d5db',
    strokeDasharray: '4 4',
    strokeOpacity: 0.9,
  }

  const chartAxisTick = { fontSize: 13, fill: '#374151', fontWeight: 500 }

  const chartLegendStyle = {
    wrapperStyle: { paddingTop: 14 },
    iconType: 'rect' as const,
    iconSize: 12,
  }

  const coloresInstitucionPago: Record<string, string> = {
    Mercantil: '#1d4ed8',
    BNC: '#dc2626',
    Binance: '#eab308',
    Zelle: '#6d28d9',
    BNV: '#c026d3',
    Recibos: '#059669',
    Otros: '#64748b',
  }

  // Asegurar que el componente siempre renderice, incluso si hay errores

  // Si hay un error crítico en las queries principales, mostrar mensaje pero no bloquear

  const hasCriticalError = errorOpcionesFiltros || errorDashboardAdmin

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto space-y-8 px-4 py-8">
        {/* Header */}

        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <ModulePageHeader
            icon={BarChart3}
            title="Dashboard ejecutivo"
            description={
              <>
                <p>
                  Bienvenido,{' '}
                  <strong className="font-semibold">{userName}</strong>.
                  Monitoreo estratégico de KPIs y gráficos.
                </p>
              </>
            }
          />
        </motion.div>

        {/* Mensaje de error si hay problemas críticos */}

        {hasCriticalError && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg border border-yellow-200 bg-yellow-50 p-4"
          >
            <div className="flex items-center gap-2 text-yellow-800">
              <AlertTriangle className="h-5 w-5" />

              <p className="text-sm font-medium">
                Algunos datos no se pudieron cargar. Por favor, recarga la
                página o intenta más tarde.
              </p>
            </div>
          </motion.div>
        )}

        {/* Barra de filtros: período general (cada gráfico puede usar este o uno propio) */}

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <Card className="rounded-xl border border-gray-200/80 bg-white/95 shadow-md backdrop-blur-sm">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-cyan-600" />

                    <span className="text-sm font-semibold text-gray-700">
                      Filtros
                    </span>
                  </div>

                  <Select value={periodo} onValueChange={v => setPeriodo(v)}>
                    <SelectTrigger className="h-9 w-[180px] border-gray-200 bg-gray-50/80">
                      <SelectValue placeholder="Período" />
                    </SelectTrigger>

                    <SelectContent>
                      {PERIODOS_VALORES.map(p => (
                        <SelectItem key={p} value={p}>
                          {getPeriodoEtiqueta(p)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Badge
                    variant="secondary"
                    className="bg-gray-100 text-xs font-medium text-gray-600"
                  >
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

        {/* GRÁFICOS PRINCIPALES */}

        {loadingDashboard ? (
          <div className="space-y-6">
            <div className="h-[400px] animate-pulse rounded-xl bg-gray-100" />

            <div className="h-[400px] animate-pulse rounded-xl bg-gray-100" />
          </div>
        ) : errorDashboardAdmin ? (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 text-red-700">
                <AlertTriangle className="h-5 w-5 shrink-0" />

                <div>
                  <p className="font-medium">
                    Error al cargar el gráfico de evolución mensual
                  </p>

                  <p className="mt-1 text-sm">
                    Usa el botón «Actualizar» en la barra de filtros o recarga
                    la página.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ) : datosDashboard ? (
          <div className="space-y-6">
            {/* Aviso cuando no hay datos en los gráficos */}

            {!datosDashboard?.evolucion_mensual?.length ||
            datosDashboard.evolucion_mensual.every(
              (e: EvolucionMensualItem) =>
                !e.cartera &&
                !e.cobrado &&
                !(e.pagos_atrasos ?? 0) &&
                !(e.pagos_anticipados ?? 0) &&
                !(e.pagos_no_conciliados_a_tiempo ?? 0) &&
                !(e.pagos_no_conciliados_atrasados ?? 0)
            ) ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.15 }}
              >
                <Card className="border-amber-200 bg-amber-50/80">
                  <CardContent className="flex items-center gap-3 p-4">
                    <Info className="h-5 w-5 shrink-0 text-amber-600" />

                    <p className="text-sm text-amber-800">
                      Los gráficos están vacíos porque no hay datos en el
                      período. Cargue <strong>préstamos</strong> y{' '}
                      <strong>cuotas</strong> en el sistema para ver la
                      información. Puede usar la opción{' '}
                      <strong>últimos 12 meses</strong> si ya tiene datos de
                      meses anteriores.
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ) : null}

            {/* Resumen cobranzas: primero (mayo 2025 → hoy) */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-emerald-50/90 to-teal-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-emerald-600" />
                      <span>Resumen cobranzas</span>
                    </CardTitle>
                    <Badge
                      variant="secondary"
                      className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                    >
                      {datosResumenCobranzas?.fecha_inicio &&
                      datosResumenCobranzas?.fecha_fin
                        ? `${datosResumenCobranzas.fecha_inicio} – ${datosResumenCobranzas.fecha_fin}`
                        : 'May 2025 – hoy'}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-gray-600">
                    Cada columna es un mes de financiamiento. Los cobros se
                    apilan por el mes en que se pagaron; el tramo sólido es lo
                    que aún falta por cobrar.
                  </p>
                </CardHeader>
                <CardContent className="p-6 pt-4">
                  {loadingResumenCobranzas ? (
                    <div className="flex h-[320px] items-center justify-center text-sm text-gray-500">
                      Cargando resumen…
                    </div>
                  ) : serieResumenCobranzas.length > 0 ? (
                    <ChartWithDateRangeSlider
                      data={serieResumenCobranzas}
                      dataKey="mes"
                      chartHeight={360}
                    >
                      {filteredData => (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={filteredData}
                            margin={{
                              top: 12,
                              right: 20,
                              left: 12,
                              bottom: 12,
                            }}
                          >
                            <CartesianGrid {...chartCartesianGrid} />
                            <XAxis dataKey="mes" tick={chartAxisTick} />
                            <YAxis
                              tick={chartAxisTick}
                              tickFormatter={value => {
                                if (value >= 1000) {
                                  return `$${(value / 1000).toFixed(0)}K`
                                }
                                return `$${value}`
                              }}
                              label={{
                                value: 'Monto (USD)',
                                angle: -90,
                                position: 'insideLeft',
                                style: { fill: '#374151', fontSize: 13 },
                              }}
                            />
                            <Tooltip
                              {...chartTooltipStyle}
                              formatter={(value: number, name: string) => {
                                if (!value) return [null, null]
                                return [
                                  formatCurrency(Number(value) || 0),
                                  name,
                                ]
                              }}
                            />
                            <Legend {...chartLegendStyle} />
                            {mesesPagoResumen.map((mp, idx) => (
                              <Bar
                                key={mp.stack_key}
                                dataKey={mp.stack_key}
                                name={mp.label}
                                stackId="cohorte"
                                fill={
                                  COLORES_MES_COBRO[
                                    idx % COLORES_MES_COBRO.length
                                  ]
                                }
                              />
                            ))}
                            <Bar
                              dataKey="por_cobrar"
                              name="Por cobrar"
                              stackId="cohorte"
                              fill={COLOR_POR_COBRAR}
                              radius={[4, 4, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </ChartWithDateRangeSlider>
                  ) : (
                    <div className="flex h-[200px] items-center justify-center text-sm text-gray-500">
                      Sin datos de financiamiento/cobranzas en el rango.
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Gráfico de Evolución Mensual */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-cyan-50/90 to-blue-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <LineChart className="h-5 w-5 text-cyan-600" />

                      <span>Evolución Mensual</span>
                    </CardTitle>

                    <div className="flex flex-wrap items-center gap-2">
                      <SelectorPeriodoGrafico chartId="evolucion" />

                      <Badge
                        variant="secondary"
                        className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                      >
                        {getRangoFechasLabelGrafico('evolucion')}
                      </Badge>

                      {datosDashboard?.evolucion_origen === 'demo' && (
                        <Badge
                          variant="outline"
                          className="border-amber-300 bg-amber-50 text-xs font-medium text-amber-700"
                        >
                          Datos de ejemplo
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-6 pt-4">
                  {evolucionMensual.length > 0 ? (
                    <ChartWithDateRangeSlider
                      data={evolucionMensual}
                      dataKey="mes"
                      chartHeight={320}
                    >
                      {filteredData => (
                        <ResponsiveContainer width="100%" height="100%">
                          <ComposedChart
                            data={filteredData}
                            margin={{
                              top: 12,
                              right: 20,
                              left: 12,
                              bottom: 12,
                            }}
                          >
                            <CartesianGrid {...chartCartesianGrid} />

                            <XAxis dataKey="mes" tick={chartAxisTick} />

                            <YAxis
                              tick={chartAxisTick}
                              tickFormatter={value => {
                                if (value >= 1000) {
                                  return `$${(value / 1000).toFixed(0)}K`
                                }

                                return `$${value}`
                              }}
                              label={{
                                value: 'Monto (USD)',
                                angle: -90,
                                position: 'insideLeft',
                                style: { fill: '#374151', fontSize: 13 },
                              }}
                            />

                            <Tooltip
                              content={({ active, payload, label }) => {
                                if (!active || !payload?.length) return null
                                const row = payload[0]?.payload as {
                                  cartera?: number
                                  cuotas_a_tiempo?: number
                                  cartera_vencida_pagada?: number
                                  cobros?: number
                                  programadas_acumuladas?: number
                                  cobros_acumulados?: number
                                  cuentas_por_cobrar?: number
                                }
                                if (!row) return null
                                const programadasMes = row.cartera ?? 0
                                const cuotasATiempo = row.cuotas_a_tiempo ?? 0
                                const carteraVencida =
                                  row.cartera_vencida_pagada ?? 0
                                const cobrosMes =
                                  row.cobros ?? cuotasATiempo + carteraVencida
                                const progAcum = row.programadas_acumuladas ?? 0
                                const cobrosAcum = row.cobros_acumulados ?? 0
                                const cxc =
                                  row.cuentas_por_cobrar ??
                                  progAcum - cobrosAcum
                                const rows: {
                                  color: string
                                  label: string
                                  value: number
                                  sign?: '+' | '-' | '='
                                  indent?: boolean
                                  section?: string
                                }[] = [
                                  {
                                    color: '#3b82f6',
                                    label: 'Cuotas programadas',
                                    value: programadasMes,
                                    sign: '+',
                                    section: 'mes',
                                  },
                                  {
                                    color: '#059669',
                                    label: 'Cobros (total del mes)',
                                    value: cobrosMes,
                                    sign: '=',
                                    section: 'mes',
                                  },
                                  {
                                    color: '#10b981',
                                    label: 'Cuotas cobradas a tiempo',
                                    value: cuotasATiempo,
                                    sign: '+',
                                    indent: true,
                                    section: 'mes',
                                  },
                                  {
                                    color: '#f97316',
                                    label: 'Cartera vencida y pagada',
                                    value: carteraVencida,
                                    sign: '+',
                                    indent: true,
                                    section: 'mes',
                                  },
                                  {
                                    color: '#3b82f6',
                                    label: 'Cuotas programadas (acumuladas)',
                                    value: progAcum,
                                    sign: '+',
                                    section: 'cxc',
                                  },
                                  {
                                    color: '#059669',
                                    label: 'Cobros acumulados (todos)',
                                    value: cobrosAcum,
                                    sign: '-',
                                    section: 'cxc',
                                  },
                                  {
                                    color: '#ef4444',
                                    label: 'Cuentas por Cobrar',
                                    value: cxc,
                                    sign: '=',
                                    section: 'cxc',
                                  },
                                ]
                                return (
                                  <div style={chartTooltipStyle.contentStyle}>
                                    <p style={chartTooltipStyle.labelStyle}>
                                      {label}
                                    </p>
                                    <ul className="m-0 list-none space-y-1.5 p-0">
                                      {rows.map((r, idx) => (
                                        <li
                                          key={`${r.section}-${r.sign}-${r.label}-${idx}`}
                                          className={`flex items-center justify-between gap-4 text-[13px] ${
                                            r.indent ? 'pl-3' : ''
                                          } ${
                                            r.section === 'cxc' &&
                                            r.sign === '+'
                                              ? 'mt-2 border-t border-gray-200 pt-2'
                                              : ''
                                          }`}
                                          style={{ color: '#4b5563' }}
                                        >
                                          <span className="flex items-center gap-2">
                                            <span
                                              className="inline-flex w-4 shrink-0 justify-center font-bold tabular-nums"
                                              style={{ color: r.color }}
                                            >
                                              {r.sign}
                                            </span>
                                            {r.label}
                                          </span>
                                          <span className="font-semibold tabular-nums text-gray-900">
                                            {formatCurrency(r.value)}
                                          </span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )
                              }}
                            />

                            <Legend {...chartLegendStyle} />

                            <Bar
                              stackId="programado"
                              dataKey="cartera"
                              fill="#3b82f6"
                              name="Cuotas programadas"
                              radius={[4, 4, 0, 0]}
                            />

                            <Bar
                              stackId="cobros"
                              dataKey="cuotas_a_tiempo"
                              fill="#10b981"
                              name="Cuotas cobradas a tiempo"
                              radius={[0, 0, 0, 0]}
                            />

                            <Bar
                              stackId="cobros"
                              dataKey="cartera_vencida_pagada"
                              fill="#f97316"
                              name="Cartera vencida y pagada"
                              radius={[4, 4, 0, 0]}
                            />
                          </ComposedChart>
                        </ResponsiveContainer>
                      )}
                    </ChartWithDateRangeSlider>
                  ) : (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      No hay datos para el período seleccionado
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
                    </div>
        ) : null}

        {/* 2. Cobro diario por banco (Mercantil, BNC, Binance, …) */}
        {enableSecondaryCharts ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.32 }}
            className="mt-6"
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
              <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-emerald-50/90 to-teal-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-emerald-600" />
                      <span>Cobro diario por banco</span>
                    </CardTitle>
                    <p className="mt-1 text-xs font-normal text-slate-500">
                      Hoy y 30 días atrás. Cada barra son los pagos de ese día
                      (USD), clasificados por banco: Mercantil, BNC, Binance,
                      BNV, Recibos y Otros.
                    </p>
                  </div>
                    <Badge
                      variant="secondary"
                      className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                    >
                    {etiquetaRangoPagosPorBanco}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-6 pt-4">
                {loadingPagosPorBancoDia ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      Cargando…
                    </div>
                ) : errorPagosPorBancoDia ? (
                    <div className="flex items-center justify-center py-16 text-red-600">
                    No se pudo cargar el cobro diario por banco
                    </div>
                ) : seriePagosPorBancoDia.length > 0 ? (
                    <ChartWithDateRangeSlider
                    data={seriePagosPorBancoDia}
                      dataKey="dia"
                      chartHeight={360}
                    >
                      {filteredData => (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={filteredData}
                            margin={{
                              top: 8,
                              right: 16,
                              left: 8,
                              bottom: 12,
                            }}
                          >
                            <CartesianGrid {...chartCartesianGrid} />
                            <XAxis
                              dataKey="dia"
                              tick={chartAxisTick}
                              interval="preserveStartEnd"
                              minTickGap={16}
                            />
                            <YAxis
                              tick={chartAxisTick}
                              width={52}
                              tickFormatter={value => {
                                if (value >= 1000) {
                                  return `$${(value / 1000).toFixed(0)}K`
                                }
                                return `$${value}`
                              }}
                              label={{
                                value: 'Monto (USD)',
                                angle: -90,
                                position: 'insideLeft',
                                style: { fill: '#374151', fontSize: 13 },
                              }}
                            />
                            <Tooltip
                              contentStyle={chartTooltipStyle.contentStyle}
                              labelStyle={chartTooltipStyle.labelStyle}
                              formatter={(value: number, name: string) => [
                                formatCurrency(
                                  typeof value === 'number'
                                    ? value
                                    : Number(value) || 0
                                ),
                                name,
                              ]}
                              labelFormatter={(_, payload) => {
                                const row = payload?.[0]?.payload as
                                  | { fecha?: string; monto?: number }
                                  | undefined
                                if (!row?.fecha) return ''
                                const total =
                                  typeof row.monto === 'number'
                                    ? ` · Total ${formatCurrency(row.monto)}`
                                    : ''
                                return `${row.fecha}${total}`
                              }}
                            />
                            <Legend {...chartLegendStyle} />
                          {categoriasPagosPorBanco.map((cat, idx) => (
                              <Bar
                                key={cat}
                                dataKey={cat}
                                name={cat}
                                stackId="institucion"
                                fill={coloresInstitucionPago[cat] || '#94a3b8'}
                                radius={
                                idx === categoriasPagosPorBanco.length - 1
                                    ? [4, 4, 0, 0]
                                    : [0, 0, 0, 0]
                                }
                              />
                            ))}
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </ChartWithDateRangeSlider>
                  ) : (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                    No hay pagos por banco en hoy ni en los 30 días previos
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
        ) : null}

        {/* 4. Cobranzas por Banco origen (mensual, apilado por banco) */}
        {enableSecondaryCharts ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.36 }}
            className="mt-6"
          >
            <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
              <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-sky-50/90 to-indigo-50/90 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-sky-600" />
                      <span>Cobranzas por Banco origen</span>
                    </CardTitle>
                    <p className="mt-1 text-xs font-normal text-slate-500">
                      Por mes de cobro (fecha de pago). Cada columna es el total
                      del mes en USD, descompuesto por banco: Mercantil, BNC,
                      Binance, Zelle, BNV, Recibos y Otros.
                    </p>
                  </div>
                  <Badge
                    variant="secondary"
                    className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                  >
                    {datosCobranzasPorBancoMes?.fecha_inicio &&
                    datosCobranzasPorBancoMes?.fecha_fin
                      ? `${datosCobranzasPorBancoMes.fecha_inicio} → ${datosCobranzasPorBancoMes.fecha_fin}`
                      : 'Desde may 2025'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-6 pt-4">
                {loadingCobranzasPorBancoMes ? (
                  <div className="flex items-center justify-center py-16 text-gray-500">
                    Cargando…
                  </div>
                ) : errorCobranzasPorBancoMes ? (
                  <div className="flex items-center justify-center py-16 text-red-600">
                    No se pudo cargar cobranzas por banco origen
                  </div>
                ) : serieCobranzasPorBancoMes.length > 0 ? (
                  <ChartWithDateRangeSlider
                    data={serieCobranzasPorBancoMes}
                    dataKey="mes"
                    chartHeight={360}
                  >
                    {filteredData => (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={filteredData}
                          margin={{
                            top: 8,
                            right: 16,
                            left: 8,
                            bottom: 12,
                          }}
                        >
                          <CartesianGrid {...chartCartesianGrid} />
                          <XAxis dataKey="mes" tick={chartAxisTick} />
                          <YAxis
                            tick={chartAxisTick}
                            width={52}
                            tickFormatter={value => {
                              if (value >= 1000) {
                                return `$${(value / 1000).toFixed(0)}K`
                              }
                              return `$${value}`
                            }}
                            label={{
                              value: 'Monto (USD)',
                              angle: -90,
                              position: 'insideLeft',
                              style: { fill: '#374151', fontSize: 13 },
                            }}
                          />
                          <Tooltip
                            contentStyle={chartTooltipStyle.contentStyle}
                            labelStyle={chartTooltipStyle.labelStyle}
                            formatter={(value: number, name: string) => [
                              formatCurrency(
                                typeof value === 'number'
                                  ? value
                                  : Number(value) || 0
                              ),
                              name,
                            ]}
                            labelFormatter={(_, payload) => {
                              const row = payload?.[0]?.payload as
                                | { mes?: string; monto?: number }
                                | undefined
                              if (!row?.mes) return ''
                              const total =
                                typeof row.monto === 'number'
                                  ? ` · Total ${formatCurrency(row.monto)}`
                                  : ''
                              return `${row.mes}${total}`
                            }}
                          />
                          <Legend {...chartLegendStyle} />
                          {categoriasCobranzasPorBancoMes.map((cat, idx) => (
                            <Bar
                              key={cat}
                              dataKey={cat}
                              name={cat}
                              stackId="banco"
                              fill={coloresInstitucionPago[cat] || '#94a3b8'}
                              radius={
                                idx ===
                                categoriasCobranzasPorBancoMes.length - 1
                                  ? [4, 4, 0, 0]
                                  : [0, 0, 0, 0]
                              }
                            />
                          ))}
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </ChartWithDateRangeSlider>
                ) : (
                  <div className="flex items-center justify-center py-16 text-gray-500">
                    No hay cobranzas por banco en el período
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ) : null}

        <CobranzasAtrasoDeudaCharts enabled={enableTertiaryCharts} />

        {/* Cantidad de pagos realizados por mes */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.28 }}
          className="mt-6"
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
            <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-indigo-50/90 to-slate-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                  <BarChart3 className="h-5 w-5 text-indigo-600" />

                  <span>Cantidad de pagos por mes</span>
                    </CardTitle>

                <div className="flex items-center gap-2">
                  <SelectorPeriodoGrafico chartId="evolucion" />

                    <Badge
                      variant="secondary"
                      className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                    >
                    {getRangoFechasLabelGrafico('evolucion')}
                    </Badge>
                </div>
                  </div>
                </CardHeader>

                <CardContent className="p-6 pt-4">
              {loadingDashboard ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                  Cargando cantidad de pagos...
                    </div>
              ) : evolucionMensual.length > 0 ? (
                    <ChartWithDateRangeSlider
                  data={evolucionMensual}
                  dataKey="mes"
                  chartHeight={320}
                    >
                      {filteredData => (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={filteredData}
                            margin={{
                          top: 12,
                          right: 20,
                          left: 12,
                              bottom: 12,
                            }}
                          >
                            <CartesianGrid {...chartCartesianGrid} />

                        <XAxis dataKey="mes" tick={chartAxisTick} />

                            <YAxis
                              tick={chartAxisTick}
                          allowDecimals={false}
                              label={{
                            value: 'Cantidad',
                                angle: -90,
                                position: 'insideLeft',
                                style: { fill: '#374151', fontSize: 13 },
                              }}
                            />

                            <Tooltip
                              contentStyle={chartTooltipStyle.contentStyle}
                              labelStyle={chartTooltipStyle.labelStyle}
                          formatter={(value: number) => [
                            Number(value).toLocaleString('es-ES'),
                            'Pagos realizados',
                          ]}
                            />

                            <Legend {...chartLegendStyle} />

                        <Bar
                          dataKey="cantidad_pagos"
                          fill="#6366f1"
                          name="Pagos realizados"
                          radius={[4, 4, 0, 0]}
                        />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </ChartWithDateRangeSlider>
                  ) : (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                  No hay datos para el período seleccionado
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

      </div>
    </div>
  )
}

export default DashboardMenu
