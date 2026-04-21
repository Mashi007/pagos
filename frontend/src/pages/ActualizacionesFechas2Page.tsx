import { Navigate } from 'react-router-dom'

/**
 * Compatibilidad: la herramienta vive en Notificaciones → Fechas (unificado).
 */
export default function ActualizacionesFechas2Page() {
  return <Navigate to="/notificaciones/fecha" replace />
}
