import React, { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/store/authStore'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRoles?: string[]
  fallbackPath?: string
}

export function ProtectedRoute({ 
  children, 
  requiredRoles = [], 
  fallbackPath = '/login' 
}: ProtectedRouteProps) {
  const { isAuthenticated, user, isLoading, refreshUser } = useAuth()
  const location = useLocation()

  useEffect(() => {
    // Si hay token pero no hay usuario, intentar refrescar
    if (!user && localStorage.getItem('access_token')) {
      refreshUser()
    }
  }, [user, refreshUser])

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
  if (requiredRoles.length > 0 && !requiredRoles.includes(user.rol)) {
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
            Su rol actual: {user.rol}
          </p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

// HOC para proteger componentes con roles específicos
export function withRoleProtection(
  Component: React.ComponentType<any>,
  requiredRoles: string[]
) {
  return function ProtectedComponent(props: any) {
    return (
      <ProtectedRoute requiredRoles={requiredRoles}>
        <Component {...props} />
      </ProtectedRoute>
    )
  }
}

// Hook para verificar permisos en componentes
export function useRoleCheck() {
  const { user } = useAuth()

  const hasRole = (role: string): boolean => {
    return user?.rol === role
  }

  const hasAnyRole = (roles: string[]): boolean => {
    return user ? roles.includes(user.rol) : false
  }

  const isAdmin = (): boolean => {
    return hasAnyRole(['ADMIN', 'GERENTE', 'DIRECTOR'])
  }

  const canManagePayments = (): boolean => {
    return hasAnyRole(['ADMIN', 'GERENTE', 'COBRADOR', 'ASESOR_COMERCIAL'])
  }

  const canViewReports = (): boolean => {
    return hasAnyRole(['ADMIN', 'GERENTE', 'DIRECTOR', 'CONTADOR', 'AUDITOR'])
  }

  const canManageConfig = (): boolean => {
    return hasAnyRole(['ADMIN', 'GERENTE'])
  }

  const canViewAllClients = (): boolean => {
    return hasAnyRole(['ADMIN', 'GERENTE', 'DIRECTOR', 'CONTADOR', 'AUDITOR'])
  }

  return {
    user,
    hasRole,
    hasAnyRole,
    isAdmin,
    canManagePayments,
    canViewReports,
    canManageConfig,
    canViewAllClients,
  }
}
