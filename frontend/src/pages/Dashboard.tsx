import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { 
  DollarSign, 
  Users, 
  CreditCard, 
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  Target,
  BarChart3,
  PieChart,
  LineChart,
  Calendar,
  RefreshCw,
  Eye,
  Activity,
  Zap,
  Award,
  Building2,
  Shield,
  Filter,
  X
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency, formatPercentage } from '@/utils'
import { apiClient } from '@/services/api'
import { userService, User } from '@/services/userService'
import { PagosKPIs } from '@/components/pagos/PagosKPIs'
import { pagoService } from '@/services/pagoService'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
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
  Area
} from 'recharts'

// Tipos para Dashboard
interface DashboardData {
  cartera_total: number
  cartera_anterior?: number
  cartera_al_dia: number
  cartera_vencida: number
  porcentaje_mora: number
  porcentaje_mora_anterior?: number
  pagos_hoy: number
  monto_pagos_hoy: number
  clientes_activos: number
  clientes_mora: number
  clientes_anterior?: number
  meta_mensual: number
  avance_meta: number
  financieros?: {
    totalCobrado: number
    totalCobradoAnterior: number
    ingresosCapital: number
    ingresosInteres: number
    ingresosMora: number
    tasaRecuperacion: number
    tasaRecuperacionAnterior: number
  }
  cobranza?: {
    promedioDiasMora: number
    promedioDiasMoraAnterior: number
    porcentajeCumplimiento: number
    porcentajeCumplimientoAnterior: number
    clientesMora: number
  }
  evolucion_mensual?: Array<{
    mes: string
    cartera: number
    cobrado: number
    morosidad: number
  }>
}

// Mock data integrado - en producción vendría del backend
const mockData: DashboardData = {
  // KPIs Principales
  cartera_total: 485750.00,
  cartera_anterior: 462300.00,
  cartera_al_dia: 425250.00,
  cartera_vencida: 60500.00,
  porcentaje_mora: 12.5,
  porcentaje_mora_anterior: 15.2,
  pagos_hoy: 15,
  monto_pagos_hoy: 45000,
  clientes_activos: 150,
  clientes_mora: 24,
  clientes_anterior: 28,
  meta_mensual: 500000,
  avance_meta: 320000,
  
  // Métricas Financieras Detalladas
  financieros: {
    totalCobrado: 125400.00,
    totalCobradoAnterior: 118200.00,
    ingresosCapital: 89500.00,
    ingresosInteres: 28750.00,
    ingresosMora: 7150.00,
    tasaRecuperacion: 85.4,
    tasaRecuperacionAnterior: 82.1,
  },
  
  // Métricas de Cobranza
  cobranza: {
    promedioDiasMora: 8.5,
    promedioDiasMoraAnterior: 12.3,
    porcentajeCumplimiento: 87.6,
    porcentajeCumplimientoAnterior: 84.2,
    clientesMora: 23,
  },
  
}

const mockEvolucionMensual = [
  { mes: 'Ene', cartera: 420000, cobrado: 95000, morosidad: 18.2 },
  { mes: 'Feb', cartera: 435000, cobrado: 102000, morosidad: 16.8 },
  { mes: 'Mar', cartera: 448000, cobrado: 108000, morosidad: 15.5 },
  { mes: 'Abr', cartera: 456000, cobrado: 112000, morosidad: 14.2 },
  { mes: 'May', cartera: 462300, cobrado: 118200, morosidad: 15.2 },
  { mes: 'Jun', cartera: 475000, cobrado: 122000, morosidad: 13.8 },
  { mes: 'Jul', cartera: 485750, cobrado: 125400, morosidad: 12.5 },
]


const mockRecentPayments = [
  { id: 1, cliente: 'Juan Pérez', monto: 850, fecha: '2024-01-15', estado: 'confirmado' },
  { id: 2, cliente: 'María García', monto: 1200, fecha: '2024-01-15', estado: 'confirmado' },
  { id: 3, cliente: 'Carlos López', monto: 950, fecha: '2024-01-15', estado: 'pendiente' },
  { id: 4, cliente: 'Ana Rodríguez', monto: 750, fecha: '2024-01-14', estado: 'confirmado' },
]

const mockAlerts = [
  { id: 1, tipo: 'vencimiento', mensaje: '5 cuotas vencen hoy', prioridad: 'alta' },
  { id: 2, tipo: 'mora', mensaje: '3 clientes entraron en mora', prioridad: 'alta' },
  { id: 3, tipo: 'pendiente', mensaje: '2 pagos pendientes de confirmación', prioridad: 'media' },
]

