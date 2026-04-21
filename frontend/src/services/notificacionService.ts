import { apiClient } from '../services/api'

/** Envíos masivos sincrónicos (PDF + SMTP): listas grandes suelen superar 3 min. */
export const TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL = 900_000

export interface NotificacionPlantilla {
  id: number

  nombre: string

  descripcion: string | null

  tipo: string

  asunto: string

  cuerpo: string

  variables_disponibles: string | null

  activa: boolean

  zona_horaria: string

  fecha_creacion: string

  fecha_actualizacion: string
}

export interface Notificacion {
  id: number

  cliente_id: number | null

  tipo: string

  canal: string | null

  mensaje: string

  asunto: string | null

  estado: string

  fecha_envio: string | null

  fecha_creacion: string

  error_mensaje?: string | null

  created_at?: string
}

export interface NotificacionStats {
  total: number

  enviadas: number

  pendientes: number

  fallidas: number

  tasa_exito: number
}

/** Un registro de cliente/cuota para notificaciones (nombre, cedula, etc.). */

export interface ClienteRetrasadoItem {
  cliente_id: number

  /** ID del préstamo (para PDF estado de cuenta, mismo endpoint que amortización). */
  prestamo_id?: number

  nombre: string

  cedula: string

  numero_cuota?: number

  fecha_vencimiento?: string

  monto?: number

  /** Suma del saldo pendiente de todas las cuotas del préstamo (mismo criterio que notificaciones). */
  total_pendiente_pagar?: number

  dias_atraso?: number
  /** Misma regla que estado de cuenta / amortización (cuotas vencidas sin cubrir al 100%). */
  cuotas_atrasadas?: number

  /** Prejudicial: total de cuotas en mora del cliente (backend get_notificaciones_tabs_data). */
  total_cuotas_atrasadas?: number
  /** Misma tabla que GET /prestamos: pendiente | revisando | en_espera | rechazado | revisado */
  revision_manual_estado?: string | null
  correo?: string
  telefono?: string
  estado?: string

  /** Submódulo GENERAL: criterio de origen de la fila (día siguiente, prejudicial, 2 días antes). */
  notificacion_caso?: string

  /** Caché en BD (prestamos.abonos_drive_cuotas_cache); evita N llamadas GET comparar en listado General. */
  comparar_abonos_drive_cuotas?: CompararAbonosDriveCuotasResponse | null

  /** Caché en BD: columna Q (hoja) vs fecha_aprobacion; submódulo Notificaciones Fecha. */
  comparar_fecha_entrega_q_aprobacion?: CompararFechaEntregaQvsAprobacionResponse | null
}

/** Opción de lote cuando la hoja tiene varios créditos por cédula (GET comparar-abonos-drive-cuotas). */
export interface OpcionLoteAbonos {
  lote: string

  abonos: number
}

/** Huella del préstamo en BD (financiamiento, cuotas, modalidad) para alinear con la fila de la hoja. */
export interface PrestamoHuellaAbonos {
  total_financiamiento: number

  numero_cuotas: number

  modalidad_pago: string
}

/** GET /notificaciones/comparar-abonos-drive-cuotas */
export interface CompararAbonosDriveCuotasResponse {
  cedula: string

  prestamo_id: number

  prestamo_huella?: PrestamoHuellaAbonos

  filas_hoja_coincidentes: number

  /** Filas en la hoja con la misma cédula (antes de filtrar por préstamo / lote). */
  filas_misma_cedula_hoja?: number

  abonos_drive: number | null

  total_pagado_cuotas: number

  diferencia: number | null

  coincide_aproximado: boolean

  tolerancia: number

  hoja_synced_at: string | null

  /** True si la última sync supera el umbral de horas definido en backend (p. ej. 48 h). */
  hoja_sync_antigua?: boolean

  /** Horas desde la última sync (aprox.); puede existir aunque no sea «antigua». */
  hoja_sync_antigua_horas?: number | null

  columna_cedula_detectada: string | null

  columna_abonos_detectada: string | null

  /** Columna LOTE detectada en la hoja (p. ej. LOTE en B). */

  columna_lote_detectada?: string | null

  /** Lote usado en esta consulta (si se envió `lote` en query). */

  lote_aplicado?: string | null

  /** Hay varios lotes para la cédula: el usuario debe elegir uno que corresponda al préstamo. */

  requiere_seleccion_lote?: boolean

  opciones_lote?: OpcionLoteAbonos[]

  advertencias: string[]

  /** "si" si ABONOS (hoja) > total pagado en cuotas (+ tolerancia); "no" en caso contrario. */

  indicador?: 'si' | 'no' | string

  /** Igual que indicador === "si" (backend envía ambos). */

  puede_aplicar?: boolean

  /** Monto ABONOS (USD) a partir del cual se exige escribir CONFIRMO antes de aplicar. */
  umbral_doble_confirmacion_abonos_usd?: number
}

/** Caché / comparación: columna Q de CONCILIACIÓN vs fecha_aprobacion del préstamo (BD). */
export interface CompararFechaEntregaQvsAprobacionResponse {
  cedula: string

  prestamo_id: number

  prestamo_huella?: PrestamoHuellaAbonos

  filas_hoja_coincidentes: number

  filas_misma_cedula_hoja?: number

  columna_q_letra?: string

  columna_q_header_detectado?: string | null

  rango_columnas_hoja?: string

  columna_q_dentro_rango?: boolean

  /** ISO YYYY-MM-DD si se pudo interpretar la celda Q. */
  fecha_entrega_column_q?: string | null

  fecha_entrega_column_q_raw?: unknown

  /** ISO YYYY-MM-DD (solo fecha) desde prestamos.fecha_aprobacion. */
  fecha_aprobacion_sistema?: string | null

