/** Subconjunto de React Query (evita TS con verbatimModuleSyntax + QueryClient). */
type QueryClientInvalidate = {
  invalidateQueries: (filters: {
    queryKey: readonly unknown[]
    exact?: boolean
  }) => Promise<unknown>
}

/** Clave estable para GET /prestamos/:id/cuotas (tabla de amortizacion). */
export const CUOTAS_PRESTAMO_QUERY_PREFIX = 'cuotas-prestamo' as const

export function cuotasPrestamoQueryKey(prestamoId: number) {
  return [CUOTAS_PRESTAMO_QUERY_PREFIX, prestamoId] as const
}

/** Lista Revisión manual (useQuery en RevisionManual.tsx). */
export const REVISION_MANUAL_PRESTAMOS_QUERY_PREFIX =
  'revision-manual-prestamos' as const

/** Detalle edición Revisión manual (useQuery en EditarRevisionManual.tsx). */
export const REVISION_EDITAR_QUERY_PREFIX = 'revision-editar' as const

/** Listas de mora en Notificaciones (cuotas sin pagar). Invalidar al registrar/editar/eliminar pagos. */
export const NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY = [
  'notificaciones-clientes-retrasados',
] as const

export const NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY = [
  'notificaciones-estadisticas-por-tab',
] as const

/** Lista prejudicial (GET /notificaciones-prejudicial); módulo Atraso 5 cuotas. */
export const NOTIFICACIONES_PREJUDICIAL_LISTA_QUERY_KEY = [
  'notificaciones-prejudicial-lista',
] as const

/** Pendiente, vence en 2 días (GET /notificaciones/cuotas-pendiente-2-dias-antes); submenú 2 días antes. */
export const NOTIFICACIONES_D2_ANTES_QUERY_KEY = [
  'notificaciones-d2-antes-vencimiento',
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
      queryKey: NOTIFICACIONES_PREJUDICIAL_LISTA_QUERY_KEY,
    }),
    queryClient.invalidateQueries({
      queryKey: NOTIFICACIONES_D2_ANTES_QUERY_KEY,
    }),
    queryClient.invalidateQueries({
      queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
    }),
  ])
  if (!options?.skipCrossTabBroadcast) {
    broadcastInvalidateNotificacionesMoraPeerTabs()
  }
}

export type InvalidatePagosRevisionOptions = {
  /** No llamar invalidateListasNotificacionesMora (el caller lo hace después). */
  skipNotificacionesMora?: boolean
  /** KPIs/resumen menú y dashboard (misma idea que tras registrar pago en Pagos). */
  includeDashboardMenu?: boolean
  /**
   * No invalidar la query del detalle de edición en revisión manual (p. ej. dentro del queryFn
   * que acaba de traer datos frescos; evita refetch duplicado del mismo GET).
   */
  skipRevisionEditar?: boolean
}

/**
 * Tras crear/editar/eliminar pagos o tocar cuotas desde Pagos o Revisión manual:
 * mantiene alineados listados de Pagos, amortización, préstamos y Revisión manual (otras pestañas).
 */
export async function invalidatePagosPrestamosRevisionYCuotas(
  queryClient: QueryClientInvalidate,
  options?: InvalidatePagosRevisionOptions
) {
  const inv: Promise<unknown>[] = [
    queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false }),
    queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false }),
    /** Sidebar / DashboardPagos usan esta clave para GET /pagos/kpis sin filtros. */
    queryClient.invalidateQueries({ queryKey: ['kpis-pagos'], exact: false }),
    queryClient.invalidateQueries({
      queryKey: ['pagos-ultimos'],
      exact: false,
    }),
    queryClient.invalidateQueries({
      queryKey: ['pagos-por-cedula'],
      exact: false,
    }),
    queryClient.invalidateQueries({
      queryKey: ['pagos-con-errores'],
      exact: false,
    }),
    queryClient.invalidateQueries({
      queryKey: [CUOTAS_PRESTAMO_QUERY_PREFIX],
      exact: false,
    }),
    /** Reportes / amortización masiva (clave plural distinta de `cuotas-prestamo`). */
    queryClient.invalidateQueries({
      queryKey: ['cuotas-prestamos'],
      exact: false,
    }),
    queryClient.invalidateQueries({ queryKey: ['prestamos'], exact: false }),
    queryClient.invalidateQueries({
      queryKey: [REVISION_MANUAL_PRESTAMOS_QUERY_PREFIX],
      exact: false,
    }),
  ]
  if (!options?.skipRevisionEditar) {
    inv.push(
      queryClient.invalidateQueries({
        queryKey: [REVISION_EDITAR_QUERY_PREFIX],
        exact: false,
      })
    )
  }
  if (options?.includeDashboardMenu) {
    inv.push(
      queryClient.invalidateQueries({ queryKey: ['kpis'], exact: false }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false }),
      queryClient.invalidateQueries({
        queryKey: ['kpis-principales-menu'],
        exact: false,
      }),
      queryClient.invalidateQueries({
        queryKey: ['dashboard-menu'],
        exact: false,
      })
    )
  }
  await Promise.all(inv)
  if (!options?.skipNotificacionesMora) {
    void invalidateListasNotificacionesMora(queryClient)
  }
}
