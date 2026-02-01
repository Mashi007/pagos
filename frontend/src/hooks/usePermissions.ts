import { useSimpleAuth } from '../store/simpleAuthStore'
import { User } from '../types'

/**
 * Hook para verificar permisos del usuario actual
 * Basado en el rol (is_admin) y estado del prÃ©stamo
 */
export function usePermissions() {
  const { user } = useSimpleAuth()

  /**
   * Verifica si el usuario es administrador
   */
  const isAdmin = (): boolean => {
    return user?.is_admin === true
  }

  /**
   * Verifica si el usuario puede editar un prÃ©stamo
   * - USER: Solo puede editar si el prÃ©stamo estÃ¡ en DRAFT
   * - ADMIN: Puede editar siempre
   */
  const canEditPrestamo = (prestamoEstado: string): boolean => {
    if (!prestamoEstado) return false

    if (isAdmin()) {
      return true // Admin puede editar siempre
    }

    return prestamoEstado === 'DRAFT' // User solo puede editar DRAFT
  }

  /**
   * Verifica si el usuario puede aprobar/rechazar prÃ©stamos
   * - Solo ADMIN puede aprobar/rechazar
   */
  const canApprovePrestamo = (): boolean => {
    return isAdmin()
  }

  /**
   * Verifica si el usuario puede eliminar prÃ©stamos
   * - Solo ADMIN puede eliminar
   */
  const canDeletePrestamo = (): boolean => {
    return isAdmin()
  }

  /**
   * Verifica si el usuario puede ver evaluaciÃ³n de riesgo
   * - Solo ADMIN puede ver
   */
  const canViewEvaluacionRiesgo = (): boolean => {
    return isAdmin()
  }

  /**
   * Verifica si el usuario puede generar amortizaciones
   * - USER y ADMIN pueden generar
   */
  const canGenerateAmortizacion = (prestamoEstado: string): boolean => {
    return prestamoEstado === 'APROBADO'
  }

  /**
   * Obtiene los estados permitidos para cambiar segÃºn el rol
   */
  const getAllowedStates = (currentState: string): string[] => {
    if (isAdmin()) {
      // Admin puede cambiar a cualquier estado
      return ['DRAFT', 'EN_REVISION', 'APROBADO', 'RECHAZADO']
    }

    // User solo puede cambiar de DRAFT a EN_REVISION
    if (currentState === 'DRAFT') {
      return ['EN_REVISION']
    }

    return []
  }

  /**
   * Verifica si el usuario puede cambiar el estado del prÃ©stamo
   */
  const canChangeState = (currentState: string, newState: string): boolean => {
    const allowedStates = getAllowedStates(currentState)
    return allowedStates.includes(newState)
  }

  return {
    user,
    isAdmin: isAdmin(),
    canEditPrestamo,
    canApprovePrestamo,
    canDeletePrestamo,
    canViewEvaluacionRiesgo,
    canGenerateAmortizacion,
    canChangeState,
    getAllowedStates,
  }
}

