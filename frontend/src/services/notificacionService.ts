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
  async listarNotificaciones(page = 1, per_page = 20, estado?: string): Promise<{ items: Notificacion[], total: number, page: number, page_size: number, total_pages: number }> {
    const params = new URLSearchParams()
    params.append('page', String(page))
    params.append('per_page', String(per_page))
    if (estado) params.append('estado', estado)
    
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
    return await apiClient.put(`${this.baseUrl}/email/configuracion`, config)
  }

  async probarConfiguracionEmail(emailDestino?: string): Promise<any> {
    const params = emailDestino ? { email_destino: emailDestino } : {}
    return await apiClient.post(`${this.baseUrl}/email/probar`, params)
  }

  async obtenerConfiguracionEnvios(): Promise<Record<string, { habilitado: boolean, cco: string[] }>> {
    return await apiClient.get<Record<string, { habilitado: boolean, cco: string[] }>>(`${this.baseUrl}/notificaciones/envios`)
  }

  async actualizarConfiguracionEnvios(config: Record<string, { habilitado: boolean, cco: string[] }>): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/notificaciones/envios`, config)
  }
}

export const notificacionService = new NotificacionService()
export const emailConfigService = new EmailConfigService()

