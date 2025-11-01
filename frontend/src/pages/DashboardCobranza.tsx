import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  CreditCard,
  Target,
  TrendingUp,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency, formatPercentage } from '@/utils'
import { apiClient } from '@/services/api'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { DashboardFiltrosPanel } from '@/components/dashboard/DashboardFiltrosPanel'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'

interface DashboardData {
  meta_mensual: number
  avance_meta: number
  financieros?: {
    totalCobrado: number
    tasaRecuperacion: number
  }
}

export function DashboardCobranza() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [periodo, setPeriodo] = useState('mes')
  const { construirParams, construirFiltrosObject } = useDashboardFiltros(filtros)

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  const construirParamsDashboard = () => construirParams(periodo)

  // Cargar datos del dashboard
  const { data: dashboardData, isLoading: loadingDashboard, refetch } = useQuery({
    queryKey: ['dashboard-cobranza', periodo, filtros],
    queryFn: async () => {
      try {
        const params = construirParamsDashboard()
        const response = await apiClient.get(`/api/v1/dashboard/admin?${params}`) as DashboardData
        return response
      } catch (error) {
        console.warn('Error cargando dashboard:', error)
        return {
          meta_mensual: 0,
          avance_meta: 0,
          financieros: {
            totalCobrado: 0,
            tasaRecuperacion: 0,
          },
        } as DashboardData
      }
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  const data = dashboardData || {
    meta_mensual: 0,
    avance_meta: 0,
    financieros: {
      totalCobrado: 0,
      tasaRecuperacion: 0,
    },
  }

  const porcentajeAvance = data.meta_mensual > 0
    ? (data.avance_meta / data.meta_mensual) * 100
    : 0

  const mesActual = new Date().toLocaleDateString('es-ES', {
    month: 'long',
    year: 'numeric',
  }).replace(/^\w/, (c) => c.toUpperCase())

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard/menu')}
          >
            ← Volver al Menú
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">KPIs de Cobranza</h1>
            <p className="text-gray-600">
              Bienvenido, {userName} • Métricas de recaudación y cumplimiento
            </p>
          </div>
        </div>
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
      </motion.div>

      {/* KPIs Grid */}
      {loadingDashboard ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-8 bg-gray-200 rounded w-1/2"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Total Cobrado */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="hover:shadow-lg transition-all border-l-4 border-l-green-500">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <CreditCard className="mr-2 h-5 w-5 text-green-600" />
                  Total Cobrado
                </CardTitle>
                <CardDescription>{mesActual}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600 mb-2">
                  {formatCurrency(data.financieros?.totalCobrado || 0)}
                </div>
                <p className="text-xs text-gray-500">Pagos conciliados del mes</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Tasa de Recuperación Mensual */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="hover:shadow-lg transition-all border-l-4 border-l-blue-500">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <TrendingUp className="mr-2 h-5 w-5 text-blue-600" />
                  Tasa de Recuperación Mensual
                </CardTitle>
                <CardDescription>{mesActual}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600 mb-2">
                  {formatPercentage(data.financieros?.tasaRecuperacion || 0)}
                </div>
                <p className="text-xs text-gray-500">Cuotas pagadas / planificadas</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Meta Mensual */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="hover:shadow-lg transition-all border-l-4 border-l-purple-500">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Target className="mr-2 h-5 w-5 text-purple-600" />
                  Meta Mensual
                </CardTitle>
                <CardDescription>{mesActual}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <div className="text-2xl font-bold text-gray-900 mb-1">
                      {formatCurrency(data.meta_mensual || 0)}
                    </div>
                    <p className="text-xs text-gray-500">Total a cobrar del mes</p>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Recaudado</span>
                      <span className="font-medium">
                        {formatCurrency(data.avance_meta || 0)}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-purple-600 h-2 rounded-full transition-all"
                        style={{ width: `${Math.min(porcentajeAvance, 100)}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-gray-500">
                      {porcentajeAvance.toFixed(1)}% de la meta
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}
    </div>
  )
}

