import { apiClient } from '@/services/api'

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
  email_activo?: string | boolean // ✅ Estado activo/inactivo
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

class NotificacionService {
  private baseUrl = '/api/v1/notificaciones'

  // Plantillas
  async listarPlantillas(tipo?: string, soloActivas = true): Promise<NotificacionPlantilla[]> {
    const params = new URLSearchParams()
    if (tipo) params.append('tipo', tipo)
    params.append('solo_activas', String(soloActivas))
    
    return await apiClient.get<NotificacionPlantilla[]>(`${this.baseUrl}/plantillas?${params}`)
  }

  async obtenerPlantilla(id: number): Promise<NotificacionPlantilla> {
    return await apiClient.get<NotificacionPlantilla>(`${this.baseUrl}/plantillas/${id}`)
  }

  async crearPlantilla(data: Partial<NotificacionPlantilla>): Promise<NotificacionPlantilla> {
    return await apiClient.post<NotificacionPlantilla>(`${this.baseUrl}/plantillas`, data)
  }

  async actualizarPlantilla(id: number, data: Partial<NotificacionPlantilla>): Promise<NotificacionPlantilla> {
    return await apiClient.put<NotificacionPlantilla>(`${this.baseUrl}/plantillas/${id}`, data)
  }

  async eliminarPlantilla(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/plantillas/${id}`)
  }

  async exportarPlantilla(id: number): Promise<NotificacionPlantilla> {
    return await apiClient.get<NotificacionPlantilla>(`${this.baseUrl}/plantillas/${id}/export`)
  }

  async enviarConPlantilla(plantillaId: number, params: { cliente_id: number, variables: Record<string, any> }): Promise<any> {
    const query = new URLSearchParams({ cliente_id: String(params.cliente_id) })
    return await apiClient.post(`${this.baseUrl}/plantillas/${plantillaId}/enviar?${query}`, params.variables)
  }

  // Notificaciones
  async listarNotificaciones(page = 1, per_page = 20, estado?: string, canal?: string): Promise<{ items: Notificacion[], total: number, page: number, page_size: number, total_pages: number }> {
    const params = new URLSearchParams()
    params.append('page', String(page))
    params.append('per_page', String(per_page))
    if (estado) params.append('estado', estado)
    if (canal) params.append('canal', canal)
    
    return await apiClient.get<{ items: Notificacion[], total: number, page: number, page_size: number, total_pages: number }>(`${this.baseUrl}/?${params}`)
  }

  async obtenerEstadisticas(): Promise<NotificacionStats> {
    return await apiClient.get<NotificacionStats>(`${this.baseUrl}/estadisticas/resumen`)
  }

  // Notificaciones automáticas
  async procesarAutomaticas(): Promise<{ mensaje: string, estadisticas: any }> {
    return await apiClient.post(`${this.baseUrl}/automaticas/procesar`)
  }

  // Notificaciones previas
  async listarNotificacionesPrevias(estado?: string): Promise<{ items: any[], total: number, dias_5: number, dias_3: number, dias_1: number }> {
    const params = new URLSearchParams()
    if (estado) params.append('estado', estado)
    
    // Usar timeout extendido para este endpoint que puede tardar más
    return await apiClient.get<{ items: any[], total: number, dias_5: number, dias_3: number, dias_1: number }>(
      `/api/v1/notificaciones-previas/?${params}`,
      { timeout: 120000 } // 2 minutos de timeout
    )
  }

  async listarNotificacionesRetrasadas(estado?: string): Promise<{ items: any[], total: number, dias_1: number, dias_3: number, dias_5: number }> {
    const params = new URLSearchParams()
    if (estado) params.append('estado', estado)
    
    return await apiClient.get<{ items: any[], total: number, dias_1: number, dias_3: number, dias_5: number }>(
      `/api/v1/notificaciones-retrasadas/?${params}`,
      { timeout: 120000 } // 2 minutos de timeout
    )
  }

  async listarNotificacionesPrejudiciales(estado?: string): Promise<{ items: any[], total: number }> {
    const params = new URLSearchParams()
    if (estado) params.append('estado', estado)
    
    return await apiClient.get<{ items: any[], total: number }>(
      `/api/v1/notificaciones-prejudicial/?${params}`,
      { timeout: 120000 } // 2 minutos de timeout
    )
  }

  async listarNotificacionesDiaPago(estado?: string): Promise<{ items: any[], total: number }> {
    const params = new URLSearchParams()
    if (estado) params.append('estado', estado)
    
    return await apiClient.get<{ items: any[], total: number }>(
      `/api/v1/notificaciones-dia-pago/?${params}`,
      { timeout: 120000 } // 2 minutos de timeout
    )
  }

  // Variables de notificaciones
  async listarVariables(activa?: boolean): Promise<NotificacionVariable[]> {
    const params = new URLSearchParams()
    if (activa !== undefined) params.append('activa', String(activa))
    
    return await apiClient.get<NotificacionVariable[]>(`${this.baseUrl}/variables?${params}`)
  }

  async obtenerVariable(id: number): Promise<NotificacionVariable> {
    return await apiClient.get<NotificacionVariable>(`${this.baseUrl}/variables/${id}`)
  }

  async crearVariable(data: Partial<NotificacionVariable>): Promise<NotificacionVariable> {
    return await apiClient.post<NotificacionVariable>(`${this.baseUrl}/variables`, data)
  }

  async actualizarVariable(id: number, data: Partial<NotificacionVariable>): Promise<NotificacionVariable> {
    return await apiClient.put<NotificacionVariable>(`${this.baseUrl}/variables/${id}`, data)
  }

  async eliminarVariable(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/variables/${id}`)
  }

  async inicializarVariablesPrecargadas(): Promise<{ mensaje: string, variables_creadas: number, variables_existentes: number, total: number }> {
    return await apiClient.post<{ mensaje: string, variables_creadas: number, variables_existentes: number, total: number }>(
      `${this.baseUrl}/variables/inicializar-precargadas`
    )
  }
}

