import React from 'react'
import { motion } from 'framer-motion'
import { 
  DollarSign, 
  Users, 
  CreditCard, 
  TrendingUp, 
  AlertTriangle,
  CheckCircle,
  Clock,
  Target
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { usePermissions } from '@/store/authStore'
import { formatCurrency, formatPercentage } from '@/utils'

// Mock data - en producción vendría del backend
const mockKPIs = {
  cartera_total: 2500000,
  cartera_al_dia: 2100000,
  cartera_vencida: 400000,
  porcentaje_mora: 16,
  pagos_hoy: 15,
  monto_pagos_hoy: 45000,
  clientes_activos: 150,
  clientes_mora: 24,
  meta_mensual: 500000,
  avance_meta: 320000,
}

const mockRecentPayments = [
  { id: 1, cliente: 'Juan Pérez', monto: 850, fecha: '2024-01-15', estado: 'confirmado' },
  { id: 2, cliente: 'María García', monto: 1200, fecha: '2024-01-15', estado: 'confirmado' },
  { id: 3, cliente: 'Carlos López', monto: 950, fecha: '2024-01-15', estado: 'pendiente' },
  { id: 4, cliente: 'Ana Rodríguez', monto: 750, fecha: '2024-01-14', estado: 'confirmado' },
]

const mockAlerts = [
  { id: 1, tipo: 'vencimiento', mensaje: '5 cuotas vencen hoy', prioridad: 'alta' },
  { id: 2, tipo: 'mora', mensaje: '3 clientes entraron en mora', prioridad: 'alta' },
  { id: 3, tipo: 'pago', mensaje: '2 pagos pendientes de confirmación', prioridad: 'media' },
]

export function Dashboard() {
  const { userRole, userName, isAdmin, canViewAllClients } = usePermissions()

  const kpiCards = [
    {
      title: 'Cartera Total',
      value: formatCurrency(mockKPIs.cartera_total),
      description: 'Total de préstamos activos',
      icon: DollarSign,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      trend: '+5.2%',
      trendUp: true,
    },
    {
      title: 'Cartera al Día',
      value: formatCurrency(mockKPIs.cartera_al_dia),
      description: `${formatPercentage(84)} de la cartera total`,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      trend: '+2.1%',
      trendUp: true,
    },
    {
      title: 'Cartera en Mora',
      value: formatCurrency(mockKPIs.cartera_vencida),
      description: `${formatPercentage(mockKPIs.porcentaje_mora)} de mora`,
      icon: AlertTriangle,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      trend: '-1.3%',
      trendUp: false,
    },
    {
      title: 'Pagos Hoy',
      value: mockKPIs.pagos_hoy.toString(),
      description: formatCurrency(mockKPIs.monto_pagos_hoy),
      icon: CreditCard,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      trend: '+12.5%',
      trendUp: true,
    },
  ]

  const progressPercentage = (mockKPIs.avance_meta / mockKPIs.meta_mensual) * 100

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-6 text-white"
      >
        <div className="flex items-center space-x-4 mb-4">
          <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
            <div className="text-center">
              <div className="text-white font-bold text-sm leading-none">RAPI</div>
              <div className="text-yellow-300 font-bold text-xs leading-none">CREDIT</div>
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-bold mb-1">
              ¡Bienvenido a RAPICREDIT, {userName}!
            </h1>
            <p className="text-blue-100">
              Dashboard {userRole} - Soluciones financieras rápidas y confiables
            </p>
          </div>
        </div>
        <div className="mt-4 flex items-center space-x-4 text-sm">
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
            <span>Sistema operativo</span>
          </div>
          <div className="flex items-center space-x-1">
            <Clock className="w-4 h-4" />
            <span>Última actualización: hace 2 min</span>
          </div>
        </div>
      </motion.div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiCards.map((kpi, index) => (
          <motion.div
            key={kpi.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="hover:shadow-lg transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 mb-1">
                      {kpi.title}
                    </p>
                    <p className="text-2xl font-bold text-gray-900">
                      {kpi.value}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {kpi.description}
                    </p>
                  </div>
                  <div className={`p-3 rounded-full ${kpi.bgColor}`}>
                    <kpi.icon className={`w-6 h-6 ${kpi.color}`} />
                  </div>
                </div>
                <div className="mt-4 flex items-center">
                  <TrendingUp className={`w-4 h-4 mr-1 ${
                    kpi.trendUp ? 'text-green-500' : 'text-red-500'
                  }`} />
                  <span className={`text-sm font-medium ${
                    kpi.trendUp ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {kpi.trend}
                  </span>
                  <span className="text-sm text-gray-500 ml-1">vs mes anterior</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Meta Mensual */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Target className="w-5 h-5 text-blue-600" />
                <span>Meta Mensual</span>
              </CardTitle>
              <CardDescription>
                Progreso de cobranza del mes actual
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Progreso</span>
                  <span className="text-sm font-medium">
                    {progressPercentage.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(progressPercentage, 100)}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">
                    Recaudado: {formatCurrency(mockKPIs.avance_meta)}
                  </span>
                  <span className="text-gray-600">
                    Meta: {formatCurrency(mockKPIs.meta_mensual)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Alertas */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5 text-yellow-600" />
                  <span>Alertas</span>
                </div>
                <Badge variant="destructive">{mockAlerts.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">
                        {alert.mensaje}
                      </p>
                    </div>
                    <Badge
                      variant={alert.prioridad === 'alta' ? 'destructive' : 'warning'}
                    >
                      {alert.prioridad}
                    </Badge>
                  </div>
                ))}
                <Button variant="outline" className="w-full mt-3">
                  Ver todas las alertas
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Pagos Recientes */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <CreditCard className="w-5 h-5 text-green-600" />
                <span>Pagos Recientes</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockRecentPayments.map((pago) => (
                  <div
                    key={pago.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {pago.cliente}
                      </p>
                      <p className="text-xs text-gray-500">{pago.fecha}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-gray-900">
                        {formatCurrency(pago.monto)}
                      </p>
                      <Badge
                        variant={pago.estado === 'confirmado' ? 'success' : 'warning'}
                      >
                        {pago.estado}
                      </Badge>
                    </div>
                  </div>
                ))}
                <Button variant="outline" className="w-full mt-3">
                  Ver todos los pagos
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Acciones Rápidas</CardTitle>
            <CardDescription>
              Accesos directos a las funciones más utilizadas
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Button className="h-20 flex flex-col space-y-2">
                <CreditCard className="w-6 h-6" />
                <span>Nuevo Pago</span>
              </Button>
              <Button variant="outline" className="h-20 flex flex-col space-y-2">
                <Users className="w-6 h-6" />
                <span>Nuevo Cliente</span>
              </Button>
              <Button variant="outline" className="h-20 flex flex-col space-y-2">
                <TrendingUp className="w-6 h-6" />
                <span>Generar Reporte</span>
              </Button>
              <Button variant="outline" className="h-20 flex flex-col space-y-2">
                <AlertTriangle className="w-6 h-6" />
                <span>Ver Mora</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
