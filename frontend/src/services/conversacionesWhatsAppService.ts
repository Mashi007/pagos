import { apiClient, buildUrl } from './api'

// Tipos para conversaciones de WhatsApp
export interface ConversacionWhatsApp {
  id: number
  message_id: string | null
  from_number: string
  to_number: string
  message_type: string
  body: string | null
  timestamp: string
  direccion: 'INBOUND' | 'OUTBOUND'
  cliente_id: number | null
  procesado: boolean
  respuesta_enviada: boolean
  respuesta_id: number | null
  respuesta_bot: string | null
  respuesta_meta_id: string | null
  error: string | null
  creado_en: string
  actualizado_en: string
}

export interface PaginacionConversaciones {
  page: number
  per_page: number
  total: number
  pages: number
}

export interface ListaConversacionesResponse {
  conversaciones: ConversacionWhatsApp[]
  paginacion: PaginacionConversaciones
}

export interface ConversacionResponse {
  conversacion: ConversacionWhatsApp
}

export interface EstadisticasConversaciones {
  total: number
  inbound: number
  outbound: number
  con_cliente: number
  sin_cliente: number
  respuestas_enviadas: number
  ultimas_24h: number
}

export interface FiltrosConversaciones {
  cliente_id?: number
  from_number?: string
  direccion?: 'INBOUND' | 'OUTBOUND'
}

class ConversacionesWhatsAppService {
  private baseUrl = '/api/v1/conversaciones-whatsapp'

  /**
   * Listar todas las conversaciones con filtros y paginación
   */
  async listarConversaciones(
    page: number = 1,
    perPage: number = 20,
    filtros?: FiltrosConversaciones
  ): Promise<ListaConversacionesResponse> {
    const params: any = { page, per_page: perPage }

    if (filtros?.cliente_id) {
      params.cliente_id = filtros.cliente_id
    }
    if (filtros?.from_number) {
      params.from_number = filtros.from_number
    }
    if (filtros?.direccion) {
      params.direccion = filtros.direccion
    }

    const url = buildUrl(this.baseUrl, params)
    const response = await apiClient.get<ListaConversacionesResponse>(url)
    return response
  }

  /**
   * Obtener una conversación específica por ID
   */
  async obtenerConversacion(conversacionId: number): Promise<ConversacionWhatsApp> {
    const response = await apiClient.get<ConversacionResponse>(
      `${this.baseUrl}/${conversacionId}`
    )
    return response.conversacion
  }

  /**
   * Obtener todas las conversaciones de un cliente específico
   */
  async obtenerConversacionesCliente(
    clienteId: number,
    page: number = 1,
    perPage: number = 50
  ): Promise<ListaConversacionesResponse> {
    const params = { page, per_page: perPage }
    const url = buildUrl(`${this.baseUrl}/cliente/${clienteId}`, params)
    const response = await apiClient.get<ListaConversacionesResponse>(url)
    return response
  }

  /**
   * Obtener todas las conversaciones de un número de teléfono
   */
  async obtenerConversacionesNumero(
    numero: string,
    page: number = 1,
    perPage: number = 50
  ): Promise<ListaConversacionesResponse> {
    const params = { page, per_page: perPage }
    const url = buildUrl(`${this.baseUrl}/numero/${numero}`, params)
    const response = await apiClient.get<ListaConversacionesResponse>(url)
    return response
  }

  /**
   * Obtener estadísticas de conversaciones
   */
  async obtenerEstadisticas(): Promise<EstadisticasConversaciones> {
    const response = await apiClient.get<EstadisticasConversaciones>(
      `${this.baseUrl}/estadisticas`
    )
    return response
  }

  /**
   * Enviar mensaje de WhatsApp desde el CRM
   */
  async enviarMensaje(
    toNumber: string,
    message: string,
    clienteId?: number
  ): Promise<{
    success: boolean
    conversacion: ConversacionWhatsApp
    cliente_encontrado: boolean
    cliente_id: number | null
    message_id: string | null
  }> {
    const response = await apiClient.post<{
      success: boolean
      conversacion: ConversacionWhatsApp
      cliente_encontrado: boolean
      cliente_id: number | null
      message_id: string | null
    }>(`${this.baseUrl}/enviar-mensaje`, {
      to_number: toNumber,
      message,
      cliente_id: clienteId,
    })
    return response
  }

  /**
   * Buscar cliente por número de teléfono
   */
  async buscarClientePorNumero(numero: string): Promise<{
    cliente_encontrado: boolean
    cliente: {
      id: number
      cedula: string
      nombres: string
      telefono: string
      email: string
    } | null
  }> {
    const response = await apiClient.get<{
      cliente_encontrado: boolean
      cliente: {
        id: number
        cedula: string
        nombres: string
        telefono: string
        email: string
      } | null
    }>(`${this.baseUrl}/buscar-cliente/${encodeURIComponent(numero)}`)
    return response
  }
}

export const conversacionesWhatsAppService = new ConversacionesWhatsAppService()