class EmailConfigService {
  private baseUrl = '/api/v1/configuracion'

  async obtenerConfiguracionEmail(): Promise<EmailConfig> {
    return await apiClient.get<EmailConfig>(`${this.baseUrl}/email/configuracion`)
  }

  async actualizarConfiguracionEmail(config: Partial<EmailConfig>): Promise<any> {
    console.log('📤 [EmailConfigService] Enviando PUT a:', `${this.baseUrl}/email/configuracion`)
    console.log('📤 [EmailConfigService] Datos a enviar:', {
      ...config,
      smtp_password: config.smtp_password ? '***' : '(vacío)'
    })
    
    try {
      // Usar timeout extendido para validación SMTP (puede tardar hasta 10-15 segundos)
      const resultado = await apiClient.put(
        `${this.baseUrl}/email/configuracion`, 
        config,
        { timeout: 60000 } // 60 segundos para permitir validación SMTP
      )
      console.log('✅ [EmailConfigService] Respuesta exitosa:', resultado)
      return resultado
    } catch (error) {
      console.error('❌ [EmailConfigService] Error en PUT:', error)
      throw error
    }
  }

  async probarConfiguracionEmail(emailDestino?: string, subject?: string, mensaje?: string): Promise<any> {
    const params: any = {}
    if (emailDestino) params.email_destino = emailDestino
    if (subject) params.subject = subject
    if (mensaje) params.mensaje = mensaje
    return await apiClient.post(`${this.baseUrl}/email/probar`, params)
  }

  async obtenerConfiguracionEnvios(): Promise<Record<string, { habilitado: boolean, cco: string[] }>> {
    return await apiClient.get<Record<string, { habilitado: boolean, cco: string[] }>>(`${this.baseUrl}/notificaciones/envios`)
  }

  async actualizarConfiguracionEnvios(config: Record<string, { habilitado: boolean, cco: string[] }>): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/notificaciones/envios`, config)
  }

  async verificarEstadoConfiguracionEmail(): Promise<{
    configurada: boolean
    mensaje: string
    configuraciones: Record<string, any>
    problemas: string[]
    conexion_smtp?: { success: boolean, message?: string }
    modo_pruebas: boolean
    email_pruebas?: string | null
  }> {
    return await apiClient.get(`${this.baseUrl}/email/estado`)
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
    return await apiClient.get<WhatsAppConfig>(`${this.baseUrl}/whatsapp/configuracion`)
  }

  async actualizarConfiguracionWhatsApp(config: Partial<WhatsAppConfig>): Promise<any> {
    console.log('📤 [WhatsAppConfigService] Enviando PUT a:', `${this.baseUrl}/whatsapp/configuracion`)
    console.log('📤 [WhatsAppConfigService] Datos a enviar:', {
      ...config,
      access_token: config.access_token ? '***' : '(vacío)'
    })
    
    try {
      const resultado = await apiClient.put(`${this.baseUrl}/whatsapp/configuracion`, config)
      console.log('✅ [WhatsAppConfigService] Respuesta exitosa:', resultado)
      return resultado
    } catch (error) {
      console.error('❌ [WhatsAppConfigService] Error en PUT:', error)
      throw error
    }
  }

  async probarConfiguracionWhatsApp(telefonoDestino?: string, mensaje?: string): Promise<any> {
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

