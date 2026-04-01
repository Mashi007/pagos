/**
 * Hook: detecta si el dispositivo es movil (ancho < 768px o touch).
 * Se usa para decidir entre vista previa (desktop) y descarga directa (movil).
 */
import { useState, useEffect } from 'react'

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return window.innerWidth < 768 || navigator.maxTouchPoints > 0
  })

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    setIsMobile(mq.matches || navigator.maxTouchPoints > 0)
    return () => mq.removeEventListener('change', handler)
  }, [])

  return isMobile
}
