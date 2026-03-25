import { Navigate } from 'react-router-dom'

import { FiniquitoGestionPage } from './FiniquitoGestionPage'

import { FiniquitoPanelPage } from './FiniquitoPanelPage'

import { getFiniquitoAccessToken } from '../services/finiquitoService'

import { useSimpleAuth } from '../store/simpleAuthStore'

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
 * - Administrador del panel → bandeja admin (FiniquitoGestionPage).
 * - Colaborador con JWT OTP (sessionStorage) → mismo enlace, contenido de portal (FiniquitoPanelPage).
 * - Sin admin ni token OTP → /finiquitos/acceso (no al login del sistema).
 */
export function FiniquitoGestionGatePage() {
  const { isAuthenticated, user, isLoading } = useSimpleAuth()

  const finiToken = getFiniquitoAccessToken()?.trim()

  const rol = user?.rol || 'operativo'

  const esAdmin = isAuthenticated && rol === 'administrador'

  if (finiToken) {
    if (isLoading && isAuthenticated) {
      return <GateSpinner />
    }

    if (!isAuthenticated || rol !== 'administrador') {
      return <FiniquitoPanelPage />
    }
  }

  if (isLoading) {
    return <GateSpinner />
  }

  if (esAdmin) {
    return <FiniquitoGestionPage />
  }

  return <Navigate to="/finiquitos/acceso" replace />
}
