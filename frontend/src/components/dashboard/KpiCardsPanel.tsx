import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DollarSign, TrendingUp, Users, AlertTriangle } from 'lucide-react'
import { KpiCard } from './KpiCard'
import { apiClient } from '../../services/api'
import { useDashboardFiltros, type DashboardFiltros } from '../../hooks/useDashboardFiltros'
import { formatCurrency } from '../../utils'

interface KpiCardsPanelProps {
  filtros: DashboardFiltros
}

interface KPIsPrincipalesData {
  total_prestamos: {
    valor_actual: number
    valor_mes_anterior: number
    variacion_porcentual: number
    variacion_absoluta: number
  }
  creditos_nuevos_mes: {
    valor_actual: number
    valor_mes_anterior: number
    variacion_porcentual: number
    variacion_absoluta: number
  }
  total_clientes: {
    valor_actual: number
    valor_mes_anterior: number
    variacion_porcentual: number
    variacion_absoluta: number
  }
  total_morosidad_usd: {
    valor_actual: number
    valor_mes_anterior: number
    variacion_porcentual: number
    variacion_absoluta: number
  }
  mes_actual: string
  mes_anterior: string
}

export function KpiCardsPanel({ filtros }: KpiCardsPanelProps) {
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  const { data: kpisData, isLoading } = useQuery({
    queryKey: ['kpis-principales', filtros],
    queryFn: async (): Promise<KPIsPrincipalesData> => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/kpis-principales${queryString ? '?' + queryString : ''}`
      ) as KPIsPrincipalesData
      return response
    },
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-[150px] bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  if (!kpisData || !kpisData.total_prestamos || !kpisData.creditos_nuevos_mes || !kpisData.total_clientes || !kpisData.total_morosidad_usd) {
    return (
      <div className="text-center text-gray-500 py-8">
        No hay datos disponibles
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <KpiCard
        title="Total PrÃ©stamos"
        value={kpisData.total_prestamos?.valor_actual ?? 0}
        variationPercent={kpisData.total_prestamos?.variacion_porcentual ?? 0}
        variationAbs={kpisData.total_prestamos?.variacion_absoluta ?? 0}
        color="blue"
        icon={DollarSign}
      />
      <KpiCard
        title="CrÃ©ditos Nuevos en el Mes"
        value={kpisData.creditos_nuevos_mes?.valor_actual ?? 0}
        variationPercent={kpisData.creditos_nuevos_mes?.variacion_porcentual ?? 0}
        variationAbs={kpisData.creditos_nuevos_mes?.variacion_absoluta ?? 0}
        color="green"
        icon={TrendingUp}
      />
      <KpiCard
        title="Total Clientes"
        value={kpisData.total_clientes?.valor_actual ?? 0}
        variationPercent={kpisData.total_clientes?.variacion_porcentual ?? 0}
        variationAbs={kpisData.total_clientes?.variacion_absoluta ?? 0}
        color="purple"
        icon={Users}
      />
      <KpiCard
        title="Total Morosidad en DÃ³lares"
        value={kpisData.total_morosidad_usd?.valor_actual ?? 0}
        variationPercent={kpisData.total_morosidad_usd?.variacion_porcentual ?? 0}
        variationAbs={kpisData.total_morosidad_usd?.variacion_absoluta ?? 0}
        color="red"
        icon={AlertTriangle}
        formatValue={(v) => formatCurrency(Number(v))}
      />
    </div>
  )
}

