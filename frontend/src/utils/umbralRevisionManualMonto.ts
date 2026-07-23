/**
 * Alineado con backend MONTO_UMBRAL_REVISION_MANUAL:
 * cifra >= 1000 (Bs o USD, sin convertir) → revisión manual.
 */
export const MONTO_UMBRAL_REVISION_MANUAL = 1000

export function montoRequiereRevisionManual(
  monto: number | null | undefined
): boolean {
  if (monto == null || !Number.isFinite(monto)) return false
  return monto >= MONTO_UMBRAL_REVISION_MANUAL
}

export function mensajeMontoRevisionManual(monto: number): string {
  return (
    `El monto (${monto.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}) ` +
    `es igual o superior a ${MONTO_UMBRAL_REVISION_MANUAL.toLocaleString('es-VE')}; ` +
    'requiere revisión manual antes de autoconciliar.'
  )
}
