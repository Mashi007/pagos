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

import { getPeriodoEtiqueta, PERIODOS_VALORES } from '../constants/dashboard'

import type {
  OpcionesFiltrosResponse,
  DashboardAdminResponse,
  CobranzasSemanalesResponse,
  EvolucionMensualItem,
  NotificacionesEnviosPorDiaResponse,
  Desempeno1CuotaStockResponse,
  Desempeno2CuotasStockResponse,
  PagosIngresadosPorDiaResponse,
} from '../types/dashboard'

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
  ComposedChart,
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
 * Añade `tendencia`: regresión lineal por índice (0..n-1) sobre `valueKey`.
 * Valores mostrados no negativos. Con menos de 2 puntos, coincide con el dato.
 */
function serieConTendenciaLineal<T extends object>(
  serie: T[],
  valueKey: keyof T
): Array<T & { tendencia: number }> {
  const n = serie.length

  if (n === 0) return []

  const yAt = (row: T) => Math.max(0, Number(row[valueKey]) || 0)

  if (n === 1) {
    return [{ ...serie[0], tendencia: yAt(serie[0]) }]
  }

  let sumX = 0

  let sumY = 0

  let sumXY = 0

  let sumXX = 0

  for (let i = 0; i < n; i++) {
    const x = i

    const y = yAt(serie[i])

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

function notificacionesSerieConTendenciaLineal<T extends { enviados: number }>(
  serie: T[]
): Array<T & { tendencia: number }> {
  return serieConTendenciaLineal(serie, 'enviados')
}

/** Eje Y comprimido al rango real de Inicio/Fin dia (sin inventar puntos). */
function dominioYDesempenoSegmento(
  serie: Array<{ notificaciones?: number; morosos?: number }>
): { domain: [number, number]; ticks: number[] } {
  const vals: number[] = []
  for (const row of serie) {
    const a = Number(row.notificaciones)
    const b = Number(row.morosos)
    if (Number.isFinite(a)) vals.push(a)
    if (Number.isFinite(b)) vals.push(b)
  }
  if (vals.length === 0) {
    return { domain: [0, 1], ticks: [0, 1] }
  }
  let lo = Math.min(...vals)
  let hi = Math.max(...vals)
  const span = hi - lo
  // Si Inicio y Fin estan muy cerca, ampliar un poco el marco para ver la brecha.
  const minSpan = Math.max(25, Math.round(((lo + hi) / 2) * 0.04))
  if (span < minSpan) {
    const mid = (lo + hi) / 2
    lo = mid - minSpan / 2
    hi = mid + minSpan / 2
  } else {
    const pad = Math.max(5, Math.ceil(span * 0.08))
    lo -= pad
    hi += pad
  }
  lo = Math.max(0, Math.floor(lo))
  hi = Math.ceil(hi)
  if (hi <= lo) hi = lo + 1
  const steps = 4
  const step = (hi - lo) / steps
  const ticks: number[] = []
  for (let i = 0; i <= steps; i++) {
    ticks.push(Math.round(lo + step * i))
  }
  ticks[0] = lo
  ticks[ticks.length - 1] = hi
  return { domain: [lo, hi], ticks }
}

/** Últimos N días de la serie diaria (visión dashboard). */
function serieUltimosNDias<T extends { fecha: string }>(
  serie: T[],
  n: number
): T[] {
  if (!serie.length || n <= 0) return serie
  return serie.length <= n ? serie : serie.slice(serie.length - n)
}

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

  const DESEMPENO_1_CUOTA_DIAS_VISION = 20
  const DESEMPENO_2_CUOTAS_DIAS_VISION = 20
  const PAGOS_INGRESADOS_POR_DIA_DIAS = 60

  const {
    data: datosPagosIngresadosPorDia,
    isLoading: loadingPagosIngresadosPorDia,
    isError: errorPagosIngresadosPorDia,
  } = useQuery({
    queryKey: ['pagos-ingresados-por-dia', PAGOS_INGRESADOS_POR_DIA_DIAS],

    queryFn: async (): Promise<PagosIngresadosPorDiaResponse> => {
      const params = new URLSearchParams({
        dias: String(PAGOS_INGRESADOS_POR_DIA_DIAS),
      })

      const response = await apiClient.get(
        `/api/v1/dashboard/pagos-ingresados-por-dia?${params.toString()}`,
        { timeout: 60000 }
      )

      return response as PagosIngresadosPorDiaResponse
    },

    staleTime: 5 * 60 * 1000,

    refetchOnWindowFocus: false,

    retry: 1,

    enabled: enableSecondaryCharts,
  })

  const {
    data: datosPagosBsIngresadosPorDia,
    isLoading: loadingPagosBsIngresadosPorDia,
    isError: errorPagosBsIngresadosPorDia,
  } = useQuery({
    queryKey: ['pagos-bs-ingresados-por-dia', PAGOS_INGRESADOS_POR_DIA_DIAS],

    queryFn: async (): Promise<PagosIngresadosPorDiaResponse> => {
      const params = new URLSearchParams({
        dias: String(PAGOS_INGRESADOS_POR_DIA_DIAS),
      })

      const response = await apiClient.get(
        `/api/v1/dashboard/pagos-bs-ingresados-por-dia?${params.toString()}`,
        { timeout: 60000 }
      )

      return response as PagosIngresadosPorDiaResponse
    },

    staleTime: 5 * 60 * 1000,

    refetchOnWindowFocus: false,

    retry: 1,

    enabled: enableSecondaryCharts,
  })

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
    data: datosDesempeno1CuotaStock,
    isLoading: loadingDesempeno1CuotaStock,
    isError: errorDesempeno1CuotaStock,
  } = useQuery({
    queryKey: ['desempeno-1-cuota-stock', DESEMPENO_1_CUOTA_DIAS_VISION],

    queryFn: async (): Promise<Desempeno1CuotaStockResponse> => {
      const params = new URLSearchParams({
        dias: String(DESEMPENO_1_CUOTA_DIAS_VISION),
      })

      const response = await apiClient.get(
        `/api/v1/dashboard/desempeno-1-cuota-stock?${params.toString()}`,
        { timeout: 120000 }
      )

      return response as Desempeno1CuotaStockResponse
    },

    staleTime: 5 * 60 * 1000,

    refetchOnWindowFocus: false,

    retry: 1,

    enabled: enableTertiaryCharts,
  })

  const {
    data: datosDesempeno2CuotasStock,
    isLoading: loadingDesempeno2CuotasStock,
    isError: errorDesempeno2CuotasStock,
  } = useQuery({
    queryKey: ['desempeno-2-cuotas-stock', DESEMPENO_2_CUOTAS_DIAS_VISION],

    queryFn: async (): Promise<Desempeno2CuotasStockResponse> => {
      const params = new URLSearchParams({
        dias: String(DESEMPENO_2_CUOTAS_DIAS_VISION),
      })

      const response = await apiClient.get(
        `/api/v1/dashboard/desempeno-2-cuotas-stock?${params.toString()}`,
        { timeout: 120000 }
      )

      return response as Desempeno2CuotasStockResponse
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

  const serieNotificacionesConTendencia = useMemo(
    () => notificacionesSerieConTendenciaLineal(serieNotificacionesGrafico),
    [serieNotificacionesGrafico]
  )

  const serieDesempeno1CuotaDiario = useMemo(
    () =>
      serieUltimosNDias(
        datosDesempeno1CuotaStock?.serie ?? [],
        DESEMPENO_1_CUOTA_DIAS_VISION
      ),
    [datosDesempeno1CuotaStock?.serie]
  )

  const serieDesempeno2CuotasDiario = useMemo(
    () =>
      serieUltimosNDias(
        datosDesempeno2CuotasStock?.serie ?? [],
        DESEMPENO_2_CUOTAS_DIAS_VISION
      ),
    [datosDesempeno2CuotasStock?.serie]
  )

  const ejeYDesempeno1Cuota = useMemo(
    () => dominioYDesempenoSegmento(serieDesempeno1CuotaDiario),
    [serieDesempeno1CuotaDiario]
  )

  const ejeYDesempeno2Cuotas = useMemo(
    () => dominioYDesempenoSegmento(serieDesempeno2CuotasDiario),
    [serieDesempeno2CuotasDiario]
  )

  const seriePagosIngresadosPorDia = useMemo(
    () => datosPagosIngresadosPorDia?.serie ?? [],
    [datosPagosIngresadosPorDia?.serie]
  )

  const categoriasPagosIngresados = useMemo(
    () =>
      datosPagosIngresadosPorDia?.categorias?.length
        ? datosPagosIngresadosPorDia.categorias
        : ['Mercantil', 'BNC', 'Binance', 'BNV', 'Recibos', 'Otros'],
    [datosPagosIngresadosPorDia?.categorias]
  )

  const etiquetaRangoPagosIngresados = useMemo(() => {
    const s = seriePagosIngresadosPorDia

    if (!s.length) return `Últimos ${PAGOS_INGRESADOS_POR_DIA_DIAS} d`

    const a = s[0]?.fecha

    const b = s[s.length - 1]?.fecha

    if (a && b) return a === b ? a : `${a} - ${b}`

    return `Últimos ${PAGOS_INGRESADOS_POR_DIA_DIAS} d`
  }, [seriePagosIngresadosPorDia])

  const seriePagosBsIngresadosPorDia = useMemo(
    () => datosPagosBsIngresadosPorDia?.serie ?? [],
    [datosPagosBsIngresadosPorDia?.serie]
  )

  const categoriasPagosBsIngresados = useMemo(
    () =>
      datosPagosBsIngresadosPorDia?.categorias?.length
        ? datosPagosBsIngresadosPorDia.categorias
        : ['Mercantil', 'BNC', 'Binance', 'BNV', 'Recibos', 'Otros'],
    [datosPagosBsIngresadosPorDia?.categorias]
  )

  const etiquetaRangoPagosBsIngresados = useMemo(() => {
    const s = seriePagosBsIngresadosPorDia
    if (!s.length) return '-'
    const a = s[0]?.fecha
    const b = s[s.length - 1]?.fecha
    if (!a || !b) return '-'
    return `${a} - ${b}`
  }, [seriePagosBsIngresadosPorDia])

  const etiquetaRangoNotificacionesEjeX = useMemo(() => {
    const s = serieNotificacionesGrafico

    if (!s.length) return `${NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d · Caracas`

    const a = s[0]?.fecha

    const b = s[s.length - 1]?.fecha

    if (a && b) return a === b ? `${a} · Caracas` : `${a} - ${b} · Caracas`

    return `${NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d · Caracas`
  }, [serieNotificacionesGrafico])

  const etiquetaRangoNotificacionesMenor60EjeX = useMemo(() => {
    const s = serieDesempeno1CuotaDiario
    if (!s.length) return `Últimos ${DESEMPENO_1_CUOTA_DIAS_VISION} d · Caracas`
    const a = s[0]?.fecha
    const b = s[s.length - 1]?.fecha
    if (a && b) return a === b ? `${a} · Caracas` : `${a} - ${b} · Caracas`
    return `Últimos ${DESEMPENO_1_CUOTA_DIAS_VISION} d · Caracas`
  }, [serieDesempeno1CuotaDiario])

  const etiquetaRangoDesempeno2Cuotas = useMemo(() => {
    const s = serieDesempeno2CuotasDiario
    if (!s.length)
      return `Últimos ${DESEMPENO_2_CUOTAS_DIAS_VISION} d · Caracas`
    const a = s[0]?.fecha
    const b = s[s.length - 1]?.fecha
    if (a && b) return a === b ? `${a} · Caracas` : `${a} - ${b} · Caracas`
    return `Últimos ${DESEMPENO_2_CUOTAS_DIAS_VISION} d · Caracas`
  }, [serieDesempeno2CuotasDiario])

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
        queryKey: ['desempeno-1-cuota-stock'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['desempeno-2-cuotas-stock'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['pagos-ingresados-por-dia'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['pagos-bs-ingresados-por-dia'],
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
        queryKey: ['desempeno-1-cuota-stock'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['desempeno-2-cuotas-stock'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['pagos-ingresados-por-dia'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['pagos-bs-ingresados-por-dia'],
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

  const coloresInstitucionPago: Record<string, string> = {
    Mercantil: '#1d4ed8',
    BNC: '#ea580c',
    Binance: '#ca8a04',
    BNV: '#7c3aed',
    Recibos: '#0891b2',
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
                    (conciliado o no) y cualquier estado del préstamo (APROBADO,
                    LIQUIDADO, DESISTIMIENTO, etc.), también sin préstamo
                    asignado.
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

            {/* Pagos ingresados por día (últimos 60 días) */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.29 }}
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-violet-50/90 to-indigo-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-violet-600" />

                      <span>Pagos ingresados por día</span>
                    </CardTitle>

                    <Badge
                      variant="secondary"
                      className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                    >
                      {etiquetaRangoPagosIngresados}
                    </Badge>
                  </div>

                  <CardDescription className="mt-2 text-xs text-gray-600">
                    Monto en USD (suma de monto_pagado) por día de fecha de
                    pago, apilado por institución (institucion_bancaria):
                    Mercantil, BNC, Binance, BNV, Recibos. Sin clasificación o
                    no reconocida → Otros. Hoy y 60 días atrás; todos los
                    estados de pago/préstamo.
                  </CardDescription>
                </CardHeader>

                <CardContent className="p-6 pt-4">
                  {loadingPagosIngresadosPorDia ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      Cargando…
                    </div>
                  ) : errorPagosIngresadosPorDia ? (
                    <div className="flex items-center justify-center py-16 text-red-600">
                      No se pudo cargar la serie diaria de pagos
                    </div>
                  ) : seriePagosIngresadosPorDia.length > 0 ? (
                    <ChartWithDateRangeSlider
                      data={seriePagosIngresadosPorDia}
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

                            {categoriasPagosIngresados.map((cat, idx) => (
                              <Bar
                                key={cat}
                                dataKey={cat}
                                name={cat}
                                stackId="institucion"
                                fill={coloresInstitucionPago[cat] || '#94a3b8'}
                                radius={
                                  idx === categoriasPagosIngresados.length - 1
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
                      No hay datos para los últimos 60 días
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Pagos BS admitidos por día (equiv. USD, últimos 60 días) */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-emerald-50/90 to-teal-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <BarChart3 className="h-5 w-5 text-emerald-600" />

                      <span>Pagos en BS por día (equiv. USD)</span>
                    </CardTitle>

                    <Badge
                      variant="secondary"
                      className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                    >
                      {etiquetaRangoPagosBsIngresados}
                    </Badge>
                  </div>

                  <CardDescription className="mt-2 text-xs text-gray-600">
                    Solo pagos admitidos en bolívares (moneda_registro = BS).
                    Monto expresado en USD (suma de monto_pagado ya convertido
                    al registrar). Apilado por institución: Mercantil, BNC,
                    Binance, BNV, Recibos; resto → Otros. Hoy y 60 días atrás.
                  </CardDescription>
                </CardHeader>

                <CardContent className="p-6 pt-4">
                  {loadingPagosBsIngresadosPorDia ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      Cargando…
                    </div>
                  ) : errorPagosBsIngresadosPorDia ? (
                    <div className="flex items-center justify-center py-16 text-red-600">
                      No se pudo cargar la serie diaria de pagos en BS
                    </div>
                  ) : seriePagosBsIngresadosPorDia.length > 0 ? (
                    <ChartWithDateRangeSlider
                      data={seriePagosBsIngresadosPorDia}
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

                            {categoriasPagosBsIngresados.map((cat, idx) => (
                              <Bar
                                key={cat}
                                dataKey={cat}
                                name={cat}
                                stackId="institucion_bs"
                                fill={coloresInstitucionPago[cat] || '#94a3b8'}
                                radius={
                                  idx === categoriasPagosBsIngresados.length - 1
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
                      No hay pagos en BS en los últimos 60 días
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
                    Cobranzas con segmento 1 cuota
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
                Dos cantidades por día (últimos {DESEMPENO_1_CUOTA_DIAS_VISION}{' '}
                días, Caracas). Independiente de envíos SMTP.{' '}
                <strong>Inicio día</strong>: stock del segmento 1 cuota a las{' '}
                <strong>00:00</strong>. <strong>Fin dia</strong>: de ese stock,
                cuántos siguen sin pagar a las <strong>23:00</strong> (hoy:
                valor en vivo hasta las 23:00).
              </CardDescription>
            </CardHeader>

            <CardContent className="p-6 pt-4">
              {loadingDesempeno1CuotaStock ? (
                <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                  Cargando…
                </div>
              ) : errorDesempeno1CuotaStock ? (
                <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-red-700">
                  <AlertTriangle className="h-8 w-8" />

                  <p className="text-sm font-medium">
                    No se pudo cargar el desempeño 1 cuota.
                  </p>
                </div>
              ) : serieDesempeno1CuotaDiario.length === 0 ? (
                <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                  Sin datos en el período.
                </div>
              ) : (
                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height={320}>
                    <RechartsLineChart
                      data={serieDesempeno1CuotaDiario}
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
                        minTickGap={12}
                      />

                      <YAxis
                        tick={chartAxisTick}
                        allowDecimals={false}
                        domain={ejeYDesempeno1Cuota.domain}
                        ticks={ejeYDesempeno1Cuota.ticks}
                        allowDataOverflow
                        width={48}
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
                        formatter={(value: number, name: string) => {
                          const rounded =
                            typeof value === 'number'
                              ? Math.round(value * 100) / 100
                              : value
                          return [rounded, name]
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
                        dataKey="notificaciones"
                        name="Fin dia"
                        stroke="#0ea5e9"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                      />

                      <Line
                        type="monotone"
                        dataKey="morosos"
                        name="Inicio día"
                        stroke="#d97706"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                      />
                    </RechartsLineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Desempeño 2 cuotas (PREJUDICIAL / ≥60 días) */}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.36 }}
          className="mt-6"
          id="dashboard-desempeno-2-cuotas"
        >
          <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
            <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-sky-50/90 to-indigo-50/90 pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                  <Mail className="h-5 w-5 shrink-0 text-sky-600" />

                  <span className="leading-tight">
                    Cobranzas con segmento 2 cuotas
                  </span>
                </CardTitle>

                <Badge
                  variant="secondary"
                  className="shrink-0 border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                >
                  {etiquetaRangoDesempeno2Cuotas}
                </Badge>
              </div>

              <CardDescription className="mt-2 text-xs text-gray-600">
                Dos cantidades por día (últimos {DESEMPENO_2_CUOTAS_DIAS_VISION}{' '}
                días, Caracas). Independiente de envíos SMTP.{' '}
                <strong>Inicio día</strong>: stock del segmento 2 cuotas a las{' '}
                <strong>00:00</strong>. <strong>Fin dia</strong>: de ese stock,
                cuántos siguen sin pagar a las <strong>23:00</strong> (hoy:
                valor en vivo hasta las 23:00).
              </CardDescription>
            </CardHeader>

            <CardContent className="p-6 pt-4">
              {loadingDesempeno2CuotasStock ? (
                <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                  Cargando…
                </div>
              ) : errorDesempeno2CuotasStock ? (
                <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-red-700">
                  <AlertTriangle className="h-8 w-8" />

                  <p className="text-sm font-medium">
                    No se pudo cargar el desempeño 2 cuotas.
                  </p>
                </div>
              ) : serieDesempeno2CuotasDiario.length === 0 ? (
                <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                  Sin datos en el período.
                </div>
              ) : (
                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height={320}>
                    <RechartsLineChart
                      data={serieDesempeno2CuotasDiario}
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
                        minTickGap={12}
                      />

                      <YAxis
                        tick={chartAxisTick}
                        allowDecimals={false}
                        domain={ejeYDesempeno2Cuotas.domain}
                        ticks={ejeYDesempeno2Cuotas.ticks}
                        allowDataOverflow
                        width={48}
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
                        formatter={(value: number, name: string) => {
                          const rounded =
                            typeof value === 'number'
                              ? Math.round(value * 100) / 100
                              : value
                          return [rounded, name]
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
                        dataKey="notificaciones"
                        name="Fin dia"
                        stroke="#0ea5e9"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                      />

                      <Line
                        type="monotone"
                        dataKey="morosos"
                        name="Inicio día"
                        stroke="#d97706"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                      />
                    </RechartsLineChart>
                  </ResponsiveContainer>
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
