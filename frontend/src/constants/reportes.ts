/** Valores por defecto y textos del Centro de Reportes (exportaciones Excel/PDF). */

/** Ventana en meses para el informe de pagos cuando el backend espera un solo entero `meses`. */
export const DEFAULT_MESES_VENTANA_PAGOS = 12

export const REPORTE_ANIO_MIN = 1990

export const REPORTE_ANIO_MAX = 2100

export const REPORTES_TOAST = {
  cartera: 'Reporte de Cartera descargado exitosamente',
  aseguradora: 'Reporte Aseguradora descargado exitosamente',
  aseguradoraImpagas: 'Listado impagas (cedula) descargado exitosamente',
  cuotasHojaPeriodo: 'Hoja Drive actualizada (cuotas por periodo)',
  pagos: 'Informe de Pagos descargado exitosamente',
  cedula: 'Reporte por Cédula descargado exitosamente',
  cedulasCuotaHoja: 'Excel cédulas con cuota (hoja Drive) descargado',
  saldosMenores200:
    'Excel Saldos menores 200 (deudores con saldo final ≤ $200) descargado',
  contableOk: 'Reporte Contable descargado exitosamente',

  pagosGmail:
    'Reporte Pagos Gmail (auditoría ABCD → pagos → cuotas) descargado',
} as const
