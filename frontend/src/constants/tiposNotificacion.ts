/** Tipos de notificación (casos) para configurar envíos, PDF anexo y adjuntos fijos */
export const TIPOS_NOTIFICACION: { tipo: string; label: string }[] = [
  { tipo: 'PAGO_5_DIAS_ANTES', label: 'Faltan 5 días' },
  { tipo: 'PAGO_3_DIAS_ANTES', label: 'Faltan 3 días' },
  { tipo: 'PAGO_1_DIA_ANTES', label: 'Falta 1 día' },
  { tipo: 'PAGO_DIA_0', label: 'Hoy vence' },
  { tipo: 'PAGO_1_DIA_ATRASADO', label: '1 día de retraso' },
  { tipo: 'PAGO_3_DIAS_ATRASADO', label: '3 días de retraso' },
  { tipo: 'PAGO_5_DIAS_ATRASADO', label: '5 días de retraso' },
  { tipo: 'PREJUDICIAL', label: 'Prejudicial' },
  { tipo: 'MORA_90', label: '90+ días de mora (moroso)' },
  { tipo: 'COBRANZA', label: 'Carta de cobranza' },
]
