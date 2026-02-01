import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { BaseModal } from '../BaseModal'
import { DashboardFiltrosPanel } from '../DashboardFiltrosPanel'
import { useDashboardFiltros, type DashboardFiltros } from '../../../hooks/useDashboardFiltros'
import { apiClient } from '../../../services/api'
import { formatCurrency } from '../../../utils'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'

interface DonutConcesionariosModalProps {
  isOpen: boolean
  onClose: () => void
}

interface ConcesionarioData {
  concesionario: string
  total_prestamos: number
  porcentaje: number
  cantidad_prestamos: number
}

interface DonutConcesionariosResponse {
  concesionarios: ConcesionarioData[]
  total_general: number
}

export function DonutConcesionariosModal({ isOpen, onClose }: DonutConcesionariosModalProps) {
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

  // Cargar datos de prÃ©stamos por concesionario
  const { data: prestamosData, isLoading: loadingPrestamos, refetch } = useQuery({
    queryKey: ['prestamos-por-concesionario', filtros],
    queryFn: async (): Promise<DonutConcesionariosResponse> => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/prestamos-por-concesionario${queryString ? '?' + queryString : ''}`
      ) as DonutConcesionariosResponse
      return response || { concesionarios: [], total_general: 0 }
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  // Preparar datos para el grÃ¡fico (agrupar segmentos pequeÃ±os en "Otros")
  const umbralPorcentaje = 3 // Agrupar si es menos del 3%
  const datosGrafico = prestamosData?.concesionarios || []
  const datosPrincipales = datosGrafico.filter((d) => d.porcentaje >= umbralPorcentaje)
  const datosOtros = datosGrafico.filter((d) => d.porcentaje < umbralPorcentaje)

  const totalOtros = datosOtros.reduce((sum, d) => sum + d.total_prestamos, 0)
  const porcentajeOtros = datosOtros.length > 0
    ? (totalOtros / (prestamosData?.total_general || 1)) * 100
    : 0

  const datosFinales = [
    ...datosPrincipales,
    ...(datosOtros.length > 0 ? [{
      concesionario: 'Otros',
      total_prestamos: totalOtros,
      porcentaje: porcentajeOtros,
      cantidad_prestamos: datosOtros.reduce((sum, d) => sum + d.cantidad_prestamos, 0),
    }] : []),
  ]

  // Colores para el grÃ¡fico
  const COLORS = [
    '#3b82f6', // azul
    '#10b981', // verde
    '#f59e0b', // amarillo
    '#ef4444', // rojo
    '#8b5cf6', // pÃºrpura
    '#ec4899', // rosa
    '#06b6d4', // cian
    '#84cc16', // lima
    '#f97316', // naranja
    '#6366f1', // Ã­ndigo
    '#14b8a6', // teal
    '#a855f7', // violeta
  ]

  // Tooltip personalizado
  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ name?: string; value?: number; payload?: { porcentaje?: number; cantidad_prestamos?: number } }> }) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold mb-2">{data.name}</p>
          <p className="text-sm mb-1">
            <span className="font-semibold">Total:</span> {formatCurrency(data.value ?? 0)}
          </p>
          <p className="text-sm mb-1">
            <span className="font-semibold">Porcentaje:</span> {typeof data.payload?.porcentaje === 'number' ? data.payload.porcentaje.toFixed(2) : '0.00'}%
          </p>
          <p className="text-sm">
            <span className="font-semibold">Cantidad:</span> {typeof data.payload?.cantidad_prestamos === 'number' ? data.payload.cantidad_prestamos : 0} prÃ©stamos
          </p>
        </div>
      )
    }
    return null
  }

  // Label personalizado
  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: { cx?: number; cy?: number; midAngle?: number; innerRadius?: number; outerRadius?: number; percent?: number }) => {
    if (!percent || percent < 0.05 || !cx || !cy || !midAngle || !innerRadius || !outerRadius) return null

    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize={12}
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    )
  }

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      title="PrÃ©stamos por Concesionario"
      size="large"
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

        {/* GrÃ¡fico Donut */}
        <Card>
          <CardHeader>
            <CardTitle>DistribuciÃ³n de PrÃ©stamos por Concesionario (Porcentaje)</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingPrestamos ? (
              <div className="h-[500px] flex items-center justify-center">
                <div className="animate-pulse text-gray-400">Cargando grÃ¡fico...</div>
              </div>
            ) : datosFinales.length === 0 ? (
              <div className="h-[500px] flex items-center justify-center text-gray-500">
                No hay datos de prÃ©stamos disponibles para el perÃ­odo seleccionado
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* GrÃ¡fico */}
                <div className="lg:col-span-2">
                  <ResponsiveContainer width="100%" height={400}>
                    <PieChart>
                      <Pie
                        data={datosFinales}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={renderCustomLabel}
                        outerRadius={120}
                        innerRadius={60}
                        fill="#8884d8"
                        dataKey="total_prestamos"
                        nameKey="concesionario"
                      >
                        {datosFinales.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                      <Legend
                        verticalAlign="bottom"
                        height={36}
                        formatter={(value: string) => `${value} (${datosFinales.find(d => d.concesionario === value)?.porcentaje.toFixed(1)}%)`}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                {/* Leyenda detallada */}
                <div className="lg:col-span-1">
                  <div className="space-y-2">
                    <h3 className="font-semibold text-lg mb-3">Desglose Detallado</h3>
                    {datosFinales.map((item, index) => (
                      <div
                        key={item.concesionario}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50"
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className="w-4 h-4 rounded"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          <span className="text-sm font-medium">{item.concesionario}</span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-bold">{item.porcentaje.toFixed(1)}%</div>
                          <div className="text-xs text-gray-500">
                            {formatCurrency(item.total_prestamos)}
                          </div>
                        </div>
                      </div>
                    ))}
                    {prestamosData && (
                      <div className="mt-4 pt-4 border-t">
                        <div className="text-sm text-gray-500">Total General</div>
                        <div className="text-xl font-bold">
                          {formatCurrency(prestamosData.total_general)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </BaseModal>
  )
}

