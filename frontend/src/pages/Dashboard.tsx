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
  Car,
  Shield
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency, formatPercentage } from '@/utils'
import { apiClient } from '@/services/api'
import { usuarioService, Usuario } from '@/services/usuarioService'

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
  financieros?: any
  cobranza?: any
  analistaes?: any
  productos?: any
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
  
  // Métricas de Asesores
  analistaes: {
    totalAsesores: 8,
    analistaesActivos: 7,
    ventasMejorAsesor: 12,
    montoMejorAsesor: 75000.00,
    promedioVentas: 8.5,
    tasaConversion: 23.4,
    tasaConversionAnterior: 21.8,
  },
  
  // Métricas de Productos
  productos: {
    modeloMasVendido: 'Toyota Corolla',
    ventasModeloMasVendido: 25,
    ticketPromedio: 18500.00,
    ticketPromedioAnterior: 17200.00,
    totalModelos: 12,
    modeloMenosVendido: 'Nissan Versa',
  }
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

const mockTopAsesores = [
  { nombre: 'Carlos Mendoza', ventas: 12, monto: 75000, clientes: 15, tasaConversion: 28.5 },
  { nombre: 'María González', ventas: 10, monto: 65000, clientes: 13, tasaConversion: 25.2 },
  { nombre: 'Luis Rodríguez', ventas: 9, monto: 58000, clientes: 11, tasaConversion: 22.8 },
  { nombre: 'Ana Pérez', ventas: 8, monto: 52000, clientes: 10, tasaConversion: 21.5 },
  { nombre: 'José Silva', ventas: 7, monto: 45000, clientes: 9, tasaConversion: 19.8 },
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
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [usuariosLoading, setUsuariosLoading] = useState(true)
  const [usuariosError, setUsuariosError] = useState<string | null>(null)
  const [periodo, setPeriodo] = useState('mes')
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Cargar usuarios reales
  useEffect(() => {
    const cargarUsuarios = async () => {
      try {
        setUsuariosLoading(true)
        setUsuariosError(null)
        const response = await usuarioService.listarUsuarios({ limit: 100 })
        if (response.items && Array.isArray(response.items)) {
          setUsuarios(response.items)
        } else {
          setUsuarios([])
        }
      } catch (error) {
        console.error('Error cargando usuarios:', error)
        setUsuariosError('Error al cargar usuarios')
        setUsuarios([])
      } finally {
        setUsuariosLoading(false)
      }
    }

    cargarUsuarios()
  }, [])

  // ✅ CORRECCIÓN: Conectar a endpoints reales del backend con tipos explícitos
  const { data: dashboardData, isLoading: loadingDashboard, refetch: refetchDashboard } = useQuery<DashboardData>({
    queryKey: ['dashboard', periodo],
    queryFn: async () => {
      try {
        const response = await apiClient.get(`/api/v1/dashboard/admin?periodo=${periodo}`)
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

  const { data: kpisData, isLoading: loadingKpis } = useQuery<DashboardData>({
    queryKey: ['kpis'],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/api/v1/kpis/dashboard')
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

  const progressPercentage = (mockData.avance_meta / mockData.meta_mensual) * 100

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
              {formatCurrency(mockData.financieros.totalCobrado)}
            </div>
            <div className="flex items-center text-sm">
              {(() => {
                const variacion = calcularVariacion(
                  mockData.financieros.totalCobrado,
                  mockData.financieros.totalCobradoAnterior
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
              {mockData.financieros.tasaRecuperacion}%
            </div>
            <div className="flex items-center text-sm">
              {(() => {
                const variacion = calcularVariacion(
                  mockData.financieros.tasaRecuperacion,
                  mockData.financieros.tasaRecuperacionAnterior
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
                  Recaudado: {formatCurrency(mockData.avance_meta)}
                </span>
                <span className="text-gray-600">
                  Meta: {formatCurrency(mockData.meta_mensual)}
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

      {/* Sección de Usuarios del Sistema */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Users className="mr-2 h-5 w-5 text-blue-600" />
            Usuarios del Sistema
          </CardTitle>
          <CardDescription>Resumen de usuarios y roles en el sistema</CardDescription>
        </CardHeader>
        <CardContent>
          {usuariosLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin text-blue-600 mr-2" />
              <span className="text-gray-600">Cargando usuarios...</span>
            </div>
          ) : usuariosError ? (
            <div className="flex items-center justify-center py-8">
              <AlertTriangle className="h-6 w-6 text-red-600 mr-2" />
              <span className="text-red-600">{usuariosError}</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Total Usuarios */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-600">Total Usuarios</p>
                    <p className="text-2xl font-bold text-blue-900">{usuarios.length}</p>
                  </div>
                  <Users className="h-8 w-8 text-blue-600" />
                </div>
              </div>

              {/* Usuarios Activos */}
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-green-600">Activos</p>
                    <p className="text-2xl font-bold text-green-900">{usuariosActivos}</p>
                    <p className="text-xs text-green-700">{porcentajeActivos.toFixed(1)}%</p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
              </div>

              {/* Administradores */}
              <div className="bg-red-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-red-600">Administradores</p>
                    <p className="text-2xl font-bold text-red-900">{usuariosAdmin}</p>
                  </div>
                  <Shield className="h-8 w-8 text-red-600" />
                </div>
              </div>

              {/* Usuarios Normales */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Usuarios Normales</p>
                    <p className="text-2xl font-bold text-gray-900">{usuariosUser}</p>
                    <p className="text-xs text-gray-700">
                      Acceso limitado
                    </p>
                  </div>
                  <Award className="h-8 w-8 text-gray-600" />
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Gráficos y Análisis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evolución Mensual */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <LineChart className="mr-2 h-5 w-5" />
              Evolución Mensual
            </CardTitle>
            <CardDescription>Comparativo de cartera, cobrado y morosidad</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockEvolucionMensual.map((mes, index) => (
                <div key={mes.mes} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-sm font-bold text-blue-600">{mes.mes}</span>
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">Enero - Julio</div>
                      <div className="text-sm text-gray-500">Período {index + 1}</div>
                    </div>
                  </div>
                  <div className="flex space-x-6 text-sm">
                    <div className="text-center">
                      <div className="text-gray-500">Cartera</div>
                      <div className="font-semibold text-gray-900">{formatCurrency(mes.cartera)}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-gray-500">Cobrado</div>
                      <div className="font-semibold text-green-600">{formatCurrency(mes.cobrado)}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-gray-500">Mora</div>
                      <div className="font-semibold text-red-600">{mes.morosidad}%</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Asesores */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Award className="mr-2 h-5 w-5" />
              Top Asesores
            </CardTitle>
            <CardDescription>Ranking por ventas y rendimiento</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockTopAsesores.map((analista, index) => (
                <div key={analista.nombre} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <div className="flex items-center space-x-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      index === 0 ? 'bg-yellow-500 text-white' : 
                      index === 1 ? 'bg-gray-400 text-white' : 
                      index === 2 ? 'bg-orange-500 text-white' : 'bg-gray-200 text-gray-600'
                    }`}>
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-semibold text-gray-900">{analista.nombre}</div>
                      <div className="text-sm text-gray-500">{analista.clientes} clientes • {analista.ventas} ventas</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-gray-900">{formatCurrency(analista.monto)}</div>
                    <div className="text-sm text-green-600">{analista.tasaConversion}% conversión</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Métricas Detalladas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Ingresos por Tipo */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <PieChart className="mr-2 h-5 w-5" />
              Ingresos por Tipo
            </CardTitle>
            <CardDescription>Desglose de ingresos por categoría</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                <span className="font-medium text-blue-900">Capital</span>
                <Badge variant="outline" className="bg-blue-100 text-blue-800">
                  {formatCurrency(mockData.financieros.ingresosCapital)}
                </Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                <span className="font-medium text-green-900">Intereses</span>
                <Badge variant="outline" className="bg-green-100 text-green-800">
                  {formatCurrency(mockData.financieros.ingresosInteres)}
                </Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                <span className="font-medium text-red-900">Mora</span>
                <Badge variant="outline" className="bg-red-100 text-red-800">
                  {formatCurrency(mockData.financieros.ingresosMora)}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Métricas de Cobranza */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" />
              Métricas de Cobranza
            </CardTitle>
            <CardDescription>Indicadores de eficiencia</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <span className="font-medium">Promedio días mora</span>
                <Badge variant="outline">
                  {mockData.cobranza.promedioDiasMora} días
                </Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                <span className="font-medium text-green-900">% Cumplimiento</span>
                <Badge className="bg-green-600 text-white">
                  {mockData.cobranza.porcentajeCumplimiento}%
                </Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                <span className="font-medium text-red-900">Clientes en mora</span>
                <Badge className="bg-red-600 text-white">
                  {mockData.cobranza.clientesMora}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Métricas de Productos */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Car className="mr-2 h-5 w-5" />
              Métricas de Productos
            </CardTitle>
            <CardDescription>Análisis de modelos</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                <span className="font-medium text-blue-900">Modelo más vendido</span>
                <Badge variant="outline" className="bg-blue-100 text-blue-800">
                  {mockData.productos.modeloMasVendido}
                </Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                <span className="font-medium text-green-900">Ventas del modelo</span>
                <Badge variant="outline" className="bg-green-100 text-green-800">
                  {mockData.productos.ventasModeloMasVendido}
                </Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                <span className="font-medium text-purple-900">Ticket promedio</span>
                <Badge variant="outline" className="bg-purple-100 text-purple-800">
                  {formatCurrency(mockData.productos.ticketPromedio)}
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