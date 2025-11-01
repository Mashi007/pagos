import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  DollarSign,
  Activity,
  Clock,
  CheckCircle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency } from '@/utils'
import { apiClient } from '@/services/api'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { DashboardFiltrosPanel } from '@/components/dashboard/DashboardFiltrosPanel'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'

interface KPIsData {
  total_financiamiento: number
  total_financiamiento_activo: number
  total_financiamiento_inactivo: number
  total_financiamiento_finalizado: number
}

export function DashboardFinanciamiento() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get<{ analistas: string[]; concesionarios: string[]; modelos: string[] }>('/api/v1/dashboard/opciones-filtros')
      return response
    },
  })

  // Cargar KPIs
  const { data: kpisData, isLoading: loadingKpis, refetch } = useQuery({
    queryKey: ['kpis-financiamiento', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get<KPIsData>(
        `/api/v1/kpis/dashboard${queryString ? '?' + queryString : ''}`
      )
      return {
        total_financiamiento: response.total_financiamiento || 0,
        total_financiamiento_activo: response.total_financiamiento_activo || 0,
        total_financiamiento_inactivo: response.total_financiamiento_inactivo || 0,
        total_financiamiento_finalizado: response.total_financiamiento_finalizado || 0,
      } as KPIsData
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

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
            <h1 className="text-3xl font-bold text-gray-900">KPIs de Financiamiento</h1>
            <p className="text-gray-600">
              Bienvenido, {userName} • Métricas de financiamiento por estado
            </p>
          </div>
        </div>
        <DashboardFiltrosPanel
          filtros={filtros}
          setFiltros={setFiltros}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
          opcionesFiltros={opcionesFiltros}
          loadingOpcionesFiltros={loadingOpcionesFiltros}
          errorOpcionesFiltros={errorOpcionesFiltros}
        />
      </motion.div>

      {/* KPIs Grid */}
      {loadingKpis ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
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
      ) : kpisData ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Total Financiamiento */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="hover:shadow-lg transition-all border-l-4 border-l-blue-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                  <DollarSign className="mr-2 h-4 w-4 text-blue-600" />
                  Total Financiamiento
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(kpisData.total_financiamiento || 0)}
                </div>
                <p className="text-xs text-gray-500 mt-1">Total préstamos</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Financiamiento Activo */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="hover:shadow-lg transition-all border-l-4 border-l-green-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                  <Activity className="mr-2 h-4 w-4 text-green-600" />
                  Financiamiento Activo
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {formatCurrency(kpisData.total_financiamiento_activo || 0)}
                </div>
                <p className="text-xs text-gray-500 mt-1">Estado activo</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Financiamiento Inactivo */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="hover:shadow-lg transition-all border-l-4 border-l-orange-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                  <Clock className="mr-2 h-4 w-4 text-orange-600" />
                  Financiamiento Inactivo
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">
                  {formatCurrency(kpisData.total_financiamiento_inactivo || 0)}
                </div>
                <p className="text-xs text-gray-500 mt-1">Estado inactivo</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Financiamiento Finalizado */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="hover:shadow-lg transition-all border-l-4 border-l-purple-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                  <CheckCircle className="mr-2 h-4 w-4 text-purple-600" />
                  Financiamiento Finalizado
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-purple-600">
                  {formatCurrency(kpisData.total_financiamiento_finalizado || 0)}
                </div>
                <p className="text-xs text-gray-500 mt-1">Estado finalizado</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      ) : null}
    </div>
  )
}

