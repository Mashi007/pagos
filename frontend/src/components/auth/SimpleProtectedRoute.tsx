// frontend/src/components/auth/SimpleProtectedRoute.tsx
import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface SimpleProtectedRouteProps {
  children: React.ReactNode
  requireAdmin?: boolean  // Cambio clave: requiredRoles → requireAdmin
  fallbackPath?: string
}

export function SimpleProtectedRoute({ 
  children, 
  requireAdmin = false,  // Cambio clave: requiredRoles → requireAdmin
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

  // Si se requiere admin y el usuario no es admin
  if (requireAdmin && !user.is_admin) {  // Cambio clave: rol → is_admin
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
            Se requiere acceso de administrador
          </p>
          <p className="text-sm text-gray-500">
            Su rol actual: {user.is_admin ? 'Administrador' : 'Usuario'}
          </p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
