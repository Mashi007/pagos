/**
 * Módulo SPA «Revisión manual» (cola / editar préstamo).
 *
 * Opción C: desactivado — el trabajo se hace con otras herramientas del sistema
 * (pagos, cascada, conciliaciones, finiquitos, cobros, etc.).
 *
 * Importante: NO apaga servicios de backend compartidos (flags, cascada, finiquito,
 * reservas de conciliación). Solo UI y deep-links al SPA.
 *
 * Para reactivar: poner `true` y volver a exponer rutas/enlaces.
 */
export const REVISION_MANUAL_MODULE_ENABLED = false

export const RUTA_REVISION_MANUAL = '/revision-manual'

export function rutaEditarRevisionManual(prestamoId: number | string): string {
  return `${RUTA_REVISION_MANUAL}/editar/${prestamoId}`
}
