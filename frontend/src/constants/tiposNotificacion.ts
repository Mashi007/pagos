/** Tipos de notificación (casos) para configurar envíos, PDF anexo y adjuntos fijos */

export const TIPOS_NOTIFICACION: { tipo: string; label: string }[] = [
  {
    tipo: 'PAGO_2_DIAS_ANTES_PENDIENTE',
    label: '2 días antes (pendiente, vence en 2 días)',
  },

  {
    tipo: 'PAGO_1_DIA_ATRASADO',
    label: 'Día siguiente al vencimiento (1 día después)',
  },

  { tipo: 'PAGO_10_DIAS_ATRASADO', label: 'Menor a 60 días (6-59, 1 cuota)' },

  { tipo: 'PREJUDICIAL', label: 'Prejudicial' },

  { tipo: 'COBRANZA', label: 'Carta de cobranza' },
]
