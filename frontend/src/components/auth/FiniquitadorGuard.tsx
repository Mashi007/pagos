import { useEffect } from 'react'
import { useLocation, Navigate } from 'react-router-dom'
import { useSimpleAuth } from '../../store/simpleAuthStore'
import { usePermissions } from '../../hooks/usePermissions'

/**
 * Guard para finiquitadores: redirige automáticamente a /finiquitos/gestion
 * y bloquea cualquier intento de acceder a otras rutas.
 * 
 * Un usuario con rol finiquitador:
 * - SOLO puede acceder a /finiquitos/gestion
 * - Cualquier otra ruta lo redirige a /finiquitos/gestion
 * - Si intenta manipular URL, es redirigido automáticamente
 */

interface FiniquitadorGuardProps {
  children: React.ReactNode
}

export function FiniquitadorGuard({ children }: FiniquitadorGuardProps) {
  const location = useLocation()
  const { user } = useSimpleAuth()
  const { isPuroFiniquitador } = usePermissions()

  // Si NO es finiquitador puro, renderizar normalmente
  if (!isPuroFiniquitador) {
    return <>{children}</>
  }

  // Si es finiquitador puro y NO está en /finiquitos/gestion
  // → redirigir a /finiquitos/gestion
  if (location.pathname !== '/finiquitos/gestion') {
    return <Navigate to="/finiquitos/gestion" replace />
  }

  // Si es finiquitador puro Y está en /finiquitos/gestion → renderizar
  return <>{children}</>
}

/**
 * Hook para detectar si debe bloquear acceso a una ruta específica
 * Usado en lazy-loaded pages para bloquear acceso tempranamente
 */
export function useFiniquitadorGuard() {
  const location = useLocation()
  const { isPuroFiniquitador } = usePermissions()

  // Si es finiquitador puro y NO está en /finiquitos/gestion
  if (isPuroFiniquitador && location.pathname !== '/finiquitos/gestion') {
    return { isBlocked: true, redirectTo: '/finiquitos/gestion' }
  }

  return { isBlocked: false, redirectTo: null }
}
