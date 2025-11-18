import { apiClient } from './api'

export interface Ticket {
  id: number
  titulo: string
  descripcion: string
  cliente_id?: number
  cliente?: string
  clienteData?: {
    id: number
    nombres: string
    apellidos: string
    cedula: string
    telefono?: string
    email?: string
  }
  conversacion_whatsapp_id?: number
  estado: string
  prioridad: string
  tipo: string
  asignado_a?: string
  asignado_a_id?: number
  creado_por_id?: number
  fechaCreacion?: string
  fechaActualizacion?: string
}

export interface TicketCreate {
  titulo: string
  descripcion: string
  cliente_id?: number
  conversacion_whatsapp_id?: number
  comunicacion_email_id?: number
  estado?: string
  prioridad?: string
  tipo?: string
  asignado_a?: string
  asignado_a_id?: number
}

export interface TicketUpdate {
  titulo?: string
  descripcion?: string
  estado?: string
  prioridad?: string
  tipo?: string
  asignado_a?: string
  asignado_a_id?: number
}

export interface TicketsResponse {
  tickets: Ticket[]
  paginacion: {
    page: number
    per_page: number
    total: number
    pages: number
  }
}

class TicketsService {
  private baseUrl = '/api/v1/tickets'

  async getTickets(params?: {
    page?: number
    per_page?: number
    cliente_id?: number
    conversacion_whatsapp_id?: number
    estado?: string
    prioridad?: string
    tipo?: string
  }): Promise<TicketsResponse> {
    return apiClient.get<TicketsResponse>(this.baseUrl, { params })
  }

  async getTicket(id: number): Promise<Ticket> {
    return apiClient.get<Ticket>(`${this.baseUrl}/${id}`)
  }

  async createTicket(ticket: TicketCreate): Promise<Ticket> {
    return apiClient.post<Ticket>(this.baseUrl, ticket)
  }

  async updateTicket(id: number, ticket: TicketUpdate): Promise<Ticket> {
    return apiClient.put<Ticket>(`${this.baseUrl}/${id}`, ticket)
  }

  async getTicketsByConversacion(conversacion_id: number): Promise<Ticket[]> {
    return apiClient.get<Ticket[]>(`${this.baseUrl}/conversacion/${conversacion_id}`)
  }
}

export const ticketsService = new TicketsService()

