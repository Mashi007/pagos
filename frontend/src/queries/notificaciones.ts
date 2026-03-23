/**




 * Query keys compartidos para notificaciones/configuración.




 * Usar los mismos keys en todos los componentes que consumen estos datos




 * para que React Query deduplique peticiones y comparta caché.




 *




 * adjuntosFijos: usado en pestaña 2 (Anexo PDF) por DocumentosAlmacenadosPorPestana




 * y en pestaña 3 (Documentos PDF anexos) por DocumentosPdfAnexos → una sola GET




 * a GET /api/v1/notificaciones/adjuntos-fijos-cobranza.




 */

export const NOTIFICACIONES_QUERY_KEYS = {
  envios: ['configuracion-notificaciones-envios'] as const,

  /** GET /configuracion/email/estado (SMTP listo: v2 cuentas o legado). */

  emailEstado: ['configuracion', 'email', 'estado'] as const,

  plantillas: ['notificaciones-plantillas', { solo_activas: false }] as const,

  adjuntosFijos: ['notificaciones-adjuntos-fijos-cobranza'] as const,

  plantillaPdfCobranza: ['notificaciones-plantilla-pdf-cobranza'] as const,

  /** GET /notificaciones/envio-batch/ultimo (resumen ultimo masivo o scheduler). */

  envioBatchUltimo: ['notificaciones-envio-batch-ultimo'] as const,
} as const
