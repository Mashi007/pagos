/** Mirror of backend envio_batch_sigue_activo (stale ~10 min). */
export const ENVIO_BATCH_STALE_MS = 10 * 60 * 1000

export type UltimoEnvioBatchLike = {
  estado?: unknown
  fin_utc?: unknown
  heartbeat_utc?: unknown
  inicio_utc?: unknown
  detalles?: unknown
}

export function envioBatchSigueActivoUi(
  ultimo: UltimoEnvioBatchLike | null | undefined,
  staleMs: number = ENVIO_BATCH_STALE_MS
): boolean {
  if (!ultimo || typeof ultimo !== 'object') return false
  const estado = String(ultimo.estado || '')
    .trim()
    .toLowerCase()
  if (estado === 'finalizado') return false
  const det =
    typeof ultimo.detalles === 'object' && ultimo.detalles !== null
      ? (ultimo.detalles as Record<string, unknown>)
      : null
  let enProc =
    estado === 'en_proceso' || Boolean(det && det.en_proceso)
  if (!enProc && (ultimo.fin_utc == null || String(ultimo.fin_utc).trim() === '')) {
    enProc = true
  }
  if (!enProc) return false
  const hb = String(ultimo.heartbeat_utc || ultimo.inicio_utc || '').trim()
  if (!hb) return true
  const ms = Date.parse(hb)
  if (!Number.isFinite(ms)) return true
  return Date.now() - ms <= staleMs
}
