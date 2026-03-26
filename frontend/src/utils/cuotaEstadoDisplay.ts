/**
 * Texto visible de estado de cuota cuando la API no envía `estado_etiqueta`.
 * Debe coincidir con `app.services.cuota_estado.etiqueta_estado_cuota` (única fuente de reglas en backend).
 * No reclasificar aquí: el código en `cuota.estado` viene del servidor.
 */

export function etiquetaEstadoCuotaRespaldo(
  codigo: string | null | undefined
): string {
  const c = (codigo || '').trim().toUpperCase()
  const labels: Record<string, string> = {
    PENDIENTE: 'Pendiente',
    PARCIAL: 'Pendiente parcial',
    VENCIDO: 'Vencido',
    MORA: 'Mora (4 meses+)',
    PAGADO: 'Pagado',
    PAGO_ADELANTADO: 'Pago adelantado',
    PAGADA: 'Pagado',
  }
  return labels[c] || (codigo || '').trim() || '-'
}

/** Código para colores de badge (mayúsculas, PAGADA → PAGADO). */
export function codigoEstadoCuotaParaUi(
  raw: string | null | undefined
): string {
  const c = (raw || '').trim().toUpperCase()
  if (!c) return 'PENDIENTE'
  if (c === 'PAGADA') return 'PAGADO'
  return c
}
