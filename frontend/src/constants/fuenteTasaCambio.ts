/** Fuente de tasa Bs→USD (Venezuela) elegida tras validar la cédula en cobros / infopagos. */
export type FuenteTasaCambio = 'bcv' | 'euro' | 'binance'

export const FUENTE_TASA_DEFAULT: FuenteTasaCambio = 'euro'

export const FUENTE_TASA_OPCIONES: ReadonlyArray<{
  value: FuenteTasaCambio
  label: string
}> = [
  { value: 'bcv', label: 'BCV' },
  { value: 'euro', label: 'Euro' },
  { value: 'binance', label: 'Binance' },
]

/** Alineado con backend `normalizar_fuente_tasa` (bcv | euro | binance; defecto euro). */
export function normalizarFuenteTasaCambio(
  raw: string | null | undefined
): FuenteTasaCambio {
  const s = String(raw ?? '')
    .trim()
    .toLowerCase()
  if (s === 'bcv' || s === 'euro' || s === 'binance') return s
  return FUENTE_TASA_DEFAULT
}
