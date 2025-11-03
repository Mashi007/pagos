import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  DollarSign,
  CreditCard,
  Calendar,
  BarChart3,
  Activity,
  ChevronRight,
} from 'lucide-react'
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
    color: 'text-cyan-600',
    hoverColor: 'hover:border-cyan-500 hover:shadow-[0_8px_30px_rgba(6,182,212,0.3)] hover:bg-gradient-to-br hover:from-cyan-50 hover:to-blue-50',
    bgColor: 'bg-gradient-to-br from-cyan-100 to-blue-100',
    route: '/dashboard/financiamiento',
  },
  {
    id: 'cuotas',
    title: 'Cuotas y Amortizaciones',
    description: 'Gestión de cuotas y pagos',
    icon: Calendar,
    color: 'text-purple-600',
    hoverColor: 'hover:border-purple-500 hover:shadow-[0_8px_30px_rgba(168,85,247,0.3)] hover:bg-gradient-to-br hover:from-purple-50 hover:to-pink-50',
    bgColor: 'bg-gradient-to-br from-purple-100 to-pink-100',
    route: '/dashboard/cuotas',
  },
  {
    id: 'cobranza',
    title: 'Cobranza',
    description: 'Recaudación y metas',
    icon: CreditCard,
    color: 'text-emerald-600',
    hoverColor: 'hover:border-emerald-500 hover:shadow-[0_8px_30px_rgba(16,185,129,0.3)] hover:bg-gradient-to-br hover:from-emerald-50 hover:to-teal-50',
    bgColor: 'bg-gradient-to-br from-emerald-100 to-teal-100',
    route: '/dashboard/cobranza',
  },
  {
    id: 'analisis',
    title: 'Análisis y Gráficos',
    description: 'Visualizaciones detalladas',
    icon: BarChart3,
    color: 'text-amber-600',
    hoverColor: 'hover:border-amber-500 hover:shadow-[0_8px_30px_rgba(245,158,11,0.3)] hover:bg-gradient-to-br hover:from-amber-50 hover:to-orange-50',
    bgColor: 'bg-gradient-to-br from-amber-100 to-orange-100',
    route: '/dashboard/analisis',
  },
  {
    id: 'pagos',
    title: 'Pagos',
    description: 'KPIs de transacciones',
    icon: Activity,
    color: 'text-violet-600',
    hoverColor: 'hover:border-violet-500 hover:shadow-[0_8px_30px_rgba(139,92,246,0.3)] hover:bg-gradient-to-br hover:from-violet-50 hover:to-indigo-50',
    bgColor: 'bg-gradient-to-br from-violet-100 to-indigo-100',
    route: '/dashboard/pagos',
  },
]

