import { useSimpleAuth } from '../store/simpleAuthStore'

import { User } from '../types'

import { isDelegatedPathForRol } from '../config/roleRoutes'
import {
  canonicalRol,
  isAdminRole,
  isManagerRole,
  isOperatorRole,
} from '../utils/rol'

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
   * Panel interno de finiquitos: disponible desde Sidebar para admin, operario o gerente.
   */

  const isFiniquitador = (): boolean => {
    return (
      isAdminRole(user?.rol) ||
      isOperatorRole(user?.rol) ||
      isManagerRole(user?.rol)
    )
  }

  /**
   * Trasladar casos entre bandeja principal, area de revision y revision contable
   * (Validar / pasar a revision contable). Admin, operario y gerente del panel.
   * Area de revision o revision contable -> area de trabajo: mismos roles.
   */
  const canTrasladarFiniquitoBandejas = (): boolean => {
    return isFiniquitador()
  }

  /**
   * Misma lista blanca que el guard de rutas (config/roleRoutes.ts).
   */

  const canAccessPath = (pathname: string): boolean => {
    return isDelegatedPathForRol(user?.rol, pathname)
  }

  /**





   * Verifica si el usuario puede editar un préstamo





   * - USER: Solo puede editar si el préstamo está en DRAFT





   * - ADMIN: Puede editar siempre





   */

  const canEditPrestamo = (prestamoEstado: string): boolean => {
    if (!prestamoEstado) return false

    // Admin y operador: editar cualquier estado (incl. DESISTIMIENTO / LIQUIDADO).
    if (isAdmin() || isOperatorRole(user?.rol)) {
      return true
    }

    return prestamoEstado === 'DRAFT'
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
    return isAdmin() || isOperatorRole(user?.rol)
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

  const getAllowedStates = (_currentState: string): string[] => {
    if (isAdmin() || isOperatorRole(user?.rol)) {
      return [
        'DRAFT',
        'EN_REVISION',
        'APROBADO',
        'RECHAZADO',
        'LIQUIDADO',
        'DESISTIMIENTO',
      ]
    }

    if (_currentState === 'DRAFT') {
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





   * - OPERATIVO: puede ver y descargar reportes no financieros (Pagos, Pagos Gmail, Por cédula)





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





   * - OPERATIVO: reportes operativos (Pagos, Pagos Gmail, Cédula,
   *   Fecha Drive, Análisis financiamiento, Clientes hoja por LOTE, Préstamos Drive). Contable / Conciliación masiva siguen solo admin.

   */

  const canAccessReport = (reportType: string): boolean => {
    if (isAdmin()) {
      return true // Admin tiene acceso a todos
    }

    const allowedForOperativos = [
      'PAGOS',
      'PAGOS_GMAIL',
      'CEDULA',
      'CEDULAS_CUOTA_HOJA',
      'SALDOS_MENORES_200',
    ]

    return allowedForOperativos.includes(reportType)
  }

  /**
   * Revisión manual: con la revisión cerrada (Visto / `revisado`), perfiles operativos con mutación
   * (admin, gerente/supervisor, operador) pueden editar pagos, eliminar y reabrir; el visualizador no.
   * El `rol` en sesión debe ser canónico (ver `normalizeAuthUser` / `canonicalRol`).
   */
  const revisionManualFullEdit =
    isAdminRole(user?.rol) ||
    isOperatorRole(user?.rol) ||
    isManagerRole(user?.rol)

  return {
    user,

    isAdmin: isAdmin(),

    revisionManualFullEdit,

    isFiniquitador: isFiniquitador(),

    canTrasladarFiniquitoBandejas: canTrasladarFiniquitoBandejas(),

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
