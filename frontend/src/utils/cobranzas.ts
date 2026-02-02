/**
 * Utilidades para la página de Cobranzas (validación de filtros, etc.)
 */

export interface ValidacionRangoDiasResult {
  valid: boolean
  error: string | null
}

/** Valida rango de días mínimo/máximo para filtros. Retorna error o null si es válido. */
export function validarRangoDias(
  min: number | undefined,
  max: number | undefined
): ValidacionRangoDiasResult {
  if (min !== undefined && max !== undefined && min > max) {
    return { valid: false, error: 'Los días mínimos no pueden ser mayores que los días máximos' }
  }
  if (min !== undefined && min < 0) {
    return { valid: false, error: 'Los días mínimos deben ser un número positivo' }
  }
  if (max !== undefined && max < 0) {
    return { valid: false, error: 'Los días máximos deben ser un número positivo' }
  }
  return { valid: true, error: null }
}
