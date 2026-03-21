import { motion } from 'framer-motion'

import { formatCurrency } from '../../utils'

import { TrendingUp, TrendingDown } from 'lucide-react'

interface KpiCardLargeProps {
  title: string

  value: number | string

  subtitle?: string

  icon: React.ComponentType<{ className?: string }>

  color: string

  bgColor: string

  borderColor: string

  format?: 'currency' | 'number' | 'percentage' | 'text'

  variation?: {
    percent: number

    label?: string
  }

  size?: 'large' | 'medium'
}

export function KpiCardLarge({
  title,

  value,

  subtitle,

  icon: Icon,

  color,

  bgColor,

  borderColor,

  format = 'currency',

  variation,

  size = 'large',
}: KpiCardLargeProps) {
  const formatValue = () => {
    if (typeof value === 'string') return value

    switch (format) {
      case 'currency':
        return formatCurrency(value)

      case 'number':
        return value.toLocaleString('es-EC')

      case 'percentage':
        return `${value.toFixed(1)}%`

      default:
        return value.toString()
    }
  }

  // âœ… Tamaños balanceados para evitar desbordes

  const textSize =
    size === 'large' ? 'text-3xl md:text-4xl' : 'text-2xl md:text-3xl'

  const cardHeight = size === 'large' ? 'min-h-[200px]' : 'min-h-[170px]'

  const titleSize = 'text-sm md:text-base' // Título más legible

  const variationSize = 'text-sm md:text-base' // Variación más visible

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -4 }}
      transition={{ duration: 0.2 }}
      className={`





        relative





        ${cardHeight}





        rounded-xl





        border-2





        bg-white





        ${borderColor}





        group





        overflow-hidden





        shadow-[0_4px_20px_rgba(0,0,0,0.12)] transition-all





        duration-300





        hover:shadow-[0_8px_30px_rgba(0,0,0,0.18)]





      `}
    >
      {/* Borde superior decorativo más prominente */}

      <div
        className={`absolute left-0 right-0 top-0 h-1.5 ${bgColor} opacity-90`}
      ></div>

      {/* Gradiente sutil de fondo */}

      <div
        className={`absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-300 group-hover:opacity-5 ${bgColor} to-transparent`}
      ></div>

      <div className="relative z-10 flex h-full flex-col p-5 md:p-6">
        {/* Header con icono y título mejorado */}

        <div className="mb-3 flex items-start justify-between md:mb-4">
          <div className="flex min-w-0 flex-1 items-center space-x-3">
            <div
              className={`rounded-xl p-2.5 md:p-3 ${bgColor} flex-shrink-0 border-2 border-white/50 shadow-lg`}
            >
              <Icon className={`h-6 w-6 md:h-7 md:w-7 ${color}`} />
            </div>

            <div className="min-w-0 flex-1">
              <h3
                className={`${titleSize} line-clamp-2 font-bold uppercase leading-tight tracking-tight text-gray-700`}
              >
                {title}
              </h3>
            </div>
          </div>
        </div>

        {/* Valor principal con mejor espaciado y sin desbordes */}

        <div className="flex w-full min-w-0 flex-1 flex-col justify-center overflow-hidden">
          <div
            className={`${textSize} font-black ${color} mb-2 w-full leading-tight tracking-tight`}
          >
            {formatValue()}
          </div>

          {/* Variación mejorada con icono y mejor diseño */}

          {variation &&
            variation.percent !== undefined &&
            typeof variation.percent === 'number' && (
              <div className="mt-3 flex items-center gap-2">
                <div
                  className={`flex items-center gap-1 rounded-md px-2 py-1 ${
                    variation.percent >= 0
                      ? 'bg-green-50 text-green-700'
                      : 'bg-red-50 text-red-700'
                  }`}
                >
                  {variation.percent >= 0 ? (
                    <TrendingUp className="h-3.5 w-3.5" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5" />
                  )}

                  <span className={`${variationSize} font-semibold`}>
                    {variation.percent >= 0 ? '+' : ''}
                    {variation.percent.toFixed(1)}%
                  </span>
                </div>

                {variation.label && (
                  <span
                    className={`${variationSize} font-medium text-gray-600`}
                  >
                    {variation.label}
                  </span>
                )}
              </div>
            )}
        </div>

        {/* Subtitle en la parte inferior izquierda */}

        {subtitle && (
          <div className="mt-auto pt-3">
            <p className="text-xs font-medium text-gray-600 md:text-sm">
              {subtitle}
            </p>
          </div>
        )}

        {/* Decoración sutil en la esquina inferior */}

        <div
          className={`absolute bottom-0 right-0 h-20 w-20 ${bgColor} -mb-10 -mr-10 rounded-tl-full opacity-5`}
        ></div>
      </div>
    </motion.div>
  )
}
