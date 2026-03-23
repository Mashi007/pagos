/** Clave estable para GET /prestamos/:id/cuotas (tabla de amortizacion). */
export const CUOTAS_PRESTAMO_QUERY_PREFIX = 'cuotas-prestamo' as const

export function cuotasPrestamoQueryKey(prestamoId: number) {
  return [CUOTAS_PRESTAMO_QUERY_PREFIX, prestamoId] as const
}
