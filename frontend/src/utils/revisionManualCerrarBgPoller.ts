/**
 * Sigue jobs de revisión manual en segundo plano tras salir del editor o guardar pagos.
 * - Guardar y cerrar (cierre completo)
 * - Cascada pagos→cuotas (editar/agregar pago)
 */
import { toast } from 'sonner'

import { pagoService } from '../services/pagoService'
import { revisionManualService } from '../services/revisionManualService'

const STORAGE_CERRAR_PREFIX = 'rev_cerrar_bg:'
const STORAGE_CASCADA_PREFIX = 'rev_cascada_bg:'
const POLL_MS = 8000
const MAX_AGE_MS = 60 * 60 * 1000

let timerId: number | null = null
let inFlight = false

type OnTerminal = (prestamoId: number, ok: boolean) => void
let onCerrarTerminal: OnTerminal | null = null
let onCascadaTerminal: OnTerminal | null = null

function listPending(prefix: string): number[] {
  const ids: number[] = []
  try {
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i)
      if (!k || !k.startsWith(prefix)) continue
      const id = Number(k.slice(prefix.length))
      if (!Number.isFinite(id) || id <= 0) continue
      try {
        const raw = sessionStorage.getItem(k)
        const parsed = raw ? JSON.parse(raw) : null
        const startedAt = Number(parsed?.startedAt) || 0
        if (startedAt && Date.now() - startedAt > MAX_AGE_MS) {
          sessionStorage.removeItem(k)
          continue
        }
      } catch {
        /* keep polling */
      }
      ids.push(id)
    }
  } catch {
    return []
  }
  return ids
}

function clearPending(prefix: string, pid: number) {
  try {
    sessionStorage.removeItem(`${prefix}${pid}`)
  } catch {
    /* ignore */
  }
}

function storePending(prefix: string, prestamoId: number, token?: string) {
  try {
    sessionStorage.setItem(
      `${prefix}${prestamoId}`,
      JSON.stringify({ token: token || '', startedAt: Date.now() })
    )
  } catch {
    /* ignore */
  }
}

async function tick() {
  if (inFlight) return
  const pendingCerrar = listPending(STORAGE_CERRAR_PREFIX)
  const pendingCascada = listPending(STORAGE_CASCADA_PREFIX)
  if (pendingCerrar.length === 0 && pendingCascada.length === 0) {
    stopPoller()
    return
  }
  inFlight = true
  try {
    for (const pid of pendingCerrar) {
      try {
        const st = await revisionManualService.estadoGuardarYCerrarBg(pid)
        const est = String(st.estado || '').toLowerCase()
        if (est === 'ok') {
          clearPending(STORAGE_CERRAR_PREFIX, pid)
          toast.success(
            `Préstamo #${pid}: cierre listo (vencimientos, cascada y revisado).`
          )
          onCerrarTerminal?.(pid, true)
        } else if (est === 'error' || est === 'interrumpido') {
          clearPending(STORAGE_CERRAR_PREFIX, pid)
          toast.error(
            `Préstamo #${pid}: falló el cierre en segundo plano. ${
              st.error || 'Reabra la revisión y vuelva a intentar.'
            }`
          )
          onCerrarTerminal?.(pid, false)
        }
      } catch {
        /* red: siguiente tick */
      }
    }
    for (const pid of pendingCascada) {
      try {
        const st = await revisionManualService.estadoCascadaBg(pid)
        const est = String(st.estado || '').toLowerCase()
        if (est === 'ok') {
          clearPending(STORAGE_CASCADA_PREFIX, pid)
          toast.success(
            `Préstamo #${pid}: cascada de pagos completada (cuotas actualizadas).`
          )
          onCascadaTerminal?.(pid, true)
        } else if (est === 'error' || est === 'interrumpido') {
          clearPending(STORAGE_CASCADA_PREFIX, pid)
          try {
            await pagoService.aplicarPagosPendientesCuotasPorPrestamo(pid)
            toast.success(
              `Préstamo #${pid}: cascada aplicada a cuotas tras reintento.`
            )
            onCascadaTerminal?.(pid, true)
          } catch {
            toast.error(
              `Préstamo #${pid}: falló la cascada en segundo plano. ${
                st.error ||
                'Vuelva a guardar el pago o aplique cuotas manualmente.'
              }`
            )
            onCascadaTerminal?.(pid, false)
          }
        }
      } catch {
        /* red: siguiente tick */
      }
    }
  } finally {
    inFlight = false
  }
}

function stopPoller() {
  if (timerId != null) {
    window.clearInterval(timerId)
    timerId = null
  }
}

function ensurePoller() {
  if (typeof window === 'undefined') return
  if (timerId != null) return
  timerId = window.setInterval(() => {
    void tick()
  }, POLL_MS)
  void tick()
}

/** Marca un cierre BG y arranca el seguimiento en cualquier pantalla. */
export function trackRevisionManualCerrarBg(
  prestamoId: number,
  token?: string
): void {
  const pid = Number(prestamoId)
  if (!Number.isFinite(pid) || pid <= 0) return
  storePending(STORAGE_CERRAR_PREFIX, pid, token)
  ensurePoller()
}

/** Marca cascada BG (editar/agregar pago) y arranca el seguimiento. */
export function trackRevisionManualCascadaBg(
  prestamoId: number,
  token?: string
): void {
  const pid = Number(prestamoId)
  if (!Number.isFinite(pid) || pid <= 0) return
  storePending(STORAGE_CASCADA_PREFIX, pid, token)
  ensurePoller()
}

/** Quita el seguimiento de cascada BG (p. ej. al guardar el pago en el mismo request). */
export function clearRevisionManualCascadaBg(prestamoId: number): void {
  const pid = Number(prestamoId)
  if (!Number.isFinite(pid) || pid <= 0) return
  clearPending(STORAGE_CASCADA_PREFIX, pid)
}

/** Hay jobs BG pendientes en sessionStorage (para UI). */
export function hayRevisionManualBgPendiente(prestamoId?: number): boolean {
  if (prestamoId != null && Number.isFinite(prestamoId) && prestamoId > 0) {
    const pid = Number(prestamoId)
    return (
      listPending(STORAGE_CERRAR_PREFIX).includes(pid) ||
      listPending(STORAGE_CASCADA_PREFIX).includes(pid)
    )
  }
  return (
    listPending(STORAGE_CERRAR_PREFIX).length > 0 ||
    listPending(STORAGE_CASCADA_PREFIX).length > 0
  )
}

/** Reanuda el poller si hay pendientes (p. ej. al montar la app o la lista). */
export function resumeRevisionManualCerrarBgPoller(opts?: {
  onTerminal?: OnTerminal
  onCascadaTerminal?: OnTerminal
}): void {
  if (opts?.onTerminal) onCerrarTerminal = opts.onTerminal
  if (opts?.onCascadaTerminal) onCascadaTerminal = opts.onCascadaTerminal
  if (
    listPending(STORAGE_CERRAR_PREFIX).length > 0 ||
    listPending(STORAGE_CASCADA_PREFIX).length > 0
  ) {
    ensurePoller()
  }
}
