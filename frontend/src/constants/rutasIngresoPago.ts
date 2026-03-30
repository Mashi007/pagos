/**
 * Criterio unificado para el reporte con moneda (Bs./USD), tasa oficial segun
 * fecha de pago y emision de recibo: implementado en ReportePagoPage y
 * endpoints publicos de cobros.
 *
 * Fuentes de ingreso (producto):
 * - /pagos/rapicredit-cobros: deudor, sin login.
 * - /pagos/infopagos: colaborador, sin login; mismo flujo que cobros con variant.
 * - /pagos/pagos: Excel, Gmail y revision; la importacion y conciliacion en
 *   backend usan la misma logica de moneda/tasa cuando el origen trae Bs.
 *
 * Reencaminamiento al proceso normal: los reportes publicos generan
 * PagoReportado, recibo y correo; tras validacion pasan a importacion/aplicacion
 * a cuotas como el resto de pagos conciliados.
 */

/** Segmentos bajo el basename de la app (p. ej. /pagos). */
export const SEGMENTO_REPORTE_COBROS = 'rapicredit-cobros'

export const SEGMENTO_REPORTE_LEGACY = 'reporte-pago'

export const SEGMENTO_INFOPAGOS = 'infopagos'

export const SEGMENTO_GESTION_PAGOS = 'pagos'

/**
 * Pathnames normalizados (sin basename) que deben quedar sin Layout y sin login.
 * Deben coincidir con las rutas declaradas en App.tsx.
 */
export const RUTAS_REPORTE_PAGO_PUBLICO: readonly string[] = [
  `/${SEGMENTO_REPORTE_LEGACY}`,
  `/${SEGMENTO_REPORTE_COBROS}`,
  `/${SEGMENTO_INFOPAGOS}`,
]
