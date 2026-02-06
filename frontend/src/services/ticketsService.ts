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
  comunicacion_email_id?: number
  estado: string
  prioridad: string
  tipo: string
  asignado_a?: string
  asignado_a_id?: number
  escalado_a_id?: number
  escalado?: boolean
  fecha_limite?: string
  archivos?: string // JSON array con rutas de archivos
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
  fecha_limite?: string // ISO format datetime
  archivos?: string // JSON array con rutas de archivos
}

export interface TicketUpdate {
  // Nota: Una vez guardado, NO se puede editar titulo/descripcion
  // Solo se pueden actualizar estos campos
  estado?: string
  prioridad?: string
  asignado_a?: string
  asignado_a_id?: number
  escalado_a_id?: number // Escalar a admin
  escalado?: boolean
  fecha_limite?: string // ISO format datetime
  archivos?: string // JSON array con rutas de archivos
}

export interface TicketsEstadisticas {
  total: number
  abiertos: number
  en_proceso: number
  resueltos: number
  cerrados: number
}

export interface TicketsResponse {
  tickets: Ticket[]
  paginacion: {
    page: number
    per_page: number
    total: number
    pages: number
  }
  /** KPI globales desde la BD (total y por estado). Presente si el backend los envía. */
  estadisticas?: TicketsEstadisticas
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

