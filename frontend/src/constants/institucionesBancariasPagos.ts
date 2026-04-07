/**
 * Instituciones para registrar/editar pago (`institucion_bancaria`).
 * Lista fija ordenada en UI; si en BD hay un valor distinto, se antepone a la lista.
 */
export const INSTITUCIONES_BANCARIAS_PAGO: readonly string[] = [
  '100% Banco',
  'Banco Activo Banco Universal',
  'Banco Agrícola de Venezuela',
  'Banco Bicentenario del Pueblo',
  'Banco Caroní',
  'Banco de Venezuela',
  'Banco del Tesoro',
  'Banco Digital de los Trabajadores Banco Universal',
  'Banco Exterior',
  'Banco Fondo Común (BFC)',
  'Banco Mercantil',
  'Banco Nacional de Crédito (BNC)',
  'Banco Plaza',
  'Banco Sofitasa',
  'Banesco',
  'Banesco Banco Universal',
  'Banplus Banco Universal',
  'BBVA Banco Provincial',
  'BINANCE',
  'BNC',
  'BOD',
  'Citibank',
  'DelSur Banco Universal',
  'Mercantil',
  'Mi Banco Banco Microfinanciero C.A.',
  'Pago móvil',
  'PayPal',
  'Provincial',
  'Zelle',
]

const SIN_ESPECIFICAR_VALUE = '__sin_especificar__'

export { SIN_ESPECIFICAR_VALUE }

export function listaInstitucionesBancariasOrdenada(): string[] {
  return [...INSTITUCIONES_BANCARIAS_PAGO].sort((a, b) =>
    a.localeCompare(b, 'es', { sensitivity: 'base' })
  )
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
