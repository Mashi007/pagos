import { useState } from 'react'
import { motion } from 'framer-motion'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { DashboardFiltrosPanel } from '@/components/dashboard/DashboardFiltrosPanel'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { PagosKPIs } from '@/components/pagos/PagosKPIs'
import { pagoService } from '@/services/pagoService'

export function DashboardPagos() {
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

  // Cargar estadísticas de pagos
  const { data: pagosStats, isLoading: pagosStatsLoading, refetch } = useQuery({
    queryKey: ['pagos-stats', filtros],
    queryFn: async () => {
      const params = construirFiltrosObject()
      return await pagoService.getStats(params)
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
            <h1 className="text-3xl font-bold text-gray-900">KPIs de Pagos</h1>
            <p className="text-gray-600">
              Bienvenido, {userName} • Métricas de pagos y transacciones
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

      {/* KPIs de Pagos */}
      {pagosStats && (
        <PagosKPIs
          totalPagos={pagosStats.total_pagos}
          totalPagado={pagosStats.total_pagado}
          pagosHoy={pagosStats.pagos_hoy}
          cuotasPagadas={pagosStats.cuotas_pagadas}
          cuotasPendientes={pagosStats.cuotas_pendientes}
          cuotasAtrasadas={pagosStats.cuotas_atrasadas}
          isLoading={pagosStatsLoading}
        />
      )}
    </div>
  )
}

