import { useSimpleAuth } from '../store/simpleAuthStore'

import { User } from '../types'

import { canonicalRol, isAdminRole } from '../utils/rol'

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
    return isAdminRole(user?.rol)
  }

  /**
   * Panel interno /finiquitos/gestion (bandeja admin): solo rol admin (alias legados incl.).
   * Colaboradores externos usan OTP (FiniquitoPanelPage), no este flag.
   */

  const isFiniquitador = (): boolean => {
    return isAdminRole(user?.rol)
  }

  /**
   * Verifica si el usuario SOLO tiene acceso a finiquito (sin acceso general)
   */

  const isPuroFiniquitador = (): boolean => {
    return false // Rol finiquitador eliminado; solo admin/manager acceden a gestion
  }

  /**
   * Verifica si una ruta está permitida para el usuario actual
   * - Finiquitador: SOLO /finiquitos/gestion
   * - Administrador: todas
   * - Operativo: reportes, préstamos, etc (excluyendo finiquito gestion)
   */

  const canAccessPath = (pathname: string): boolean => {
    const rol = canonicalRol(user?.rol)

    // admin: acceso total
    if (rol === 'admin') {
      return true
    }

    if (rol === 'manager') {
      return true
    }

    if (rol === 'operator') {
      const OPERATOR_ALLOWED = [
        '/clientes',
        '/prestamos',
        '/infopagos',
        '/finiquitos/gestion',
      ]
      return OPERATOR_ALLOWED.some(
        p => pathname === p || pathname.startsWith(p + '/')
      )
    }

    // viewer: sin panel admin de finiquito; el resto lo limitan rutas con requireAdmin en App
    return pathname !== '/finiquitos/gestion'
  }

  /**





   * Verifica si el usuario puede editar un préstamo





   * - USER: Solo puede editar si el préstamo está en DRAFT





   * - ADMIN: Puede editar siempre





   */

  const canEditPrestamo = (prestamoEstado: string): boolean => {
    if (!prestamoEstado) return false

    if (prestamoEstado === 'DESISTIMIENTO') {
      return false
    }

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

  /**





   * Verifica si el usuario puede ver reportes





   * - ADMIN: acceso total





   * - OPERATIVO: puede ver y descargar reportes no financieros (Pagos, Morosidad, Vencimiento, Por cédula)





   */

  const canViewReports = (): boolean => {
    return true // Todos los usuarios autenticados pueden ver la página de reportes
  }

  /**





   * Verifica si el usuario puede descargar reportes (en general).





   * La descarga específica por tipo se valida con canAccessReport.





   */

  const canDownloadReports = (): boolean => {
    return true // Todos pueden descargar los reportes a los que tienen acceso
  }

  /**





   * Verifica si el usuario puede acceder a reportes específicos por tipo





   * - ADMIN: Acceso a todos





   * - OPERATIVO: Solo acceso a reportes no financieros (Pagos, Morosidad)





   */

  const canAccessReport = (reportType: string): boolean => {
    if (isAdmin()) {
      return true // Admin tiene acceso a todos
    }

    // Operativos pueden ver: Pagos, Morosidad, Vencimiento, Por cédula. Contable solo admin.

    const allowedForOperativos = [
      'PAGOS',
      'MOROSIDAD',
      'VENCIMIENTO',
      'CEDULA',
      'FECHAS',
    ]

    return allowedForOperativos.includes(reportType)
  }

  return {
    user,

    isAdmin: isAdmin(),

    isFiniquitador: isFiniquitador(),

    isPuroFiniquitador: isPuroFiniquitador(),

    canAccessPath,

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
