import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

/**
 * Guard que previene navegación desde /infopagos a otras rutas protegidas.
 * Si alguien intenta acceder a cualquier ruta protegida sin autenticación,
 * será bloqueado en /acceso-limitado
 */
export function ProtectedAccessGuard() {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    // Si intenta navegar hacia atrás o a otra ruta protegida, lo devolvemos a /infopagos
    const handleBlockNavigation = (e: PopStateEvent) => {
      const currentPath = location.pathname
      // Si intenta retroceder desde /acceso-limitado, lo devolvemos a /infopagos
      if (currentPath === '/pagos/acceso-limitado') {
        e.preventDefault()
        navigate('/pagos/infopagos', { replace: true })
      }
    }

    window.addEventListener('popstate', handleBlockNavigation)
    return () => window.removeEventListener('popstate', handleBlockNavigation)
  }, [location.pathname, navigate])

  return null
}
