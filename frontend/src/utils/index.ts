import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { format, parseISO, isValid } from "date-fns"
import { es } from "date-fns/locale"

// Constantes de formateo
const CURRENCY_MIN_FRACTION_DIGITS = 2
const PERCENTAGE_MIN_FRACTION_DIGITS = 1
const PERCENTAGE_MAX_FRACTION_DIGITS = 2
const DEFAULT_DATE_FORMAT = 'dd/MM/yyyy'
const PERCENTAGE_DIVISOR = 100

// Utilidad para combinar clases de Tailwind
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Formateo de moneda
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-EC', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: CURRENCY_MIN_FRACTION_DIGITS,
  }).format(amount)
}

// Formateo de porcentajes
export function formatPercentage(value: number): string {
  return new Intl.NumberFormat('es-EC', {
    style: 'percent',
    minimumFractionDigits: PERCENTAGE_MIN_FRACTION_DIGITS,
    maximumFractionDigits: PERCENTAGE_MAX_FRACTION_DIGITS,
  }).format(value / PERCENTAGE_DIVISOR)
}

// Formateo de fechas
export function formatDate(date: string | Date, formatStr: string = DEFAULT_DATE_FORMAT): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date
    if (!isValid(dateObj)) return 'Fecha invÃ¡lida'
    return format(dateObj, formatStr, { locale: es })
  } catch {
    return 'Fecha invÃ¡lida'
  }
}

export { formatAddress } from './formatAddress'

// Capitalizar primera letra
export function capitalize(text: string): string {
  if (!text) return ''
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase()
}

