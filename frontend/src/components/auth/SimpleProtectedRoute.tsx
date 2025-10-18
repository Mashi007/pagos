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
  if (requireAdmin && !user.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="mb-6">
            <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Acceso Denegado
            </h1>
            <p className="text-gray-600 mb-4">
              No tiene permisos para acceder a esta página.
            </p>
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-gray-700 mb-1">
                <strong>Se requiere:</strong> Acceso de administrador
              </p>
              <p className="text-sm text-gray-700">
                <strong>Su rol actual:</strong> {user.is_admin ? 'Administrador' : 'Usuario'}
              </p>
            </div>
          </div>
          
          <div className="space-y-3">
            <button
              onClick={() => window.history.back()}
              className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              ← Volver a la página anterior
            </button>
            
            <button
              onClick={() => window.location.href = '/dashboard'}
              className="w-full bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700 transition-colors font-medium"
            >
              Ir al Dashboard
            </button>
          </div>
          
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              Si cree que esto es un error, contacte al administrador del sistema.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
