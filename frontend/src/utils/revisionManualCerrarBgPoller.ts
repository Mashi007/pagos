/**
 * Sigue el estado de «Guardar y cerrar» en segundo plano tras salir del editor.
 * Un solo interval compartido; no bloquea la UI.
 */
import { toast } from 'sonner'

import { revisionManualService } from '../services/revisionManualService'

const STORAGE_PREFIX = 'rev_cerrar_bg:'
const POLL_MS = 8000
const MAX_AGE_MS = 60 * 60 * 1000

let timerId: number | null = null
let inFlight = false

type OnTerminal = (prestamoId: number, ok: boolean) => void
let onTerminal: OnTerminal | null = null

function listPending(): number[] {
  const ids: number[] = []
  try {
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i)
      if (!k || !k.startsWith(STORAGE_PREFIX)) continue
      const id = Number(k.slice(STORAGE_PREFIX.length))
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

function clearPending(pid: number) {
  try {
    sessionStorage.removeItem(`${STORAGE_PREFIX}${pid}`)
  } catch {
    /* ignore */
  }
}

async function tick() {
  if (inFlight) return
  const pending = listPending()
  if (pending.length === 0) {
    stopPoller()
    return
  }
  inFlight = true
  try {
    for (const pid of pending) {
      try {
        const st = await revisionManualService.estadoGuardarYCerrarBg(pid)
        const est = String(st.estado || '').toLowerCase()
        if (est === 'ok') {
          clearPending(pid)
          toast.success(
            `Préstamo #${pid}: cierre listo (vencimientos, cascada y revisado).`
          )
          onTerminal?.(pid, true)
        } else if (est === 'error' || est === 'interrumpido') {
          clearPending(pid)
          toast.error(
            `Préstamo #${pid}: falló el cierre en segundo plano. ${
              st.error || 'Reabra la revisión y vuelva a intentar.'
            }`
          )
          onTerminal?.(pid, false)
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
  try {
    sessionStorage.setItem(
      `${STORAGE_PREFIX}${pid}`,
      JSON.stringify({ token: token || '', startedAt: Date.now() })
    )
  } catch {
    /* ignore */
  }
  ensurePoller()
}

/** Reanuda el poller si hay pendientes (p. ej. al montar la app o la lista). */
export function resumeRevisionManualCerrarBgPoller(
  opts?: { onTerminal?: OnTerminal }
): void {
  if (opts?.onTerminal) onTerminal = opts.onTerminal
  if (listPending().length > 0) ensurePoller()
}
