/**
 * Constantes del dashboard: periodos y etiquetas.
 * Usamos secuencias Unicode para evitar problemas de codificacion en el navegador.
 */

/** Valor del periodo "Hoy" (usado en Select y en calculo de fechas) */
export const PERIODO_DIA = 'd\u00EDa' as const

/** Valores de periodo admitidos en el selector general */
export const PERIODOS_VALORES = [
  'ultimos_12_meses',
  PERIODO_DIA,
  'semana',
  'mes',
  'a\u00F1o',
] as const

export type PeriodoValor = (typeof PERIODOS_VALORES)[number]

/** Etiquetas para mostrar en la UI */
export const PERIODOS_ETIQUETAS: Record<string, string> = {
  ultimos_12_meses: 'Ultimos 12 meses',
  'd\u00EDa': 'Hoy',
  dia: 'Hoy',
  semana: 'Esta semana',
  mes: 'Este mes',
  'a\u00F1o': 'Este a\u00F1o',
}

/** Obtiene la etiqueta de un periodo (acepta "dia" o "d\u00EDa") */
export function getPeriodoEtiqueta(periodo: string): string {
  return PERIODOS_ETIQUETAS[periodo] ?? 'Ultimos 12 meses'
}