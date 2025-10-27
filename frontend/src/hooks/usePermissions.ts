import { useSimpleAuth } from '@/store/simpleAuthStore'
import { User } from '@/types'

/**
 * Hook para verificar permisos del usuario actual
 * Basado en el rol (is_admin) y estado del préstamo
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
   * Verifica si el usuario puede editar un préstamo
   * - USER: Solo puede editar si el préstamo está en DRAFT
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
   * Verifica si el usuario puede aprobar/rechazar préstamos
   * - Solo ADMIN puede aprobar/rechazar
   */
  const canApprovePrestamo = (): boolean => {
    return isAdmin()
  }

  /**
   * Verifica si el usuario puede eliminar préstamos
   * - Solo ADMIN puede eliminar
   */
  const canDeletePrestamo = (): boolean => {
    return isAdmin()
  }

  /**
   * Verifica si el usuario puede ver evaluación de riesgo
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
   * Obtiene los estados permitidos para cambiar según el rol
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
   * Verifica si el usuario puede cambiar el estado del préstamo
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