  /** ISO YYYY-MM-DD desde prestamos.fecha_requerimiento (expediente); no cambia al aplicar Q. */
  fecha_requerimiento_prestamo?: string | null

  /** Días calendario: fecha Q (entrega hoja) − fecha_aprobacion (sistema). */
  diferencia_dias?: number | null

  coincide_calendario?: boolean

  /** Misma clave que ABONOS: true si misma fecha calendario (tolerancia días en tolerancia_dias). */
  coincide_aproximado?: boolean

  /**
   * True si se puede POST aplicar-fecha-entrega-q: Q posterior a la aprobación en BD, o
   * Q anterior pero >= fecha_requerimiento (corrección de aprobación errónea vs columna Q).
   */
  puede_aplicar?: boolean

  /** True si el caso aplicable es «Q antes que la aprobación en BD» (corrección hacia atrás). */
  correccion_desde_q_anterior_bd?: boolean

  indicador?: 'si' | 'no' | string

  tolerancia_dias?: number

  hoja_synced_at?: string | null

  hoja_sync_antigua?: boolean

  hoja_sync_antigua_horas?: number | null

  columna_cedula_detectada?: string | null

  columna_lote_detectada?: string | null

  lote_aplicado?: string | null

  requiere_seleccion_lote?: boolean

  opciones_lote?: Array<{ lote: string }>

  advertencias?: string[]
}

/** Respuesta de POST /notificaciones/aplicar-abonos-drive-a-cuotas (solo admin). */

export interface AplicarAbonosDriveCuotasResponse {
  ok: boolean

  prestamo_id: number

  pago_id: number

  abonos_drive_origen: number

  monto_pago_usd: number

  pagos_eliminados: number

  cuotas_completadas: number

  cuotas_parciales: number

  referencia_pago: string
}

/** Préstamo con total financiamiento = total abonos (liquidado). */

export interface LiquidadoItem {
  prestamo_id: number

  nombre: string

  cedula: string

  total_financiamiento: number | string

  total_abonos: number | string
}

export interface ClientesRetrasadosResponse {
  actualizado_en: string

  dias_5: ClienteRetrasadoItem[]

  dias_3: ClienteRetrasadoItem[]

  dias_1: ClienteRetrasadoItem[]

  hoy: ClienteRetrasadoItem[]

  dias_1_atraso?: ClienteRetrasadoItem[]

  dias_10_atraso?: ClienteRetrasadoItem[]

  liquidados?: LiquidadoItem[]
}

export interface NotificacionesMasivosResponse {
  items: ClienteRetrasadoItem[]
  total: number
}

export interface EstadisticasTabItem {
  enviados: number

  rebotados: number
}

export interface EstadisticasPorTab {
  dias_5: EstadisticasTabItem

  dias_3: EstadisticasTabItem

  dias_1: EstadisticasTabItem

  hoy: EstadisticasTabItem

  /** Envios del caso "1 dia de retraso" (tipo_tab en BD). */

  dias_1_retraso: EstadisticasTabItem

  dias_10_retraso: EstadisticasTabItem

  prejudicial: EstadisticasTabItem

  masivos: EstadisticasTabItem

  liquidados: EstadisticasTabItem

  /** Submenú 2 días antes (PAGO_2_DIAS_ANTES_PENDIENTE). */

  d_2_antes_vencimiento: EstadisticasTabItem

  /** Correos estado de cuenta «Recibos» (tipo_tab recibos en envios_notificacion). */

  recibos?: EstadisticasTabItem
}

/** Fila del listado Recibos (pago conciliado + contexto cuota/cliente como notificaciones). */

export type ReciboConciliacionFila = ClienteRetrasadoItem & {
  pago_id: number

  cedula_normalizada?: string

  fecha_registro?: string | null

  monto_pagado?: number

  /** URL o ruta del comprobante (tabla pagos). */
  link_comprobante?: string | null

  documento_ruta?: string | null

  documento_nombre?: string | null

  documento_tipo?: string | null
}

/** Detalle por cédula en POST /notificaciones/recibos/ejecutar (truncado en servidor). */
export interface RecibosEjecutarEnvioDetalle {
  cedula?: string

  motivo?: string

  error?: string

  [key: string]: unknown
}

/** Respuesta de POST /notificaciones/recibos/ejecutar (simulación o envío real). */
export interface RecibosEjecutarEnvioResponse {
  fecha_dia: string

  slot: string

  solo_simular: boolean

  sin_casos_en_ventana: boolean

  pagos_en_ventana: number

  cedulas_distintas: number

  enviados: number

  fallidos: number

  omitidos_sin_email: number

  omitidos_ya_enviado: number

  omitidos_desistimiento: number

  omitidos_sin_datos: number

  omitidos_error_estado_cuenta: number

  omitidos_cedula_desalineada: number

  detalles: RecibosEjecutarEnvioDetalle[]

  /** Códigos de negocio p. ej. `email_activo_recibos_desactivado` (HTTP 200). */
  error?: string

  hoy_negocio?: string
}

/** Un registro del historial de envíos por cédula (para reportes/legales). */

export interface HistorialEnvioItem {
  id: number

  fecha_envio: string | null

  tipo_tab: string

  asunto: string

  email: string

  nombre: string

  cedula: string

  exito: boolean

  /** Indicador de entrega: "entregado" (enviado correctamente) o "rebotado" (fallo en envío). */

  estado_envio: 'entregado' | 'rebotado'

  error_mensaje: string | null

  prestamo_id: number | null

  correlativo: number | null

  /** Metadatos de adjuntos persistidos (envíos con snapshot). */

  adjuntos?: Array<{ id: number; nombre_archivo: string; orden: number }>

  tiene_mensaje_html?: boolean

  tiene_mensaje_texto?: boolean

  /** Hay HTML o texto guardado: se puede descargar el cuerpo como PDF. */

  tiene_mensaje_pdf?: boolean

