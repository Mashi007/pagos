import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts'
import { BaseModal } from '../BaseModal'
import { DashboardFiltrosPanel } from '../DashboardFiltrosPanel'
import { useDashboardFiltros, type DashboardFiltros } from '../../../hooks/useDashboardFiltros'
import { apiClient } from '../../../services/api'
import { formatCurrency } from '../../../utils'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select'
import { RefreshCw } from 'lucide-react'
import { Button } from '../../../components/ui/button'

interface TendenciasModalProps {
  isOpen: boolean
  onClose: () => void
}

interface DiaTendenciaData {
  fecha: string
  fecha_formateada: string
  cuentas_por_cobrar: number | null
  cuotas_en_dias: number | null
  cuentas_por_cobrar_proyectado: number | null
  cuotas_en_dias_proyectado: number | null
  es_proyeccion: boolean
}

interface TendenciasResponse {
  datos: DiaTendenciaData[]
  fecha_inicio: string
  fecha_fin: string
  meses_proyeccion: number
  ultima_actualizacion: string
}

type GranularidadConfig = 'mes_actual' | 'proximos_n_dias' | 'hasta_fin_anio' | 'personalizado'

export function TendenciasModal({ isOpen, onClose }: TendenciasModalProps) {
  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [mesesProyeccion, setMesesProyeccion] = useState(6)
  const [granularidad, setGranularidad] = useState<GranularidadConfig>('mes_actual')
  const [diasPersonalizado, setDiasPersonalizado] = useState(30)
  const { construirFiltrosObject } = useDashboardFiltros(filtros)

  // ConfiguraciÃ³n de polling (cada 10 minutos por defecto)
  const POLLING_INTERVAL = 10 * 60 * 1000 // 10 minutos

  // Cargar opciones de filtros
  const { data: opcionesFiltros, isLoading: loadingOpcionesFiltros, isError: errorOpcionesFiltros } = useQuery({
    queryKey: ['opciones-filtros'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')
      return response as { analistas: string[]; concesionarios: string[]; modelos: string[] }
    },
  })

  // Cargar datos de tendencias
  const { data: tendenciasData, isLoading: loadingTendencias, refetch } = useQuery({
    queryKey: ['cuentas-cobrar-tendencias', filtros, mesesProyeccion, granularidad, diasPersonalizado],
    queryFn: async (): Promise<TendenciasResponse> => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses_proyeccion', mesesProyeccion.toString())
      queryParams.append('granularidad', granularidad)
      if (granularidad === 'proximos_n_dias') {
        queryParams.append('dias', diasPersonalizado.toString())
      }
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const queryString = queryParams.toString()
      const response = await apiClient.get(
        `/api/v1/dashboard/cuentas-cobrar-tendencias?${queryString}`
      ) as TendenciasResponse
      return response || { datos: [], fecha_inicio: '', fecha_fin: '', meses_proyeccion: 6, ultima_actualizacion: '' }
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: isOpen ? POLLING_INTERVAL : false, // Polling solo si el modal estÃ¡ abierto
  })

  // Efecto para actualizaciÃ³n automÃ¡tica cuando cambian los crÃ©ditos/amortizaciones
  useEffect(() => {
    if (!isOpen) return

    const intervalId = setInterval(() => {
      refetch()
    }, POLLING_INTERVAL)

    return () => clearInterval(intervalId)
  }, [isOpen, refetch])

  const [isRefreshing, setIsRefreshing] = useState(false)
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  // Separar datos histÃ³ricos de proyecciones
  const datosHistoricos = tendenciasData?.datos.filter((d) => !d.es_proyeccion) || []
  const datosProyeccion = tendenciasData?.datos.filter((d) => d.es_proyeccion) || []
  const fechaDivision = datosHistoricos.length > 0 ? datosHistoricos[datosHistoricos.length - 1].fecha : null

  // Combinar datos para el grÃ¡fico
  const datosGrafico = tendenciasData?.datos || []

  // Tooltip personalizado
  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name?: string; value?: number; dataKey?: string; color?: string; payload?: Record<string, unknown> }>; label?: string | number }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold mb-2">{label}</p>
          {payload.map((entry, index: number) => {
            const dataKey = entry.dataKey || ''
            const value = entry.value
            const isProyectado = dataKey.includes('proyectado')
            return (
              <p key={index} className="text-sm" style={{ color: entry.color }}>
                {entry.name}:{' '}
                {dataKey.includes('cuotas_en_dias')
                  ? `${typeof value === 'number' ? value.toFixed(0) : 'N/A'} dÃ­as`
                  : typeof value === 'number'
                  ? formatCurrency(value)
                  : 'N/A'}
                {isProyectado && <span className="text-xs text-gray-500 ml-1">(proy.)</span>}
              </p>
            )
          })}
          {typeof data?.es_proyeccion === 'boolean' && data.es_proyeccion && (
            <p className="text-xs text-amber-600 mt-2 font-semibold">Datos proyectados</p>
          )}
        </div>
      )
    }
    return null
  }

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      title="Tendencias de Cuentas por Cobrar y Cuotas en DÃ­as"
      size="xlarge"
    >
      <div className="space-y-6">
        {/* Filtros y Configuraciones */}
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

          {/* Configuraciones adicionales */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Meses de ProyecciÃ³n:</label>
              <Select
                value={mesesProyeccion.toString()}
                onValueChange={(v) => setMesesProyeccion(Number(v))}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">3 meses</SelectItem>
                  <SelectItem value="6">6 meses</SelectItem>
                  <SelectItem value="12">12 meses</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Granularidad:</label>
              <Select
                value={granularidad}
                onValueChange={(v) => setGranularidad(v as GranularidadConfig)}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mes_actual">Mes Actual</SelectItem>
                  <SelectItem value="proximos_n_dias">PrÃ³ximos N DÃ­as</SelectItem>
                  <SelectItem value="hasta_fin_anio">Hasta Fin de AÃ±o</SelectItem>
                  <SelectItem value="personalizado">Personalizado</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {granularidad === 'proximos_n_dias' && (
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">DÃ­as:</label>
                <Select
                  value={diasPersonalizado.toString()}
                  onValueChange={(v) => setDiasPersonalizado(Number(v))}
                >
                  <SelectTrigger className="w-[100px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7">7 dÃ­as</SelectItem>
                    <SelectItem value="15">15 dÃ­as</SelectItem>
                    <SelectItem value="30">30 dÃ­as</SelectItem>
                    <SelectItem value="60">60 dÃ­as</SelectItem>
                    <SelectItem value="90">90 dÃ­as</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {tendenciasData?.ultima_actualizacion && (
              <div className="flex items-center gap-2 ml-auto">
                <RefreshCw className="h-4 w-4 text-gray-400 animate-spin" />
                <span className="text-xs text-gray-500">
                  Ãšltima actualizaciÃ³n: {new Date(tendenciasData.ultima_actualizacion).toLocaleString('es-ES')}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* GrÃ¡fico de Tendencias */}
        <Card>
          <CardHeader>
            <CardTitle>Cuentas por Cobrar y Cuotas en DÃ­as (con ProyecciÃ³n)</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingTendencias ? (
              <div className="h-[500px] flex items-center justify-center">
                <div className="animate-pulse text-gray-400">Cargando grÃ¡fico...</div>
              </div>
            ) : datosGrafico.length === 0 ? (
              <div className="h-[500px] flex items-center justify-center text-gray-500">
                No hay datos disponibles para el perÃ­odo seleccionado
              </div>
            ) : (
              <div className="space-y-6">
                {/* GrÃ¡fico 1: Cuentas por Cobrar */}
                <div>
                  <h3 className="text-lg font-semibold mb-3">Cuentas por Cobrar</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={datosGrafico} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorCuentas" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
                        </linearGradient>
                        <linearGradient id="colorCuentasProy" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="fecha_formateada"
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
                      {fechaDivision && (
                        <ReferenceLine
                          x={datosHistoricos[datosHistoricos.length - 1]?.fecha_formateada}
                          stroke="#ef4444"
                          strokeDasharray="5 5"
                          label={{ value: 'Inicio ProyecciÃ³n', position: 'top', fill: '#ef4444' }}
                        />
                      )}
                      <Area
                        type="monotone"
                        dataKey="cuentas_por_cobrar"
                        name="Cuentas por Cobrar (Real)"
                        stroke="#3b82f6"
                        fillOpacity={1}
                        fill="url(#colorCuentas)"
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="cuentas_por_cobrar_proyectado"
                        name="Cuentas por Cobrar (Proyectado)"
                        stroke="#3b82f6"
                        strokeDasharray="5 5"
                        fillOpacity={0.3}
                        fill="url(#colorCuentasProy)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* GrÃ¡fico 2: Cuotas en DÃ­as */}
                <div>
                  <h3 className="text-lg font-semibold mb-3">Cuotas en DÃ­as</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={datosGrafico} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="fecha_formateada"
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                      />
                      <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                        label={{ value: 'DÃ­as', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      {fechaDivision && (
                        <ReferenceLine
                          x={datosHistoricos[datosHistoricos.length - 1]?.fecha_formateada}
                          stroke="#ef4444"
                          strokeDasharray="5 5"
                          label={{ value: 'Inicio ProyecciÃ³n', position: 'top', fill: '#ef4444' }}
                        />
                      )}
                      <Line
                        type="monotone"
                        dataKey="cuotas_en_dias"
                        name="Cuotas en DÃ­as (Real)"
                        stroke="#10b981"
                        strokeWidth={3}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="cuotas_en_dias_proyectado"
                        name="Cuotas en DÃ­as (Proyectado)"
                        stroke="#10b981"
                        strokeDasharray="5 5"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </BaseModal>
  )
}

