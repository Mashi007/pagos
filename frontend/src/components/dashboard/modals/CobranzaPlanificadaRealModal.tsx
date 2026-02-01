import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
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
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import { apiClient } from '@/services/api'
import { formatCurrency } from '@/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { TrendingUp, TrendingDown, Target, CheckCircle2, XCircle } from 'lucide-react'

interface CobranzaPlanificadaRealModalProps {
  isOpen: boolean
  onClose: () => void
}

interface DiaData {
  fecha: string
  cobranza_planificada: number
  cobranza_real: number
  total_a_cobrar?: number
  pagos?: number
  morosidad?: number
}

interface CobranzaPorDiaResponse {
  dias: DiaData[]
}

type TipoGrafico = 'line' | 'bar' | 'area'

type VistaRapida = 'hoy' | 'manana' | 'ultimos3' | 'personalizado'

export function CobranzaPlanificadaRealModal({ isOpen, onClose }: CobranzaPlanificadaRealModalProps) {
  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [tipoGrafico, setTipoGrafico] = useState<TipoGrafico>('line')
  const [diasMostrar, setDiasMostrar] = useState<number>(30)
  const [vistaRapida, setVistaRapida] = useState<VistaRapida>('hoy')
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  // Calcular fechas según vista rápida
  const calcularFechasVista = (vista: VistaRapida) => {
    const hoy = new Date()
    hoy.setHours(0, 0, 0, 0)
    const manana = new Date(hoy)
    manana.setDate(manana.getDate() + 1)
    // Últimos 3 días: desde hace 2 días hasta hoy (3 días en total)
    const ultimos3Inicio = new Date(hoy)
    ultimos3Inicio.setDate(ultimos3Inicio.getDate() - 2)

    switch (vista) {
      case 'hoy':
        return {
          fecha_inicio: hoy.toISOString().split('T')[0],
          fecha_fin: hoy.toISOString().split('T')[0],
        }
      case 'manana':
        return {
          fecha_inicio: manana.toISOString().split('T')[0],
          fecha_fin: manana.toISOString().split('T')[0],
        }
      case 'ultimos3':
        return {
          fecha_inicio: ultimos3Inicio.toISOString().split('T')[0],
          fecha_fin: hoy.toISOString().split('T')[0],
        }
      default:
        // personalizado - usar días mostrar
        const fechaInicio = new Date(hoy)
        fechaInicio.setDate(fechaInicio.getDate() - (diasMostrar - 1))
        return {
          fecha_inicio: fechaInicio.toISOString().split('T')[0],
          fecha_fin: hoy.toISOString().split('T')[0],
        }
    }
  }

  // Cargar datos por día
  const fechasVista = calcularFechasVista(vistaRapida)
  const { data: cobranzaPorDiaData, isLoading: loadingPorDia, refetch } = useQuery({
    queryKey: ['cobranza-por-dia', filtros, vistaRapida, fechasVista],
    queryFn: async (): Promise<CobranzaPorDiaResponse> => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        // ✅ Evitar duplicar fecha_inicio y fecha_fin ya que se agregan manualmente después
        if (key !== 'fecha_inicio' && key !== 'fecha_fin' && value) {
          queryParams.append(key, value.toString())
        }
      })
      queryParams.append('fecha_inicio', fechasVista.fecha_inicio)
      queryParams.append('fecha_fin', fechasVista.fecha_fin)
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/cobranza-por-dia${queryString ? '?' + queryString : ''}`
      ) as CobranzaPorDiaResponse
      return response || { dias: [] }
    },
    staleTime: 5 * 60 * 1000,
  })

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  // Procesar datos para el gráfico
  const datosGrafico = useMemo(() => {
    if (!cobranzaPorDiaData?.dias) return []

    return cobranzaPorDiaData.dias.map((d) => {
      const fecha = new Date(d.fecha)
      const planificada = d.cobranza_planificada || d.total_a_cobrar || 0
      const real = d.cobranza_real || d.pagos || 0
      const diferencia = real - planificada
      const porcentajeCumplimiento = planificada > 0 ? (real / planificada) * 100 : 0

      return {
        fecha: d.fecha,
        fechaFormateada: fecha.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' }),
        fechaCompleta: fecha.toLocaleDateString('es-ES', {
          weekday: 'short',
          day: '2-digit',
          month: 'short'
        }),
        cobranza_planificada: planificada,
        cobranza_real: real,
        diferencia: diferencia,
        porcentaje_cumplimiento: porcentajeCumplimiento,
        cumplio_meta: real >= planificada,
      }
    })
  }, [cobranzaPorDiaData])

  // Calcular métricas agregadas
  const metricas = useMemo(() => {
    if (datosGrafico.length === 0) {
      return {
        totalPlanificada: 0,
        totalReal: 0,
        diferenciaTotal: 0,
        porcentajeCumplimiento: 0,
        diasCumplidos: 0,
        diasNoCumplidos: 0,
        promedioDiarioPlanificada: 0,
        promedioDiarioReal: 0,
      }
    }

    const totalPlanificada = datosGrafico.reduce((sum, d) => sum + d.cobranza_planificada, 0)
    const totalReal = datosGrafico.reduce((sum, d) => sum + d.cobranza_real, 0)
    const diferenciaTotal = totalReal - totalPlanificada
    const porcentajeCumplimiento = totalPlanificada > 0 ? (totalReal / totalPlanificada) * 100 : 0
    const diasCumplidos = datosGrafico.filter(d => d.cumplio_meta).length
    const diasNoCumplidos = datosGrafico.length - diasCumplidos
    const promedioDiarioPlanificada = totalPlanificada / datosGrafico.length
    const promedioDiarioReal = totalReal / datosGrafico.length

    return {
      totalPlanificada,
      totalReal,
      diferenciaTotal,
      porcentajeCumplimiento,
      diasCumplidos,
      diasNoCumplidos,
      promedioDiarioPlanificada,
      promedioDiarioReal,
    }
  }, [datosGrafico])

  // Tooltip personalizado
  const CustomTooltip = ({
    active,
    payload,
    label
  }: {
    active?: boolean
    payload?: Array<{
      name?: string
      value?: number
      color?: string
      dataKey?: string
      payload?: any
    }>
    label?: string | number
  }) => {
    if (active && payload && payload.length) {
      const data = payload[0]?.payload || payload[0]
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg min-w-[200px]">
          <p className="font-semibold mb-3 text-gray-800">{label}</p>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Planificada:</span>
              <span className="font-semibold text-blue-600">
                {formatCurrency(data?.cobranza_planificada || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Real:</span>
              <span className="font-semibold text-emerald-600">
                {formatCurrency(data?.cobranza_real || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center pt-2 border-t">
              <span className="text-sm text-gray-600">Diferencia:</span>
              <span className={`font-semibold ${data?.diferencia >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {data?.diferencia >= 0 ? '+' : ''}{formatCurrency(data?.diferencia || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Cumplimiento:</span>
              <span className={`font-semibold ${data?.porcentaje_cumplimiento >= 100 ? 'text-emerald-600' : 'text-orange-600'}`}>
                {data?.porcentaje_cumplimiento.toFixed(1) || 0}%
              </span>
            </div>
          </div>
        </div>
      )
    }
    return null
  }

  // Renderizar gráfico según tipo
  const renderGrafico = () => {
    const commonProps = {
      data: datosGrafico,
      margin: { top: 10, right: 30, left: 0, bottom: 0 },
    }

    switch (tipoGrafico) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="fechaFormateada"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar dataKey="cobranza_planificada" name="Cobranza Planificada" fill="#3b82f6" />
            <Bar dataKey="cobranza_real" name="Cobranza Real" fill="#10b981" />
          </BarChart>
        )
      case 'area':
        return (
          <AreaChart {...commonProps}>
            <defs>
              <linearGradient id="colorPlanificada" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorReal" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="fechaFormateada"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              angle={-45}
              textAnchor="end"
              height={80}
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
              dataKey="cobranza_planificada"
              name="Cobranza Planificada"
              stroke="#3b82f6"
              fillOpacity={1}
              fill="url(#colorPlanificada)"
            />
            <Area
              type="monotone"
              dataKey="cobranza_real"
              name="Cobranza Real"
              stroke="#10b981"
              fillOpacity={1}
              fill="url(#colorReal)"
            />
          </AreaChart>
        )
      default: // 'line'
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="fechaFormateada"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="cobranza_planificada"
              name="Cobranza Planificada"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="cobranza_real"
              name="Cobranza Real"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        )
    }
  }

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      title="Cobranza Planificada vs Real por Día"
      size="xlarge"
    >
      <div className="space-y-6">
        {/* Filtros y controles */}
        <div className="space-y-4">
          <DashboardFiltrosPanel
            filtros={filtros}
            setFiltros={setFiltros}
            onRefresh={handleRefresh}
            isRefreshing={isRefreshing}
            opcionesFiltros={opcionesFiltros}
            loadingOpcionesFiltros={loadingOpcionesFiltros}
            errorOpcionesFiltros={errorOpcionesFiltros}
          />

          {/* Controles de visualización */}
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                {/* Vistas rápidas */}
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">Vista rápida:</span>
                  <div className="flex gap-2">
                    <Button
                      variant={vistaRapida === 'hoy' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setVistaRapida('hoy')}
                    >
                      Hoy
                    </Button>
                    <Button
                      variant={vistaRapida === 'manana' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setVistaRapida('manana')}
                    >
                      Mañana
                    </Button>
                    <Button
                      variant={vistaRapida === 'ultimos3' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setVistaRapida('ultimos3')}
                    >
                      Últimos 3 días
                    </Button>
                    <Button
                      variant={vistaRapida === 'personalizado' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setVistaRapida('personalizado')}
                    >
                      Personalizado
                    </Button>
                  </div>
                </div>
                {/* Tipo de gráfico y días (solo visible en personalizado) */}
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Tipo de gráfico:</span>
                    <div className="flex gap-2">
                      <Button
                        variant={tipoGrafico === 'line' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setTipoGrafico('line')}
                      >
                        Líneas
                      </Button>
                      <Button
                        variant={tipoGrafico === 'bar' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setTipoGrafico('bar')}
                      >
                        Barras
                      </Button>
                      <Button
                        variant={tipoGrafico === 'area' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setTipoGrafico('area')}
                      >
                        Área
                      </Button>
                    </div>
                  </div>
                  {vistaRapida === 'personalizado' && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-700">Días a mostrar:</span>
                      <select
                        value={diasMostrar}
                        onChange={(e) => {
                          setDiasMostrar(Number(e.target.value))
                          setVistaRapida('personalizado')
                        }}
                        className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value={7}>7 días</option>
                        <option value={15}>15 días</option>
                        <option value={30}>30 días</option>
                        <option value={60}>60 días</option>
                        <option value={90}>90 días</option>
                      </select>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Métricas principales */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                <Target className="h-4 w-4 text-blue-600" />
                Total Planificada
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {formatCurrency(metricas.totalPlanificada)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Promedio diario: {formatCurrency(metricas.promedioDiarioPlanificada)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Total Real
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-600">
                {formatCurrency(metricas.totalReal)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Promedio diario: {formatCurrency(metricas.promedioDiarioReal)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                {metricas.diferenciaTotal >= 0 ? (
                  <TrendingUp className="h-4 w-4 text-emerald-600" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
                Diferencia
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${metricas.diferenciaTotal >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {metricas.diferenciaTotal >= 0 ? '+' : ''}{formatCurrency(metricas.diferenciaTotal)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {metricas.diferenciaTotal >= 0 ? 'Sobre meta' : 'Bajo meta'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                {metricas.porcentajeCumplimiento >= 100 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <XCircle className="h-4 w-4 text-orange-600" />
                )}
                Cumplimiento
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${metricas.porcentajeCumplimiento >= 100 ? 'text-emerald-600' : 'text-orange-600'}`}>
                {metricas.porcentajeCumplimiento.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {metricas.diasCumplidos} días cumplidos / {metricas.diasNoCumplidos} no cumplidos
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Gráfico principal */}
        <Card>
          <CardHeader>
            <CardTitle>Cobranza Planificada vs Real</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingPorDia ? (
              <div className="h-[500px] flex items-center justify-center">
                <div className="animate-pulse text-gray-400">Cargando gráfico...</div>
              </div>
            ) : datosGrafico.length === 0 ? (
              <div className="h-[500px] flex items-center justify-center text-gray-500">
                No hay datos disponibles para el período seleccionado
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={500}>
                {renderGrafico()}
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </BaseModal>
  )
}