  tiene_comprobante_pdf?: boolean
}

export interface HistorialEnvioResponse {
  items: HistorialEnvioItem[]

  total: number

  cedula: string
}

export interface EmailConfig {
  smtp_host: string

  smtp_port: string

  smtp_user: string

  smtp_password?: string

  from_email: string

  from_name: string

  smtp_use_tls: string

  modo_pruebas?: string

  email_pruebas?: string

  email_activo?: string | boolean

  imap_host?: string

  imap_port?: string

  imap_user?: string

  imap_password?: string

  imap_use_ssl?: string

  /** Contactos prestablecidos: emails separados por coma para notificación automática de tickets CRM */

  tickets_notify_emails?: string
}

export interface NotificacionVariable {
  id?: number

  nombre_variable: string

  tabla: string

  campo_bd: string

  descripcion: string | null

  activa: boolean

  fecha_creacion?: string

  fecha_actualizacion?: string
}

/** Respuesta de POST /notificaciones/enviar-prueba-paquete (mismo shape que resumen de envio + meta). */
export interface EnvioPruebaPaqueteResponse {
  mensaje?: string
  enviados?: number
  fallidos?: number
  sin_email?: number
  omitidos_config?: number
  omitidos_paquete_incompleto?: number
  enviados_whatsapp?: number
  fallidos_whatsapp?: number
  tipo?: string
  destinos?: string[]
}

export interface DiagnosticoPaquetePruebaResponse {
  ok?: boolean
  motivo?: string
  tipo_solicitado?: string
  tipo_config?: string
  habilitado_envio?: boolean
  plantilla_id?: number | null
  plantilla_ok?: boolean
  plantilla_motivo?: string | null
  paquete_estricto?: boolean
  relax_solo_prueba_destino?: boolean
  paquete_completo?: boolean
  paquete_motivo?: string | null
  adjuntos_previstos?: Array<{
    nombre: string
    bytes: number
    cabecera_pdf: boolean
  }>
  error_adjuntos?: string
}

/** Prefijo API v1; pestañas de notificaciones usan rutas propias (notificaciones-previas, etc.). */

const API_V1 = '/api/v1'

class NotificacionService {
  private baseUrl = `${API_V1}/notificaciones`

  /** Lista plantillas por tipo. Backend puede devolver [] si no hay tabla plantillas. */

  async listarPlantillas(
    tipo?: string,
    soloActivas = true
  ): Promise<NotificacionPlantilla[]> {
    const params = new URLSearchParams()

    if (tipo) params.append('tipo', tipo)

    params.append('solo_activas', String(soloActivas))

    return await apiClient.get<NotificacionPlantilla[]>(
      `${this.baseUrl}/plantillas?${params}`
    )
  }

  async obtenerPlantilla(id: number): Promise<NotificacionPlantilla> {
    return await apiClient.get<NotificacionPlantilla>(
      `${this.baseUrl}/plantillas/${id}`
    )
  }

  async crearPlantilla(
    data: Partial<NotificacionPlantilla>
  ): Promise<NotificacionPlantilla> {
    return await apiClient.post<NotificacionPlantilla>(
      `${this.baseUrl}/plantillas`,
      data
    )
  }

  async actualizarPlantilla(
    id: number,
    data: Partial<NotificacionPlantilla>
  ): Promise<NotificacionPlantilla> {
    return await apiClient.put<NotificacionPlantilla>(
      `${this.baseUrl}/plantillas/${id}`,
      data
    )
  }

