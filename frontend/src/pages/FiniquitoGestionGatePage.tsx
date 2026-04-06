import { Navigate } from 'react-router-dom'

import { FiniquitoGestionPage } from './FiniquitoGestionPage'

import { FiniquitoPanelPage } from './FiniquitoPanelPage'

import { getFiniquitoAccessToken } from '../services/finiquitoService'

import { useSimpleAuth } from '../store/simpleAuthStore'
import { isAdminRole, isOperatorRole } from '../utils/rol'

function GateSpinner() {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-slate-100/80">
      <div
        className="h-10 w-10 animate-spin rounded-full border-2 border-slate-400 border-t-transparent"
        aria-label="Cargando"
        role="status"
      />
    </div>
  )
}

/**
 * Una sola URL canónica /finiquitos/gestion:
 * - Usuario con rol admin u operario (panel) → bandeja gestión (FiniquitoGestionPage).
 * - Colaborador con JWT OTP (sessionStorage) → mismo enlace, contenido de portal (FiniquitoPanelPage).
 * - Sin admin ni token OTP → /finiquitos/acceso (no al login del sistema).
 */
export function FiniquitoGestionGatePage() {
  const { isAuthenticated, user, isLoading } = useSimpleAuth()

  const finiToken = getFiniquitoAccessToken()?.trim()

  const esPanelGestionFiniquito =
    isAuthenticated &&
    (isAdminRole(user?.rol) || isOperatorRole(user?.rol))

  if (finiToken) {
    if (isLoading && isAuthenticated) {
      return <GateSpinner />
    }

    if (!esPanelGestionFiniquito) {
      return <FiniquitoPanelPage />
    }
  }

  if (isLoading) {
    return <GateSpinner />
  }

  if (esPanelGestionFiniquito) {
    return <FiniquitoGestionPage />
  }

  return <Navigate to="/finiquitos/acceso" replace />
}
