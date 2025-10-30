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
  cliente_id: number
  tipo: string
  mensaje: string
  estado: string
  enviada_en: string | null
  created_at: string
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
  async listarNotificaciones(skip = 0, limit = 100, estado?: string): Promise<Notificacion[]> {
    const params = new URLSearchParams()
    params.append('skip', String(skip))
    params.append('limit', String(limit))
    if (estado) params.append('estado', estado)
    
    return await apiClient.get<Notificacion[]>(`${this.baseUrl}/?${params}`)
  }

  async obtenerEstadisticas(): Promise<NotificacionStats> {
    return await apiClient.get<NotificacionStats>(`${this.baseUrl}/estadisticas/resumen`)
  }

  // Notificaciones automáticas
  async procesarAutomaticas(): Promise<{ mensaje: string, estadisticas: any }> {
    return await apiClient.post(`${this.baseUrl}/automaticas/procesar`)
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

  async probarConfiguracionEmail(): Promise<any> {
    return await apiClient.post(`${this.baseUrl}/email/probar`)
  }
}

export const notificacionService = new NotificacionService()
export const emailConfigService = new EmailConfigService()

