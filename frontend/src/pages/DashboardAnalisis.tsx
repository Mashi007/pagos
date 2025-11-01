import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  PieChart,
  LineChart,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency } from '@/utils'
import { apiClient } from '@/services/api'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { DashboardFiltrosPanel } from '@/components/dashboard/DashboardFiltrosPanel'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import {
  BarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'

interface CobroDiario {
  fecha: string
  dia: string
  dia_semana: string
  total_a_cobrar: number
  total_cobrado: number
}

interface DashboardData {
  financieros?: {
    ingresosCapital: number
    ingresosInteres: number
    ingresosMora: number
  }
  evolucion_mensual?: Array<{
    mes: string
    cartera: number
    cobrado: number
    morosidad: number
  }>
}

interface CobrosDiariosResponse {
  datos: CobroDiario[]
}

export function DashboardAnalisis() {
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
      const response = await apiClient.get<{ analistas: string[]; concesionarios: string[]; modelos: string[] }>('/api/v1/dashboard/opciones-filtros')
      return response
    },
  })

  const construirParamsDashboard = () => construirParams(periodo)

  // Cargar datos del dashboard
  const { data: dashboardData, isLoading: loadingDashboard, refetch } = useQuery({
    queryKey: ['dashboard-analisis', periodo, filtros],
    queryFn: async () => {
      try {
        const params = construirParamsDashboard()
        const response = await apiClient.get<DashboardData>(`/api/v1/dashboard/admin?${params}`)
        return response
      } catch (error) {
        console.warn('Error cargando dashboard:', error)
        return {} as DashboardData
      }
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cargar cobros diarios
  const { data: cobrosDiariosData, isLoading: loadingCobrosDiarios } = useQuery({
    queryKey: ['cobros-diarios', filtros],
    queryFn: async () => {
      try {
        const params = construirFiltrosObject()
        const queryParams = new URLSearchParams()
        queryParams.append('dias', '30')
        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })
        const response = await apiClient.get<CobrosDiariosResponse>(`/api/v1/dashboard/cobros-diarios?${queryParams.toString()}`)
        return response
      } catch (error) {
        console.warn('Error cargando cobros diarios:', error)
        return { datos: [] } as CobrosDiariosResponse
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

  const data = dashboardData || {}
  const cobrosDiarios = cobrosDiariosData?.datos || []

  // Análisis de Morosidad
  const totalFinanciamiento = data.financieros?.ingresosCapital || 0
  const carteraCobrada = data.financieros?.ingresosInteres || 0
  const morosidadDiferencia = data.financieros?.ingresosMora || 0
  const base = totalFinanciamiento

  const porcentajeFinanciamiento = base > 0 ? 100 : 0
  const porcentajeCobrado = base > 0 ? (carteraCobrada / base * 100) : 0
  const porcentajeMorosidad = base > 0 ? (morosidadDiferencia / base * 100) : 0

  const datosAnalisisMorosidad = totalFinanciamiento > 0 ? [
    {
      name: 'Total Financiamiento',
      value: totalFinanciamiento,
      color: '#3b82f6',
      porcentaje: porcentajeFinanciamiento
    },
    {
      name: 'Cartera Cobrada',
      value: carteraCobrada,
      color: '#10b981',
      porcentaje: porcentajeCobrado
    },
    {
      name: 'Morosidad',
      value: morosidadDiferencia,
      color: '#ef4444',
      porcentaje: porcentajeMorosidad
    },
  ] : []

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
            <h1 className="text-3xl font-bold text-gray-900">Análisis y Gráficos</h1>
            <p className="text-gray-600">
              Bienvenido, {userName} • Visualizaciones y análisis detallados
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

      {/* Análisis de Morosidad */}
      {loadingDashboard ? (
        <Card>
          <CardContent className="p-6">
            <div className="animate-pulse">
              <div className="h-64 bg-gray-200 rounded"></div>
            </div>
          </CardContent>
        </Card>
      ) : datosAnalisisMorosidad.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <BarChart3 className="mr-2 h-5 w-5" />
                Análisis de Morosidad
              </CardTitle>
              <CardDescription>Total Financiamiento vs Cartera Cobrada</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={datosAnalisisMorosidad}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip
                    formatter={(value: number, name: string, props: any) => {
                      const porcentaje = props.payload.porcentaje || 0
                      return [
                        `${formatCurrency(value)} (${porcentaje.toFixed(1)}%)`,
                        name
                      ]
                    }}
                  />
                  <Legend />
                  <Bar
                    dataKey="value"
                    fill="#8884d8"
                    name="Monto"
                    label={(props: any) => {
                      const { payload, y } = props
                      const porcentaje = payload?.porcentaje || 0
                      return (
                        <text
                          x={props.x + (props.width || 0) / 2}
                          y={y}
                          dy={-8}
                          fill={payload?.color || '#000'}
                          fontSize={12}
                          fontWeight="bold"
                          textAnchor="middle"
                        >
                          {`${porcentaje.toFixed(1)}%`}
                        </text>
                      )
                    }}
                  >
                    {datosAnalisisMorosidad.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <PieChart className="mr-2 h-5 w-5" />
                Análisis de Morosidad
              </CardTitle>
              <CardDescription>Distribución por tipo</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <RechartsPieChart>
                  <Pie
                    data={datosAnalisisMorosidad}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {datosAnalisisMorosidad.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  <Legend />
                </RechartsPieChart>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2">
                {totalFinanciamiento > 0 && (
                  <div className="flex justify-between items-center p-2 bg-blue-50 rounded-lg">
                    <span className="text-sm font-medium text-blue-900">Total Financiamiento</span>
                    <Badge variant="outline" className="bg-blue-100 text-blue-800">
                      {formatCurrency(totalFinanciamiento)} ({porcentajeFinanciamiento.toFixed(1)}%)
                    </Badge>
                  </div>
                )}
                {carteraCobrada > 0 && (
                  <div className="flex justify-between items-center p-2 bg-green-50 rounded-lg">
                    <span className="text-sm font-medium text-green-900">Cartera Cobrada</span>
                    <Badge variant="outline" className="bg-green-100 text-green-800">
                      {formatCurrency(carteraCobrada)} ({porcentajeCobrado.toFixed(1)}%)
                    </Badge>
                  </div>
                )}
                {morosidadDiferencia > 0 && (
                  <div className="flex justify-between items-center p-2 bg-red-50 rounded-lg">
                    <span className="text-sm font-medium text-red-900">Morosidad</span>
                    <Badge variant="outline" className="bg-red-100 text-red-800">
                      {formatCurrency(morosidadDiferencia)} ({porcentajeMorosidad.toFixed(1)}%)
                    </Badge>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" />
              Análisis de Morosidad
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-64 text-gray-500">
              No hay datos disponibles para el período seleccionado
            </div>
          </CardContent>
        </Card>
      )}

      {/* Evolución Mensual */}
      {data.evolucion_mensual && data.evolucion_mensual.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <LineChart className="mr-2 h-5 w-5" />
              Evolución Mensual
            </CardTitle>
            <CardDescription>Últimos 6 meses</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={data.evolucion_mensual}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="mes" />
                <YAxis />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend />
                <Area type="monotone" dataKey="cartera" stackId="1" stroke="#3b82f6" fill="#3b82f6" name="Cartera" />
                <Area type="monotone" dataKey="cobrado" stackId="1" stroke="#10b981" fill="#10b981" name="Cobrado" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Cobros Diarios */}
      {loadingCobrosDiarios ? (
        <Card>
          <CardContent className="p-6">
            <div className="animate-pulse">
              <div className="h-64 bg-gray-200 rounded"></div>
            </div>
          </CardContent>
        </Card>
      ) : cobrosDiarios.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" />
              Cobros Diarios
            </CardTitle>
            <CardDescription>
              Total a cobrar por día (barras) y total cobrado embebido (últimos 30 días)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart
                data={cobrosDiarios}
                margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="dia"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  interval={Math.floor(cobrosDiarios.length / 15)}
                />
                <YAxis yAxisId="left" />
                <Tooltip
                  formatter={(value: number) => formatCurrency(value)}
                  labelFormatter={(label) => {
                    const item = cobrosDiarios.find((d) => d.dia === label)
                    return item ? `${item.dia_semana} ${item.dia}` : label
                  }}
                />
                <Legend />
                <Bar
                  yAxisId="left"
                  dataKey="total_a_cobrar"
                  name="Total a Cobrar"
                  fill="#ef4444"
                  radius={[4, 4, 0, 0]}
                >
                  {cobrosDiarios.map((entry, index) => (
                    <Cell
                      key={`cell-a-${index}`}
                      fill={entry.total_a_cobrar > 0 ? '#ef4444' : '#f3f4f6'}
                    />
                  ))}
                </Bar>
                <Bar
                  yAxisId="left"
                  dataKey="total_cobrado"
                  name="Total Cobrado"
                  fill="#10b981"
                  radius={[3, 3, 0, 0]}
                >
                  {cobrosDiarios.map((entry, index) => (
                    <Cell
                      key={`cell-b-${index}`}
                      fill={entry.total_cobrado > 0 ? '#10b981' : 'transparent'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" />
              Cobros Diarios
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-64 text-gray-500">
              No hay datos disponibles
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

