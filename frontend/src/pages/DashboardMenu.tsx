import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  DollarSign,
  CreditCard,
  Calendar,
  BarChart3,
  Activity,
  Shield,
  ChevronRight,
  LayoutDashboard,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useSimpleAuth } from '@/store/simpleAuthStore'

interface KpiCategory {
  id: string
  title: string
  description: string
  icon: typeof DollarSign
  color: string
  hoverColor: string
  bgColor: string
  route: string
}

const categories: KpiCategory[] = [
  {
    id: 'financiamiento',
    title: 'Financiamiento',
    description: 'Total y por estado',
    icon: DollarSign,
    color: 'text-blue-600',
    hoverColor: 'hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300',
    bgColor: 'bg-blue-50',
    route: '/dashboard/financiamiento',
  },
  {
    id: 'cuotas',
    title: 'Cuotas y Amortizaciones',
    description: 'Gestión de cuotas y pagos',
    icon: Calendar,
    color: 'text-purple-600',
    hoverColor: 'hover:bg-purple-50 hover:text-purple-700 hover:border-purple-300',
    bgColor: 'bg-purple-50',
    route: '/dashboard/cuotas',
  },
  {
    id: 'cobranza',
    title: 'Cobranza',
    description: 'Recaudación y metas',
    icon: CreditCard,
    color: 'text-green-600',
    hoverColor: 'hover:bg-green-50 hover:text-green-700 hover:border-green-300',
    bgColor: 'bg-green-50',
    route: '/dashboard/cobranza',
  },
  {
    id: 'analisis',
    title: 'Análisis y Gráficos',
    description: 'Visualizaciones detalladas',
    icon: BarChart3,
    color: 'text-orange-600',
    hoverColor: 'hover:bg-orange-50 hover:text-orange-700 hover:border-orange-300',
    bgColor: 'bg-orange-50',
    route: '/dashboard/analisis',
  },
  {
    id: 'pagos',
    title: 'Pagos',
    description: 'KPIs de transacciones',
    icon: Activity,
    color: 'text-indigo-600',
    hoverColor: 'hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-300',
    bgColor: 'bg-indigo-50',
    route: '/dashboard/pagos',
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
            Bienvenido, {userName} • Selecciona una categoría para ver los KPIs detallados
          </p>
        </div>
      </motion.div>

      {/* Grid de Botones Compactos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {categories.map((category, index) => {
          const Icon = category.icon
          return (
            <motion.button
              key={category.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate(category.route)}
              className={`
                group relative
                flex items-center justify-between
                px-6 py-4
                bg-white border-2 border-gray-200 rounded-xl
                shadow-sm
                transition-all duration-200
                ${category.hoverColor}
                hover:shadow-md
                text-left
              `}
            >
              <div className="flex items-center space-x-4 flex-1">
                <div className={`
                  p-3 rounded-lg 
                  ${category.bgColor}
                  group-hover:scale-110
                  transition-transform duration-200
                `}>
                  <Icon className={`h-6 w-6 ${category.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 group-hover:text-gray-900">
                    {category.title}
                  </h3>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {category.description}
                  </p>
                </div>
              </div>
              <ChevronRight className={`
                h-5 w-5 
                text-gray-400 
                group-hover:text-gray-600
                group-hover:translate-x-1
                transition-all duration-200
                flex-shrink-0 ml-4
              `} />
            </motion.button>
          )
        })}
      </div>

      {/* Información adicional compacta */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <Shield className="h-5 w-5 text-blue-600 flex-shrink-0" />
              <div>
                <h3 className="text-sm font-semibold text-gray-900">
                  Filtros Globales Disponibles
                </h3>
                <p className="text-xs text-gray-600 mt-0.5">
                  Todas las páginas incluyen filtros por Analista, Concesionario, Modelo y Fechas que se aplican automáticamente a todos los KPIs y gráficos.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

