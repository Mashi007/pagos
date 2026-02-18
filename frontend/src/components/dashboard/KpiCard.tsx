import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { formatCurrency } from '../../utils'
import type React from 'react'

interface KpiCardProps {
  title: string
  value: number | string
  variationPercent?: number
  variationAbs?: number
  color: 'blue' | 'green' | 'purple' | 'red'
  icon?: React.ComponentType<{ className?: string }>
  formatValue?: (value: number | string) => string
}

export function KpiCard({
  title,
  value,
  variationPercent,
  variationAbs,
  color,
  icon: Icon,
  formatValue = (v) => String(v),
}: KpiCardProps) {
  const colorClasses = {
    blue: {
      bg: 'bg-blue-50',
      text: 'text-blue-700',
      border: 'border-blue-200',
      variation: 'text-blue-600',
    },
    green: {
      bg: 'bg-green-50',
      text: 'text-green-700',
      border: 'border-green-200',
      variation: 'text-green-600',
    },
    purple: {
      bg: 'bg-purple-50',
      text: 'text-purple-700',
      border: 'border-purple-200',
      variation: 'text-purple-600',
    },
    red: {
      bg: 'bg-red-50',
      text: 'text-red-700',
      border: 'border-red-200',
      variation: 'text-red-600',
    },
  }

  const colors = colorClasses[color]
  const isPositive = variationPercent !== undefined && variationPercent > 0
  const isNegative = variationPercent !== undefined && variationPercent < 0
  const isNeutral = variationPercent === undefined || variationPercent === 0

  const VariationIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus
  const variationColor = isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-500'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        relative
        ${colors.bg}
        ${colors.border}
        border-2 rounded-xl
        p-5
        shadow-sm hover:shadow-md
        transition-all duration-300
        min-h-[150px]
      `}
    >
      {/* Icono opcional */}
      {Icon && (
        <div className="mb-3">
          <Icon className={`h-5 w-5 ${colors.text} opacity-60`} />
        </div>
      )}

      {/* Título */}
      <h3 className={`text-sm font-semibold ${colors.text} mb-2`}>{title}</h3>

      {/* Valor Principal */}
      <div className={`text-3xl font-black ${colors.text} mb-2`}>
        {typeof value === 'number' && (title.includes('Morosidad') || title.includes('Pago vencido'))
          ? formatCurrency(value)
          : typeof value === 'number' && title.includes('Préstamos')
          ? value.toLocaleString()
          : formatValue(value)}
      </div>

      {/* Variación */}
      {variationPercent !== undefined && (
        <div className="absolute bottom-4 right-4 flex items-center gap-1">
          <VariationIcon className={`h-4 w-4 ${variationColor}`} />
          <span className={`text-sm font-bold ${variationColor}`}>
            {isPositive ? '+' : ''}
            {variationPercent.toFixed(1)}%
          </span>
        </div>
      )}
    </motion.div>
  )
}

