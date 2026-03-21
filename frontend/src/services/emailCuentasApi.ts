/**
 * API para configuraciÃÂ³n de 4 cuentas de correo.
 * Cuenta 1 = Cobros, 2 = Estado de cuenta, 3 y 4 = Notificaciones (por pestaÃÂ±a).
 */
import { apiClient } from './api'

export interface CuentaEmailItem {
  smtp_host?: string
  smtp_port?: string
  smtp_user?: string
  smtp_password?: string
  from_email?: string
  from_name?: string
  smtp_use_tls?: string
  imap_host?: string
  imap_port?: string
  imap_user?: string
  imap_password?: string
  imap_use_ssl?: string
}

export interface EmailCuentasResponse {
  version: number
  cuentas: CuentaEmailItem[]
  asignacion: {
    cobros: number
    estado_cuenta: number
    notificaciones_tab?: Record<string, number>
  }
  modo_pruebas?: string
  email_pruebas?: string
  email_activo?: string
  email_activo_notificaciones?: string
  email_activo_estado_cuenta?: string
  email_activo_cobros?: string
  tickets_notify_emails?: string
}

const BASE = '/api/v1/configuracion'

export const emailCuentasApi = {
  async get(): Promise<EmailCuentasResponse> {
    return apiClient.get<EmailCuentasResponse>(`${BASE}/email/cuentas`)
  },
  async put(payload: {
    cuentas: CuentaEmailItem[]
    asignacion: EmailCuentasResponse['asignacion']
    modo_pruebas?: string
    email_pruebas?: string
    email_activo?: string
    email_activo_notificaciones?: string
    email_activo_estado_cuenta?: string
    email_activo_cobros?: string
    tickets_notify_emails?: string
  }): Promise<{ message: string; version: number }> {
    return apiClient.put(`${BASE}/email/cuentas`, payload, { timeout: 60000 })
  },
  /** Envia un correo de prueba a todos los correos de pruebas registrados. */
  async enviarPrueba(): Promise<{ success: boolean; enviados: { cuenta: number; email: string }[]; errores: { cuenta: number; email: string; mensaje: string }[]; mensaje: string }> {
    return apiClient.post(`${BASE}/email/enviar-prueba`, {}, { timeout: 30000 })
  },
}

/** Etiquetas de servicio por cuenta (para UI). */
export const SERVICIO_POR_CUENTA: Record<number, string> = {
  1: 'Cobros (formulario pÃÂºblico de reporte de pago)',
  2: 'Estado de cuenta (consulta por cÃÂ©dula + envÃÂ­o PDF)',
  3: 'Notificaciones (pestaÃÂ±as asignadas a esta cuenta)',
  4: 'Notificaciones (pestaÃÂ±as asignadas a esta cuenta)',
}

/** PestaÃÂ±as de notificaciones que pueden usar cuenta 3 o 4. */
export const NOTIF_TABS = [
  { id: 'dias_5', label: 'Faltan 5 dÃÂ­as' },
  { id: 'dias_3', label: 'Faltan 3 dÃÂ­as' },
  { id: 'dias_1', label: 'Faltan 1 dÃÂ­a' },
  { id: 'hoy', label: 'Vence hoy' },
  { id: 'dias_1_retraso', label: '1 dÃÂ­a retraso' },
  { id: 'dias_3_retraso', label: '3 dÃÂ­as retraso' },
  { id: 'dias_5_retraso', label: '5 dÃÂ­as retraso' },
  { id: 'prejudicial', label: 'Prejudicial' },
  { id: 'mora_90', label: 'Mora 90+' },
] as const
