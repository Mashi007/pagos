import { useState, useMemo, useEffect, useLayoutEffect } from 'react'

import { motion } from 'framer-motion'

import { useNavigate } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  BarChart3,
  ChevronRight,
  Filter,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Shield,
  History,
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
  FINANCIAMIENTO_BANDAS_GRAFICO_TITULO,
  FINANCIAMIENTO_BANDAS_ORDEN_CATEGORIAS,
  getPeriodoEtiqueta,
  PERIODOS_VALORES,
} from '../constants/dashboard'

import type {
  KpisPrincipalesResponse,
  OpcionesFiltrosResponse,
  DashboardAdminResponse,
  FinanciamientoPorRangosResponse,
  CobranzasSemanalesResponse,
  MorosidadPorAnalistaItem,
  AnalisisCuentasPorCobrarResponse,
  TendenciaProgramadoTotalCobradoResponse,
  EvolucionMensualItem,
  NotificacionesEnviosPorDiaResponse,
} from '../types/dashboard'

import { DashboardFiltrosPanel } from '../components/dashboard/DashboardFiltrosPanel'

import { KpiCardLarge } from '../components/dashboard/KpiCardLarge'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

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

export function DashboardMenu() {
  const navigate = useNavigate()

  const { user } = useSimpleAuth()

  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const queryClient = useQueryClient()

  useEffect(() => {
    const run = async () => {
      try {
        await queryClient.prefetchQuery({
          queryKey: ['dashboard-pagos-inicial', {}],
          queryFn: async () =>
            apiClient.get('/api/v1/dashboard/pagos-inicial?meses_evolucion=6'),
          staleTime: 2 * 60 * 1000,
        })
      } catch {
        /* prefetch opcional */
      }
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

  // Batch 1: CRÍTICO - KPIs principales (visible primero para el usuario)

  // Los KPIs siempre reflejan solo el mes actual (ej. febrero) - independiente del período de los gráficos

  const mesActualKey = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`

  const {
    data: kpisPrincipales,
    isLoading: loadingKPIs,
    isError: errorKPIs,
    refetch,
  } = useQuery({
    queryKey: [
      'kpis-principales-menu',
      'mes',
      mesActualKey,
      JSON.stringify(filtros),
    ],

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

    staleTime: 5 * 60 * 1000, // 5 min para datos más frescos

    refetchOnWindowFocus: true,

    refetchOnMount: true,

    refetchInterval: 10 * 60 * 1000, // Refrescar cada 10 min

    enabled: true,

    retry: false,
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

  // Batch 4: BAJA - Gráficos menos críticos. Período con fallback para incluir 2025.

  const periodoRangos =
    getPeriodoGrafico('rangos') || periodo || 'ultimos_12_meses'

  const {
    data: datosFinanciamientoRangos,
    isLoading: loadingFinanciamientoRangos,
    isError: errorFinanciamientoRangos,
    error: errorFinanciamientoRangosDetail,
    refetch: refetchFinanciamientoRangos,
  } = useQuery({
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

        if (
          (status != null && status >= 500) ||
          err?.code === 'ERR_NETWORK' ||
          err?.code === 'ECONNABORTED'
        ) {
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

    retry: 1, // Permitir 1 reintento para errores de red

    retryDelay: 2000, // Esperar 2 segundos antes de reintentar
  })

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

    enabled: true,

    refetchOnWindowFocus: false,
  })

  const periodoMorosidadAnalista = getPeriodoGrafico('morosidad-analista')

  const { data: datosMorosidadAnalista, isLoading: loadingMorosidadAnalista } =
    useQuery({
      queryKey: [
        'morosidad-analista',
        periodoMorosidadAnalista,
        JSON.stringify(filtros),
      ],

      queryFn: async () => {
        const params = construirFiltrosObject(periodoMorosidadAnalista)

        const queryParams = new URLSearchParams()

        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })

        const response = await apiClient.get<{
          analistas: MorosidadPorAnalistaItem[]
        }>(`/api/v1/dashboard/morosidad-por-analista?${queryParams.toString()}`)

        return response.analistas ?? []
      },

      staleTime: 4 * 60 * 60 * 1000,

      refetchOnWindowFocus: false,

      enabled: true,
    })

  const {
    data: datosMontoProgramadoSemana,
    isLoading: loadingMontoProgramadoSemana,
  } = useQuery({
    queryKey: ['monto-programado-proxima-semana'],

    queryFn: async () => {
      const response = await apiClient.get<{
        dias: {
          fecha: string
          dia: string
          monto_programado: number
          pagos_conciliados_dia: number
          pagos_dias_anteriores_dia: number
        }[]
      }>('/api/v1/dashboard/monto-programado-proxima-semana')

      return response.dias ?? []
    },

    staleTime: 5 * 60 * 1000,

    refetchOnWindowFocus: false,

    enabled: true,
  })

  const periodoAnalisisCuentas = getPeriodoGrafico('analisis-cuentas')

  const { data: datosAnalisisCuentas, isLoading: loadingAnalisisCuentas } =
    useQuery({
      queryKey: [
        'analisis-cuentas-por-cobrar',
        periodoAnalisisCuentas,
        JSON.stringify(filtros),
      ],

      queryFn: async () => {
        const params = construirFiltrosObject(periodoAnalisisCuentas)

        const queryParams = new URLSearchParams()

        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })

        if (!queryParams.has('periodo') && periodoAnalisisCuentas)
          queryParams.append('periodo', periodoAnalisisCuentas)

        const response = await apiClient.get(
          `/api/v1/dashboard/analisis-cuentas-por-cobrar${queryParams.toString() ? `?${queryParams.toString()}` : ''}`,
          { timeout: 60000 }
        )

        return response as AnalisisCuentasPorCobrarResponse
      },

      staleTime: 4 * 60 * 60 * 1000,

      refetchOnWindowFocus: false,

      enabled: true,
    })

  const periodoTendenciaCobranza = getPeriodoGrafico(
    'tendencia-cobranza-lineas'
  )

  const { data: datosTendenciaCobranza, isLoading: loadingTendenciaCobranza } =
    useQuery({
      queryKey: [
        'tendencia-programado-total-cobrado',
        periodoTendenciaCobranza,
        JSON.stringify(filtros),
      ],

      queryFn: async () => {
        const params = construirFiltrosObject(periodoTendenciaCobranza)

        const queryParams = new URLSearchParams()

        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })

        if (!queryParams.has('periodo') && periodoTendenciaCobranza)
          queryParams.append('periodo', periodoTendenciaCobranza)

        const response = await apiClient.get(
          `/api/v1/dashboard/tendencia-programado-total-cobrado${queryParams.toString() ? `?${queryParams.toString()}` : ''}`,
          { timeout: 60000 }
        )

        return response as TendenciaProgramadoTotalCobradoResponse
      },

      staleTime: 4 * 60 * 60 * 1000,

      refetchOnWindowFocus: false,

      enabled: true,
    })

  const NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS = 90

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

    enabled: true,
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

  const etiquetaRangoNotificacionesEjeX = useMemo(() => {
    const s = serieNotificacionesGrafico

    if (!s.length) return `${NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d · Caracas`

    const a = s[0]?.fecha

    const b = s[s.length - 1]?.fecha

    if (a && b) return a === b ? `${a} · Caracas` : `${a} - ${b} · Caracas`

    return `${NOTIFICACIONES_ENVIOS_TENDENCIA_DIAS} d · Caracas`
  }, [serieNotificacionesGrafico])

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
        queryKey: ['kpis-principales-menu'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['dashboard-menu'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['financiamiento-rangos'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['cobranzas-semanales'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['morosidad-analista'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['monto-programado-proxima-semana'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['analisis-cuentas-por-cobrar'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['tendencia-programado-total-cobrado'],
        exact: false,
      })

      await queryClient.invalidateQueries({
        queryKey: ['notificaciones-envios-por-dia'],
        exact: false,
      })

      // Refrescar todas las queries activas del dashboard

      await queryClient.refetchQueries({
        queryKey: ['kpis-principales-menu'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['dashboard-menu'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['financiamiento-rangos'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['cobranzas-semanales'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['morosidad-analista'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['monto-programado-proxima-semana'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['analisis-cuentas-por-cobrar'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['tendencia-programado-total-cobrado'],
        exact: false,
      })

      await queryClient.refetchQueries({
        queryKey: ['notificaciones-envios-por-dia'],
        exact: false,
      })

      await refetch()

      toast.success('Datos actualizados correctamente')
    } catch (error) {
      toast.error('Error al actualizar los datos. Intenta de nuevo.')
    } finally {
      setIsRefreshing(false)
    }
  }

  const evolucionMensual = useMemo(() => {
    const raw = datosDashboard?.evolucion_mensual ?? []

    return raw.map((e: EvolucionMensualItem) => ({
      ...e,
      cuentas_por_cobrar: e.cartera - e.cobrado,
    }))
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

  // Bandas desde backend: pasos de $300 desde $800 hasta $4.000 + colas (alineado con API)

  const datosBandasFinanciamiento = useMemo(() => {
    try {
      if (
        !datosFinanciamientoRangos?.rangos ||
        datosFinanciamientoRangos.rangos.length === 0
      ) {
        return []
      }

      // Eje Y: arriba mayor banda, abajo "Menos de $800" (Recharts: primera fila = arriba)

      const ordenPrioridadMayorArriba = [
        ...FINANCIAMIENTO_BANDAS_ORDEN_CATEGORIAS,
      ]

      return [...datosFinanciamientoRangos.rangos]

        .sort((a, b) => {
          const ia = ordenPrioridadMayorArriba.indexOf(a.categoria)

          const ib = ordenPrioridadMayorArriba.indexOf(b.categoria)

          const sa = ia === -1 ? 999 : ia

          const sb = ib === -1 ? 999 : ib

          return sa - sb
        })

        .map(r => ({
          ...r,

          categoriaFormateada: r.categoria.replace(/,/g, ''),

          cantidad: r.cantidad_prestamos,
        }))
    } catch (error) {
      console.error(
        'Error procesando datos de financiamiento por rangos:',
        error
      )

      return []
    }
  }, [datosFinanciamientoRangos])

  // Asegurar que el componente siempre renderice, incluso si hay errores

  // Si hay un error crítico en las queries principales, mostrar mensaje pero no bloquear

  const hasCriticalError =
    errorOpcionesFiltros || errorKPIs || errorDashboardAdmin

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

        {/* KPIs PRINCIPALES (cuatro tarjetas; fila completa en xl) */}

        <section id="dashboard-kpis" aria-label="KPIs principales">
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4 xl:items-stretch">
              {loadingKPIs ? (
                <>
                  {[1, 2, 3, 4].map(i => (
                    <div
                      key={i}
                      className="h-[180px] animate-pulse rounded-xl bg-gray-100"
                    />
                  ))}
                </>
              ) : errorKPIs ? (
                <Card className="border-red-200 bg-red-50 md:col-span-2 xl:col-span-4">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3 text-red-700">
                      <AlertTriangle className="h-5 w-5" />

                      <p>
                        Error al cargar los KPIs principales. Por favor, intente
                        nuevamente.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ) : kpisPrincipales ? (
                <>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    <KpiCardLarge
                      title="Pagos conciliados en USD (hoy)"
                      subtitle="Suma del monto del pago en dólares (USD del registro; BS con tasa del comprobante), conciliado hoy (Caracas), solo cuotas que vencen hoy; un pago cuenta una vez. Sin atrasos."
                      value={kpisPrincipales.pagos_conciliados_hoy.valor_actual}
                      variation={
                        kpisPrincipales.pagos_conciliados_hoy
                          .variacion_porcentual !== undefined
                          ? {
                              percent:
                                kpisPrincipales.pagos_conciliados_hoy
                                  .variacion_porcentual,

                              label: 'vs día anterior',
                            }
                          : undefined
                      }
                      icon={TrendingUp}
                      color="text-green-600"
                      bgColor="bg-green-100"
                      borderColor="border-green-500"
                      format="currency"
                    />
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    <KpiCardLarge
                      title="Pagos programados (hoy)"
                      subtitle={
                        kpisPrincipales.porcentaje_cuotas_pagadas_hoy !==
                        undefined
                          ? `Monto con vencimiento hoy (Caracas) · ${Number(kpisPrincipales.porcentaje_cuotas_pagadas_hoy).toFixed(1)}% de esas cuotas ya con fecha de pago`
                          : 'Monto con vencimiento hoy (America/Caracas)'
                      }
                      value={kpisPrincipales.pagos_programados_hoy.valor_actual}
                      variation={
                        kpisPrincipales.pagos_programados_hoy
                          .variacion_porcentual !== undefined
                          ? {
                              percent:
                                kpisPrincipales.pagos_programados_hoy
                                  .variacion_porcentual,

                              label: 'vs día anterior',
                            }
                          : undefined
                      }
                      icon={FileText}
                      color="text-blue-600"
                      bgColor="bg-blue-100"
                      borderColor="border-blue-500"
                      format="currency"
                    />
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.11 }}
                  >
                    <KpiCardLarge
                      title="Atrasos cobrados (hoy)"
                      subtitle="Monto en USD de cuotas con vencimiento anterior a hoy (Caracas) y conciliación hoy; no incluye cuotas que vencen hoy"
                      value={
                        kpisPrincipales.cuotas_atrasadas_conciliadas_hoy
                          ?.valor_actual ?? 0
                      }
                      variation={
                        kpisPrincipales.cuotas_atrasadas_conciliadas_hoy
                          ?.variacion_porcentual !== undefined
                          ? {
                              percent:
                                kpisPrincipales.cuotas_atrasadas_conciliadas_hoy
                                  .variacion_porcentual,

                              label: 'vs día anterior',
                            }
                          : undefined
                      }
                      icon={History}
                      color="text-amber-700"
                      bgColor="bg-amber-100"
                      borderColor="border-amber-500"
                      format="currency"
                    />
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.12 }}
                  >
                    <KpiCardLarge
                      title="Pago vencido (mensual)"
                      subtitle="Cuotas vencidas sin pagar (solo si ya pasó la fecha de vencimiento)"
                      value={kpisPrincipales.total_morosidad_usd.valor_actual}
                      variation={
                        kpisPrincipales.total_morosidad_usd
                          .variacion_porcentual !== undefined
                          ? {
                              percent:
                                kpisPrincipales.total_morosidad_usd
                                  .variacion_porcentual,

                              label: 'vs mes anterior',
                            }
                          : undefined
                      }
                      icon={AlertTriangle}
                      color="text-red-600"
                      bgColor="bg-red-100"
                      borderColor="border-red-500"
                      format="currency"
                    />
                  </motion.div>
                </>
              ) : null}
            </div>
          </div>
        </section>

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

            {kpisPrincipales &&
            Number(kpisPrincipales.total_prestamos?.valor_actual ?? 0) === 0 &&
            (!datosDashboard?.evolucion_mensual?.length ||
              datosDashboard.evolucion_mensual.every(
                (e: EvolucionMensualItem) =>
                  !e.cartera && !e.cobrado && !(e.pagos_atrasos ?? 0)
              )) ? (
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
                    La línea roja <strong>Cuentas por cobrar</strong> es cada
                    mes: <strong>pagos programados</strong> (azul) menos{' '}
                    <strong>pagos conciliados</strong> del mismo mes (verde).
                    Los <strong>pagos de meses anteriores</strong> (naranja) son
                    informativos y <strong>no</strong> entran en ese cálculo.
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
                              contentStyle={chartTooltipStyle.contentStyle}
                              labelStyle={chartTooltipStyle.labelStyle}
                              formatter={(value: number, name: string) => {
                                const suffix =
                                  name === 'Cuentas por Cobrar'
                                    ? ' (programados - conciliados del mes)'
                                    : ''

                                return [
                                  formatCurrency(value),
                                  `${name}${suffix}`,
                                ]
                              }}
                            />

                            <Legend {...chartLegendStyle} />

                            <Bar
                              stackId="programado"
                              dataKey="cartera"
                              fill="#3b82f6"
                              name="Pagos programados"
                              radius={[4, 4, 0, 0]}
                            />

                            <Bar
                              stackId="cobros"
                              dataKey="cobrado"
                              fill="#10b981"
                              name="Pagos conciliados"
                              radius={[0, 0, 0, 0]}
                            />

                            <Bar
                              stackId="cobros"
                              dataKey="pagos_atrasos"
                              fill="#f97316"
                              name="Pagos de meses anteriores"
                              radius={[4, 4, 0, 0]}
                            />

                            <Line
                              type="monotone"
                              dataKey="cuentas_por_cobrar"
                              stroke="#ef4444"
                              strokeWidth={2}
                              name="Cuentas por Cobrar"
                              dot={{ r: 4 }}
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

            {/* Análisis de Cuentas por Cobrar - Cartera vs Pagos de Atrasos */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-amber-50/90 to-orange-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <DollarSign className="h-5 w-5 text-amber-600" />

                      <span>Análisis de Cuentas por Cobrar</span>
                    </CardTitle>

                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="analisis-cuentas" />

                      <Badge
                        variant="secondary"
                        className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                      >
                        Últimos 12 meses
                      </Badge>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-6 pt-4">
                  {loadingAnalisisCuentas ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      Cargando análisis de cuentas por cobrar...
                    </div>
                  ) : datosAnalisisCuentas?.analisis &&
                    datosAnalisisCuentas.analisis.length > 0 ? (
                    <ChartWithDateRangeSlider
                      data={datosAnalisisCuentas.analisis}
                      dataKey="mes"
                      chartHeight={400}
                    >
                      {filteredData => (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
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

                            <Bar
                              stackId="cobros-analisis"
                              dataKey="cobrado_mes"
                              fill="#10b981"
                              name="Pagos conciliados"
                              radius={[0, 0, 0, 0]}
                            />

                            <Bar
                              stackId="cobros-analisis"
                              dataKey="pagos_atrasos"
                              fill="#f97316"
                              name="Pagos de meses anteriores"
                              radius={[4, 4, 0, 0]}
                            />

                            <Line
                              type="monotone"
                              dataKey="cobrado_mes"
                              stroke="#10b981"
                              strokeWidth={2}
                              dot={{ r: 3 }}
                              name="Tendencia pagos conciliados"
                              isAnimationActive={false}
                            />

                            <Line
                              type="monotone"
                              dataKey="pagos_atrasos"
                              stroke="#f97316"
                              strokeWidth={2}
                              dot={{ r: 3 }}
                              name="Tendencia atrasos"
                              isAnimationActive={false}
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

            {/* Tendencia: programado vs total cobrado (2 líneas) */}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-sky-50/90 to-indigo-50/90 pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <LineChart className="h-5 w-5 text-sky-600" />

                      <span>Programado vs cobrado (mensual)</span>
                    </CardTitle>

                    <div className="flex items-center gap-2">
                      <SelectorPeriodoGrafico chartId="tendencia-cobranza-lineas" />

                      <Badge
                        variant="secondary"
                        className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                      >
                        2 líneas
                      </Badge>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-6 pt-4">
                  {loadingTendenciaCobranza ? (
                    <div className="flex items-center justify-center py-16 text-gray-500">
                      Cargando tendencia programado vs cobrado...
                    </div>
                  ) : datosTendenciaCobranza?.series &&
                    datosTendenciaCobranza.series.length > 0 ? (
                    <ChartWithDateRangeSlider
                      data={datosTendenciaCobranza.series}
                      dataKey="mes"
                      chartHeight={400}
                    >
                      {filteredData => (
                        <ResponsiveContainer width="100%" height="100%">
                          <RechartsLineChart
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

                            <Line
                              type="monotone"
                              dataKey="cuotas_programadas"
                              stroke="#2563eb"
                              strokeWidth={2}
                              dot={{ r: 4 }}
                              name="Cuotas programadas a cobrar"
                            />

                            <Line
                              type="monotone"
                              dataKey="total_cobrado"
                              stroke="#059669"
                              strokeWidth={2}
                              dot={{ r: 4 }}
                              name="Pagos conciliados + meses anteriores"
                            />
                          </RechartsLineChart>
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

        {/* Notificaciones por día: gráfico de línea (después de Programado vs cobrado); no es KPI */}

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

        {/* GRÁFICOS: BANDAS DE FINANCIAMIENTO Y COBRANZA PLANIFICADA VS REAL */}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {datosDashboard ? (
            <>
              {/* Cobranza diaria + monto programado solo hoy (hoy-10 .. hoy, Caracas) */}

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.36 }}
              >
                <Card className="flex h-full flex-col overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
                  <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-emerald-50/90 to-teal-50/90 pb-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                        <DollarSign className="h-5 w-5 text-emerald-600" />

                        <span>Cobranza diaria y monto programado (hoy)</span>
                      </CardTitle>

                      <Badge
                        variant="secondary"
                        className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                      >
                        11 días · hoy-10 → hoy · Caracas
                      </Badge>
                    </div>

                    <CardDescription className="text-sm text-gray-600">
                      Por cada día: barras apiladas{' '}
                      <strong>Pagos conciliados</strong> (vencimiento = ese día
                      y pago ese día) y <strong>Pagos días anteriores</strong>{' '}
                      (vencimiento anterior, pago ese día), como el análisis
                      mensual pero en escala diaria.{' '}
                      <strong>Monto programado</strong>: suma de monto_cuota con
                      vencimiento <strong>solo en hoy</strong> (barra aparte,
                      resto de días en cero).
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="p-6 pt-4">
                    {loadingMontoProgramadoSemana ? (
                      <div className="flex items-center justify-center py-16 text-gray-500">
                        Cargando...
                      </div>
                    ) : datosMontoProgramadoSemana &&
                      datosMontoProgramadoSemana.length > 0 ? (
                      <ResponsiveContainer width="100%" height={420}>
                        <BarChart
                          data={datosMontoProgramadoSemana}
                          margin={{ top: 14, right: 24, left: 8, bottom: 56 }}
                        >
                          <CartesianGrid {...chartCartesianGrid} />

                          <XAxis
                            dataKey="dia"
                            tick={chartAxisTick}
                            interval={0}
                            angle={-32}
                            textAnchor="end"
                            height={68}
                            minTickGap={4}
                          />

                          <YAxis
                            tick={chartAxisTick}
                            tickFormatter={value =>
                              `$${value >= 1000 ? (value / 1000).toFixed(1) + 'K' : value}`
                            }
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
                            labelFormatter={(_, payload) =>
                              payload?.[0]?.payload?.fecha
                                ? `Fecha: ${payload[0].payload.fecha}`
                                : ''
                            }
                          />

                          <Legend {...chartLegendStyle} />

                          <Bar
                            stackId="cobranza"
                            dataKey="pagos_conciliados_dia"
                            name="Pagos conciliados (venc. = día, pago = día)"
                            fill="#10b981"
                            radius={[0, 0, 0, 0]}
                            maxBarSize={44}
                          />

                          <Bar
                            stackId="cobranza"
                            dataKey="pagos_dias_anteriores_dia"
                            name="Pagos días anteriores (pago = día)"
                            fill="#f97316"
                            radius={[4, 4, 0, 0]}
                            maxBarSize={44}
                          />

                          <Bar
                            stackId="programado"
                            dataKey="monto_programado"
                            name="Monto programado (solo hoy)"
                            fill="#06b6d4"
                            radius={[4, 4, 0, 0]}
                            maxBarSize={36}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex items-center justify-center py-16 text-gray-500">
                        No hay datos en la ventana de 11 días (Caracas).
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </>
          ) : null}

          {/* GRÁFICO DE BANDAS (financiamiento, pasos $300 desde $800 hasta $4.000) */}

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="flex h-full flex-col overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
              <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-indigo-50/90 to-purple-50/90 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                    <BarChart3 className="h-5 w-5 text-indigo-600" />

                    <span>{FINANCIAMIENTO_BANDAS_GRAFICO_TITULO}</span>
                  </CardTitle>

                  <div className="flex items-center gap-2">
                    <SelectorPeriodoGrafico chartId="rangos" />

                    <Badge
                      variant="secondary"
                      className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                    >
                      {getRangoFechasLabelGrafico('rangos')}
                    </Badge>
                  </div>
                </div>

                <CardDescription className="px-6 pb-1 pt-0 text-xs text-gray-600">
                  Clasificación en el gráfico: tramos de{' '}
                  <strong>USD 300</strong> desde <strong>800</strong> hasta{' '}
                  <strong>4.000</strong>, más Menos de $800 (todo lo inferior) y
                  Más de $4.000 (misma lógica que el endpoint{' '}
                  <code className="rounded bg-gray-100 px-1 py-0.5 text-[10px]">
                    /api/v1/dashboard/financiamiento-por-rangos
                  </code>
                  ).
                </CardDescription>
              </CardHeader>

              <CardContent className="flex-1 p-6">
                {datosBandasFinanciamiento &&
                datosBandasFinanciamiento.length > 0 ? (
                  <ChartWithDateRangeSlider
                    data={datosBandasFinanciamiento}
                    dataKey="categoriaFormateada"
                    chartHeight={560}
                  >
                    {filteredData => (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={filteredData}
                          layout="vertical"
                          margin={{ top: 14, right: 24, left: 132, bottom: 24 }}
                        >
                          <CartesianGrid {...chartCartesianGrid} />

                          <XAxis
                            type="number"
                            domain={[0, 'dataMax']}
                            tick={chartAxisTick}
                            tickFormatter={value =>
                              value.toLocaleString('es-EC')
                            }
                            label={{
                              value: 'Cantidad de Préstamos',
                              position: 'insideBottom',
                              offset: -10,
                              style: {
                                textAnchor: 'middle',
                                fill: '#374151',
                                fontSize: 13,
                                fontWeight: 600,
                              },
                            }}
                            allowDecimals={false}
                          />

                          <YAxis
                            type="category"
                            dataKey="categoriaFormateada"
                            width={128}
                            tick={{
                              fontSize: 10,
                              fill: '#4b5563',
                              fontWeight: 500,
                            }}
                            interval={0}
                            tickLine={false}
                          />

                          <Tooltip
                            contentStyle={chartTooltipStyle.contentStyle}
                            labelStyle={chartTooltipStyle.labelStyle}
                            formatter={(value: number) => [
                              `${value.toLocaleString('es-EC')} préstamos`,
                              'Cantidad',
                            ]}
                            labelFormatter={label => `Banda: ${label}`}
                            cursor={{ fill: 'rgba(99, 102, 241, 0.08)' }}
                          />

                          <Legend {...chartLegendStyle} />

                          <Bar
                            dataKey="cantidad"
                            radius={[0, 6, 6, 0]}
                            name="Cantidad de Préstamos"
                          >
                            {filteredData.map((entry, index) => {
                              const maxCant = Math.max(
                                ...filteredData.map(d => d.cantidad)
                              )

                              const intensity =
                                maxCant > 0 ? entry.cantidad / maxCant : 0

                              const opacity = 0.6 + intensity * 0.4

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
                    )}
                  </ChartWithDateRangeSlider>
                ) : (
                  <div className="flex items-center justify-center py-16 text-gray-500">
                    No hay datos para mostrar
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* GRÁFICOS DE MOROSIDAD */}

        <div className="grid grid-cols-1 gap-6">
          {/* Cantidad de préstamos en mora por rango de días */}
        </div>

        {/* Pago vencido por Analista (por analista) */}

        <div className="mt-6 flex flex-col gap-6">
          {/* Dólares vencidos por analista (barras) */}

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.95 }}
            className="w-full"
          >
            <Card className="w-full overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">
              <CardHeader className="border-b border-gray-200/80 bg-gradient-to-r from-amber-50/90 to-orange-50/90 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle className="flex items-center gap-2 text-lg font-bold text-gray-800">
                    <DollarSign className="h-5 w-5 text-amber-600" />

                    <span>Pago vencido por Analista - Dólares vencidos</span>
                  </CardTitle>

                  <div className="flex items-center gap-2">
                    <SelectorPeriodoGrafico chartId="morosidad-analista" />

                    <Badge
                      variant="secondary"
                      className="border border-gray-200 bg-white/80 text-xs font-medium text-gray-600"
                    >
                      Al día de hoy
                    </Badge>
                  </div>
                </div>

                <p className="mt-1 px-6 text-xs text-gray-600">
                  Suma de monto_cuota de cuotas vencidas (fecha_vencimiento &lt;
                  hoy, sin pagar), snapshot actual por analista
                </p>
              </CardHeader>

              <CardContent className="p-6">
                {loadingMorosidadAnalista ? (
                  <div className="flex items-center justify-center py-16 text-gray-500">
                    Cargando...
                  </div>
                ) : datosMorosidadAnalista &&
                  datosMorosidadAnalista.length > 0 ? (
                  <>
                    <h4 className="mb-1 text-center text-sm font-semibold text-gray-700">
                      Dólares vencidos por analista
                    </h4>

                    <ResponsiveContainer
                      width="100%"
                      height={Math.max(
                        380,
                        Math.min(620, datosMorosidadAnalista.length * 28)
                      )}
                    >
                      <BarChart
                        data={datosMorosidadAnalista}
                        layout="vertical"
                        margin={{ top: 12, right: 32, left: 16, bottom: 12 }}
                        barCategoryGap="12%"
                      >
                        <CartesianGrid
                          {...chartCartesianGrid}
                          horizontal={false}
                        />

                        <XAxis
                          type="number"
                          tickFormatter={v =>
                            `$${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`
                          }
                          tick={chartAxisTick}
                          axisLine={{ stroke: '#e5e7eb' }}
                        />

                        <YAxis
                          type="category"
                          dataKey="analista"
                          width={200}
                          tick={{
                            fontSize: 12,
                            fill: '#374151',
                            fontWeight: 500,
                          }}
                          interval={0}
                          tickLine={false}
                          axisLine={{ stroke: '#e5e7eb' }}
                          tickFormatter={name =>
                            name && name.length > 24
                              ? `${name.slice(0, 22)}…`
                              : name
                          }
                        />

                        <Tooltip
                          contentStyle={chartTooltipStyle.contentStyle}
                          labelStyle={chartTooltipStyle.labelStyle}
                          formatter={(value: number) => [
                            formatCurrency(value),
                            'Dólares vencidos',
                          ]}
                          labelFormatter={label => `Analista: ${label}`}
                          cursor={{ fill: 'rgba(234, 88, 12, 0.06)' }}
                        />

                        <Legend {...chartLegendStyle} />

                        <Bar
                          dataKey="monto_vencido"
                          name="Dólares vencidos"
                          fill="#ea580c"
                          radius={[0, 4, 4, 0]}
                          maxBarSize={28}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </>
                ) : (
                  <div className="flex items-center justify-center py-16 text-gray-500">
                    No hay datos para mostrar
                  </div>
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
