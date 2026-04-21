/**
 * Infopagos: registro de pago a nombre del deudor (colaborador).
 * Se despliega dentro del layout principal (con sidebar), con embedded=true
 * para que ReportePagoPage no use el fondo oscuro full-screen.
 */
import { useEffect } from 'react'

import ReportePagoPage from './ReportePagoPage'

const INFO_TITLE = 'Infopagos · RapiCredit'

export default function InfopagosPage() {
  useEffect(() => {
    const prev = document.title
    document.title = INFO_TITLE
    return () => {
      document.title = prev
    }
  }, [])

  return <ReportePagoPage variant="infopagos" embedded={true} />
}
