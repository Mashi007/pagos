import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { BaseModal } from '../BaseModal'
import { DashboardFiltrosPanel } from '../DashboardFiltrosPanel'
import { KpiCardsPanel } from '../KpiCardsPanel'
import { useDashboardFiltros, type DashboardFiltros } from '../../../hooks/useDashboardFiltros'
import { apiClient } from '../../../services/api'
import { formatCurrency } from '../../../utils'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'

interface CobranzasMensualesModalProps {
  isOpen: boolean
  onClose: () => void
}

interface MesData {
  mes: string
  nombre_mes: string
  cobranzas_planificadas: number
  pagos_reales: number
  meta_mensual: number
}

interface CobranzasMensualesResponse {
  meses: MesData[]
  meta_actual: number
}

export function CobranzasMensualesModal({ isOpen, onClose }: CobranzasMensualesModalProps) {
  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  // Cargar datos de cobranzas mensuales
  const { data: cobranzasData, isLoading: loadingCobranzas, refetch } = useQuery({
    queryKey: ['cobranzas-mensuales', filtros],
    queryFn: async (): Promise<CobranzasMensualesResponse> => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/cobranzas-mensuales${queryString ? '?' + queryString : ''}`
      ) as CobranzasMensualesResponse
      return response || { meses: [], meta_actual: 0 }
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  // Separar datos reales de proyecciones (si aplica)
  const datosGrafico = cobranzasData?.meses || []

  // Tooltip personalizado
  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name?: string; value?: number; color?: string }>; label?: string | number }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold mb-2">{label}</p>
          {payload.map((entry, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {formatCurrency(entry.value ?? 0)}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      title="Cobranzas Mensuales vs Pagos"
      size="xlarge"
    >
      <div className="space-y-6">
        {/* Filtros */}
        <DashboardFiltrosPanel
          filtros={filtros}
          setFiltros={setFiltros}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
          opcionesFiltros={opcionesFiltros}
          loadingOpcionesFiltros={loadingOpcionesFiltros}
          errorOpcionesFiltros={errorOpcionesFiltros}
        />

        {/* Layout: Tarjetas KPI Izquierda + GrÃ¡fico Derecha */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Tarjetas KPI - Izquierda */}
          <div className="lg:col-span-1">
            <KpiCardsPanel filtros={filtros} />
          </div>

          {/* GrÃ¡fico - Derecha */}
          <div className="lg:col-span-3">
            <Card>
              <CardHeader>
                <CardTitle>Cobranzas Mensuales vs Pagos</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingCobranzas ? (
                  <div className="h-[400px] flex items-center justify-center">
                    <div className="animate-pulse text-gray-400">Cargando grÃ¡fico...</div>
                  </div>
                ) : datosGrafico.length === 0 ? (
                  <div className="h-[400px] flex items-center justify-center text-gray-500">
                    No hay datos disponibles para el perÃ­odo seleccionado
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={400}>
                    <AreaChart data={datosGrafico} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorCobranzas" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0891b2" stopOpacity={0.8} />
                          <stop offset="95%" stopColor="#0891b2" stopOpacity={0.1} />
                        </linearGradient>
                        <linearGradient id="colorPagos" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="nombre_mes"
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                      />
                      <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                        tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="cobranzas_planificadas"
                        name="Cobranzas Planificadas"
                        stroke="#0891b2"
                        fillOpacity={1}
                        fill="url(#colorCobranzas)"
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="pagos_reales"
                        name="Pagos Reales"
                        stroke="#10b981"
                        fillOpacity={1}
                        fill="url(#colorPagos)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </BaseModal>
  )
}

