/**
 * Tipos para componentes de Recharts
 * Evita el uso de 'any' en props de tooltips, formatters, etc.
 */

export interface TooltipPayload {
  name?: string
  value?: number | string
  payload?: Record<string, unknown>
  dataKey?: string
  color?: string
}

export interface CustomTooltipProps {
  active?: boolean
  payload?: TooltipPayload[]
  label?: string | number
}

export interface FormatterProps {
  value: number | string
  name: string
  payload?: Record<string, unknown>
  [key: string]: unknown
}

