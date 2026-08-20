/**




 * Conceptos de negocio unificados (Backend y Frontend).




 *




 * PAGO VENCIDO Y MOROSO:




 * - Pago vencido = cuotas vencidas y no pagadas (fecha_vencimiento < hoy).




 * - Vencido: si debo pagar hasta el 23 feb, NO estoy vencido hasta el 24 feb.




 *   Desde el 24 = vencido (1-89 días de atraso).




 * - Moroso: umbral oficial en backend/app/services/cuota_estado.py
 *   (MORA_DESDE_MESES + MORA_BUFFER_DIAS). No calcular estado aquí.




 *




 * Condición técnica: fecha_vencimiento < fecha_referencia AND fecha_pago IS NULL




 */

/** Meses/días de mora: documentativo. La clasificación vive en el backend (cuota_estado). */

export const MESES_MOROSO_DESDE = 4

/** Etiqueta en UI: reemplaza "Morosidad" por "Pago vencido" */

export const ETIQUETA_PAGO_VENCIDO = 'Pago vencido'
