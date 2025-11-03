import { LucideIcon } from 'lucide-react'
import { motion } from 'framer-motion'
import { formatCurrency, formatNumber } from '@/utils'

interface KpiCardLargeProps {
  title: string
  value: number | string
  subtitle?: string
  icon: LucideIcon
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
        return formatNumber(value)
      case 'percentage':
        return `${value.toFixed(1)}%`
      default:
        return value.toString()
    }
  }

  const textSize = size === 'large' ? 'text-4xl' : 'text-3xl'
  const cardHeight = size === 'large' ? 'min-h-[180px]' : 'min-h-[150px]'

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
      {/* Borde superior decorativo */}
      <div className={`absolute top-0 left-0 right-0 h-1 ${bgColor} opacity-80`}></div>

      {/* Efecto de brillo en hover */}
      <div
        className={`absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 ${bgColor}`}
      ></div>

      <div className="relative z-10 p-6 h-full flex flex-col justify-between">
        {/* Header con icono y título */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className={`p-3 rounded-lg ${bgColor} border-2 border-white/50 shadow-lg`}>
              <Icon className={`h-6 w-6 ${color}`} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                {title}
              </h3>
              {subtitle && (
                <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
              )}
            </div>
          </div>
        </div>

        {/* Valor principal */}
        <div className="flex items-end justify-between">
          <div>
            <div className={`${textSize} font-black ${color} mb-1 leading-tight`}>
              {formatValue()}
            </div>
            {variation && (
              <div className="flex items-center space-x-1 mt-2">
                <span
                  className={`text-sm font-bold ${
                    variation.percent >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {variation.percent >= 0 ? '+' : ''}
                  {variation.percent.toFixed(1)}%
                </span>
                {variation.label && (
                  <span className="text-xs text-gray-500">{variation.label}</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

