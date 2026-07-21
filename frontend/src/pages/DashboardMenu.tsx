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
  DollarSign,
  Mail,
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '../components/ui/card'

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

import { toast } from 'sonner'

import {
  useDashboardFiltros,
  type DashboardFiltros,
} from '../hooks/useDashboardFiltros'

import {
  DASHBOARD_STAGGER,
  useStaggeredEnable,
} from '../hooks/useStaggeredEnable'

import {
  getPeriodoEtiqueta,
  PERIODOS_VALORES,
  PERIODO_DIA,
} from '../constants/dashboard'

import type {
  OpcionesFiltrosResponse,
  DashboardAdminResponse,
  CobranzasSemanalesResponse,
  EvolucionMensualItem,
  NotificacionesEnviosPorDiaResponse,
  PagosRealizadosMensualResponse,
} from '../types/dashboard'
import {
  finiquitoAdminResumenFlujoDiario,
  type FiniquitoFlujoDia,
  type FiniquitoFlujoResumenDiario,
} from '../services/finiquitoService'

import { DashboardFiltrosPanel } from '../components/dashboard/DashboardFiltrosPanel'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { ChartWithDateRangeSlider } from '../components/dashboard/ChartWithDateRangeSlider'

import {
  BarChart,
  Bar,
  LineChart as RechartsLineChart,
  Line,
  PieChart as RechartsPieChart,
  Pie,
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

function parseIsoDateLocal(s: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s).trim())

  if (!m) return null

  const y = Number(m[1])

  const mo = Number(m[2])

  const d = Number(m[3])

  if (!y || mo < 1 || mo > 12 || d < 1 || d > 31) return null

  return new Date(y, mo - 1, d)
}

/**
 * Deja solo puntos con fecha >= 5 de abril del año del último dato (calendario local).
 * Si no quedara ninguno, devuelve la serie original (evita gráfico vacío fuera de temporada).
 */
function serieNotificacionesEjeDesde5Abril<
  T extends { fecha: string; enviados: number },
>(serie: T[]): T[] {
  if (!serie.length) return serie

  let max: Date | null = null

  for (const row of serie) {
    const dt = parseIsoDateLocal(row.fecha)

    if (dt && (!max || dt.getTime() > max.getTime())) max = dt
  }

  if (!max) return serie

  const cutoff = new Date(max.getFullYear(), 3, 5)

  const out = serie.filter(row => {
    const dt = parseIsoDateLocal(row.fecha)

    return dt != null && dt >= cutoff
  })

  return out.length > 0 ? out : serie
}

/**
 * Deja solo puntos con fecha >= 20 de julio del año del último dato (calendario local).
 * Usado en «Cobranzas entre 5 y 59 días». Si no quedara ninguno, devuelve la serie original.
 */
function serieNotificacionesEjeDesde20Julio<
  T extends { fecha: string; enviados: number },
>(serie: T[]): T[] {
  if (!serie.length) return serie

  let max: Date | null = null

  for (const row of serie) {
    const dt = parseIsoDateLocal(row.fecha)

    if (dt && (!max || dt.getTime() > max.getTime())) max = dt
  }

  if (!max) return serie

  const cutoff = new Date(max.getFullYear(), 6, 20)

  const out = serie.filter(row => {
    const dt = parseIsoDateLocal(row.fecha)

    return dt != null && dt >= cutoff
  })

  return out.length > 0 ? out : serie
}

/**
 * Añade `tendencia`: regresión lineal por índice (0..n-1) sobre `enviados`.
 * Valores mostrados no negativos (conteo de correos). Con menos de 2 puntos, coincide con el dato.
 */
function notificacionesSerieConTendenciaLineal<T extends { enviados: number }>(
  serie: T[]
): Array<T & { tendencia: number }> {
  const n = serie.length

  if (n === 0) return []

  if (n === 1) {
    const y0 = Math.max(0, Number(serie[0].enviados) || 0)

    return [{ ...serie[0], tendencia: y0 }]
  }

  let sumX = 0

  let sumY = 0

  let sumXY = 0

  let sumXX = 0

  for (let i = 0; i < n; i++) {
    const x = i

    const y = Math.max(0, Number(serie[i].enviados) || 0)

    sumX += x

    sumY += y

    sumXY += x * y

    sumXX += x * x
  }

  const denom = n * sumXX - sumX * sumX

  let b = 0

  let a = sumY / n

  if (Math.abs(denom) > 1e-9) {
    b = (n * sumXY - sumX * sumY) / denom

    a = (sumY - b * sumX) / n
  }

  return serie.map((row, i) => ({
    ...row,

    tendencia: Math.max(0, a + b * i),
  }))
}

