/**
 * Conceptos de negocio unificados (Backend y Frontend).
 *
 * PAGO VENCIDO Y MOROSO:
 * - Pago vencido = cuotas vencidas y no pagadas (fecha_vencimiento < hoy).
 * - Vencido: si debo pagar hasta el 23 feb, NO estoy vencido hasta el 24 feb.
 *   Desde el 24 = vencido (1-89 días de atraso).
 * - Moroso: 90+ días de atraso (se declara como moroso desde el día 90).
 *
 * Condición técnica: fecha_vencimiento < fecha_referencia AND fecha_pago IS NULL
 */

/** Días a partir de los cuales se declara MOROSO (90+ días de atraso) */
export const DIAS_MOROSO_DESDE = 90

/** Etiqueta en UI: reemplaza "Morosidad" por "Pago vencido" */
export const ETIQUETA_PAGO_VENCIDO = 'Pago vencido'
