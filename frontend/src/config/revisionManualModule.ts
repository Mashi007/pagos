/**
 * Módulo SPA «Revisión manual» (cola / editar préstamo).
 *
 * `REVISION_MANUAL_MODULE_ENABLED`: apaga solo UI/rutas/deep-links al SPA.
 * Backend compartido (flags, cascada, finiquito, conciliación) sigue activo.
 */
export const REVISION_MANUAL_MODULE_ENABLED = true

export const RUTA_REVISION_MANUAL = '/revision-manual'

export function rutaEditarRevisionManual(prestamoId: number | string): string {
  return `${RUTA_REVISION_MANUAL}/editar/${prestamoId}`
}