export function Dashboard() {
  const { user } = useSimpleAuth()
  const userRole = user?.is_admin ? 'ADMIN' : 'USER'  // Cambio clave: rol → is_admin
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'
  const isAdmin = user?.is_admin || false  // Cambio clave: rol → is_admin
  const canViewAllClients = true // Todos pueden ver todos los clientes

  // Estados para datos reales
  const [usuarios, setUsuarios] = useState<User[]>([])
  const [usuariosLoading, setUsuariosLoading] = useState(true)
  const [usuariosError, setUsuariosError] = useState<string | null>(null)
  const [periodo, setPeriodo] = useState('mes')
  const [isRefreshing, setIsRefreshing] = useState(false)
  
  // Estados para filtros (usar tipo centralizado)
  const [filtros, setFiltros] = useState<DashboardFiltros>({})
  const [showFiltros, setShowFiltros] = useState(false)
  
  // ✅ Hook centralizado para manejar filtros - cualquier KPI nuevo debe usar esto
  const {
    construirParams,
    construirFiltrosObject,
    tieneFiltrosActivos,
    cantidadFiltrosActivos,
  } = useDashboardFiltros(filtros)

  // Cargar usuarios reales
  useEffect(() => {
    const cargarUsuarios = async () => {
      try {
        setUsuariosLoading(true)
        setUsuariosError(null)
        const response = await userService.listarUsuarios(1, 100)
        if (response.items && Array.isArray(response.items)) {
          setUsuarios(response.items)
        } else {
          setUsuarios([])
        }
      } catch (error: any) {
        console.error('Error cargando usuarios:', error)
        
        // Manejar error 403 (Forbidden) - Usuario normal sin permisos
        if (error.response?.status === 403) {
          console.log('ℹ️ Usuario normal - Sin permisos para ver lista de usuarios')
          setUsuarios([])
          setUsuariosError(null) // No mostrar error para usuarios normales
        } else {
          setUsuariosError('Error al cargar usuarios')
          setUsuarios([])
        }
      } finally {
        setUsuariosLoading(false)
      }
    }

    cargarUsuarios()
  }, [])

  // Cargar opciones de filtros
  const { data: opcionesFiltros } = useQuery({
    queryKey: ['dashboard-filtros-opciones'],
    queryFn: async () => {
      try {
        return await apiClient.get('/api/v1/dashboard/opciones-filtros')
      } catch (error) {
        console.warn('Error cargando opciones de filtros:', error)
        return { analistas: [], concesionarios: [], modelos: [] }
      }
    },
    staleTime: 30 * 60 * 1000, // 30 minutos - las opciones no cambian frecuentemente
  })

  // ✅ Usar función centralizada del hook para construir parámetros
  const construirParamsDashboard = () => construirParams(periodo)

  // ✅ CORRECCIÓN: Conectar a endpoints reales del backend con tipos explícitos
  const { data: dashboardData, isLoading: loadingDashboard, refetch: refetchDashboard } = useQuery({
    queryKey: ['dashboard', periodo, filtros],
    queryFn: async (): Promise<DashboardData> => {
      try {
        const params = construirParamsDashboard()
        const response = await apiClient.get(`/api/v1/dashboard/admin?${params}`)
        return response as DashboardData
      } catch (error) {
        console.warn('Error cargando dashboard desde backend, usando datos mock:', error)
        return mockData // Fallback a datos mock
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutos
    refetchInterval: 10 * 60 * 1000, // Actualizar cada 10 minutos
    initialData: mockData, // Datos iniciales mientras carga
  })

  // ✅ Query de KPIs adicionales - usa filtros automáticos del hook
  const { data: kpisData, isLoading: loadingKpis } = useQuery({
    queryKey: ['kpis', filtros],
    queryFn: async (): Promise<DashboardData> => {
      try {
        const params = construirFiltrosObject()
        const queryParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })
        const queryString = queryParams.toString()
        const response = await apiClient.get(
          `/api/v1/kpis/dashboard${queryString ? '?' + queryString : ''}`
        )
        return response as DashboardData
      } catch (error) {
        console.warn('Error cargando KPIs desde backend, usando datos mock:', error)
        return mockData // Fallback a datos mock
      }
    },
    staleTime: 5 * 60 * 1000,
    initialData: mockData, // Datos iniciales mientras carga
  })

  // Usar datos del backend si están disponibles, sino usar mock
  const data: DashboardData = dashboardData || mockData
  const isLoadingData = loadingDashboard || loadingKpis

  const calcularVariacion = (actual: number, anterior?: number) => {
    if (!anterior || anterior === 0) {
      return {
        valor: 0,
        esPositivo: true,
        icono: TrendingUp,
        color: 'text-gray-600',
        bgColor: 'bg-gray-50'
      }
    }
    
    const variacion = ((actual - anterior) / anterior) * 100
    return {
      valor: variacion,
      esPositivo: variacion > 0,
      icono: variacion > 0 ? TrendingUp : TrendingDown,
      color: variacion > 0 ? 'text-green-600' : 'text-red-600',
      bgColor: variacion > 0 ? 'bg-green-50' : 'bg-red-50'
    }
  }

  // Calcular KPIs reales de usuarios
  const usuariosActivos = usuarios.filter(u => u.is_active).length
  const usuariosInactivos = usuarios.filter(u => !u.is_active).length
  const usuariosAdmin = usuarios.filter(u => u.is_admin).length  // Cambio clave: rol → is_admin
  const usuariosUser = usuarios.filter(u => !u.is_admin).length  // Cambio clave: rol → is_admin
  const porcentajeActivos = usuarios.length > 0 ? (usuariosActivos / usuarios.length) * 100 : 0

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      // ✅ CORRECCIÓN: Refrescar datos reales del backend
      await Promise.all([
        refetchDashboard(),
        // Invalidar también queries de clientes para datos actualizados
        // queryClient.invalidateQueries({ queryKey: ['clientes'] })
      ])
    } catch (error) {
      console.error('Error al refrescar dashboard:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  // KPIs Principales con tendencias (incluyendo datos reales de usuarios)
  const kpiCards = [
    {
      title: 'Total Usuarios',
      value: usuariosLoading ? '...' : usuarios.length.toString(),
      description: usuariosError ? 'Error al cargar' : `${usuariosActivos} activos`,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      variacion: { valor: 0, esPositivo: true, icono: TrendingUp, color: 'text-gray-600', bgColor: 'bg-gray-50' },
      status: 'excellent'
    },
    {
      title: 'Usuarios Activos',
      value: usuariosLoading ? '...' : usuariosActivos.toString(),
      description: usuariosError ? 'Error al cargar' : `${porcentajeActivos.toFixed(1)}% del total`,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      variacion: { valor: 0, esPositivo: true, icono: TrendingUp, color: 'text-green-600', bgColor: 'bg-green-50' },
      status: 'good'
    },
    {
      title: 'Administradores',
      value: usuariosLoading ? '...' : usuariosAdmin.toString(),
      description: usuariosError ? 'Error al cargar' : 'Acceso completo al sistema',
      icon: Shield,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      variacion: { valor: 0, esPositivo: true, icono: TrendingUp, color: 'text-gray-600', bgColor: 'bg-gray-50' },
      status: 'warning'
    },
    {
      title: 'Cartera Total',
      value: formatCurrency(data.cartera_total),
      description: 'Total de préstamos activos',
      icon: DollarSign,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      variacion: calcularVariacion(data.cartera_total, data.cartera_anterior),
      status: 'excellent'
    }
  ]

  const progressPercentage = (data.avance_meta / data.meta_mensual) * 100

  // ✅ Query para estadísticas de pagos - usa filtros automáticos del hook
  const { data: pagosStats, isLoading: pagosStatsLoading } = useQuery({
    queryKey: ['pagos-stats', filtros],
    queryFn: () => pagoService.getStats(construirFiltrosObject()),
    refetchInterval: 60000, // Refrescar cada minuto
  })

  const handleLimpiarFiltros = () => {
    setFiltros({})
  }

  // Datos para gráficos
  const evolucionMensual = (data.evolucion_mensual && data.evolucion_mensual.length > 0) 
    ? data.evolucion_mensual 
    : mockEvolucionMensual
  const datosIngresos = data.financieros && data.financieros.ingresosCapital > 0 ? [
    { name: 'Capital', value: data.financieros.ingresosCapital, color: '#3b82f6' },
    { name: 'Intereses', value: data.financieros.ingresosInteres, color: '#10b981' },
    { name: 'Mora', value: data.financieros.ingresosMora, color: '#ef4444' },
  ] : (mockData.financieros ? [
    { name: 'Capital', value: mockData.financieros.ingresosCapital || 0, color: '#3b82f6' },
    { name: 'Intereses', value: mockData.financieros.ingresosInteres || 0, color: '#10b981' },
    { name: 'Mora', value: mockData.financieros.ingresosMora || 0, color: '#ef4444' },
  ] : [
    { name: 'Capital', value: 0, color: '#3b82f6' },
    { name: 'Intereses', value: 0, color: '#10b981' },
    { name: 'Mora', value: 0, color: '#ef4444' },
  ])

  return (
    <div className="space-y-6">
      {/* Header con controles */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard Ejecutivo</h1>
          <p className="text-gray-600">
            Bienvenido, {userName} • Resumen completo del sistema de financiamiento
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Select value={periodo} onValueChange={setPeriodo}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dia">Hoy</SelectItem>
              <SelectItem value="semana">Esta semana</SelectItem>
              <SelectItem value="mes">Este mes</SelectItem>
              <SelectItem value="año">Este año</SelectItem>
            </SelectContent>
          </Select>
          
          {/* Popover de Filtros */}
          <Popover open={showFiltros} onOpenChange={setShowFiltros}>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm">
                <Filter className="mr-2 h-4 w-4" />
                Filtros
                {tieneFiltrosActivos && (
                  <Badge variant="secondary" className="ml-2">
                    {cantidadFiltrosActivos}
                  </Badge>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-96" align="end">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold">Filtros Generales</h4>
                  {tieneFiltrosActivos && (
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={handleLimpiarFiltros}
                    >
                      <X className="h-4 w-4 mr-1" />
                      Limpiar
                    </Button>
                  )}
                </div>
                
                {/* Analista */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Analista</label>
                  <Select 
                    value={filtros.analista || ''} 
                    onValueChange={(value) => setFiltros(prev => ({ ...prev, analista: value || undefined }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Todos los analistas" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Todos los analistas</SelectItem>
                      {opcionesFiltros?.analistas?.map((a: string) => (
                        <SelectItem key={a} value={a}>{a}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Concesionario */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Concesionario</label>
                  <Select 
                    value={filtros.concesionario || ''} 
                    onValueChange={(value) => setFiltros(prev => ({ ...prev, concesionario: value || undefined }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Todos los concesionarios" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Todos los concesionarios</SelectItem>
                      {opcionesFiltros?.concesionarios?.map((c: string) => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Modelo */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Modelo</label>
                  <Select 
                    value={filtros.modelo || ''} 
                    onValueChange={(value) => setFiltros(prev => ({ ...prev, modelo: value || undefined }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Todos los modelos" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Todos los modelos</SelectItem>
                      {opcionesFiltros?.modelos?.map((m: string) => (
                        <SelectItem key={m} value={m}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Rango de Fechas */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Fecha Desde</label>
                    <Input 
                      type="date"
                      value={filtros.fecha_inicio || ''}
                      onChange={(e) => setFiltros(prev => ({ ...prev, fecha_inicio: e.target.value || undefined }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Fecha Hasta</label>
                    <Input 
                      type="date"
                      value={filtros.fecha_fin || ''}
                      onChange={(e) => setFiltros(prev => ({ ...prev, fecha_fin: e.target.value || undefined }))}
                    />
                  </div>
                </div>
              </div>
            </PopoverContent>
          </Popover>

          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </motion.div>

      {/* KPIs Principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiCards.map((kpi, index) => (
          <motion.div
            key={kpi.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="hover:shadow-lg transition-all duration-200 border-l-4 border-l-blue-500">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-gray-600">
                        {kpi.title}
                      </p>
                      <div className={`p-2 rounded-full ${kpi.bgColor}`}>
                        <kpi.icon className={`w-5 h-5 ${kpi.color}`} />
                      </div>
                    </div>
                    <p className="text-3xl font-bold text-gray-900 mb-1">
                      {kpi.value}
                    </p>
                    <p className="text-sm text-gray-500 mb-3">
                      {kpi.description}
                    </p>
                    <div className="flex items-center">
                      <kpi.variacion.icono className={`w-4 h-4 mr-1 ${kpi.variacion.color}`} />
                      <span className={`text-sm font-medium ${kpi.variacion.color}`}>
                        {Math.abs(kpi.variacion.valor).toFixed(1)}%
                      </span>
                      <span className="text-sm text-gray-500 ml-1">vs mes anterior</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

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

      {/* Métricas Financieras Detalladas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Total Cobrado */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <CreditCard className="mr-2 h-5 w-5 text-green-600" />
              Total Cobrado
            </CardTitle>
            <CardDescription>Recaudación del período actual</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600 mb-2">
              {formatCurrency(data.financieros?.totalCobrado || 0)}
            </div>
            <div className="flex items-center text-sm">
              {(() => {
                const variacion = calcularVariacion(
                  data.financieros?.totalCobrado || 0,
                  data.financieros?.totalCobradoAnterior
                )
                const IconComponent = variacion.icono
                return (
                  <>
                    <IconComponent className={`h-4 w-4 mr-1 ${variacion.color}`} />
                    <span className={variacion.color}>
                      {Math.abs(variacion.valor).toFixed(1)}% vs mes anterior
                    </span>
                  </>
                )
              })()}
            </div>
          </CardContent>
        </Card>

        {/* Tasa de Recuperación */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Target className="mr-2 h-5 w-5 text-blue-600" />
              Tasa de Recuperación
            </CardTitle>
            <CardDescription>Eficiencia en cobranza</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600 mb-2">
              {data.financieros?.tasaRecuperacion?.toFixed(1) || 0}%
            </div>
            <div className="flex items-center text-sm">
              {(() => {
                const variacion = calcularVariacion(
                  data.financieros?.tasaRecuperacion || 0,
                  data.financieros?.tasaRecuperacionAnterior
                )
                const IconComponent = variacion.icono
                return (
                  <>
                    <IconComponent className={`h-4 w-4 mr-1 ${variacion.color}`} />
                    <span className={variacion.color}>
                      {Math.abs(variacion.valor).toFixed(1)}% vs mes anterior
                    </span>
                  </>
                )
              })()}
            </div>
          </CardContent>
        </Card>

        {/* Progreso de Meta Mensual */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="mr-2 h-5 w-5 text-purple-600" />
              Meta Mensual
            </CardTitle>
            <CardDescription>Avance hacia la meta de recaudación</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">
                  Recaudado: {formatCurrency(data.avance_meta)}
                </span>
                <span className="text-gray-600">
                  Meta: {formatCurrency(data.meta_mensual)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${progressPercentage}%` }}
                ></div>
              </div>
              <div className="text-center">
                <span className="text-lg font-bold text-purple-600">
                  {progressPercentage.toFixed(1)}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gráficos y Análisis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evolución Mensual - Gráfico de Líneas */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <LineChart className="mr-2 h-5 w-5" />
              Evolución Mensual
            </CardTitle>
            <CardDescription>Comparativo de cartera, cobrado y morosidad</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={evolucionMensual}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="mes" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip 
                  formatter={(value: any, name: string) => {
                    if (name === 'Morosidad %') return `${value}%`
                    return formatCurrency(value)
                  }}
                />
                <Legend />
                <Area 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="cartera" 
                  stroke="#6366f1" 
                  fill="#6366f1" 
                  fillOpacity={0.3}
                  name="Cartera"
                />
                <Area 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="cobrado" 
                  stroke="#10b981" 
                  fill="#10b981" 
                  fillOpacity={0.3}
                  name="Cobrado"
                />
                <Area 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="morosidad" 
                  stroke="#ef4444" 
                  fill="#ef4444" 
                  fillOpacity={0.1}
                  name="Morosidad %"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Distribución de Ingresos - Gráfico de Barras */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" />
              Distribución de Ingresos
            </CardTitle>
            <CardDescription>Desglose por tipo de ingreso</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={datosIngresos}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend />
                <Bar dataKey="value" fill="#8884d8" name="Monto">
                  {datosIngresos.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Métricas Detalladas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Ingresos por Tipo - Gráfico de Pastel */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <PieChart className="mr-2 h-5 w-5" />
              Ingresos por Tipo
            </CardTitle>
            <CardDescription>Desglose de ingresos por categoría</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <RechartsPieChart>
                <Pie
                  data={datosIngresos}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {datosIngresos.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend />
              </RechartsPieChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between items-center p-2 bg-blue-50 rounded-lg">
                <span className="text-sm font-medium text-blue-900">Capital</span>
                <Badge variant="outline" className="bg-blue-100 text-blue-800">
                  {formatCurrency(data.financieros?.ingresosCapital || 0)}
                </Badge>
              </div>
              <div className="flex justify-between items-center p-2 bg-green-50 rounded-lg">
                <span className="text-sm font-medium text-green-900">Intereses</span>
                <Badge variant="outline" className="bg-green-100 text-green-800">
                  {formatCurrency(data.financieros?.ingresosInteres || 0)}
                </Badge>
              </div>
              <div className="flex justify-between items-center p-2 bg-red-50 rounded-lg">
                <span className="text-sm font-medium text-red-900">Mora</span>
                <Badge variant="outline" className="bg-red-100 text-red-800">
                  {formatCurrency(data.financieros?.ingresosMora || 0)}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Métricas de Cobranza - Gráfico de Barras */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" />
              Métricas de Cobranza
            </CardTitle>
            <CardDescription>Indicadores de eficiencia</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={[
                { 
                  name: 'Cumplimiento', 
                  valor: data.cobranza?.porcentajeCumplimiento ?? mockData.cobranza?.porcentajeCumplimiento ?? 0,
                  color: '#10b981'
                },
                { 
                  name: 'Prom. Días Mora', 
                  valor: data.cobranza?.promedioDiasMora ?? mockData.cobranza?.promedioDiasMora ?? 0,
                  color: '#f59e0b'
                },
                { 
                  name: 'Clientes Mora', 
                  valor: data.cobranza?.clientesMora ?? mockData.cobranza?.clientesMora ?? 0,
                  color: '#ef4444'
                }
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="valor" fill="#8884d8">
                  {[
                    data.cobranza?.porcentajeCumplimiento ?? mockData.cobranza?.porcentajeCumplimiento ?? 0,
                    data.cobranza?.promedioDiasMora ?? mockData.cobranza?.promedioDiasMora ?? 0,
                    data.cobranza?.clientesMora ?? mockData.cobranza?.clientesMora ?? 0
                  ].map((_, index) => {
                    const colors = ['#10b981', '#f59e0b', '#ef4444']
                    return <Cell key={`cell-${index}`} fill={colors[index]} />
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between items-center p-2 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium">Promedio días mora</span>
                <Badge variant="outline">
                  {data.cobranza?.promedioDiasMora?.toFixed(1) || 0} días
                </Badge>
              </div>
              <div className="flex justify-between items-center p-2 bg-green-50 rounded-lg">
                <span className="text-sm font-medium text-green-900">% Cumplimiento</span>
                <Badge className="bg-green-600 text-white">
                  {data.cobranza?.porcentajeCumplimiento?.toFixed(1) || 0}%
                </Badge>
              </div>
              <div className="flex justify-between items-center p-2 bg-red-50 rounded-lg">
                <span className="text-sm font-medium text-red-900">Clientes en mora</span>
                <Badge className="bg-red-600 text-white">
                  {data.cobranza?.clientesMora || 0}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

      </div>

      {/* Alertas y Actividad Reciente */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alertas Importantes */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertTriangle className="mr-2 h-5 w-5 text-orange-600" />
              Alertas Importantes
            </CardTitle>
            <CardDescription>Notificaciones que requieren atención</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockAlerts.map((alert) => (
                <div key={alert.id} className={`p-3 rounded-lg border-l-4 ${
                  alert.prioridad === 'alta' 
                    ? 'bg-red-50 border-red-500' 
                    : 'bg-yellow-50 border-yellow-500'
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{alert.mensaje}</p>
                      <p className="text-sm text-gray-600 capitalize">
                        Tipo: {alert.tipo} • Prioridad: {alert.prioridad}
                      </p>
                    </div>
                    <Badge variant={alert.prioridad === 'alta' ? 'destructive' : 'secondary'}>
                      {alert.prioridad}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Pagos Recientes */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <CreditCard className="mr-2 h-5 w-5 text-green-600" />
              Pagos Recientes
            </CardTitle>
            <CardDescription>Últimas transacciones procesadas</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockRecentPayments.map((payment) => (
                <div key={payment.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={`w-2 h-2 rounded-full ${
                      payment.estado === 'confirmado' ? 'bg-green-500' : 'bg-yellow-500'
                    }`}></div>
                    <div>
                      <p className="font-medium text-gray-900">{payment.cliente}</p>
                      <p className="text-sm text-gray-600">{payment.fecha}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-gray-900">{formatCurrency(payment.monto)}</p>
                    <Badge variant={payment.estado === 'confirmado' ? 'default' : 'secondary'}>
                      {payment.estado}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}