/**
 * Contexto de plantilla de correo alineado con cada submenú de Notificaciones.
 * Query en Configuración → Plantillas: ?tab=plantillas&notif_tipo=PAGO_2_DIAS_ANTES_PENDIENTE
 */

export const NOTIF_PLANTILLA_TIPO_QUERY = 'notif_tipo'

/** Títulos para el panel "Servicio de notificación" y resúmenes. */
export const ETIQUETA_SERVICIO_PLANTILLA: Record<string, string> = {
  PAGO_5_DIAS_ANTES: '5 días antes del vencimiento',
  PAGO_3_DIAS_ANTES: '3 días antes del vencimiento',
  PAGO_1_DIA_ANTES: '1 día antes del vencimiento',
  PAGO_2_DIAS_ANTES_PENDIENTE:
    '2 días antes (cuota pendiente; vence en 2 días, calendario)',
  PAGO_DIA_0: 'Día de pago (vence hoy)',
  PAGO_1_DIA_ATRASADO:
    'Día siguiente al vencimiento (1 día de atraso calendario)',
  PAGO_10_DIAS_ATRASADO: '10 días de retraso (calendario desde vencimiento)',
  PREJUDICIAL: 'Prejudicial (5+ cuotas VENCIDO/MORA)',
  MASIVOS: 'Comunicaciones masivas',
  COBRANZA: 'Carta de cobranza (COBRANZA)',
}

const _KNOWN = new Set(Object.keys(ETIQUETA_SERVICIO_PLANTILLA))

export function normalizarNotifTipoDesdeQuery(raw: string | null): string {
  if (raw && _KNOWN.has(raw)) return raw
  return 'PAGO_1_DIA_ATRASADO'
}

export function etiquetaServicioPlantilla(tipo: string): string {
  return ETIQUETA_SERVICIO_PLANTILLA[tipo] ?? tipo
}

export function bordeTarjetaServicioPlantilla(tipo: string): string {
  if (tipo === 'PREJUDICIAL') return 'border-red-400'
  if (tipo === 'PAGO_2_DIAS_ANTES_PENDIENTE') return 'border-sky-400'
  if (tipo === 'MASIVOS') return 'border-teal-400'
  if (tipo === 'COBRANZA') return 'border-violet-400'
  if (tipo === 'PAGO_DIA_0') return 'border-emerald-400'
  if (tipo.includes('ANTES') && tipo.includes('PAGO_')) return 'border-blue-400'
  if (tipo.includes('ATRASADO') || tipo === 'PAGO_1_DIA_ATRASADO')
    return 'border-amber-400'
  return 'border-slate-400'
}

/** Listado Notificaciones acorde al tipo de plantilla (submenú). */
export function rutaListadoNotificacionesPorTipoPlantilla(
  tipo: string
): string {
  switch (tipo) {
    case 'PAGO_2_DIAS_ANTES_PENDIENTE':
      return '/notificaciones/d-2-antes'
    case 'PREJUDICIAL':
      return '/notificaciones/a-3-cuotas'
    case 'PAGO_10_DIAS_ATRASADO':
      return '/notificaciones/atraso-10-dias'
    default:
      return '/notificaciones'
  }
}

export function hrefPlantillasConContexto(tipoNotificacion: string): string {
  return `/configuracion?tab=plantillas&${NOTIF_PLANTILLA_TIPO_QUERY}=${encodeURIComponent(tipoNotificacion)}`
}

/** Selector en Configuración → Plantillas (orden alfabético por etiqueta). */
export const OPCIONES_SELECT_NOTIF_TIPO_PLANTILLA: {
  value: string
  label: string
}[] = Object.entries(ETIQUETA_SERVICIO_PLANTILLA)
  .map(([value, label]) => ({ value, label }))
  .sort((a, b) => a.label.localeCompare(b.label, 'es'))
