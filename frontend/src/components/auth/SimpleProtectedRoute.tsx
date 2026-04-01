// frontend/src/components/auth/SimpleProtectedRoute.tsx

import React from 'react'

import { Navigate, useLocation } from 'react-router-dom'

import { useSimpleAuth } from '../../store/simpleAuthStore'

import { LoadingSpinner } from '../../components/ui/loading-spinner'

import { BASE_PATH } from '../../config/env'

interface SimpleProtectedRouteProps {
  children: React.ReactNode

  requireAdmin?: boolean // Cambio clave: requiredRoles -> requireAdmin

  /** Si no autenticado, redirige aquí. Por defecto /rapicredit (formulario público). Empleados usan /login. */

  fallbackPath?: string
}

export function SimpleProtectedRoute({
  children,

  requireAdmin = false,

  fallbackPath = '/login',
}: SimpleProtectedRouteProps) {
  const { isAuthenticated, user, isLoading } = useSimpleAuth()

  const homeForRole =
    (user?.rol || '').toLowerCase() === 'operator' ? '/clientes' : '/dashboard'

  const location = useLocation()

  const [loadingTimeout, setLoadingTimeout] = React.useState(false)

  // Timeout para evitar loading infinito (10 segundos)

  React.useEffect(() => {
    if (isLoading) {
      const timeout = setTimeout(() => {
        setLoadingTimeout(true)
      }, 10000) // 10 segundos

      return () => clearTimeout(timeout)
    } else {
      setLoadingTimeout(false)
    }
  }, [isLoading])

  // Mostrar loading mientras se verifica la autenticación

  if (isLoading && !loadingTimeout) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner size="lg" text="Verificando autenticación..." />
      </div>
    )
  }

  // Si hay timeout, mostrar mensaje de error y redirigir

  if (loadingTimeout && !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="w-full max-w-md rounded-lg bg-white p-8 text-center shadow-lg">
          <div className="mb-6">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-yellow-100">
              <svg
                className="h-8 w-8 text-yellow-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>

            <h1 className="mb-2 text-2xl font-bold text-gray-900">
              Tiempo de espera agotado
            </h1>

            <p className="mb-4 text-gray-600">
              No se pudo verificar la autenticación. Por favor, intente iniciar
              sesión nuevamente.
            </p>
          </div>

          <button
            onClick={() => (window.location.href = BASE_PATH + fallbackPath)}
            className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
          >
            {fallbackPath === '/login' ? 'Ir al Login' : 'Continuar'}
          </button>
        </div>
      </div>
    )
  }

  // Si no está autenticado, redirigir al login

  if (!isAuthenticated || !user) {
    return <Navigate to={fallbackPath} state={{ from: location }} replace />
  }

  // Si se requiere admin y el usuario no es admin

  if (requireAdmin && (user.rol || 'viewer') !== 'admin') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="w-full max-w-md rounded-lg bg-white p-8 text-center shadow-lg">
          <div className="mb-6">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
              <svg
                className="h-8 w-8 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>

            <h1 className="mb-2 text-2xl font-bold text-gray-900">
              Acceso Denegado
            </h1>

            <p className="mb-4 text-gray-600">
              No tiene permisos para acceder a esta página.
            </p>

            <div className="mb-6 rounded-lg bg-gray-50 p-4">
              <p className="mb-1 text-sm text-gray-700">
                <strong>Se requiere:</strong> Acceso de administrador
              </p>

              <p className="text-sm text-gray-700">
                <strong>Su rol actual:</strong>{' '}
                {(user.rol || 'viewer') === 'admin'
                  ? 'Administrador'
                  : 'Operativo'}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <button
              onClick={() => window.history.back()}
              className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
            >
              ← Volver a la página anterior
            </button>

            <button
              onClick={() => (window.location.href = BASE_PATH + homeForRole)}
              className="w-full rounded-lg bg-gray-600 px-6 py-3 font-medium text-white transition-colors hover:bg-gray-700"
            >
              {homeForRole === '/clientes' ? 'Ir a Clientes' : 'Ir al Dashboard'}
            </button>
          </div>

          <div className="mt-6 border-t border-gray-200 pt-6">
            <p className="text-xs text-gray-500">
              Si cree que esto es un error, contacte al administrador del
              sistema.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
