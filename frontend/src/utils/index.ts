import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { format, parseISO, isValid, differenceInDays } from "date-fns"
import { es } from "date-fns/locale"

// Utilidad para combinar clases de Tailwind
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Formateo de moneda
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-EC', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

// Formateo de números
export function formatNumber(number: number): string {
  return new Intl.NumberFormat('es-EC').format(number)
}

// Formateo de porcentajes
export function formatPercentage(value: number): string {
  return new Intl.NumberFormat('es-EC', {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(value / 100)
}

// Formateo de fechas
export function formatDate(date: string | Date, formatStr: string = 'dd/MM/yyyy'): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date
    if (!isValid(dateObj)) return 'Fecha inválida'
    return format(dateObj, formatStr, { locale: es })
  } catch {
    return 'Fecha inválida'
  }
}

// Formateo de fecha y hora
export function formatDateTime(date: string | Date): string {
  return formatDate(date, 'dd/MM/yyyy HH:mm')
}

// Formateo de fecha relativa
export function formatRelativeDate(date: string | Date): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date
    if (!isValid(dateObj)) return 'Fecha inválida'
    
    const now = new Date()
    const diffDays = differenceInDays(now, dateObj)
    
    if (diffDays === 0) return 'Hoy'
    if (diffDays === 1) return 'Ayer'
    if (diffDays === -1) return 'Mañana'
    if (diffDays > 0) return `Hace ${diffDays} días`
    return `En ${Math.abs(diffDays)} días`
  } catch {
    return 'Fecha inválida'
  }
}

// Validación de cédula ecuatoriana
export function validateEcuadorianId(cedula: string): boolean {
  if (!cedula || cedula.length !== 10) return false
  
  const digits = cedula.split('').map(Number)
  const province = parseInt(cedula.substring(0, 2))
  
  if (province < 1 || province > 24) return false
  
  const coefficients = [2, 1, 2, 1, 2, 1, 2, 1, 2]
  let sum = 0
  
  for (let i = 0; i < 9; i++) {
    let result = digits[i] * coefficients[i]
    if (result > 9) result -= 9
    sum += result
  }
  
  const checkDigit = sum % 10 === 0 ? 0 : 10 - (sum % 10)
  return checkDigit === digits[9]
}

// Formateo de cédula
export function formatCedula(cedula: string): string {
  if (!cedula) return ''
  const cleaned = cedula.replace(/\D/g, '')
  if (cleaned.length <= 10) {
    return cleaned.replace(/(\d{10})/, '$1')
  }
  return cleaned
}

// Formateo de teléfono
export function formatPhone(phone: string): string {
  if (!phone) return ''
  const cleaned = phone.replace(/\D/g, '')
  
  if (cleaned.length === 10) {
    return cleaned.replace(/(\d{4})(\d{3})(\d{3})/, '$1-$2-$3')
  }
  if (cleaned.length === 9) {
    return cleaned.replace(/(\d{3})(\d{3})(\d{3})/, '$1-$2-$3')
  }
  return cleaned
}

// Validación de email
export function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

// Generación de colores para gráficos
export function generateChartColors(count: number): string[] {
  const baseColors = [
    'hsl(220, 70%, 50%)',  // Azul primario
    'hsl(142, 76%, 36%)',  // Verde
    'hsl(38, 92%, 50%)',   // Amarillo
    'hsl(0, 84%, 60%)',    // Rojo
    'hsl(270, 70%, 50%)',  // Púrpura
    'hsl(199, 89%, 48%)',  // Azul claro
    'hsl(25, 95%, 53%)',   // Naranja
    'hsl(340, 82%, 52%)',  // Rosa
  ]
  
  const colors = []
  for (let i = 0; i < count; i++) {
    colors.push(baseColors[i % baseColors.length])
  }
  return colors
}

// Cálculo de estado de mora
export function getMoraStatus(diasMora: number): {
  status: 'al-dia' | 'por-vencer' | 'vencido' | 'mora';
  label: string;
  color: string;
} {
  if (diasMora < -3) {
    return {
      status: 'al-dia',
      label: 'Al día',
      color: 'text-green-600 bg-green-50'
    }
  } else if (diasMora >= -3 && diasMora <= 0) {
    return {
      status: 'por-vencer',
      label: 'Por vencer',
      color: 'text-yellow-600 bg-yellow-50'
    }
  } else if (diasMora >= 1 && diasMora <= 30) {
    return {
      status: 'vencido',
      label: 'Vencido',
      color: 'text-orange-600 bg-orange-50'
    }
  } else {
    return {
      status: 'mora',
      label: 'En mora',
      color: 'text-red-600 bg-red-50'
    }
  }
}

// Cálculo de progreso de meta
export function calculateProgress(current: number, target: number): number {
  if (target === 0) return 0
  return Math.min((current / target) * 100, 100)
}

// Debounce para búsquedas
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

// Truncar texto
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// Capitalizar primera letra
export function capitalize(text: string): string {
  if (!text) return ''
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase()
}

// Generar iniciales
export function getInitials(name: string, lastName?: string): string {
  const firstInitial = name?.charAt(0)?.toUpperCase() || ''
  const lastInitial = lastName?.charAt(0)?.toUpperCase() || ''
  return firstInitial + lastInitial
}

// Validar archivo
export function validateFile(
  file: File,
  allowedTypes: string[],
  maxSizeMB: number
): { valid: boolean; error?: string } {
  if (!allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: `Tipo de archivo no permitido. Tipos permitidos: ${allowedTypes.join(', ')}`
    }
  }
  
  const maxSizeBytes = maxSizeMB * 1024 * 1024
  if (file.size > maxSizeBytes) {
    return {
      valid: false,
      error: `El archivo es demasiado grande. Tamaño máximo: ${maxSizeMB}MB`
    }
  }
  
  return { valid: true }
}

// Descargar archivo
export function downloadFile(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// Copiar al portapapeles
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Fallback para navegadores que no soportan clipboard API
    const textArea = document.createElement('textarea')
    textArea.value = text
    document.body.appendChild(textArea)
    textArea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textArea)
    return success
  }
}

// Generar ID único
export function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36)
}

// Ordenar array por campo
export function sortBy<T>(
  array: T[],
  key: keyof T,
  direction: 'asc' | 'desc' = 'asc'
): T[] {
  return [...array].sort((a, b) => {
    const aVal = a[key]
    const bVal = b[key]
    
    if (aVal < bVal) return direction === 'asc' ? -1 : 1
    if (aVal > bVal) return direction === 'asc' ? 1 : -1
    return 0
  })
}

// Agrupar array por campo
export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const group = String(item[key])
    groups[group] = groups[group] || []
    groups[group].push(item)
    return groups
  }, {} as Record<string, T[]>)
}
