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
  reporteCuotasJunAgo:
    'REPORTE cuotas jun-ago: Drive actualizado (columnas D/E)',
  pagos: 'Informe de Pagos descargado exitosamente',
  cedula: 'Reporte por Cédula descargado exitosamente',
  cedulasCuotaHoja: 'Excel cédulas con cuota (hoja Drive) descargado',
  contableOk: 'Reporte Contable descargado exitosamente',

  fechaDrive: 'Reporte Fecha Drive (hoja vs sistema, 5 columnas) descargado',

  analisisFinanciamiento:
    'Reporte Análisis financiamiento (hoja vs sistema, 5 columnas) descargado',

  clientesHoja:
    'Reporte Clientes (hoja CONCILIACIÓN filtrada por LOTE) descargado',

  prestamosDrive:
    'Reporte Préstamos Drive (11 columnas, filtro por LOTE) descargado',

  pagosGmail:
    'Reporte Pagos Gmail (auditoría ABCD → pagos → cuotas) descargado',
} as const
