import { useRef, useEffect } from 'react'

/**
 * Hook para verificar si un componente estÃ¡ montado
 * Ãtil para evitar actualizaciones de estado despuÃ©s del desmontaje
 * que pueden causar errores como NS_ERROR_FAILURE en Firefox
 */
export function useIsMounted() {
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  return () => isMountedRef.current
}

