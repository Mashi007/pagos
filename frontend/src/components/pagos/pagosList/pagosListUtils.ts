import type { Pago } from '../../../services/pagoService'
import type { PagoConError } from '../../../services/pagoConErrorService'

/** Visible en columna Observaciones (lista principal y revisar pagos). */
export const OBSERVACION_COL_PAGO_DUPLICADO = 'PAGO DUPLICADO'

export const GMAIL_METRICS_SNAPSHOT_KEY = 'pagos:last_gmail_metrics_snapshot'

export function observacionesConMarcaDuplicadoCartera(p: PagoConError): string {
  const obs = (p.observaciones ?? '').trim()
  if (p.duplicado_documento_en_pagos === true) {
    return obs
      ? `${OBSERVACION_COL_PAGO_DUPLICADO} ${obs}`
      : OBSERVACION_COL_PAGO_DUPLICADO
  }
  return obs
}

/**
 * Pago «cerrado»: conciliado, verificado SI, aplicado a cuotas y estado PAGADO/ADELANTADO.
 */
export function pagoEstaCerradoSoloConsulta(
  p: Pago | PagoConError | null | undefined
): boolean {
  if (!p) return false
  const pago = p as Pago
  if (pago.tiene_aplicacion_cuotas === false) return false
  if (!Boolean(pago.conciliado)) return false
  const verif = String(pago.verificado_concordancia ?? '')
    .trim()
    .toUpperCase()
  if (verif !== 'SI') return false
  const est = String(pago.estado ?? '')
    .trim()
    .toUpperCase()
  return est === 'PAGADO' || est === 'PAGO_ADELANTADO' || est === 'ADELANTADO'
}

/** Pago elegible para «Conciliar y aplicar cuotas» en lote desde «Todos los Pagos». */
export function pagoElegibleConciliarAplicar(
  p: Pago | PagoConError | null | undefined
): boolean {
  if (!p) return false
  const pago = p as Pago
  if (!pago.prestamo_id) return false
  const monto =
    typeof pago.monto_pagado === 'number'
      ? pago.monto_pagado
      : parseFloat(String(pago.monto_pagado ?? 0))
  if (!Number.isFinite(monto) || monto <= 0) return false
  const estado = String(pago.estado ?? '')
    .trim()
    .toUpperCase()
  if (estado !== 'PENDIENTE' && estado !== '') return false
  if (pago.tiene_aplicacion_cuotas === true) return false
  return true
}
