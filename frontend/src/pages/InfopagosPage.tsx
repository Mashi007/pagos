/**
 * Pagina publica Infopagos: registro de pago a nombre del deudor (colaborador).
 * Mismo flujo y reglas de moneda (Bs./USD) que /rapicredit-cobros (ReportePagoPage).
 * El recibo se envia al correo del deudor; el colaborador puede descargarlo en pantalla.
 */
import ReportePagoPage from './ReportePagoPage'

export default function InfopagosPage() {
  return <ReportePagoPage variant="infopagos" />
}
