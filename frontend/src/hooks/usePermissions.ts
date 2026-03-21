import { useSimpleAuth } from '../store/simpleAuthStore'
import { User } from '../types'

/**
 * Hook para verificar permisos del usuario actual
 * Basado en el rol (is_admin) y estado del prÃÂ©stamo
 */
export function usePermissions() {
  const { user } = useSimpleAuth()

  /**
   * Verifica si el usuario es administrador
   */
  const isAdmin = (): boolean => {
    return (user?.rol || 'operativo') === 'administrador'
  }

  /**
   * Verifica si el usuario puede editar un prÃÂ©stamo
   * - USER: Solo puede editar si el prÃÂ©stamo estÃÂ¡ en DRAFT
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
   * Verifica si el usuario puede aprobar/rechazar prÃÂ©stamos
   * - Solo ADMIN puede aprobar/rechazar
   */
  const canApprovePrestamo = (): boolean => {
    return isAdmin()
  }

  /**
   * Verifica si el usuario puede eliminar prÃÂ©stamos
   * - Solo ADMIN puede eliminar
   */
  const canDeletePrestamo = (): boolean => {
    return isAdmin()
  }

  /**
   * Verifica si el usuario puede ver evaluaciÃÂ³n de riesgo
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
   * Obtiene los estados permitidos para cambiar segÃÂºn el rol
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
   * Verifica si el usuario puede cambiar el estado del prÃÂ©stamo
   */
  const canChangeState = (currentState: string, newState: string): boolean => {
    const allowedStates = getAllowedStates(currentState)
    return allowedStates.includes(newState)
  }

  /**
   * Verifica si el usuario puede ver reportes
   * - ADMIN: acceso total
   * - OPERATIVO: puede ver y descargar reportes no financieros (Pagos, Morosidad, Vencimiento, Por cÃÂ©dula)
   */
  const canViewReports = (): boolean => {
    return true // Todos los usuarios autenticados pueden ver la pÃÂ¡gina de reportes
  }

  /**
   * Verifica si el usuario puede descargar reportes (en general).
   * La descarga especÃÂ­fica por tipo se valida con canAccessReport.
   */
  const canDownloadReports = (): boolean => {
    return true // Todos pueden descargar los reportes a los que tienen acceso
  }

  /**
   * Verifica si el usuario puede acceder a reportes especÃÂ­ficos por tipo
   * - ADMIN: Acceso a todos
   * - OPERATIVO: Solo acceso a reportes no financieros (Pagos, Morosidad)
   */
  const canAccessReport = (reportType: string): boolean => {
    if (isAdmin()) {
      return true // Admin tiene acceso a todos
    }

    // Operativos pueden ver: Pagos, Morosidad, Vencimiento, Por cÃÂ©dula. Contable solo admin.
    const allowedForOperativos = ['PAGOS', 'MOROSIDAD', 'VENCIMIENTO', 'CEDULA']
    return allowedForOperativos.includes(reportType)
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
    canViewReports,
    canDownloadReports,
    canAccessReport,
  }
}