  async eliminarPlantilla(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/plantillas/${id}`)
  }

  async exportarPlantilla(id: number): Promise<NotificacionPlantilla> {
    return await apiClient.get<NotificacionPlantilla>(
      `${this.baseUrl}/plantillas/${id}/export`
    )
  }

  async enviarConPlantilla(
    plantillaId: number,
    params: { cliente_id: number; variables: Record<string, any> }
  ): Promise<any> {
    const query = new URLSearchParams({ cliente_id: String(params.cliente_id) })

    return await apiClient.post(
      `${this.baseUrl}/plantillas/${plantillaId}/enviar?${query}`,
      params.variables
    )
  }

  // Notificaciones

  async listarNotificaciones(
    page = 1,
    per_page = 20,
    estado?: string,
    canal?: string
  ): Promise<{
    items: Notificacion[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }> {
    const params = new URLSearchParams()

    params.append('page', String(page))

    params.append('per_page', String(per_page))

    if (estado) params.append('estado', estado)

    if (canal) params.append('canal', canal)

    return await apiClient.get<{
      items: Notificacion[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`${this.baseUrl}?${params}`)
  }

  async obtenerEstadisticas(): Promise<NotificacionStats> {
    return await apiClient.get<NotificacionStats>(
      `${this.baseUrl}/estadisticas/resumen`
    )
  }

  /** Clientes retrasados por reglas (previas, hoy, atrasos, liquidados). Datos reales desde BD. */

  async getClientesRetrasados(
    fechaCaracas?: string | null
  ): Promise<ClientesRetrasadosResponse> {
    return await apiClient.get<ClientesRetrasadosResponse>(
      `${this.baseUrl}/clientes-retrasados`,
      {
        timeout: 60000,
        params:
          fechaCaracas && String(fechaCaracas).trim()
            ? { fecha_caracas: String(fechaCaracas).trim() }
            : undefined,
      }
    )
  }

  /** Cuotas PENDIENTE con vencimiento = hoy + 2 (Caracas). Submenú 2 días antes. */

  async getCuotasPendiente2DiasAntes(fechaCaracas?: string | null): Promise<{
    actualizado_en: string
    items: ClienteRetrasadoItem[]
    total: number
  }> {
    return await apiClient.get<{
      actualizado_en: string
      items: ClienteRetrasadoItem[]
      total: number
    }>(`${this.baseUrl}/cuotas-pendiente-2-dias-antes`, {
      timeout: 60000,
      params:
        fechaCaracas && String(fechaCaracas).trim()
          ? { fecha_caracas: String(fechaCaracas).trim() }
          : undefined,
    })
  }

  /** KPIs por pestaña: enviados y rebotados (dias_5, dias_3, dias_1, hoy, dias_1_retraso). */

  async getEstadisticasPorTab(): Promise<EstadisticasPorTab> {
    return await apiClient.get<EstadisticasPorTab>(
      `${this.baseUrl}/estadisticas-por-tab`
    )
  }

  /** Historial de notificaciones enviadas/fallidas por cédula (reportes y fines legales). */

  async getHistorialNotificacionesPorCedula(
    cedula: string
  ): Promise<HistorialEnvioResponse> {
    return await apiClient.get<HistorialEnvioResponse>(
      `${this.baseUrl}/historial-por-cedula`,
      {
        params: { cedula: cedula.trim() },
      }
    )
  }

  /** Descarga Excel con historial de notificaciones para una cédula. */

  async descargarHistorialNotificacionesExcel(cedula: string): Promise<Blob> {
    const blob = await apiClient.get<Blob>(
      `${this.baseUrl}/historial-por-cedula/excel`,
      {
        params: { cedula: cedula.trim() },

        responseType: 'blob',
      }
    )

    return blob as Blob
  }

  /** Descarga el cuerpo del correo como PDF (snapshot HTML o texto). */

  async descargarHistorialMensajePdf(envioId: number): Promise<Blob> {
    return (await apiClient.get<Blob>(
      `${this.baseUrl}/historial-por-cedula/${envioId}/mensaje-pdf`,
      { responseType: 'blob' }
    )) as Blob
  }

  /** Descarga cuerpo texto del correo (snapshot). */

  async descargarHistorialMensajeTexto(envioId: number): Promise<Blob> {
    return (await apiClient.get<Blob>(
      `${this.baseUrl}/historial-por-cedula/${envioId}/mensaje-texto`,
      { responseType: 'blob' }
    )) as Blob
  }

  /** Descarga un adjunto del envío (PDF u otro). */

  async descargarHistorialAdjunto(
    envioId: number,
    adjuntoId: number
  ): Promise<Blob> {
    return (await apiClient.get<Blob>(
      `${this.baseUrl}/historial-por-cedula/${envioId}/adjunto/${adjuntoId}`,
      { responseType: 'blob' }
    )) as Blob
  }

  /** Comprobante de envío en PDF (generado al persistir). */

  async descargarHistorialComprobantePdf(envioId: number): Promise<Blob> {
    return (await apiClient.get<Blob>(
      `${this.baseUrl}/historial-por-cedula/${envioId}/comprobante-pdf`,
      { responseType: 'blob' }
    )) as Blob
  }

  /** Recalcular dias_mora en clientes (POST manual desde la UI «Actualizar» o API). */

  async actualizarNotificaciones(opts?: { signal?: AbortSignal }): Promise<{
    mensaje: string
    clientes_actualizados: number
  }> {
    return await apiClient.post<{
      mensaje: string
      clientes_actualizados: number
    }>(`${this.baseUrl}/actualizar`, {}, { signal: opts?.signal })
  }

  /**
   * Programa en el servidor el recálculo de la caché «Diferencia abono» (mismo job que 02:00 Caracas).
   * La respuesta es inmediata; el trabajo corre en segundo plano.
   */
  async refreshAbonosDriveCache(): Promise<{ ok: boolean; mensaje: string }> {
    return await apiClient.post<{ ok: boolean; mensaje: string }>(
      `${this.baseUrl}/refresh-abonos-drive-cache`,
      {}
    )
  }

  async refreshFechaEntregaQCache(): Promise<{ ok: boolean; mensaje: string }> {
    return await apiClient.post<{ ok: boolean; mensaje: string }>(
      `${this.baseUrl}/refresh-fecha-entrega-q-cache`,
      {}
    )
  }

  /** Plantilla editable del PDF de carta de cobranza (adjunto al email). */

  async getPlantillaPdfCobranza(): Promise<{
    ciudad_default: string
    cuerpo_principal: string | null
    clausula_septima: string | null
    firma?: string | null
  }> {
    return await apiClient.get(`${this.baseUrl}/plantilla-pdf-cobranza`)
  }

  async updatePlantillaPdfCobranza(data: {
    ciudad_default?: string
    cuerpo_principal?: string | null
    clausula_septima?: string | null
    firma?: string | null
  }): Promise<{
    ciudad_default: string
    cuerpo_principal: string | null
    clausula_septima: string | null
    firma?: string | null
  }> {
    return await apiClient.put(`${this.baseUrl}/plantilla-pdf-cobranza`, data)
  }

  /** PDF fijo que se anexa siempre al email de cobranza (sin cambios). */

  async getAdjuntoFijoCobranza(): Promise<{
    nombre_archivo: string
    ruta: string
  }> {
    return await apiClient.get(`${this.baseUrl}/adjunto-fijo-cobranza`)
  }

  async updateAdjuntoFijoCobranza(data: {
    nombre_archivo?: string
    ruta?: string
  }): Promise<{ nombre_archivo: string; ruta: string }> {
    return await apiClient.put(`${this.baseUrl}/adjunto-fijo-cobranza`, data)
  }

  /** Comprueba si la ruta del adjunto fijo existe en el servidor. */

  async verificarAdjuntoFijoCobranza(): Promise<{
    existe: boolean
    mensaje: string
  }> {
    return await apiClient.get(
      `${this.baseUrl}/adjunto-fijo-cobranza/verificar`
    )
  }

  async getAdjuntosFijosCobranza(): Promise<
    Record<string, Array<{ id: string; nombre_archivo: string; ruta: string }>>
  > {
    return await apiClient.get(`${this.baseUrl}/adjuntos-fijos-cobranza`)
  }

  async uploadAdjuntoFijoCobranza(
    file: File,
    tipoCaso: string
  ): Promise<{ id: string; nombre_archivo: string; tipo_caso: string }> {
    const form = new FormData()
    form.append('file', file)
    return await apiClient.post(
      `${this.baseUrl}/adjuntos-fijos-cobranza/upload?tipo_caso=${encodeURIComponent(tipoCaso)}`,
      form
    )
  }

  async deleteAdjuntoFijoCobranza(id: string): Promise<void> {
    await apiClient.delete(
      `${this.baseUrl}/adjuntos-fijos-cobranza/${encodeURIComponent(id)}`
    )
  }

  /** Vista previa del PDF de carta de cobranza (datos de ejemplo). Devuelve el blob del PDF. */

  async getPlantillaPdfCobranzaPreview(): Promise<Blob> {
    const response = await apiClient.get<Blob>(
      `${this.baseUrl}/plantilla-pdf-cobranza/preview`,
      {
        responseType: 'blob',
      }
    )

    return response as Blob
  }

  // Notificaciones previas

  async listarNotificacionesPrevias(estado?: string): Promise<{
    items: any[]
    total: number
    dias_5: number
    dias_3: number
    dias_1: number
  }> {
    const params = new URLSearchParams()

    if (estado) params.append('estado', estado)

    // Usar timeout extendido para este endpoint que puede tardar más

    return await apiClient.get<{
      items: any[]
      total: number
      dias_5: number
      dias_3: number
      dias_1: number
    }>(
      `${API_V1}/notificaciones-previas/?${params}`,

      { timeout: 120000 }
    )
  }

  async listarNotificacionesRetrasadas(estado?: string): Promise<{
    items: any[]
    total: number
    dias_1: number
    dias_3: number
    dias_5: number
  }> {
    const params = new URLSearchParams()

    if (estado) params.append('estado', estado)

    return await apiClient.get<{
      items: any[]
      total: number
      dias_1: number
      dias_3: number
      dias_5: number
    }>(
      `${API_V1}/notificaciones-retrasadas/?${params}`,

      { timeout: 120000 }
    )
  }

  async listarNotificacionesPrejudiciales(
    estado?: string,
    fechaCaracas?: string | null
  ): Promise<{ items: ClienteRetrasadoItem[]; total: number }> {
    const params = new URLSearchParams()

    if (estado) params.append('estado', estado)

    if (fechaCaracas && String(fechaCaracas).trim()) {
      params.append('fecha_caracas', String(fechaCaracas).trim())
    }

    const qs = params.toString()

    return await apiClient.get<{
      items: ClienteRetrasadoItem[]
      total: number
    }>(`${API_V1}/notificaciones-prejudicial${qs ? `?${qs}` : ''}`, {
      timeout: 120000,
    })
  }

  async listarNotificacionesDiaPago(
    estado?: string
  ): Promise<{ items: any[]; total: number }> {
    const params = new URLSearchParams()

    if (estado) params.append('estado', estado)

    return await apiClient.get<{ items: any[]; total: number }>(
      `${API_V1}/notificaciones-dia-pago/?${params}`,

      { timeout: 120000 }
    )
  }

  async listarNotificacionesMasivos(): Promise<NotificacionesMasivosResponse> {
    return await apiClient.get<NotificacionesMasivosResponse>(
      `${API_V1}/notificaciones-masivos/`,
      { timeout: 120000 }
    )
  }

  /** Envía correo a cada cliente en la clasificación indicada (email desde tabla clientes). */

  async enviarNotificacionesPrevias(): Promise<{
    mensaje: string
    enviados: number
    sin_email: number
    fallidos: number
  }> {
    return await apiClient.post<{
      mensaje: string
      enviados: number
      sin_email: number
      fallidos: number
    }>(
      `${API_V1}/notificaciones-previas/enviar`,

      {},

      { timeout: 120000 }
    )
  }

  async enviarNotificacionesDiaPago(): Promise<{
    mensaje: string
    enviados: number
    sin_email: number
    fallidos: number
  }> {
    return await apiClient.post<{
      mensaje: string
      enviados: number
      sin_email: number
      fallidos: number
    }>(
      `${API_V1}/notificaciones-dia-pago/enviar`,

      {},

      { timeout: 120000 }
    )
  }

  async enviarNotificacionesRetrasadas(): Promise<{
    mensaje: string
    enviados: number
    sin_email: number
    fallidos: number
  }> {
    return await apiClient.post<{
      mensaje: string
      enviados: number
      sin_email: number
      fallidos: number
    }>(
      `${API_V1}/notificaciones-retrasadas/enviar`,

      {},

      { timeout: 120000 }
    )
  }

  async enviarNotificacionesPrejudiciales(opts?: {
    signal?: AbortSignal
    fechaCaracas?: string | null
  }): Promise<{
    mensaje: string
    enviados: number
    sin_email: number
    fallidos: number
  }> {
    const fc =
      opts?.fechaCaracas && String(opts.fechaCaracas).trim()
        ? String(opts.fechaCaracas).trim()
        : undefined
    return await apiClient.post<{
      mensaje: string
      enviados: number
      sin_email: number
      fallidos: number
    }>(
      `${API_V1}/notificaciones-prejudicial/enviar`,
      {},
      {
        timeout: TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL,
        signal: opts?.signal,
        params: fc ? { fecha_caracas: fc } : undefined,
      }
    )
  }

  async enviarNotificacionesMasivos(opts?: { signal?: AbortSignal }): Promise<{
    mensaje: string
    enviados: number
    sin_email: number
    fallidos: number
  }> {
    return await apiClient.post<{
      mensaje: string
      enviados: number
      sin_email: number
      fallidos: number
    }>(
      `${API_V1}/notificaciones-masivos/enviar`,

      {},

      { timeout: 120000, signal: opts?.signal }
    )
  }

  /**
   * Prueba de paquete completo: cuerpo desde plantilla vinculada + Carta PDF + PDFs fijos (mismo flujo que producción).
   */

  async diagnosticoPaquetePrueba(
    tipo: string
  ): Promise<DiagnosticoPaquetePruebaResponse> {
    const params = new URLSearchParams({ tipo })
    return await apiClient.get<DiagnosticoPaquetePruebaResponse>(
      `${this.baseUrl}/diagnostico-paquete-prueba?${params}`,
      { timeout: 180000 }
    )
  }

  async enviarPruebaPaqueteCompleta(params: {
    tipo: string
    destinos: string[]
    signal?: AbortSignal
  }): Promise<EnvioPruebaPaqueteResponse> {
    const { signal, ...body } = params
    return await apiClient.post<EnvioPruebaPaqueteResponse>(
      `${this.baseUrl}/enviar-prueba-paquete`,
      body,
      { timeout: 120000, signal }
    )
  }

  async enviarTodasNotificaciones(): Promise<{
    mensaje?: string

    en_proceso?: boolean

    enviados?: number

    fallidos?: number

    sin_email?: number

    omitidos_config?: number

    enviados_whatsapp?: number

    fallidos_whatsapp?: number

    detalles?: Record<string, unknown>
  }> {
    return await apiClient.post<{
      mensaje?: string

      en_proceso?: boolean

      enviados?: number

      fallidos?: number

      sin_email?: number

      omitidos_config?: number

      enviados_whatsapp?: number

      fallidos_whatsapp?: number

      detalles?: Record<string, unknown>
    }>(`${this.baseUrl}/enviar-todas`, {}, { timeout: 20000 })
  }

  /** Envio masivo sincrono solo para un criterio (configuracion por fila). */
  async enviarCasoManual(
    tipo: string,
    opts?: { signal?: AbortSignal; fechaCaracas?: string | null }
  ): Promise<{
    mensaje: string
    tipo_caso: string
    total_en_lista: number
    enviados: number
    sin_email: number
    fallidos: number
    omitidos_config?: number
    omitidos_paquete_incompleto?: number
    enviados_whatsapp?: number
    fallidos_whatsapp?: number
  }> {
    const fc =
      opts?.fechaCaracas && String(opts.fechaCaracas).trim()
        ? String(opts.fechaCaracas).trim()
        : undefined
    return await apiClient.post(
      `${this.baseUrl}/enviar-caso-manual`,
      { tipo, ...(fc ? { fecha_caracas: fc } : {}) },
      { timeout: TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL, signal: opts?.signal }
    )
  }

  /** Ultimo resumen persistido tras enviar-todas o enviar-caso-manual (sin depender solo de logs). */

  async obtenerUltimoEnvioBatch(): Promise<{
    ultimo: Record<string, unknown> | null
  }> {
    return await apiClient.get<{ ultimo: Record<string, unknown> | null }>(
      `${this.baseUrl}/envio-batch/ultimo`
    )
  }

  // Variables de notificaciones

  async listarVariables(activa?: boolean): Promise<NotificacionVariable[]> {
    const params = new URLSearchParams()

    if (activa !== undefined) params.append('activa', String(activa))

    return await apiClient.get<NotificacionVariable[]>(
      `${this.baseUrl}/variables?${params}`
    )
  }

  async obtenerVariable(id: number): Promise<NotificacionVariable> {
    return await apiClient.get<NotificacionVariable>(
      `${this.baseUrl}/variables/${id}`
    )
  }

  async crearVariable(
    data: Partial<NotificacionVariable>
  ): Promise<NotificacionVariable> {
    return await apiClient.post<NotificacionVariable>(
      `${this.baseUrl}/variables`,
      data
    )
  }

  async actualizarVariable(
    id: number,
    data: Partial<NotificacionVariable>
  ): Promise<NotificacionVariable> {
    return await apiClient.put<NotificacionVariable>(
      `${this.baseUrl}/variables/${id}`,
      data
    )
  }

  async eliminarVariable(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/variables/${id}`)
  }

  async inicializarVariablesPrecargadas(): Promise<{
    mensaje: string
    variables_creadas: number
    variables_existentes: number
    total: number
  }> {
    return await apiClient.post<{
      mensaje: string
      variables_creadas: number
      variables_existentes: number
      total: number
    }>(`${this.baseUrl}/variables/inicializar-precargadas`)
  }

  /** ABONOS (hoja CONCILIACIÓN) vs sum(cuotas.total_pagado) del préstamo. */
  async getCompararAbonosDriveCuotas(params: {
    cedula: string
    prestamoId: number
    /** Lote en hoja cuando hay varios créditos por cédula; debe corresponder al préstamo. */
    lote?: string | null
  }): Promise<CompararAbonosDriveCuotasResponse> {
    const q = new URLSearchParams()
    q.set('cedula', params.cedula.trim())
    q.set('prestamo_id', String(params.prestamoId))
    const lote = params.lote?.trim()
    if (lote) q.set('lote', lote)
    return await apiClient.get<CompararAbonosDriveCuotasResponse>(
      `${this.baseUrl}/comparar-abonos-drive-cuotas?${q.toString()}`
    )
  }

  /** Columna Q (hoja) vs fecha_aprobacion (BD); lectura en vivo (no persiste caché). */
  async getCompararFechaEntregaQvsAprobacion(params: {
    cedula: string
    prestamoId: number
    lote?: string | null
  }): Promise<CompararFechaEntregaQvsAprobacionResponse> {
    const q = new URLSearchParams()
    q.set('cedula', params.cedula.trim())
    q.set('prestamo_id', String(params.prestamoId))
    const lote = params.lote?.trim()
    if (lote) q.set('lote', lote)
    return await apiClient.get<CompararFechaEntregaQvsAprobacionResponse>(
      `${this.baseUrl}/comparar-fecha-entrega-q-aprobacion?${q.toString()}`
    )
  }

  /**
   * Persiste la fecha de la columna Q como `prestamos.fecha_aprobacion` (y alinea base de cálculo);
   * recalcula vencimientos de cuotas con la misma lógica que `PUT /prestamos/{id}`.
   * Solo si la fecha Q es estrictamente posterior a la fecha de aprobación actual; requiere admin.
   */
  async postAplicarFechaEntregaQComoFechaAprobacion(params: {
    cedula: string
    prestamoId: number
    lote?: string | null
    /** Obligatorio cuando el backend indica corrección con Q anterior a la BD: texto exacto CONFIRMO. */
    confirmacionCorreccionFechaQAtras?: string | null
  }): Promise<{ ok: boolean; prestamo?: Record<string, unknown> }> {
    const body: Record<string, unknown> = {
      cedula: params.cedula.trim(),
      prestamo_id: params.prestamoId,
    }
    const lote = params.lote?.trim()
    if (lote) body.lote = lote
    const conf = params.confirmacionCorreccionFechaQAtras?.trim()
    if (conf) body.confirmacion_correccion_fecha_q_atras = conf
    return await apiClient.post(`${this.baseUrl}/aplicar-fecha-entrega-q-como-fecha-aprobacion`, body)
  }

  /**
   * Elimina pagos del préstamo y aplica ABONOS (hoja) en cascada.
   * Solo si ABONOS > sum(cuotas.total_pagado); requiere rol admin en backend.
   */
  async postAplicarAbonosDriveACuotas(params: {
    cedula: string

    prestamoId: number

    lote?: string | null

    /** Si ABONOS supera el umbral del backend, debe ser exactamente `CONFIRMO`. */
    confirmacionMontosAltos?: string | null
  }): Promise<AplicarAbonosDriveCuotasResponse> {
    const body: Record<string, unknown> = {
      cedula: params.cedula.trim(),

      prestamo_id: params.prestamoId,
    }
    const lote = params.lote?.trim()
    if (lote) body.lote = lote
    const conf = params.confirmacionMontosAltos?.trim()
    if (conf) body.confirmacion_montos_altos = conf
    return await apiClient.post<AplicarAbonosDriveCuotasResponse>(
      `${this.baseUrl}/aplicar-abonos-drive-a-cuotas`,
      body
    )
  }

  /** Submódulo Recibos: vista previa de pagos conciliados en la franja (fecha_registro en Caracas). */
  async listarRecibosConciliacion(params: {
    fecha_caracas?: string
  }): Promise<{
    fecha_dia: string
    slot: string
    total_pagos: number
    cedulas_distintas: number
    kpis: {
      correos_enviados: number
      correos_rebotados: number
      /** Cédulas distintas con al menos un registro en recibos_email_envio para este día de corte. */
      cedulas_registradas_envio_dia: number
      /** Filas en recibos_email_envio ese día (suma de lotes; suele coincidir con cédulas salvo dos slots). */
      registros_envio_dia_total: number
      /**
       * Un elemento por cada commit de envío real: orden 1, 2, … y correos_registrados_lote = filas
       * insertadas en ese instante (agrupación por creado_en en BD, PostgreSQL).
       */
      olas_envio_recibos_dia: Array<{
        orden: number
        creado_en: string
        correos_registrados_lote: number
      }>
      pagos_en_ventana_total: number
      cedulas_en_ventana_total: number
    }
    pagos: ReciboConciliacionFila[]
  }> {
    const q = new URLSearchParams()
    if (params.fecha_caracas) q.set('fecha_caracas', params.fecha_caracas)
    return await apiClient.get(
      `${API_V1}/notificaciones/recibos/listado?${q.toString()}`
    )
  }

  /** Ejecuta envío Recibos (mismo criterio que el motor de envío en servidor). */
  async ejecutarRecibosEnvio(body: {
    fecha_caracas?: string
    solo_simular?: boolean
    /** Solo envío real: día pasado explícito (admin). */
    forzar_envio_fecha_pasada?: boolean
  }): Promise<RecibosEjecutarEnvioResponse> {
    return await apiClient.post<RecibosEjecutarEnvioResponse>(
      `${API_V1}/notificaciones/recibos/ejecutar`,
      {
        fecha_caracas: body.fecha_caracas,
        solo_simular: body.solo_simular ?? false,
        forzar_envio_fecha_pasada: body.forzar_envio_fecha_pasada ?? false,
      },
      { timeout: TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL }
    )
  }

  /** HTML crudo del archivo de plantilla Recibos (editor; sin pipeline send_email). */
  async obtenerPlantillaHtmlRecibos(): Promise<string> {
    return await apiClient.get<string>(
      `${API_V1}/notificaciones/recibos/plantilla-correo-html`,
      { responseType: 'text' }
    )
  }

  /** Mismo HTML que iría en text/html tras el pipeline SMTP (logo URL, etc.). */
  async previsualizarPlantillaRecibosHtml(
    html: string,
    opts?: { signal?: AbortSignal }
  ): Promise<{ html: string }> {
    return await apiClient.post(
      `${API_V1}/notificaciones/recibos/plantilla-html-preview`,
      { html },
      { signal: opts?.signal }
    )
  }

  /**
   * Vista previa de la plantilla **ya persistida** (BD o archivo por defecto), con el mismo pipeline
   * que `send_email` — idéntica fuente que el envío masivo Recibos en servidor.
   */
  async obtenerPlantillaRecibosHtmlVistaEnvio(): Promise<{ html: string }> {
    return await apiClient.get<{ html: string }>(
      `${API_V1}/notificaciones/recibos/plantilla-html-envio-preview`
    )
  }

  /** Persiste la plantilla en el servidor (misma fuente que el envío Recibos en servidor). */
  async guardarPlantillaRecibosHtml(html: string): Promise<{ ok: boolean }> {
    return await apiClient.put(`${API_V1}/notificaciones/recibos/plantilla-correo-html`, {
      html,
    })
  }
}

