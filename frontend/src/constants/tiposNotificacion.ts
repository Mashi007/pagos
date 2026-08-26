/** Tipos de notificación (casos) para configurar envíos, PDF anexo y adjuntos fijos */

export const TIPOS_NOTIFICACION: { tipo: string; label: string }[] = [
  { tipo: 'PAGO_10_DIAS_ATRASADO', label: '1 Cuota' },

  { tipo: 'PREJUDICIAL', label: '2 Cuotas (>=2)' },

  { tipo: 'ESTADO_CUENTA', label: 'Estado de cuenta' },

  { tipo: 'COBRANZAS_EXCEL', label: 'Cobranzas' },

  { tipo: 'CUOTAS_4_MAS', label: '4 cuotas y más' },

  { tipo: 'COBRANZA', label: 'Carta de cobranza' },
]
