import type { NotificacionesModulo } from './notificacionesPage.tabs'

/** Título del h1 en el encabezado del módulo (orientación por submenú). */
export function tituloEncabezadoNotificaciones(
  modulo: NotificacionesModulo
): string {
  switch (modulo) {
    case 'd2antes':
      return 'Notificaciones: 2 días antes del vencimiento'
    case 'a1dia':
      return 'Notificaciones: día siguiente al vencimiento'
    case 'a10dias':
      return 'Notificaciones: 10 días de atraso'
    case 'a3cuotas':
      return 'Notificaciones: prejudicial (5+ cuotas)'
    case 'general':
      return 'Notificaciones: vista general'
    case 'fecha':
      return 'Notificaciones: diferencia fecha (consulta)'
    default:
      return 'Notificaciones'
  }
}

/** Texto de la pestaña del navegador al estar en este submódulo. */
export function tituloDocumentoNotificaciones(
  modulo: NotificacionesModulo
): string {
  return `${tituloEncabezadoNotificaciones(modulo)} · RapiCredit`
}
