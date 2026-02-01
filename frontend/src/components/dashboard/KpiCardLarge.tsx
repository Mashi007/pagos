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

  // âœ… TamaÃ±os balanceados para evitar desbordes
  const textSize = size === 'large' ? 'text-3xl md:text-4xl' : 'text-2xl md:text-3xl'
  const cardHeight = size === 'large' ? 'min-h-[200px]' : 'min-h-[170px]'
  const titleSize = 'text-sm md:text-base' // TÃ­tulo mÃ¡s legible
  const variationSize = 'text-sm md:text-base' // VariaciÃ³n mÃ¡s visible

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -4 }}
      transition={{ duration: 0.2 }}
      className={`
        relative
        ${cardHeight}
        bg-white
        rounded-xl
        border-2
        ${borderColor}
        shadow-[0_4px_20px_rgba(0,0,0,0.12)]
        hover:shadow-[0_8px_30px_rgba(0,0,0,0.18)]
        transition-all duration-300
        overflow-hidden
        group
      `}
    >
      {/* Borde superior decorativo mÃ¡s prominente */}
      <div className={`absolute top-0 left-0 right-0 h-1.5 ${bgColor} opacity-90`}></div>

      {/* Gradiente sutil de fondo */}
      <div
        className={`absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300 bg-gradient-to-br ${bgColor} to-transparent`}
      ></div>

      <div className="relative z-10 p-5 md:p-6 h-full flex flex-col">
        {/* Header con icono y tÃ­tulo mejorado */}
        <div className="flex items-start justify-between mb-3 md:mb-4">
          <div className="flex items-center space-x-3 flex-1 min-w-0">
            <div className={`p-2.5 md:p-3 rounded-xl ${bgColor} border-2 border-white/50 shadow-lg flex-shrink-0`}>
              <Icon className={`h-6 w-6 md:h-7 md:w-7 ${color}`} />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className={`${titleSize} font-bold text-gray-700 uppercase tracking-tight leading-tight line-clamp-2`}>
                {title}
              </h3>
            </div>
          </div>
        </div>

        {/* Valor principal con mejor espaciado y sin desbordes */}
        <div className="flex-1 flex flex-col justify-center min-w-0 w-full overflow-hidden">
          <div className={`${textSize} font-black ${color} mb-2 leading-tight tracking-tight w-full`}>
            {formatValue()}
          </div>

          {/* VariaciÃ³n mejorada con icono y mejor diseÃ±o */}
          {variation && variation.percent !== undefined && typeof variation.percent === 'number' && (
            <div className="flex items-center gap-2 mt-3">
              <div className={`flex items-center gap-1 px-2 py-1 rounded-md ${
                variation.percent >= 0
                  ? 'bg-green-50 text-green-700'
                  : 'bg-red-50 text-red-700'
              }`}>
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
                <span className={`${variationSize} text-gray-600 font-medium`}>
                  {variation.label}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Subtitle en la parte inferior izquierda */}
        {subtitle && (
          <div className="mt-auto pt-3">
            <p className="text-xs md:text-sm text-gray-600 font-medium">{subtitle}</p>
          </div>
        )}

        {/* DecoraciÃ³n sutil en la esquina inferior */}
        <div className={`absolute bottom-0 right-0 w-20 h-20 ${bgColor} opacity-5 rounded-tl-full -mr-10 -mb-10`}></div>
      </div>
    </motion.div>
  )
}

