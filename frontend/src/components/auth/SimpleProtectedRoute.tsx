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
  const { isAuthenticated, user, isLoading, refreshUser } = useSimpleAuth()
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
          <p className="text-sm text-red-600 font-semibold">
            DEBUG: requireAdmin={requireAdmin ? 'true' : 'false'}, user.is_admin={user.is_admin ? 'true' : 'false'}
          </p>
          <div className="mt-4 space-y-2">
            <button
              onClick={refreshUser}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              🔄 Actualizar Permisos desde Servidor
            </button>
            <button
              onClick={async () => {
                try {
                  const response = await fetch('/api/v1/fix-refresh/fix-user-admin', {
                    method: 'POST',
                    headers: {
                      'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`,
                      'Content-Type': 'application/json'
                    }
                  })
                  const result = await response.json()
                  if (result.status === 'success') {
                    alert('✅ Usuario marcado como administrador exitosamente')
                    window.location.reload()
                  } else {
                    alert(`❌ Error: ${result.error}`)
                  }
                } catch (error) {
                  alert(`❌ Error: ${error}`)
                }
              }}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors"
            >
              🔧 Marcar como Administrador
            </button>
            <p className="text-sm text-blue-600 font-semibold">
              Si eres administrador, haz clic en el botón para actualizar tus permisos
            </p>
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
