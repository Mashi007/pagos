import { lazy, Suspense, useState } from 'react'

import { motion } from 'framer-motion'

import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  CreditCard,
  Shield,
  Clock,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  ChevronRight,
  Filter,
  Search,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Button } from '../components/ui/button'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { useSimpleAuth } from '../store/simpleAuthStore'

import { formatCurrency } from '../utils'

import { apiClient } from '../services/api'

import {
  useDashboardFiltros,
  type DashboardFiltros,
} from '../hooks/useDashboardFiltros'

import { DashboardFiltrosPanel } from '../components/dashboard/DashboardFiltrosPanel'

import { useNavigate } from 'react-router-dom'

import { KpiCardLarge } from '../components/dashboard/KpiCardLarge'


const DashboardPagosCharts = lazy(() =>
  import('../components/dashboard/DashboardPagosCharts').then(m => ({
    default: m.DashboardPagosCharts,
  }))
)

export function DashboardPagos() {
  const navigate = useNavigate()

  const { user } = useSimpleAuth()

  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})

  const { construirFiltrosObject, tieneFiltrosActivos } =
    useDashboardFiltros(filtros)

  const queryClient = useQueryClient()

  const {
    data: inicialPagos,
    isLoading: loadingInicialPagos,
    isError: errorOpcionesFiltros,
    refetch,
    isFetching: fetchingInicialPagos,
  } = useQuery({
    queryKey: ['dashboard-pagos-inicial', filtros],

    queryFn: async ({ signal }) => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses_evolucion', '6')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const res = (await apiClient.get(
        `/api/v1/dashboard/pagos-inicial?${queryParams.toString()}`,
        { signal }
      )) as {
        opciones_filtros: {
          analistas: string[]
          concesionarios: string[]
          modelos: string[]
        }
        pagos_stats: {
          total_pagos: number
          total_pagado: number
          pagos_por_estado: Array<{ estado: string; count: number }>
          cuotas_pagadas: number
          cuotas_pendientes: number
        }
        kpis_pagos: {
          montoCobradoMes: number
          saldoPorCobrar: number
          clientesEnMora: number
          clientesAlDia: number
          cuotas_pendientes?: number
        }
        evolucion_pagos_meses: Array<{
          mes: string
          pagos: number
          monto: number
        }>
      }

      queryClient.setQueryData(['opciones-filtros'], res.opciones_filtros)
      const filtrosActivos =
        Boolean(filtros.analista) ||
        Boolean(filtros.concesionario) ||
        Boolean(filtros.modelo) ||
        Boolean(filtros.fecha_inicio) ||
        Boolean(filtros.fecha_fin)
      if (!filtrosActivos) {
        queryClient.setQueryData(['kpis-pagos'], res.kpis_pagos)
      }
      return res
    },

    placeholderData: keepPreviousData,

    staleTime: 2 * 60 * 1000,

    refetchOnWindowFocus: false,

    refetchInterval: 5 * 60 * 1000,

    refetchIntervalInBackground: false,

    retry: 1,
  })

  const opcionesFiltros = inicialPagos?.opciones_filtros

  const loadingOpcionesFiltros = loadingInicialPagos

  const pagosStats = inicialPagos?.pagos_stats

  const pagosStatsLoading = loadingInicialPagos

  const kpisPagos = inicialPagos?.kpis_pagos

  const loadingKPIs = loadingInicialPagos

  const pagosPorEstado = inicialPagos?.pagos_stats

  const loadingPagosEstado = loadingInicialPagos

  const datosPagosEstado =
    pagosPorEstado?.pagos_por_estado.map(item => ({
      estado: item.estado,

      cantidad: item.count,

      porcentaje:
        (pagosPorEstado?.total_pagos || 0) > 0
          ? (item.count / (pagosPorEstado?.total_pagos || 1)) * 100
          : 0,
    })) || []

  const datosEvolucion = inicialPagos?.evolucion_pagos_meses

  const loadingEvolucion = loadingInicialPagos

  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)

    await refetch()

    setIsRefreshing(false)
  }

  const totalPagos = pagosStats?.total_pagos || 0

  const totalPagado = pagosStats?.total_pagado || 0

  const pagosConciliados = pagosStats?.cuotas_pagadas || 0

  const pagosPendientes = pagosStats?.cuotas_pendientes || 0

  const promedioPorPago = totalPagos > 0 ? totalPagado / totalPagos : 0

  const porcentajeConciliados =
    totalPagos > 0 ? (pagosConciliados / totalPagos) * 100 : 0

  const porcentajePendientes =
    totalPagos > 0 ? (pagosPendientes / totalPagos) * 100 : 0

  const COLORS_ESTADO = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#9ca3af']

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto space-y-8 px-4 py-8">
        {/* Header Estratégico */}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <ModulePageHeader
            icon={CreditCard}
            title="Pagos"
            description={`Monitoreo estratégico · ${userName}`}
            actions={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/dashboard/menu')}
                className="hover:bg-violet-50"
              >
                ← Menú
              </Button>
            }
          />
        </motion.div>

        {/* BARRA DE FILTROS HORIZONTAL */}

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="border-2 border-gray-200 bg-gradient-to-r from-gray-50 to-white shadow-md">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center space-x-2">
                  <div className="flex items-center space-x-2 text-sm font-semibold text-gray-700">
                    <Filter className="h-4 w-4 text-violet-600" />

                    <span>Filtros Rápidos</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <DashboardFiltrosPanel
                    filtros={filtros}
                    setFiltros={setFiltros}
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

        {pagosStatsLoading || loadingKPIs ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map(i => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="animate-pulse">
                    <div className="mb-4 h-4 w-3/4 rounded bg-gray-200"></div>

                    <div className="h-10 w-1/2 rounded bg-gray-200"></div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            <KpiCardLarge
              title="Total Pagos Mes"
              value={totalPagado}
              subtitle={`${totalPagos.toLocaleString()} pagos`}
              icon={CreditCard}
              color="text-violet-600"
              bgColor="bg-violet-100"
              borderColor="border-violet-500"
              format="currency"
            />

            <KpiCardLarge
              title="Pagos Conciliados"
              value={pagosConciliados}
              subtitle={`${porcentajeConciliados.toFixed(1)}% del total`}
              icon={Shield}
              color="text-blue-600"
              bgColor="bg-blue-100"
              borderColor="border-blue-500"
              format="number"
            />

            <KpiCardLarge
              title="Pagos Pendientes"
              value={pagosPendientes}
              subtitle={`${porcentajePendientes.toFixed(1)}% del total`}
              icon={Clock}
              color="text-amber-600"
              bgColor="bg-amber-100"
              borderColor="border-amber-500"
              format="number"
            />

            <KpiCardLarge
              title="Promedio por Pago"
              value={promedioPorPago}
              subtitle="Mes actual"
              icon={TrendingUp}
              color="text-indigo-600"
              bgColor="bg-indigo-100"
              borderColor="border-indigo-500"
              format="currency"
            />
          </div>
        )}

        <Suspense
          fallback={
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="flex h-[320px] items-center justify-center rounded-lg border border-gray-200 bg-white">
                <div className="animate-pulse text-gray-400">
                  Cargando graficos...
                </div>
              </div>
              <div className="flex h-[320px] items-center justify-center rounded-lg border border-gray-200 bg-white">
                <div className="animate-pulse text-gray-400">
                  Cargando graficos...
                </div>
              </div>
            </div>
          }
        >
          <DashboardPagosCharts
            loadingPagosEstado={loadingPagosEstado}
            datosPagosEstado={datosPagosEstado}
            totalPagos={totalPagos}
            COLORS_ESTADO={COLORS_ESTADO}
            loadingEvolucion={loadingEvolucion}
            datosEvolucion={datosEvolucion}
          />
        </Suspense>

        {/* BOTONES EXPLORAR DETALLES */}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-8"
        >
          <div className="rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 p-6 shadow-xl">
            <h2 className="mb-4 flex items-center space-x-2 text-2xl font-bold text-white">
              <span>ðŸ"</span>

              <span>Explorar Análisis Detallados</span>
            </h2>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              <Button
                variant="secondary"
                className="flex h-auto flex-col items-center space-y-2 border-2 border-transparent bg-white py-4 text-gray-800 hover:border-violet-300 hover:bg-gray-50"
                onClick={() => {
                  // TODO: Navegar a detalles de transacciones

                  console.log('Detalles de Transacciones')
                }}
              >
                <CreditCard className="h-6 w-6" />

                <span className="font-semibold">Detalles de Transacciones</span>

                <ChevronRight className="h-4 w-4" />
              </Button>

              <Button
                variant="secondary"
                className="flex h-auto flex-col items-center space-y-2 border-2 border-transparent bg-white py-4 text-gray-800 hover:border-violet-300 hover:bg-gray-50"
                onClick={() => {
                  // TODO: Navegar a análisis de conciliaciones

                  console.log('Análisis de Conciliaciones')
                }}
              >
                <Shield className="h-6 w-6" />

                <span className="font-semibold">
                  Análisis de Conciliaciones
                </span>

                <ChevronRight className="h-4 w-4" />
              </Button>

              <Button
                variant="secondary"
                className="flex h-auto flex-col items-center space-y-2 border-2 border-transparent bg-white py-4 text-gray-800 hover:border-violet-300 hover:bg-gray-50"
                onClick={() => {
                  // TODO: Navegar a reportes de pagos

                  console.log('Reportes de Pagos')
                }}
              >
                <CheckCircle className="h-6 w-6" />

                <span className="font-semibold">Reportes de Pagos</span>

                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
