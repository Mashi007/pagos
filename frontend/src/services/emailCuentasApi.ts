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

    /** Índice 1-4: cuenta SMTP para envíos automáticos Recibos (post-conciliación). */
    recibos?: number

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

  email_activo_recibos?: string

  modo_pruebas_notificaciones?: string

  modo_pruebas_informe_pagos?: string

  modo_pruebas_estado_cuenta?: string

  modo_pruebas_finiquito?: string

  modo_pruebas_cobros?: string

  modo_pruebas_campanas?: string

  modo_pruebas_tickets?: string

  modo_pruebas_recibos?: string

  tickets_notify_emails?: string

  /** Lista opcional de correos de prueba (config avanzada). */

  emails_pruebas?: string[]

  /** Hasta 2 correos en copia oculta (CCO/BCC) para envíos automáticos Recibos. */

  recibos_bcc_emails?: string[]
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

    email_activo_recibos?: string

    modo_pruebas_notificaciones?: string

    modo_pruebas_informe_pagos?: string

    modo_pruebas_estado_cuenta?: string

    modo_pruebas_finiquito?: string

    modo_pruebas_cobros?: string

    modo_pruebas_campanas?: string

    modo_pruebas_tickets?: string

    modo_pruebas_recibos?: string

    tickets_notify_emails?: string

    emails_pruebas?: string[]

    recibos_bcc_emails?: string[]
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
  1: 'pagos@rapicreditca.com',

  2: 'tucuenta@rapicreditca.com',

  3: 'notificaciones@rapicreditca.com',

  4: 'recuerda@rapicreditca.com',
}

/** Etiquetas cortas de cuenta en selects de asignación. */
export const CUENTA_OPCIONES_ASIGNACION = [
  { value: 1, label: 'Cuenta 1 (pagos@)' },
  { value: 2, label: 'Cuenta 2 (tucuenta@)' },
  { value: 3, label: 'Cuenta 3 (notificaciones@)' },
  { value: 4, label: 'Cuenta 4 (recuerda@)' },
] as const

/** Servicios con una sola cuenta SMTP (no por tipo_tab). */
export const ASIGNACION_SERVICIOS = [
  {
    key: 'cobros' as const,
    label: 'Cobros (formulario público)',
    defaultCuenta: 1,
  },
  {
    key: 'estado_cuenta' as const,
    label: 'Estado de cuenta (código y PDF)',
    defaultCuenta: 2,
  },
  {
    key: 'recibos' as const,
    label: 'Recibos (PDF tras conciliación, job 15:00 Caracas)',
    defaultCuenta: 1,
  },
] as const

export type AsignacionServicioKey = (typeof ASIGNACION_SERVICIOS)[number]['key']

/** Grupos alineados con el menú Notificaciones y submódulos General/Fechas. */
export const ASIGNACION_NOTIF_GRUPOS = [
  {
    titulo: 'Menú Notificaciones (sidebar)',
    descripcion:
      'Misma lista que en el menú lateral: cada fila define qué buzón SMTP usa ese módulo.',
    items: [
      {
        id: 'dias_1_retraso',
        label: 'Día siguiente al vencimiento',
        defaultCuenta: 2,
      },
      {
        id: 'prejudicial',
        label: '60 días o más',
        defaultCuenta: 3,
      },
      {
        id: 'd_2_antes_vencimiento',
        label: '3 días antes (cuota pendiente)',
        defaultCuenta: 4,
      },
      {
        id: 'dias_10_retraso',
        label: 'Menor a 60 días',
        defaultCuenta: 3,
      },
    ],
  },
  {
    titulo: 'Recordatorios antes de vencimiento (General / Fechas)',
    descripcion:
      'Casos PAGO_5/3/1 días antes y día 0; suelen enviarse desde los submódulos General o Fechas.',
    items: [
      { id: 'dias_5', label: '5 días antes', defaultCuenta: 4 },
      { id: 'dias_3', label: '3 días antes', defaultCuenta: 4 },
      { id: 'dias_1', label: '1 día antes', defaultCuenta: 4 },
      { id: 'hoy', label: 'Día de vencimiento (hoy)', defaultCuenta: 4 },
    ],
  },
  {
    titulo: 'Otros casos de mora',
    descripcion: 'Tabs adicionales usados en estadísticas y envíos legacy.',
    items: [
      { id: 'dias_3_retraso', label: '3 días de atraso', defaultCuenta: 3 },
      { id: 'dias_5_retraso', label: '5 días de atraso', defaultCuenta: 3 },
      { id: 'mora_90', label: 'Mora 90+ días', defaultCuenta: 3 },
    ],
  },
] as const

/** Defaults planos tipo_tab → cuenta (1-4). */
export const ASIGNACION_NOTIF_DEFAULTS: Record<string, number> =
  Object.fromEntries(
    ASIGNACION_NOTIF_GRUPOS.flatMap(g =>
      g.items.map(it => [it.id, it.defaultCuenta])
    )
  )

/** @deprecated Usar ASIGNACION_NOTIF_GRUPOS */
export const NOTIF_TABS = ASIGNACION_NOTIF_GRUPOS[0].items
