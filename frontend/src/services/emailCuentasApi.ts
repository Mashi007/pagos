/**





 * API para configuración de 4 cuentas de correo.





 * Cuenta 1 = Cobros, 2 = Estado de cuenta, 3 y 4 = Notificaciones (por pestaña).





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

  email_activo_finiquito?: string

  email_activo_cobros?: string

  email_activo_informe_pagos?: string

  email_activo_campanas?: string

  email_activo_tickets?: string

  modo_pruebas_notificaciones?: string

  modo_pruebas_informe_pagos?: string

  modo_pruebas_estado_cuenta?: string

  modo_pruebas_finiquito?: string

  modo_pruebas_cobros?: string

  modo_pruebas_campanas?: string

  modo_pruebas_tickets?: string

  tickets_notify_emails?: string

  /** Lista opcional de correos de prueba (config avanzada). */

  emails_pruebas?: string[]
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

    email_activo_finiquito?: string

    email_activo_cobros?: string

    email_activo_informe_pagos?: string

    email_activo_campanas?: string

    email_activo_tickets?: string

    modo_pruebas_notificaciones?: string

    modo_pruebas_informe_pagos?: string

    modo_pruebas_estado_cuenta?: string

    modo_pruebas_finiquito?: string

    modo_pruebas_cobros?: string

    modo_pruebas_campanas?: string

    modo_pruebas_tickets?: string

    tickets_notify_emails?: string

    emails_pruebas?: string[]
  }): Promise<{ message: string; version: number }> {
    return apiClient.put(`${BASE}/email/cuentas`, payload, { timeout: 60000 })
  },

  /** Envia un correo de prueba a todos los correos de pruebas registrados. */

  async enviarPrueba(): Promise<{
    success: boolean
    enviados: { cuenta: number; email: string }[]
    errores: { cuenta: number; email: string; mensaje: string }[]
    mensaje: string
    nota_smtp?: string
  }> {
    return apiClient.post(`${BASE}/email/enviar-prueba`, {}, { timeout: 30000 })
  },
}

/** Etiquetas de servicio por cuenta (para UI). */

export const SERVICIO_POR_CUENTA: Record<number, string> = {
  1: 'Cobros (formulario público de reporte de pago)',

  2: 'Estado de cuenta y Finiquito (OTP + PDF; misma cuenta SMTP)',

  3: 'Notificaciones (pestañas asignadas a esta cuenta)',

  4: 'Notificaciones (casos de envío asignados a esta cuenta)',
}

/** Casos de envío de notificaciones que pueden usar cuenta 3 o 4. */

export const NOTIF_TABS = [
  { id: 'dias_1_retraso', label: 'Día siguiente al venc.' },

  { id: 'dias_3_retraso', label: '3 días retraso' },

  { id: 'dias_5_retraso', label: '5 días retraso' },

  { id: 'dias_30_retraso', label: '30 días retraso' },

  { id: 'prejudicial', label: 'Prejudicial' },
] as const
