import { apiClient, ApiResponse, PaginatedResponse, buildUrl } from './api'
import { Prestamo, PrestamoForm } from '@/types'
import { logger } from '@/utils/logger'

// Constantes de configuración
const DEFAULT_PER_PAGE = 20

class PrestamoService {
  private baseUrl = '/api/v1/prestamos'

  // Obtener lista de préstamos con filtros y paginación
  async getPrestamos(
    filters?: { search?: string; estado?: string },
    page: number = 1,
    perPage: number = DEFAULT_PER_PAGE
  ): Promise<PaginatedResponse<Prestamo>> {
    const params = { ...filters, page, per_page: perPage }
    const url = buildUrl(this.baseUrl, params)
    
    const response = await apiClient.get<any>(url)
    
    // Adaptar respuesta del backend al formato esperado
    return {
      data: response.data || [],
      total: response.total || 0,
      page: response.page || page,
      per_page: response.per_page || perPage,
      total_pages: response.total_pages || Math.ceil((response.total || 0) / perPage)
    }
  }

  // Obtener préstamo por ID
  async getPrestamo(id: number): Promise<Prestamo> {
    const response = await apiClient.get<ApiResponse<Prestamo>>(`${this.baseUrl}/${id}`)
    return response.data
  }

  // Crear nuevo préstamo
  async createPrestamo(data: PrestamoForm): Promise<Prestamo> {
    const response = await apiClient.post<ApiResponse<Prestamo>>(this.baseUrl, data)
    return response.data
  }

  // Actualizar préstamo
  async updatePrestamo(id: number, data: Partial<PrestamoForm>): Promise<Prestamo> {
    const response = await apiClient.put<ApiResponse<Prestamo>>(`${this.baseUrl}/${id}`, data)
    return response.data
  }

  // Buscar préstamos por cédula
  async getPrestamosByCedula(cedula: string): Promise<Prestamo[]> {
    const response = await apiClient.get<ApiResponse<Prestamo[]>>(`${this.baseUrl}/cedula/${cedula}`)
    return response.data
  }

  // Obtener historial de auditoría de un préstamo
  async getAuditoria(prestamoId: number): Promise<any[]> {
    const response = await apiClient.get<any[]>(`${this.baseUrl}/auditoria/${prestamoId}`)
    return response
  }

  // Eliminar préstamo (solo Admin)
  async deletePrestamo(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  // Búsqueda general
  async searchPrestamos(query: string): Promise<Prestamo[]> {
    const response = await apiClient.get<Prestamo[]>(
      buildUrl(this.baseUrl, { search: query })
    )
    return response
  }
}

export const prestamoService = new PrestamoService()
logger.info('Servicio de préstamos inicializado')
