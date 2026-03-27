/** Valores por defecto y textos del Centro de Reportes (exportaciones Excel/PDF). */

/** Ventana en meses para el informe de pagos cuando el backend espera un solo entero `meses`. */
export const DEFAULT_MESES_VENTANA_PAGOS = 12

export const REPORTE_ANIO_MIN = 1990

export const REPORTE_ANIO_MAX = 2100

export const REPORTES_TOAST = {
  cartera: 'Reporte de Cartera descargado exitosamente',
  pagos: 'Informe de Pagos descargado exitosamente',
  morosidad:
    'Reporte de Morosidad descargado (solo cuotas en estado Mora 4+ meses, codigo MORA)',
  vencimiento: 'Reporte de Vencimiento descargado exitosamente',
  pagoVencido: 'Reporte de Pago Vencido descargado exitosamente',
  cedula: 'Reporte por Cédula descargado exitosamente',
  contableOk: 'Reporte Contable descargado exitosamente',
} as const
