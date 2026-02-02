/**
 * Constantes del dashboard: períodos y etiquetas.
 * Una sola fuente de verdad para evitar desajustes (ej. "día" vs "dia").
 */

/** Valor del período "Hoy" (usado en Select y en cálculo de fechas) */
export const PERIODO_DIA = 'día' as const

/** Valores de período admitidos en el selector general */
export const PERIODOS_VALORES = [
  'ultimos_12_meses',
  PERIODO_DIA,
  'semana',
  'mes',
  'año',
] as const

export type PeriodoValor = (typeof PERIODOS_VALORES)[number]

/** Etiquetas para mostrar en la UI */
export const PERIODOS_ETIQUETAS: Record<string, string> = {
  ultimos_12_meses: 'Últimos 12 meses',
  día: 'Hoy',
  dia: 'Hoy',
  semana: 'Esta semana',
  mes: 'Este mes',
  año: 'Este año',
}

/** Obtiene la etiqueta de un período (acepta "día" o "dia") */
export function getPeriodoEtiqueta(periodo: string): string {
  return PERIODOS_ETIQUETAS[periodo] ?? 'Últimos 12 meses'
}
