/**
 * Infopagos: registro de pago a nombre del deudor (colaborador).
 * Se despliega dentro del layout principal (con sidebar), con embedded=true
 * para que ReportePagoPage no use el fondo oscuro full-screen.
 */
import ReportePagoPage from './ReportePagoPage'

export default function InfopagosPage() {
  return <ReportePagoPage variant="infopagos" embedded={true} />
}