class EmailConfigService {
  private baseUrl = '/api/v1/configuracion'

  async obtenerConfiguracionEmail(): Promise<EmailConfig> {
    return await apiClient.get<EmailConfig>(
      `${this.baseUrl}/email/configuracion`
    )
  }

  async actualizarConfiguracionEmail(
    config: Partial<EmailConfig>
  ): Promise<any> {
    try {
      // Usar timeout extendido para validación SMTP (puede tardar hasta 10-15 segundos)

      const resultado = await apiClient.put(
        `${this.baseUrl}/email/configuracion`,

        config,

        { timeout: 60000 } // 60 segundos para permitir validación SMTP
      )

      return resultado
    } catch (error) {
      throw error
    }
  }

  async probarConfiguracionEmail(
    emailDestino?: string,
    subject?: string,
    mensaje?: string,
    emailCC?: string,
    opts?: {
      servicio?: string
      tipo_tab?: string
      /** Recibos: HTML plantilla + PDF estado de cuenta del primer cliente en ventana; To = emailDestino. */
      recibos_prueba_datos_reales?: boolean
      fecha_caracas?: string
      /** Recibos: HTML crudo del editor; mismo cuerpo que la vista previa (POST preview). Vacío = archivo en disco. */
      recibos_html_plantilla?: string
    },
    axiosConfig?: { timeout?: number }
  ): Promise<any> {
    const body: Record<string, unknown> = {}

    if (emailDestino) body.email_destino = emailDestino

    if (subject) body.subject = subject

    if (mensaje) body.mensaje = mensaje

    if (emailCC) body.email_cc = emailCC

    if (opts?.servicio) body.servicio = opts.servicio

    if (opts?.tipo_tab) body.tipo_tab = opts.tipo_tab

    if (opts?.recibos_prueba_datos_reales) body.recibos_prueba_datos_reales = true

    if (opts?.fecha_caracas?.trim()) body.fecha_caracas = opts.fecha_caracas.trim()

    if (opts?.recibos_html_plantilla != null && opts.recibos_html_plantilla !== '') {
      body.recibos_html_plantilla = opts.recibos_html_plantilla
    }

    return await apiClient.post(
      `${this.baseUrl}/email/probar`,
      body,
      axiosConfig
    )
  }

