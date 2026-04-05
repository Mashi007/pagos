import { apiClient } from '../services/api'

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

  dias_5_atraso?: ClienteRetrasadoItem[]

  dias_30_atraso?: ClienteRetrasadoItem[]

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

  dias_3_retraso: EstadisticasTabItem

  dias_5_retraso: EstadisticasTabItem

  dias_30_retraso: EstadisticasTabItem

  prejudicial: EstadisticasTabItem

  masivos: EstadisticasTabItem

  liquidados: EstadisticasTabItem

  /** Submenú 2 días antes (PAGO_2_DIAS_ANTES_PENDIENTE). */

  d_2_antes_vencimiento: EstadisticasTabItem
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

  async getClientesRetrasados(): Promise<ClientesRetrasadosResponse> {
    return await apiClient.get<ClientesRetrasadosResponse>(
      `${this.baseUrl}/clientes-retrasados`,
      {
        timeout: 60000,
      }
    )
  }

  /** Cuotas PENDIENTE con vencimiento = hoy + 2 (Caracas). Submenú 2 días antes. */

  async getCuotasPendiente2DiasAntes(): Promise<{
    actualizado_en: string
    items: ClienteRetrasadoItem[]
    total: number
  }> {
    return await apiClient.get<{
      actualizado_en: string
      items: ClienteRetrasadoItem[]
      total: number
    }>(`${this.baseUrl}/cuotas-pendiente-2-dias-antes`, { timeout: 60000 })
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

  async actualizarNotificaciones(opts?: {
    signal?: AbortSignal
  }): Promise<{
    mensaje: string
    clientes_actualizados: number
  }> {
    return await apiClient.post<{
      mensaje: string
      clientes_actualizados: number
    }>(`${this.baseUrl}/actualizar`, {}, { signal: opts?.signal })
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
    estado?: string
  ): Promise<{ items: ClienteRetrasadoItem[]; total: number }> {
    const params = new URLSearchParams()

    if (estado) params.append('estado', estado)

    return await apiClient.get<{
      items: ClienteRetrasadoItem[]
      total: number
    }>(
      `${API_V1}/notificaciones-prejudicial/?${params}`,

      { timeout: 120000 }
    )
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
  }): Promise<{
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
      `${API_V1}/notificaciones-prejudicial/enviar`,

      {},

      { timeout: 120000, signal: opts?.signal }
    )
  }

  async enviarNotificacionesMasivos(opts?: {
    signal?: AbortSignal
  }): Promise<{
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
    opts?: { signal?: AbortSignal }
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
    return await apiClient.post(
      `${this.baseUrl}/enviar-caso-manual`,
      { tipo },
      { timeout: 180000, signal: opts?.signal }
    )
  }

  /** Ultimo resumen persistido tras enviar-todas o job 01:00 (sin depender solo de logs). */

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
    opts?: { servicio?: string; tipo_tab?: string }
  ): Promise<any> {
    const params: Record<string, string> = {}

    if (emailDestino) params.email_destino = emailDestino

    if (subject) params.subject = subject

    if (mensaje) params.mensaje = mensaje

    if (emailCC) params.email_cc = emailCC

    if (opts?.servicio) params.servicio = opts.servicio

    if (opts?.tipo_tab) params.tipo_tab = opts.tipo_tab

    return await apiClient.post(`${this.baseUrl}/email/probar`, params)
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
