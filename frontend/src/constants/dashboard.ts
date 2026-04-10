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

/** Título del gráfico de bandas de financiamiento (menú dashboard). */
export const FINANCIAMIENTO_BANDAS_GRAFICO_TITULO =
  'Distribuci\u00F3n por bandas ($300, desde $500 hasta $4.000)'

/**
 * Orden del eje Y (arriba mayor banda). Debe coincidir con `categoria` de
 * GET /api/v1/dashboard/financiamiento-por-rangos (backend `utils._rangos_financiamiento`).
 */
export const FINANCIAMIENTO_BANDAS_ORDEN_CATEGORIAS: readonly string[] = [
  'M\u00E1s de $4,000',
  '$3,800 - $4,000',
  '$3,500 - $3,800',
  '$3,200 - $3,500',
  '$2,900 - $3,200',
  '$2,600 - $2,900',
  '$2,300 - $2,600',
  '$2,000 - $2,300',
  '$1,700 - $2,000',
  '$1,400 - $1,700',
  '$1,100 - $1,400',
  '$800 - $1,100',
  '$500 - $800',
  'Menos de $500',
]