  /** Config por tipo (habilitado, cco, plantilla_id, campos legacy programador/dias_semana) + global: modo_pruebas, email_pruebas. */

  async obtenerConfiguracionEnvios(): Promise<Record<string, unknown>> {
    return await apiClient.get<Record<string, unknown>>(
      `${this.baseUrl}/notificaciones/envios`
    )
  }

  async actualizarConfiguracionEnvios(
    config: Record<string, unknown>,
    opts?: { signal?: AbortSignal }
  ): Promise<any> {
    return await apiClient.put(
      `${this.baseUrl}/notificaciones/envios`,
      config,
      { signal: opts?.signal }
    )
  }

  /** Diagnostico PDF fijos (global + pestaña 3 por caso). */

  async obtenerDiagnosticoAdjuntosEnvios(): Promise<Record<string, unknown>> {
    return await apiClient.get<Record<string, unknown>>(
      `${API_V1}/configuracion/notificaciones/envios/diagnostico-adjuntos`
    )
  }

  async verificarEstadoConfiguracionEmail(): Promise<{
    configurada: boolean

    mensaje: string

    configuraciones: Record<string, any>

    problemas: string[]

    conexion_smtp?: { success: boolean; message?: string }

    modo_pruebas: boolean

    email_pruebas?: string | null
  }> {
    return await apiClient.get(`${this.baseUrl}/email/estado`)
  }

