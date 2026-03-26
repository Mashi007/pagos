/** Subconjunto de React Query (evita TS con verbatimModuleSyntax + QueryClient). */
type QueryClientInvalidate = {
  invalidateQueries: (filters: {
    queryKey: readonly unknown[]
  }) => Promise<unknown>
}

/** Clave estable para GET /prestamos/:id/cuotas (tabla de amortizacion). */
export const CUOTAS_PRESTAMO_QUERY_PREFIX = 'cuotas-prestamo' as const

export function cuotasPrestamoQueryKey(prestamoId: number) {
  return [CUOTAS_PRESTAMO_QUERY_PREFIX, prestamoId] as const
}

/** Listas de mora en Notificaciones (cuotas sin pagar). Invalidar al registrar/editar/eliminar pagos. */
export const NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY = [
  'notificaciones-clientes-retrasados',
] as const

export const NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY = [
  'notificaciones-estadisticas-por-tab',
] as const

/** Mismo nombre en todas las pestañas del origen (sync listas de mora). */
export const NOTIFICACIONES_MORA_BROADCAST_CHANNEL =
  'pagos-notificaciones-mora-v1' as const

export type InvalidateNotificacionesMoraOptions = {
  /**
   * Evita reenviar por BroadcastChannel (la pestaña que recibe el evento
   * solo invalida localmente; sin esto habría ping-pong entre pestañas).
   */
  skipCrossTabBroadcast?: boolean
}

function broadcastInvalidateNotificacionesMoraPeerTabs() {
  if (typeof BroadcastChannel === 'undefined') return
  try {
    const ch = new BroadcastChannel(NOTIFICACIONES_MORA_BROADCAST_CHANNEL)
    ch.postMessage({ type: 'invalidate' as const })
    ch.close()
  } catch {
    // entornos sin canal o políticas del navegador
  }
}

/**
 * Refresca listas y KPIs de notificaciones cuando cambia el estado de cuotas
 * (p. ej. tras registrar un pago que marca fecha_pago en la cuota).
 * También avisa a otras pestañas del mismo origen para que invaliden su caché.
 */
export async function invalidateListasNotificacionesMora(
  queryClient: QueryClientInvalidate,
  options?: InvalidateNotificacionesMoraOptions
) {
  await Promise.all([
    queryClient.invalidateQueries({
      queryKey: NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
    }),
    queryClient.invalidateQueries({
      queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
    }),
  ])
  if (!options?.skipCrossTabBroadcast) {
    broadcastInvalidateNotificacionesMoraPeerTabs()
  }
}
