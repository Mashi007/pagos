/**
 * Página pública Infopagos: registro de pago a nombre del deudor (uso interno / personal).
 * Mismo flujo que rapicredit-cobros pero sin token para el deudor; al final el recibo
 * se envía al email registrado (por cédula) y el colaborador puede descargar el recibo aquí.
 */
import ReportePagoPage from './ReportePagoPage'

export default function InfopagosPage() {
  return <ReportePagoPage variant="infopagos" />
}
