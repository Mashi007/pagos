import { useEffect, useState } from 'react'

/**
 * Retorna false hasta que pase `delayMs` desde el montaje.
 * Sirve para escalonar peticiones del dashboard y no saturar el worker en carga fría.
 */
export function useStaggeredEnable(delayMs: number): boolean {
  const [enabled, setEnabled] = useState(delayMs <= 0)

  useEffect(() => {
    if (delayMs <= 0) {
      setEnabled(true)
      return
    }
    setEnabled(false)
    const timer = window.setTimeout(() => setEnabled(true), delayMs)
    return () => window.clearTimeout(timer)
  }, [delayMs])

  return enabled
}

/** Delays estándar para batches del dashboard (ms). */
export const DASHBOARD_STAGGER = {
  critical: 0,
  secondary: 400,
  tertiary: 900,
} as const
