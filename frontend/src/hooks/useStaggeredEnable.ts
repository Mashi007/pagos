import { useEffect, useState } from 'react'

/**
 * Retorna false hasta que pase `delayMs` desde el montaje.
 * Si `immediate` es true (p. ej. hay caché caliente), habilita al instante
 * para no “recargar” el dashboard al volver a la ruta.
 */
export function useStaggeredEnable(
  delayMs: number,
  immediate: boolean = false
): boolean {
  const [enabled, setEnabled] = useState(delayMs <= 0 || immediate)

  useEffect(() => {
    if (immediate || delayMs <= 0) {
      setEnabled(true)
      return
    }
    setEnabled(false)
    const timer = window.setTimeout(() => setEnabled(true), delayMs)
    return () => window.clearTimeout(timer)
  }, [delayMs, immediate])

  return enabled
}

/** Delays estándar para batches del dashboard (ms). */
export const DASHBOARD_STAGGER = {
  critical: 0,
  secondary: 400,
  tertiary: 900,
} as const