export function DashboardMenu() {
  const navigate = useNavigate()
  const { user } = useSimpleAuth()
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  // Verificar que el componente se está renderizando
  console.log('✅ DashboardMenu renderizado - diseño nuevo')

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 p-6 relative overflow-hidden">
      {/* Efecto de fondo con patrones de grid estratégico */}
      <div className="absolute inset-0 opacity-[0.03]">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(90deg, rgba(0,0,0,0.1) 1px, transparent 1px),
            linear-gradient(rgba(0,0,0,0.1) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px'
        }}></div>
      </div>

      {/* Gradientes decorativos de fondo */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-200/10 rounded-full blur-3xl"></div>
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-200/10 rounded-full blur-3xl"></div>

      <div className="relative z-10 space-y-8">
        {/* Header con estilo estratégico moderno */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative"
        >
          {/* Línea superior decorativa con efecto neón */}
          <div className="absolute -top-3 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 via-purple-400 to-transparent opacity-60"></div>
          
          {/* Badge de identificación del nuevo diseño */}
          <div className="absolute top-0 right-0 bg-emerald-500 text-white px-3 py-1 rounded-full text-xs font-bold shadow-lg z-20">
            ✨ NUEVO DISEÑO v2.0
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-5xl font-black text-gray-900 mb-3 tracking-tight">
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-600 via-blue-600 to-purple-600">
                  DASHBOARD
                </span>{' '}
                <span className="text-gray-800">EJECUTIVO</span>
              </h1>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
                  <div className="absolute inset-0 h-2 w-2 rounded-full bg-emerald-400 animate-ping opacity-75"></div>
                </div>
                <p className="text-gray-600 font-semibold text-sm tracking-wide">
                  Bienvenido, <span className="text-cyan-600 font-black">{userName}</span> • Selecciona un módulo estratégico
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Grid de Botones con estilo de monitoreo estratégico */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((category, index) => {
            const Icon = category.icon
            return (
              <motion.button
                key={category.id}
                initial={{ opacity: 0, y: 30, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ 
                  delay: index * 0.08,
                  type: "spring",
                  stiffness: 120,
                  damping: 12
                }}
                whileHover={{ 
                  scale: 1.04, 
                  y: -6,
                  transition: { duration: 0.25 }
                }}
                whileTap={{ scale: 0.96 }}
                onClick={() => navigate(category.route)}
                className={`
                  group relative
                  flex items-center justify-between
                  px-6 py-6
                  bg-white
                  border-2 rounded-xl
                  shadow-[0_4px_20px_rgba(0,0,0,0.08)]
                  transition-all duration-300
                  ${category.hoverColor}
                  hover:border-opacity-100
                  text-left
                  overflow-hidden
                  before:absolute before:inset-0
                  before:bg-gradient-to-r before:from-transparent before:via-white/40 before:to-transparent
                  before:translate-x-[-200%] before:group-hover:translate-x-[200%]
                  before:transition-transform before:duration-1000
                `}
                style={{
                  borderColor: category.id === 'financiamiento' ? 'rgba(148,163,184,0.3)' :
                              category.id === 'cuotas' ? 'rgba(148,163,184,0.3)' :
                              category.id === 'cobranza' ? 'rgba(148,163,184,0.3)' :
                              category.id === 'analisis' ? 'rgba(148,163,184,0.3)' :
                              'rgba(148,163,184,0.3)'
                }}
              >
                {/* Borde superior brillante */}
                <div className={`
                  absolute top-0 left-0 right-0 h-1 rounded-t-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300
                  ${category.id === 'financiamiento' && 'bg-gradient-to-r from-cyan-500 to-blue-500'}
                  ${category.id === 'cuotas' && 'bg-gradient-to-r from-purple-500 to-pink-500'}
                  ${category.id === 'cobranza' && 'bg-gradient-to-r from-emerald-500 to-teal-500'}
                  ${category.id === 'analisis' && 'bg-gradient-to-r from-amber-500 to-orange-500'}
                  ${category.id === 'pagos' && 'bg-gradient-to-r from-violet-500 to-indigo-500'}
                `}></div>

                {/* Efecto de brillo radial en hover */}
                <div 
                  className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{
                    background: category.id === 'financiamiento' ? 'radial-gradient(circle at center, rgba(103,232,249,0.15), transparent)' :
                               category.id === 'cuotas' ? 'radial-gradient(circle at center, rgba(192,132,252,0.15), transparent)' :
                               category.id === 'cobranza' ? 'radial-gradient(circle at center, rgba(110,231,183,0.15), transparent)' :
                               category.id === 'analisis' ? 'radial-gradient(circle at center, rgba(251,191,36,0.15), transparent)' :
                               'radial-gradient(circle at center, rgba(167,139,250,0.15), transparent)'
                  }}
                ></div>

                <div className="flex items-center space-x-5 flex-1 relative z-10">
                  <div className={`
                    relative p-4 rounded-xl
                    ${category.bgColor}
                    border-2 border-white/50
                    shadow-[0_4px_15px_rgba(0,0,0,0.1)]
                    group-hover:scale-110 group-hover:rotate-3
                    group-hover:shadow-[0_8px_25px_rgba(0,0,0,0.15)]
                    transition-all duration-300
                  `}>
                    <Icon className={`h-7 w-7 ${category.color} drop-shadow-[0_2px_4px_rgba(0,0,0,0.1)]`} />
                    {/* Efecto de glow en el icono */}
                    <div className={`
                      absolute inset-0 rounded-xl blur-lg opacity-0 group-hover:opacity-40 transition-opacity duration-300
                      ${category.id === 'financiamiento' && 'bg-cyan-400'}
                      ${category.id === 'cuotas' && 'bg-purple-400'}
                      ${category.id === 'cobranza' && 'bg-emerald-400'}
                      ${category.id === 'analisis' && 'bg-amber-400'}
                      ${category.id === 'pagos' && 'bg-violet-400'}
                    `}></div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className={`
                      text-xl font-black mb-1.5
                      group-hover:tracking-wide
                      transition-all duration-300
                      ${category.id === 'financiamiento' && 'text-cyan-700 group-hover:text-cyan-600'}
                      ${category.id === 'cuotas' && 'text-purple-700 group-hover:text-purple-600'}
                      ${category.id === 'cobranza' && 'text-emerald-700 group-hover:text-emerald-600'}
                      ${category.id === 'analisis' && 'text-amber-700 group-hover:text-amber-600'}
                      ${category.id === 'pagos' && 'text-violet-700 group-hover:text-violet-600'}
                    `}>
                      {category.title}
                    </h3>
                    <p className="text-sm text-gray-600 group-hover:text-gray-700 transition-colors duration-300 font-semibold">
                      {category.description}
                    </p>
                  </div>
                </div>
                <ChevronRight className={`
                  h-6 w-6 flex-shrink-0 ml-4 relative z-10
                  text-gray-400 
                  group-hover:text-gray-600
                  group-hover:translate-x-2
                  transition-all duration-300
                  ${category.id === 'financiamiento' && 'group-hover:text-cyan-600'}
                  ${category.id === 'cuotas' && 'group-hover:text-purple-600'}
                  ${category.id === 'cobranza' && 'group-hover:text-emerald-600'}
                  ${category.id === 'analisis' && 'group-hover:text-amber-600'}
                  ${category.id === 'pagos' && 'group-hover:text-violet-600'}
                `} />
              </motion.button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

