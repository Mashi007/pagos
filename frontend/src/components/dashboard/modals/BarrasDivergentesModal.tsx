import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { BaseModal } from '../BaseModal'
import { DashboardFiltrosPanel } from '../DashboardFiltrosPanel'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { apiClient } from '@/services/api'
import { formatCurrency } from '@/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface BarrasDivergentesModalProps {
  isOpen: boolean
  onClose: () => void
}

type TipoDistribucion = 'rango_monto' | 'plazo' | 'rango_monto_plazo' | 'estado'

interface DistribucionData {
  categoria: string
  cantidad_prestamos: number
  monto_total: number
  porcentaje_cantidad: number
  porcentaje_monto: number
}

interface BarrasDivergentesResponse {
  distribucion: DistribucionData[]
  tipo: TipoDistribucion
  total_prestamos: number
  total_monto: number
}

export function BarrasDivergentesModal({ isOpen, onClose }: BarrasDivergentesModalProps) {
  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [tipoDistribucion, setTipoDistribucion] = useState<TipoDistribucion>('rango_monto')
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  // Cargar datos de distribución
  const { data: distribucionData, isLoading: loadingDistribucion, refetch } = useQuery({
    queryKey: ['distribucion-prestamos', filtros, tipoDistribucion],
    queryFn: async (): Promise<BarrasDivergentesResponse> => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('tipo', tipoDistribucion)
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/distribucion-prestamos?${queryString}`
      ) as BarrasDivergentesResponse
      return response || { distribucion: [], tipo: tipoDistribucion, total_prestamos: 0, total_monto: 0 }
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  // Preparar datos para gráfico divergente
  // Ordenar por monto total (ascendente para visualización)
  const datosGrafico = [...(distribucionData?.distribucion || [])].sort((a, b) => 
    a.monto_total - b.monto_total
  )

  // Tooltip personalizado
  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ payload?: Record<string, unknown>; value?: number }>; label?: string }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold mb-2">{label}</p>
          <p className="text-sm mb-1">
            <span className="font-semibold">Cantidad:</span> {data.cantidad_prestamos} préstamos
          </p>
          <p className="text-sm mb-1">
            <span className="font-semibold">Monto Total:</span> {formatCurrency(data.monto_total)}
          </p>
          <p className="text-sm">
            <span className="font-semibold">Porcentaje:</span> {data.porcentaje_monto.toFixed(2)}%
          </p>
        </div>
      )
    }
    return null
  }

  const getTitulo = () => {
    switch (tipoDistribucion) {
      case 'rango_monto':
        return 'Distribución por Rango de Monto'
      case 'plazo':
        return 'Distribución por Plazo'
      case 'rango_monto_plazo':
        return 'Distribución por Rango de Monto y Plazo'
      case 'estado':
        return 'Distribución por Estado'
      default:
        return 'Distribución de Préstamos'
    }
  }

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      title="Distribución de Préstamos"
      size="xlarge"
    >
      <div className="space-y-6">
        {/* Filtros y Selector de Tipo */}
        <div className="flex items-center justify-between gap-4">
          <DashboardFiltrosPanel
            filtros={filtros}
            setFiltros={setFiltros}
            onRefresh={handleRefresh}
            isRefreshing={isRefreshing}
            opcionesFiltros={opcionesFiltros}
            loadingOpcionesFiltros={loadingOpcionesFiltros}
            errorOpcionesFiltros={errorOpcionesFiltros}
          />
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Tipo de Distribución:</label>
            <Select value={tipoDistribucion} onValueChange={(v) => setTipoDistribucion(v as TipoDistribucion)}>
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="rango_monto">Rango de Monto</SelectItem>
                <SelectItem value="plazo">Plazo</SelectItem>
                <SelectItem value="rango_monto_plazo">Monto y Plazo</SelectItem>
                <SelectItem value="estado">Estado</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Gráfico de Barras Divergentes */}
        <Card>
          <CardHeader>
            <CardTitle>{getTitulo()}</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingDistribucion ? (
              <div className="h-[500px] flex items-center justify-center">
                <div className="animate-pulse text-gray-400">Cargando gráfico...</div>
              </div>
            ) : datosGrafico.length === 0 ? (
              <div className="h-[500px] flex items-center justify-center text-gray-500">
                No hay datos disponibles para el período seleccionado
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={500}>
                <BarChart
                  data={datosGrafico}
                  layout="vertical"
                  margin={{ top: 20, right: 30, left: 80, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    type="number"
                    stroke="#6b7280"
                    style={{ fontSize: '12px' }}
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                  />
                  <YAxis
                    type="category"
                    dataKey="categoria"
                    stroke="#6b7280"
                    style={{ fontSize: '12px' }}
                    width={70}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar
                    dataKey="monto_total"
                    name="Monto Total"
                    fill="#3b82f6"
                    radius={[0, 8, 8, 0]}
                  >
                    {datosGrafico.map((entry, index) => {
                      // Colores alternados para mejor visualización
                      const color = index % 2 === 0 ? '#3b82f6' : '#2563eb'
                      return <Cell key={`cell-${index}`} fill={color} />
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}

            {/* Resumen */}
            {distribucionData && (
              <div className="mt-6 grid grid-cols-2 gap-4 pt-6 border-t">
                <div>
                  <div className="text-sm text-gray-500">Total de Préstamos</div>
                  <div className="text-2xl font-bold">{distribucionData.total_prestamos}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Monto Total</div>
                  <div className="text-2xl font-bold">{formatCurrency(distribucionData.total_monto)}</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </BaseModal>
  )
}

