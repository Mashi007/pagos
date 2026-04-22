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
