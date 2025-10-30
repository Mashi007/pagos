import { useEffect } from 'react'

/**
 * Dispara onClose cuando el usuario presiona Escape en cualquier parte de la vista.
 * Útil para formularios/modales. Pasa `enabled=false` para desactivar temporalmente.
 */
export function useEscapeClose(onClose: () => void, enabled: boolean = true) {
  useEffect(() => {
    if (!enabled) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
        try {
          onClose()
        } catch {
          // noop
        }
      }
    }
    window.addEventListener('keydown', handler, { capture: true })
    return () => window.removeEventListener('keydown', handler, { capture: true } as any)
  }, [onClose, enabled])
}


