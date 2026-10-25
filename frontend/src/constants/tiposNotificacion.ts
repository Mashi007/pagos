/** Tipos de notificación (casos) para configurar envíos, PDF anexo y adjuntos fijos */

export const TIPOS_NOTIFICACION: { tipo: string; label: string }[] = [
  { tipo: 'PAGO_1_DIA_ATRASADO', label: 'Día siguiente' },

  { tipo: 'PAGO_10_DIAS_ATRASADO', label: '1 Cuota' },

  { tipo: 'PREJUDICIAL', label: '2 Cuotas (>=2)' },

  { tipo: 'ESTADO_CUENTA', label: 'Estado de cuenta' },

  { tipo: 'COBRANZA', label: 'Carta de cobranza' },
]
