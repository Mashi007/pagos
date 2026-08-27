import { useSyncExternalStore } from 'react'

import {
  hayRevisionManualCascadaBgPendiente,
  subscribeRevisionManualBgPending,
} from '../utils/revisionManualCerrarBgPoller'

const POLL_UI_MS = 2500

/** True mientras la cascada pagos→cuotas sigue en segundo plano para este préstamo. */
export function useRevisionManualCascadaBgPendiente(
  prestamoId: number | undefined
): boolean {
  const pid =
    prestamoId != null && Number.isFinite(prestamoId) && prestamoId > 0
      ? Number(prestamoId)
      : 0

  const subscribe = (onStoreChange: () => void) => {
    if (pid <= 0) return () => {}
    const unsub = subscribeRevisionManualBgPending(onStoreChange)
    const iv = window.setInterval(onStoreChange, POLL_UI_MS)
    return () => {
      unsub()
      window.clearInterval(iv)
    }
  }

  const getSnapshot = () =>
    pid > 0 ? hayRevisionManualCascadaBgPendiente(pid) : false

  return useSyncExternalStore(subscribe, getSnapshot, () => false)
}
