import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Calendar,
  CheckCircle,
  Shield,
  AlertTriangle,
  Users,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { apiClient } from '@/services/api'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { DashboardFiltrosPanel } from '@/components/dashboard/DashboardFiltrosPanel'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'

interface KPIsData {
  total_cuotas_mes: number
  cuotas_pagadas: number
  porcentaje_cuotas_pagadas: number
  total_cuotas_conciliadas: number
  cuotas_atrasadas_mes: number
  total_cuotas_impagas_2mas: number
}

export function DashboardCuotas() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery<{ analistas: string[]; concesionarios: string[]; modelos: string[] }>({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get<{ analistas: string[]; concesionarios: string[]; modelos: string[] }>('/api/v1/dashboard/opciones-filtros')
      return response
    },
  })

  // Cargar KPIs
  const { data: kpisData, isLoading: loadingKpis, refetch } = useQuery({
    queryKey: ['kpis-cuotas', filtros],
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
        total_cuotas_mes: response.total_cuotas_mes || 0,
        cuotas_pagadas: response.cuotas_pagadas || 0,
        porcentaje_cuotas_pagadas: response.porcentaje_cuotas_pagadas || 0,
        total_cuotas_conciliadas: response.total_cuotas_conciliadas || 0,
        cuotas_atrasadas_mes: response.cuotas_atrasadas_mes || 0,
        total_cuotas_impagas_2mas: response.total_cuotas_impagas_2mas || 0,
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
            <h1 className="text-3xl font-bold text-gray-900">KPIs de Cuotas</h1>
            <p className="text-gray-600">
              Bienvenido, {userName} • Gestión de cuotas y amortizaciones
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
          {[1, 2, 3, 4, 5, 6].map((i) => (
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
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Cuotas a Cobrar (Mes) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card className="hover:shadow-lg transition-all border-l-4 border-l-purple-500">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                    <Calendar className="mr-2 h-4 w-4 text-purple-600" />
                    Cuotas a Cobrar (Mes)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-gray-900">
                    {kpisData.total_cuotas_mes || 0}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Mes en curso</p>
                </CardContent>
              </Card>
            </motion.div>

            {/* Cuotas Pagadas */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card className="hover:shadow-lg transition-all border-l-4 border-l-green-500">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                    <CheckCircle className="mr-2 h-4 w-4 text-green-600" />
                    Cuotas Pagadas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">
                    {kpisData.cuotas_pagadas || 0}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {kpisData.porcentaje_cuotas_pagadas?.toFixed(1) || 0}% del total
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            {/* Cuotas Conciliadas */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="hover:shadow-lg transition-all border-l-4 border-l-blue-500">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                    <Shield className="mr-2 h-4 w-4 text-blue-600" />
                    Cuotas Conciliadas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-600">
                    {kpisData.total_cuotas_conciliadas || 0}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Con pagos conciliados</p>
                </CardContent>
              </Card>
            </motion.div>

            {/* Cuotas Atrasadas */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card className="hover:shadow-lg transition-all border-l-4 border-l-red-500">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                    <AlertTriangle className="mr-2 h-4 w-4 text-red-600" />
                    Cuotas Atrasadas (Mes)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600">
                    {kpisData.cuotas_atrasadas_mes || 0}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Sin pagar ni conciliar</p>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Cuotas Impagas 2+ */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card className="hover:shadow-lg transition-all border-l-4 border-l-orange-500">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-gray-600 flex items-center">
                    <Users className="mr-2 h-4 w-4 text-orange-600" />
                    Cuotas Impagas (2+)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-orange-600">
                    {kpisData.total_cuotas_impagas_2mas || 0}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">2 o más por cliente</p>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </>
      ) : null}
    </div>
  )
}

