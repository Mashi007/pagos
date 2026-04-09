/**
 * Instituciones para registrar/editar pago (`institucion_bancaria`).
 * Lista corta fija en UI; si en BD hay un valor distinto, se antepone a la lista.
 */
export const INSTITUCIONES_BANCARIAS_PAGO: readonly string[] = [
  'Mercantil',
  'BNC',
  'BNV',
  'Binance',
  'Recibo',
]

const SIN_ESPECIFICAR_VALUE = '__sin_especificar__'

export { SIN_ESPECIFICAR_VALUE }

/** Mismo orden que el catálogo (no orden alfabético). */
export function listaInstitucionesBancariasOrdenada(): string[] {
  return [...INSTITUCIONES_BANCARIAS_PAGO]
}

/** Incluye el valor actual si no está en el catálogo (datos legacy). */
export function opcionesBancoConValorActual(
  actual: string | null | undefined
): string[] {
  const base = listaInstitucionesBancariasOrdenada()
  const t = (actual || '').trim()
  if (!t) return base
  if (base.includes(t)) return base
  return [t, ...base]
}
