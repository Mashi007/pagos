/**
 * PÃ¡gina pÃºblica Infopagos: registro de pago a nombre del deudor (uso interno / personal).
 * Mismo flujo que rapicredit-cobros pero sin token para el deudor; al final el recibo
 * se envÃ­a al email registrado (por cÃ©dula) y el colaborador puede descargar el recibo aquÃ­.
 */
import ReportePagoPage from './ReportePagoPage'

export default function InfopagosPage() {
  return <ReportePagoPage variant="infopagos" />
}
