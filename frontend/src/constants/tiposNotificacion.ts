/** Tipos de notificación (casos) para configurar envíos, PDF anexo y adjuntos fijos */

export const TIPOS_NOTIFICACION: { tipo: string; label: string }[] = [
  {
    tipo: 'PAGO_2_DIAS_ANTES_PENDIENTE',
    label: 'D:2 días (pendiente, vence en 2 días)',
  },

  {
    tipo: 'PAGO_1_DIA_ATRASADO',
    label: 'Día siguiente al vencimiento (1 día después)',
  },

  { tipo: 'PAGO_3_DIAS_ATRASADO', label: '3 días de retraso' },

  { tipo: 'PAGO_5_DIAS_ATRASADO', label: '5 días atrasado' },

  { tipo: 'PAGO_30_DIAS_ATRASADO', label: '30 días de retraso' },

  { tipo: 'PREJUDICIAL', label: 'Prejudicial' },

  { tipo: 'COBRANZA', label: 'Carta de cobranza' },
]
