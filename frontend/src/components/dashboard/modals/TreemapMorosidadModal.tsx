import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Treemap,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { BaseModal } from '../BaseModal'
import { DashboardFiltrosPanel } from '../DashboardFiltrosPanel'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { apiClient } from '@/services/api'
import { formatCurrency } from '@/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface TreemapMorosidadModalProps {
  isOpen: boolean
  onClose: () => void
}

interface AnalistaMorosidadData {
  analista: string
  total_morosidad: number
  cantidad_clientes: number
  cantidad_cuotas_atrasadas: number
  promedio_morosidad_por_cliente: number
}

interface TreemapMorosidadResponse {
  analistas: AnalistaMorosidadData[]
}

export function TreemapMorosidadModal({ isOpen, onClose }: TreemapMorosidadModalProps) {
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

  // Cargar datos de morosidad por analista
  const { data: morosidadData, isLoading: loadingMorosidad, refetch } = useQuery({
    queryKey: ['morosidad-por-analista', filtros],
    queryFn: async (): Promise<TreemapMorosidadResponse> => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/morosidad-por-analista${queryString ? '?' + queryString : ''}`
      ) as TreemapMorosidadResponse
      return response || { analistas: [] }
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  // Preparar datos para Treemap
  const datosTreemap = morosidadData?.analistas.map((a) => ({
    name: a.analista,
    value: a.total_morosidad,
    cantidad_clientes: a.cantidad_clientes,
    cantidad_cuotas_atrasadas: a.cantidad_cuotas_atrasadas,
    promedio_morosidad_por_cliente: a.promedio_morosidad_por_cliente,
  })) || []

  // Colores para el treemap (gradiente)
  const getColor = (value: number, maxValue: number) => {
    const ratio = value / maxValue
    if (ratio > 0.7) return '#dc2626' // rojo oscuro
    if (ratio > 0.4) return '#f97316' // naranja
    if (ratio > 0.2) return '#eab308' // amarillo
    return '#84cc16' // verde claro
  }

  const maxValue = Math.max(...datosTreemap.map((d) => d.value), 0)

  // Tooltip personalizado
  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload?: { name?: string; value?: number; cantidad_clientes?: number; cantidad_cuotas_atrasadas?: number; promedio_morosidad_por_cliente?: number } }> }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      if (!data) return null
      
      const value = typeof data.value === 'number' ? data.value : 0
      const cantidadClientes = typeof data.cantidad_clientes === 'number' ? data.cantidad_clientes : 0
      const cantidadCuotas = typeof data.cantidad_cuotas_atrasadas === 'number' ? data.cantidad_cuotas_atrasadas : 0
      const promedio = typeof data.promedio_morosidad_por_cliente === 'number' ? data.promedio_morosidad_por_cliente : 0
      
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-bold text-lg mb-2">{typeof data.name === 'string' ? data.name : 'N/A'}</p>
          <p className="text-sm mb-1">
            <span className="font-semibold">Morosidad Total:</span>{' '}
            <span className="text-red-600">{formatCurrency(value)}</span>
          </p>
          <p className="text-sm mb-1">
            <span className="font-semibold">Clientes:</span> {cantidadClientes}
          </p>
          <p className="text-sm mb-1">
            <span className="font-semibold">Cuotas Atrasadas:</span> {cantidadCuotas}
          </p>
          <p className="text-sm">
            <span className="font-semibold">Promedio por Cliente:</span>{' '}
            {formatCurrency(promedio)}
          </p>
        </div>
      )
    }
    return null
  }

  // Componente personalizado para cada celda del Treemap
  const CustomCell = ({ x, y, width, height, payload }: { x?: number; y?: number; width?: number; height?: number; payload?: { name?: string; value?: number } }) => {
    const color = getColor(payload.value, maxValue)
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill={color}
          stroke="#fff"
          strokeWidth={2}
          opacity={0.8}
        />
        {width > 80 && height > 40 && (
          <>
            <text
              x={x + width / 2}
              y={y + height / 2 - 10}
              textAnchor="middle"
              fill="#fff"
              fontSize={14}
              fontWeight="bold"
            >
              {payload.name}
            </text>
            <text
              x={x + width / 2}
              y={y + height / 2 + 10}
              textAnchor="middle"
              fill="#fff"
              fontSize={12}
            >
              {formatCurrency(payload.value)}
            </text>
          </>
        )}
      </g>
    )
  }

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      title="Morosidad por Analista"
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

        {/* Gráfico Treemap */}
        <Card>
          <CardHeader>
            <CardTitle>Morosidad por Analista (Clientes con morosidad desde 1 día)</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingMorosidad ? (
              <div className="h-[500px] flex items-center justify-center">
                <div className="animate-pulse text-gray-400">Cargando gráfico...</div>
              </div>
            ) : datosTreemap.length === 0 ? (
              <div className="h-[500px] flex items-center justify-center text-gray-500">
                No hay datos de morosidad disponibles para el período seleccionado
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={500}>
                <Treemap
                  data={datosTreemap}
                  dataKey="value"
                  stroke="#fff"
                  fill="#8884d8"
                  content={<CustomCell />}
                >
                  <Tooltip content={<CustomTooltip />} />
                </Treemap>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </BaseModal>
  )
}

