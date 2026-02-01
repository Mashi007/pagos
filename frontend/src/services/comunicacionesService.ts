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
   * Listar todas las comunicaciones unificadas con filtros y paginación
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
   * Crear cliente automáticamente desde una comunicación
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

