import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  DollarSign,
  CreditCard,
  Calendar,
  BarChart3,
  TrendingUp,
  Activity,
  Shield,
  ChevronRight,
  LayoutDashboard,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useSimpleAuth } from '@/store/simpleAuthStore'

interface KpiCategory {
  id: string
  title: string
  description: string
  icon: typeof DollarSign
  color: string
  bgColor: string
  route: string
  metrics: string[]
}

const categories: KpiCategory[] = [
  {
    id: 'financiamiento',
    title: 'Financiamiento',
    description: 'KPIs relacionados con el financiamiento total y por estado',
    icon: DollarSign,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    route: '/dashboard/financiamiento',
    metrics: [
      'Total Financiamiento',
      'Financiamiento Activo',
      'Financiamiento Inactivo',
      'Financiamiento Finalizado',
    ],
  },
  {
    id: 'cuotas',
    title: 'Cuotas y Amortizaciones',
    description: 'Gestión de cuotas, pagos y estados de amortización',
    icon: Calendar,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    route: '/dashboard/cuotas',
    metrics: [
      'Cuotas a Cobrar (Mes)',
      'Cuotas Pagadas',
      'Cuotas Conciliadas',
      'Cuotas Atrasadas',
      'Cuotas Impagas (2+)',
    ],
  },
  {
    id: 'cobranza',
    title: 'Cobranza',
    description: 'Métricas de recaudación y cumplimiento de metas',
    icon: CreditCard,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    route: '/dashboard/cobranza',
    metrics: [
      'Total Cobrado Mes',
      'Tasa de Recuperación Mensual',
      'Meta Mensual',
      'Avance de Meta',
    ],
  },
  {
    id: 'analisis',
    title: 'Análisis y Gráficos',
    description: 'Visualizaciones y análisis detallados',
    icon: BarChart3,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    route: '/dashboard/analisis',
    metrics: [
      'Análisis de Morosidad',
      'Evolución Mensual',
      'Cobros Diarios',
      'Distribución de Ingresos',
    ],
  },
  {
    id: 'pagos',
    title: 'Pagos',
    description: 'KPIs de pagos y transacciones',
    icon: Activity,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    route: '/dashboard/pagos',
    metrics: [
      'Total Pagos',
      'Pagos del Día',
      'Total Pagado',
      'Cuotas Pagadas',
      'Cuotas Pendientes',
    ],
  },
]

export function DashboardMenu() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard Ejecutivo</h1>
          <p className="text-gray-600 mt-1">
            Bienvenido, {userName} • Selecciona una categoría de KPIs para explorar
          </p>
        </div>
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <LayoutDashboard className="h-4 w-4" />
            <span>Vista General</span>
          </button>
        </motion.div>
      </motion.div>

      {/* Grid de Categorías */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {categories.map((category, index) => {
          const Icon = category.icon
          return (
            <motion.div
              key={category.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ y: -4 }}
              className="cursor-pointer"
              onClick={() => navigate(category.route)}
            >
              <Card className="h-full hover:shadow-xl transition-all duration-200 border-l-4 border-l-transparent hover:border-l-blue-500">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <div className={`p-3 rounded-lg ${category.bgColor}`}>
                      <Icon className={`h-6 w-6 ${category.color}`} />
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
                  </div>
                  <CardTitle className="text-xl">{category.title}</CardTitle>
                  <CardDescription className="mt-2">
                    {category.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-700 mb-3">
                      Métricas incluidas:
                    </p>
                    <ul className="space-y-1.5">
                      {category.metrics.map((metric, idx) => (
                        <li
                          key={idx}
                          className="text-sm text-gray-600 flex items-center"
                        >
                          <div className="h-1.5 w-1.5 rounded-full bg-gray-400 mr-2" />
                          {metric}
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* Información adicional */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
      >
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <CardContent className="p-6">
            <div className="flex items-start space-x-4">
              <Shield className="h-6 w-6 text-blue-600 mt-1 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">
                  Filtros Globales Disponibles
                </h3>
                <p className="text-sm text-gray-600">
                  Todas las páginas de KPIs incluyen filtros por Analista, Concesionario,
                  Modelo y Rango de Fechas. Los filtros se aplican automáticamente a todos
                  los KPIs y gráficos en la página seleccionada.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

