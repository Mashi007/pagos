import { apiClient, buildUrl } from './api'

// Tipos para comunicaciones unificadas
export interface ComunicacionUnificada {
  id: number
  tipo: 'whatsapp' | 'email'
  from_contact: string
  to_contact: string
  subject?: string | null
  body: string | null
  timestamp: string
  direccion: 'INBOUND' | 'OUTBOUND'
  cliente_id: number | null
  ticket_id: number | null
  requiere_respuesta: boolean
  procesado: boolean
  respuesta_enviada: boolean
  creado_en: string
  /** Nombre del contacto (bot cobranza WhatsApp). */
  nombre_contacto?: string | null
  /** CÃ©dula capturada en el flujo de cobranza (cuando ya la enviÃ³ el usuario). */
  cedula?: string | null
  /** Estado del flujo: esperando_cedula, esperando_confirmacion, esperando_foto, etc. */
  estado_cobranza?: string | null
  /** True si ya se ha enviado al menos un mensaje (OUTBOUND) en esta conversaciÃ³n; si no, se muestra etiqueta NUEVO. */
  operado?: boolean
}

export interface PaginacionComunicaciones {
  page: number
  per_page: number
  total: number
  pages: number
}

export interface ListaComunicacionesResponse {
  comunicaciones: ComunicacionUnificada[]
  paginacion: PaginacionComunicaciones
}

/** Mensaje del historial WhatsApp (copia de la conversaciÃ³n). */
export interface MensajeWhatsappItem {
  id: number
  body: string
  direccion: 'INBOUND' | 'OUTBOUND'
  message_type: string
  timestamp: string
}

export interface ListaMensajesWhatsAppResponse {
  mensajes: MensajeWhatsappItem[]
}

export interface CrearClienteAutomaticoRequest {
  telefono?: string
  email?: string
  nombres?: string
  cedula?: string
  direccion?: string
  notas?: string
}

class ComunicacionesService {
  private baseUrl = '/api/v1/comunicaciones'

  /**
   * Listar todas las comunicaciones unificadas con filtros y paginaciÃ³n
   */
  async listarComunicaciones(
    page: number = 1,
    perPage: number = 20,
    tipo?: 'whatsapp' | 'email' | 'all',
    clienteId?: number,
    requiereRespuesta?: boolean,
    direccion?: 'INBOUND' | 'OUTBOUND'
  ): Promise<ListaComunicacionesResponse> {
    const params: any = { page, per_page: perPage }

    if (tipo) params.tipo = tipo
    if (clienteId) params.cliente_id = clienteId
    if (requiereRespuesta !== undefined) params.requiere_respuesta = requiereRespuesta
    if (direccion) params.direccion = direccion

    const url = buildUrl(this.baseUrl, params)
    const response = await apiClient.get<ListaComunicacionesResponse>(url)
    return response
  }

  /**
   * Historial de mensajes WhatsApp de una conversaciÃ³n (copia de lo hablado con el cliente).
   */
  async listarMensajesWhatsApp(telefono: string): Promise<ListaMensajesWhatsAppResponse> {
    const params = { telefono, limit: 200 }
    const url = buildUrl(`${this.baseUrl}/mensajes`, params)
    const response = await apiClient.get<ListaMensajesWhatsAppResponse>(url)
    return response
  }

  /**
   * Obtener comunicaciones que requieren respuesta
   */
  async obtenerComunicacionesPorResponder(
    page: number = 1,
    perPage: number = 20
  ): Promise<ListaComunicacionesResponse> {
    const params = { page, per_page: perPage }
    const url = buildUrl(`${this.baseUrl}/por-responder`, params)
    const response = await apiClient.get<ListaComunicacionesResponse>(url)
    return response
  }

  /**
   * Enviar mensaje de WhatsApp desde Comunicaciones (modo manual).
   * Usa ConfiguraciÃ³n > WhatsApp. Respeta modo_pruebas.
   */
  async enviarWhatsApp(toNumber: string, message: string): Promise<{
    success: boolean
    mensaje?: string
    telefono_destino?: string
  }> {
    const response = await apiClient.post<{
      success: boolean
      mensaje?: string
      telefono_destino?: string
    }>(`${this.baseUrl}/enviar-whatsapp`, {
      to_number: toNumber,
      message,
    })
    return response
  }

  /**
   * Crear cliente automÃ¡ticamente desde una comunicaciÃ³n
   */
  async crearClienteAutomatico(
    request: CrearClienteAutomaticoRequest
  ): Promise<{
    success: boolean
    cliente: {
      id: number
      cedula: string
      nombres: string
      telefono: string
      email: string
    }
  }> {
    const response = await apiClient.post<{
      success: boolean
      cliente: {
        id: number
        cedula: string
        nombres: string
        telefono: string
        email: string
      }
    }>(`${this.baseUrl}/crear-cliente-automatico`, request)
    return response
  }
}

export const comunicacionesService = new ComunicacionesService()