  async probarConfiguracionImap(imapConfig?: {
    imap_host?: string

    imap_port?: string

    imap_user?: string

    imap_password?: string

    imap_use_ssl?: string
  }): Promise<{ success: boolean; mensaje?: string }> {
    return await apiClient.post<{ success: boolean; mensaje?: string }>(
      `${this.baseUrl}/email/probar-imap`,

      imapConfig ?? {},

      { timeout: 60000 }
    )
  }
}

export interface WhatsAppConfig {
  api_url: string

  access_token: string

  phone_number_id: string

  business_account_id: string

  webhook_verify_token: string

  modo_pruebas?: string

  telefono_pruebas?: string
}

class WhatsAppConfigService {
  private baseUrl = '/api/v1/configuracion'

  async obtenerConfiguracionWhatsApp(): Promise<WhatsAppConfig> {
    return await apiClient.get<WhatsAppConfig>(
      `${this.baseUrl}/whatsapp/configuracion`
    )
  }

  async actualizarConfiguracionWhatsApp(
    config: Partial<WhatsAppConfig>
  ): Promise<any> {
    try {
      const resultado = await apiClient.put(
        `${this.baseUrl}/whatsapp/configuracion`,
        config
      )

      return resultado
    } catch (error) {
      throw error
    }
  }

  async probarConfiguracionWhatsApp(
    telefonoDestino?: string,
    mensaje?: string
  ): Promise<any> {
    const params: any = {}

    if (telefonoDestino) params.telefono_destino = telefonoDestino

    if (mensaje) params.mensaje = mensaje

    return await apiClient.post(`${this.baseUrl}/whatsapp/probar`, params)
  }

  async testCompletoWhatsApp(): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/whatsapp/test-completo`)
  }
}

export const notificacionService = new NotificacionService()

export const emailConfigService = new EmailConfigService()

export const whatsappConfigService = new WhatsAppConfigService()