function diasVentanaFiniquito(periodo: string): number {
  if (periodo === PERIODO_DIA || periodo === 'dia') return 7
  if (periodo === 'semana') return 14
  if (periodo === 'mes') return 31
  if (periodo === 'año') return 180
  return 90
}

const FINIQUITO_GRAFICO_MAX_DIARIO = 50

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
          staleTime: 2 * 60 * 1000,
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

  const enableSecondaryCharts = useStaggeredEnable(DASHBOARD_STAGGER.secondary)
  const enableTertiaryCharts = useStaggeredEnable(DASHBOARD_STAGGER.tertiary)

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

  const {
    data: opcionesFiltros,
    isLoading: loadingOpcionesFiltros,
    isError: errorOpcionesFiltros,
  } = useQuery({
    queryKey: ['opciones-filtros'],

    queryFn: async (): Promise<OpcionesFiltrosResponse> => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')

      return response as OpcionesFiltrosResponse
    },

    staleTime: 30 * 60 * 1000, // 30 minutos - cambian muy poco

    refetchOnWindowFocus: false, // No recargar automáticamente

    // Prioridad máxima - carga inmediatamente
  })

  // Batch 2: IMPORTANTE - Dashboard admin (gráfico principal). Siempre con período que incluya 2025 si hay datos.

  const periodoEvolucion =
    getPeriodoGrafico('evolucion') || periodo || 'ultimos_12_meses'

  const {
    data: datosDashboard,
    isLoading: loadingDashboard,
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

      return response as DashboardAdminResponse
    },

    staleTime: 4 * 60 * 60 * 1000, // 4 h: backend actualiza caché a las 6:00, 13:00, 16:00

    retry: 1,

    refetchOnWindowFocus: false, // Evitar refetch al cambiar de pestaña (carga lenta)

    enabled: true,
  })

  const periodoPagosRealizados =
    getPeriodoGrafico('pagos-realizados') || periodo || 'ultimos_12_meses'

  const {
    data: datosPagosRealizados,
    isLoading: loadingPagosRealizados,
    isError: errorPagosRealizados,
  } = useQuery({
    queryKey: [
      'pagos-realizados-mensual',
      periodoPagosRealizados,
      JSON.stringify(filtros),
    ],
    queryFn: async (): Promise<PagosRealizadosMensualResponse> => {
      const obj = construirFiltrosObject(periodoPagosRealizados)
      const params = new URLSearchParams()
      Object.entries(obj).forEach(([key, value]) => {
        if (value != null && value !== '') params.append(key, String(value))
      })
      if (!params.has('periodo') && periodoPagosRealizados) {
        params.append('periodo', periodoPagosRealizados)
      }
      const queryString = params.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/pagos-realizados-mensual${
          queryString ? `?${queryString}` : ''
        }`,
        { timeout: 60000 }
      )
      return response as PagosRealizadosMensualResponse
    },
    staleTime: 15 * 60 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
    enabled: enableSecondaryCharts,
  })

  const seriePagosRealizados = useMemo(
    () => datosPagosRealizados?.series ?? [],
    [datosPagosRealizados?.series]
  )

  // Batch 3: Gráficos secundarios rápidos. Período por gráfico; filtros (fecha_inicio/fecha_fin) se envían siempre.

  const periodoCobranzasSemanales = getPeriodoGrafico('cobranzas-semanales')

  const {
    data: datosCobranzasSemanales,
    isLoading: loadingCobranzasSemanales,
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

      return response as CobranzasSemanalesResponse
    },

    staleTime: 15 * 60 * 1000,

    enabled: enableSecondaryCharts,

    refetchOnWindowFocus: false,
  })

  const NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS = 90
  const diasGraficoFlujoFiniquito = diasVentanaFiniquito(
    getPeriodoGrafico('finiquito-flujo')
  )

  const {
    data: datosNotificacionesPorDia,
    isLoading: loadingNotificacionesPorDia,
    isError: errorNotificacionesPorDia,
  } = useQuery({
    queryKey: [
      'notificaciones-envios-por-dia',
      'dias_1_retraso',
      NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS,
    ],

    queryFn: async (): Promise<NotificacionesEnviosPorDiaResponse> => {
      const params = new URLSearchParams({
        tipo_tab: 'dias_1_retraso',
        dias: String(NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS),
      })

      const response = await apiClient.get(
        `/api/v1/dashboard/notificaciones-envios-por-dia?${params.toString()}`,
        { timeout: 60000 }
      )

      return response as NotificacionesEnviosPorDiaResponse
    },

    staleTime: 5 * 60 * 1000,

    refetchOnWindowFocus: false,

    retry: 1,

    enabled: enableTertiaryCharts,
  })

  const {
    data: datosNotificacionesMenor60PorDia,
    isLoading: loadingNotificacionesMenor60PorDia,
    isError: errorNotificacionesMenor60PorDia,
  } = useQuery({
    queryKey: [
      'notificaciones-envios-por-dia',
      'dias_10_retraso',
      NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS,
    ],

    queryFn: async (): Promise<NotificacionesEnviosPorDiaResponse> => {
      const params = new URLSearchParams({
        tipo_tab: 'dias_10_retraso',
        dias: String(NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS),
      })

      const response = await apiClient.get(
        `/api/v1/dashboard/notificaciones-envios-por-dia?${params.toString()}`,
        { timeout: 60000 }
      )

      return response as NotificacionesEnviosPorDiaResponse
    },

    staleTime: 5 * 60 * 1000,

    refetchOnWindowFocus: false,

    retry: 1,

    enabled: enableTertiaryCharts,
  })

  const serieNotificacionesGrafico = useMemo(
    () =>
      serieNotificacionesEjeDesde5Abril(datosNotificacionesPorDia?.serie ?? []),
    [datosNotificacionesPorDia?.serie]
  )

  const serieNotificacionesMenor60Grafico = useMemo(
    () =>
      serieNotificacionesEjeDesde20Julio(
        datosNotificacionesMenor60PorDia?.serie ?? []
      ),
    [datosNotificacionesMenor60PorDia?.serie]
  )

  const { data: datosFlujoFiniquito, isLoading: loadingFlujoFiniquito } =
    useQuery({
      queryKey: ['finiquito-flujo-diario', diasGraficoFlujoFiniquito],
      queryFn: async (): Promise<FiniquitoFlujoResumenDiario> =>
        finiquitoAdminResumenFlujoDiario(undefined, diasGraficoFlujoFiniquito),
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
      enabled: enableTertiaryCharts,
    })

  const serieFlujoFiniquito = useMemo<FiniquitoFlujoDia[]>(
    () => datosFlujoFiniquito?.dias ?? [],
    [datosFlujoFiniquito?.dias]
  )

  const serieFlujoFiniquitoCapada = useMemo(
    () =>
      serieFlujoFiniquito.map(row => ({
        ...row,
        cantidad_ingresados: Math.min(
          FINIQUITO_GRAFICO_MAX_DIARIO,
          Number(row.cantidad_ingresados) || 0
        ),
        cantidad_revision: Math.min(
          FINIQUITO_GRAFICO_MAX_DIARIO,
          Number(row.cantidad_revision) || 0
        ),
        cantidad_terminados: Math.min(
          FINIQUITO_GRAFICO_MAX_DIARIO,
          Number(row.cantidad_terminados) || 0
        ),
      })),
    [serieFlujoFiniquito]
  )

  const serieNotificacionesConTendencia = useMemo(
    () => notificacionesSerieConTendenciaLineal(serieNotificacionesGrafico),
    [serieNotificacionesGrafico]
  )

  const serieNotificacionesMenor60ConTendencia = useMemo(
    () =>
      notificacionesSerieConTendenciaLineal(serieNotificacionesMenor60Grafico),
    [serieNotificacionesMenor60Grafico]
  )

  const etiquetaRangoNotificacionesEjeX = useMemo(() => {
    const s = serieNotificacionesGrafico

    if (!s.length) return `${NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d · Caracas`

    const a = s[0]?.fecha

    const b = s[s.length - 1]?.fecha

    if (a && b) return a === b ? `${a} · Caracas` : `${a} - ${b} · Caracas`

    return `${NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d · Caracas`
  }, [serieNotificacionesGrafico])

  const etiquetaRangoNotificacionesMenor60EjeX = useMemo(() => {
    const s = serieNotificacionesMenor60Grafico

    if (!s.length) return `${NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d · Caracas`

    const a = s[0]?.fecha

    const b = s[s.length - 1]?.fecha

    if (a && b) return a === b ? `${a} · Caracas` : `${a} - ${b} · Caracas`

    return `${NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d · Caracas`
  }, [serieNotificacionesMenor60Grafico])

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
      // Invalidar y refrescar solo las queries usadas por esta página (auditoría: alinear con queryKeys reales)

      await queryClient.invalidateQueries({
        queryKey: ['dashboard-menu'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['cobranzas-semanales'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['notificaciones-envios-por-dia'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['finiquito-flujo-diario'],
        exact: false,
      })

      // Refrescar todas las queries activas del dashboard

      await queryClient.refetchQueries({
        queryKey: ['dashboard-menu'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['cobranzas-semanales'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['notificaciones-envios-por-dia'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['finiquito-flujo-diario'],
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

                  <CardDescription className="mt-2 text-xs text-gray-600">
                    Incluye cuotas de cualquier estado de préstamo (APROBADO,
                    LIQUIDADO, DESISTIMIENTO, etc.). Barras del mes: programadas
                    vs cobros (a tiempo + cartera vencida y pagada).
                  </CardDescription>
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

            {/* Cantidad de pagos realizados por mes */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.28 }}
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

                  <CardDescription className="mt-2 text-xs text-gray-600">
                    Número de pagos registrados (tabla pagos) por mes de fecha
                    de pago. Incluye todos: cualquier estado del pago
                    (conciliado o no) y cualquier estado del préstamo
                    (APROBADO, LIQUIDADO, DESISTIMIENTO, etc.), también sin
                    préstamo asignado.
                  </CardDescription>
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

            {/* Pagos realizados por mes (conteo tabla pagos) */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.32 }}
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-violet-50/90 to-indigo-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-violet-600" />
                      <span>Pagos realizados por mes</span>
                    </CardTitle>

                    <div className="flex flex-wrap items-center gap-2">
                      <SelectorPeriodoGrafico chartId="pagos-realizados" />
                      <Badge
                        variant="secondary"
                        className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                      >
                        {getRangoFechasLabelGrafico('pagos-realizados')}
                      </Badge>
                    </div>
                  </div>

                  <CardDescription className="mt-2 text-xs text-gray-600">
                    Número de registros en pagos por mes de fecha de pago.
                    Incluye conciliados y no conciliados, y cualquier contexto
                    (APROBADO, finiquito/LIQUIDADO, DESISTIMIENTO, etc.).
                    Excluye anulados, duplicados y cancelados.
                  </CardDescription>
                </CardHeader>

                <CardContent className="p-6 pt-4">
                  {loadingPagosRealizados ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      Cargando pagos realizados...
                    </div>
                  ) : errorPagosRealizados ? (
                    <div className="flex items-center justify-center py-16 text-red-600">
                      No se pudo cargar el conteo de pagos
                    </div>
                  ) : seriePagosRealizados.length > 0 ? (
                    <ChartWithDateRangeSlider
                      data={seriePagosRealizados}
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
                                value: 'Cantidad de pagos',
                                angle: -90,
                                position: 'insideLeft',
                                style: { fill: '#374151', fontSize: 13 },
                              }}
                            />
                            <Tooltip
                              content={({ active, payload, label }) => {
                                if (!active || !payload?.length) return null
                                const row = payload[0]?.payload as {
                                  cantidad_pagos?: number
                                  monto_total?: number
                                }
                                if (!row) return null
                                return (
                                  <div style={chartTooltipStyle.contentStyle}>
                                    <p style={chartTooltipStyle.labelStyle}>
                                      {label}
                                    </p>
                                    <ul className="m-0 list-none space-y-1.5 p-0">
                                      <li
                                        className="flex items-center justify-between gap-4 text-[13px]"
                                        style={{ color: '#4b5563' }}
                                      >
                                        <span>Pagos realizados</span>
                                        <span className="font-semibold tabular-nums text-gray-900">
                                          {(
                                            row.cantidad_pagos ?? 0
                                          ).toLocaleString('es-ES')}
                                        </span>
                                      </li>
                                      <li
                                        className="flex items-center justify-between gap-4 text-[13px]"
                                        style={{ color: '#4b5563' }}
                                      >
                                        <span>Monto total (USD)</span>
                                        <span className="font-semibold tabular-nums text-gray-900">
                                          {formatCurrency(row.monto_total ?? 0)}
                                        </span>
                                      </li>
                                    </ul>
                                  </div>
                                )
                              }}
                            />
                            <Legend {...chartLegendStyle} />
                            <Bar
                              dataKey="cantidad_pagos"
                              fill="#7c3aed"
                              name="Pagos realizados"
                              radius={[4, 4, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </ChartWithDateRangeSlider>
                  ) : (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      No hay pagos en el período seleccionado
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Cobrados acumulados vs por cobrar */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-emerald-50/90 to-teal-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <DollarSign className="h-5 w-5 text-emerald-600" />

                      <span>Cobrados acumulados y por cobrar</span>
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

                  <CardDescription className="mt-2 text-xs text-gray-600">
                    Áreas acumuladas hasta cada mes: cobrados (todos) y por
                    cobrar (= programadas acumuladas − cobros acumulados). Mismo
                    período que Evolución Mensual.
                  </CardDescription>
                </CardHeader>

                <CardContent className="p-6 pt-4">
                  {loadingDashboard ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      Cargando acumulados...
                    </div>
                  ) : evolucionMensual.length > 0 ? (
                    <ChartWithDateRangeSlider
                      data={evolucionMensual}
                      dataKey="mes"
                      chartHeight={400}
                    >
                      {filteredData => (
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart
                            data={filteredData}
                            margin={{
                              top: 14,
                              right: 24,
                              left: 12,
                              bottom: 14,
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
                              contentStyle={chartTooltipStyle.contentStyle}
                              labelStyle={chartTooltipStyle.labelStyle}
                              formatter={(value: number, name: string) => [
                                formatCurrency(value),
                                name,
                              ]}
                            />

                            <Legend {...chartLegendStyle} />

                            <Area
                              type="monotone"
                              stackId="acum"
                              dataKey="cobros_acumulados"
                              stroke="#059669"
                              fill="#10b981"
                              fillOpacity={0.55}
                              name="Cobrados acumulados"
                            />

                            <Area
                              type="monotone"
                              stackId="acum"
                              dataKey="cuentas_por_cobrar"
                              stroke="#d97706"
                              fill="#f59e0b"
                              fillOpacity={0.45}
                              name="Por cobrar"
                            />
                          </AreaChart>
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

        {/* Notificaciones por día */}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.32 }}
          className="mt-6"
          id="dashboard-notificaciones-dia"
        >
          <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
            <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-sky-50/90 to-indigo-50/90 pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                  <Mail className="h-5 w-5 shrink-0 text-sky-600" />

                  <span className="leading-tight">
                    Notificaciones por día (día siguiente al vencimiento)
                  </span>
                </CardTitle>

                <Badge
                  variant="secondary"
                  className="shrink-0 border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                >
                  {etiquetaRangoNotificacionesEjeX}
                </Badge>
              </div>

              <CardDescription className="mt-2 text-xs text-gray-600">
                Historial{' '}
                <code className="rounded bg-gray-100 px-1 py-0.5 text-[11px]">
                  dias_1_retraso
                </code>
                : correos aceptados por SMTP (enviados) por día. Eje X desde el{' '}
                <strong>5 de abril</strong> del año del último día con datos
                (muestra de {NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d recortada).
                Línea gris discontinua: <strong>tendencia</strong> (regresión
                lineal sobre la serie mostrada).
              </CardDescription>
            </CardHeader>

            <CardContent className="p-6 pt-4">
              {loadingNotificacionesPorDia ? (
                <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                  Cargando…
                </div>
              ) : errorNotificacionesPorDia ? (
                <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-red-700">
                  <AlertTriangle className="h-8 w-8" />

                  <p className="text-sm font-medium">
                    No se pudo cargar la tendencia.
                  </p>
                </div>
              ) : (datosNotificacionesPorDia?.serie?.length ?? 0) === 0 ? (
                <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                  Sin envíos en el período.
                </div>
              ) : (
                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height={320}>
                    <RechartsLineChart
                      data={serieNotificacionesConTendencia}
                      margin={{
                        top: 12,
                        right: 20,
                        left: 12,
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
                        allowDecimals={false}
                        width={40}
                        label={{
                          value: 'Enviados',
                          angle: -90,
                          position: 'insideLeft',
                          style: { fill: '#374151', fontSize: 13 },
                        }}
                      />

                      <Tooltip
                        contentStyle={chartTooltipStyle.contentStyle}
                        labelStyle={chartTooltipStyle.labelStyle}
                        formatter={(value: number, name: string) => {
                          const rounded =
                            typeof value === 'number'
                              ? Math.round(value * 100) / 100
                              : value

                          if (
                            name === 'Tendencia (regresión lineal)' ||
                            name === 'tendencia'
                          ) {
                            return [rounded, name]
                          }

                          return [rounded, 'Enviados (éxito SMTP)']
                        }}
                        labelFormatter={(_, payload) =>
                          payload?.[0]?.payload?.fecha
                            ? String(payload[0].payload.fecha)
                            : ''
                        }
                      />

                      <Legend {...chartLegendStyle} />

                      <Line
                        type="monotone"
                        dataKey="enviados"
                        name="Correos enviados (SMTP)"
                        stroke="#0ea5e9"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                      />

                      <Line
                        type="linear"
                        dataKey="tendencia"
                        name="Tendencia (regresión lineal)"
                        stroke="#64748b"
                        strokeWidth={2}
                        strokeDasharray="6 4"
                        dot={false}
                        isAnimationActive={false}
                      />
                    </RechartsLineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Notificaciones por día - menor a 60 días */}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.34 }}
          className="mt-6"
          id="dashboard-notificaciones-dia-menor-60"
        >
          <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
            <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-sky-50/90 to-indigo-50/90 pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                  <Mail className="h-5 w-5 shrink-0 text-sky-600" />

                  <span className="leading-tight">
                    Cobranzas entre 5 y 59 días
                  </span>
                </CardTitle>

                <Badge
                  variant="secondary"
                  className="shrink-0 border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                >
                  {etiquetaRangoNotificacionesMenor60EjeX}
                </Badge>
              </div>

              <CardDescription className="mt-2 text-xs text-gray-600">
                Cuenta filas del historial en BD (
                <code className="rounded bg-gray-100 px-1 py-0.5 text-[11px]">
                  envios_notificacion
                </code>
                /{' '}
                <code className="rounded bg-gray-100 px-1 py-0.5 text-[11px]">
                  dias_10_retraso
                </code>
                ), no el buzón de Gmail. Si un lote SMTP se cortó antes de
                persistir, Gmail puede tener cientos y esta gráfica pocos. Eje X
                desde el <strong>20 de julio</strong> del año del último día con
                datos (muestra de {NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d
                recortada). Línea gris discontinua: <strong>tendencia</strong>{' '}
                (regresión lineal sobre la serie mostrada).
              </CardDescription>
            </CardHeader>

            <CardContent className="p-6 pt-4">
              {loadingNotificacionesMenor60PorDia ? (
                <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                  Cargando…
                </div>
              ) : errorNotificacionesMenor60PorDia ? (
                <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-red-700">
                  <AlertTriangle className="h-8 w-8" />

                  <p className="text-sm font-medium">
                    No se pudo cargar la tendencia.
                  </p>
                </div>
              ) : (datosNotificacionesMenor60PorDia?.serie?.length ?? 0) ===
                0 ? (
                <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                  Sin envíos en el período.
                </div>
              ) : (
                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height={320}>
                    <RechartsLineChart
                      data={serieNotificacionesMenor60ConTendencia}
                      margin={{
                        top: 12,
                        right: 20,
                        left: 12,
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
                        allowDecimals={false}
                        width={40}
                        label={{
                          value: 'Enviados',
                          angle: -90,
                          position: 'insideLeft',
                          style: { fill: '#374151', fontSize: 13 },
                        }}
                      />

                      <Tooltip
                        contentStyle={chartTooltipStyle.contentStyle}
                        labelStyle={chartTooltipStyle.labelStyle}
                        formatter={(value: number, name: string) => {
                          const rounded =
                            typeof value === 'number'
                              ? Math.round(value * 100) / 100
                              : value

                          if (
                            name === 'Tendencia (regresión lineal)' ||
                            name === 'tendencia'
                          ) {
                            return [rounded, name]
                          }

                          return [rounded, 'Enviados (éxito SMTP)']
                        }}
                        labelFormatter={(_, payload) =>
                          payload?.[0]?.payload?.fecha
                            ? String(payload[0].payload.fecha)
                            : ''
                        }
                      />

                      <Legend {...chartLegendStyle} />

                      <Line
                        type="monotone"
                        dataKey="enviados"
                        name="Correos enviados (SMTP)"
                        stroke="#0ea5e9"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                      />

                      <Line
                        type="linear"
                        dataKey="tendencia"
                        name="Tendencia (regresión lineal)"
                        stroke="#64748b"
                        strokeWidth={2}
                        strokeDasharray="6 4"
                        dot={false}
                        isAnimationActive={false}
                      />
                    </RechartsLineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="mt-2"
        >
          <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
            <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-amber-50/80 to-emerald-50/80 pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                    <BarChart3 className="h-5 w-5 text-amber-600" />
                    <span>Flujo de finiquitos</span>
                  </CardTitle>
                  <CardDescription>
                    Bandeja principal, área de revisión y terminados.
                  </CardDescription>
                </div>

                <div className="flex items-center gap-2">
                  <SelectorPeriodoGrafico chartId="finiquito-flujo" />
                  <Badge
                    variant="secondary"
                    className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                  >
                    3 barras
                  </Badge>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-6 pt-4">
              {loadingFlujoFiniquito ? (
                <div className="flex items-center justify-center py-16 text-gray-500">
                  Cargando flujo de finiquitos...
                </div>
              ) : serieFlujoFiniquitoCapada.length > 0 ? (
                <ChartWithDateRangeSlider
                  data={serieFlujoFiniquitoCapada}
                  dataKey="fecha"
                  chartHeight={360}
                >
                  {filteredData => (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={filteredData}
                        margin={{ top: 14, right: 24, left: 12, bottom: 14 }}
                      >
                        <CartesianGrid {...chartCartesianGrid} />
                        <XAxis
                          dataKey="etiqueta"
                          tick={chartAxisTick}
                          minTickGap={18}
                        />
                        <YAxis
                          tick={chartAxisTick}
                          allowDecimals={false}
                          domain={[0, FINIQUITO_GRAFICO_MAX_DIARIO]}
                          label={{
                            value: 'Casos',
                            angle: -90,
                            position: 'insideLeft',
                            style: { fill: '#374151', fontSize: 13 },
                          }}
                        />
                        <Tooltip
                          contentStyle={chartTooltipStyle.contentStyle}
                          labelStyle={chartTooltipStyle.labelStyle}
                          cursor={{ fill: 'rgba(148, 163, 184, 0.12)' }}
                          formatter={(
                            value: number,
                            name: string,
                            item: any
                          ) => {
                            const original =
                              Number(item?.payload?.[item?.dataKey]) || 0
                            const shown = Number(value) || 0
                            return [
                              original > FINIQUITO_GRAFICO_MAX_DIARIO
                                ? `${shown} (real: ${original})`
                                : shown,
                              name,
                            ]
                          }}
                          labelFormatter={(_, payload) =>
                            payload?.[0]?.payload?.fecha || ''
                          }
                        />
                        <Legend {...chartLegendStyle} />
                        <Bar
                          dataKey="cantidad_ingresados"
                          fill="#1d4ed8"
                          name="Ingresados"
                          radius={[4, 4, 0, 0]}
                        />
                        <Bar
                          dataKey="cantidad_revision"
                          fill="#d97706"
                          name="Procesados"
                          radius={[4, 4, 0, 0]}
                        />
                        <Bar
                          dataKey="cantidad_terminados"
                          fill="#7c3aed"
                          name="Terminados"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </ChartWithDateRangeSlider>
              ) : (
                <div className="flex items-center justify-center py-16 text-gray-500">
                  No hay datos de flujo de finiquitos para el período
                  seleccionado
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
