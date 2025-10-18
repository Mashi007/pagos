// frontend/src/components/auth/SimpleProtectedRoute.tsx
import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface SimpleProtectedRouteProps {
  children: React.ReactNode
  requiredRoles?: string[]
  fallbackPath?: string
}

export function SimpleProtectedRoute({ 
  children, 
  requiredRoles = [], 
  fallbackPath = '/login' 
}: SimpleProtectedRouteProps) {
  const { isAuthenticated, user, isLoading } = useSimpleAuth()
  const location = useLocation()

  // Mostrar loading mientras se verifica la autenticación
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" text="Verificando autenticación..." />
      </div>
    )
  }

  // Si no está autenticado, redirigir al login
  if (!isAuthenticated || !user) {
    return <Navigate to={fallbackPath} state={{ from: location }} replace />
  }

  // Si se requieren roles específicos, verificar permisos
  if (requiredRoles.length > 0 && !requiredRoles.includes(user.rol as string)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Acceso Denegado
          </h1>
          <p className="text-gray-600 mb-4">
            No tiene permisos para acceder a esta página.
          </p>
          <p className="text-sm text-gray-500">
            Rol requerido: {requiredRoles.join(', ')}
          </p>
          <p className="text-sm text-gray-500">
            Su rol actual: {user?.rol || 'No disponible'}
          </p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
