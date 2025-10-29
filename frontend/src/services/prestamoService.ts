import { apiClient, ApiResponse, PaginatedResponse, buildUrl } from './api'
import { Prestamo, PrestamoForm } from '@/types'
import { logger } from '@/utils/logger'

// Constantes de configuración
const DEFAULT_PER_PAGE = 20

// Tipo para el resumen de préstamos
type ResumenPrestamos = {
  tiene_prestamos: boolean
  total_prestamos: number
  total_saldo_pendiente?: number
  total_cuotas_mora?: number
  prestamos?: Array<{
    id: number
    modelo_vehiculo: string
    total_financiamiento: number
    saldo_pendiente: number
    cuotas_en_mora: number
    estado: string
    fecha_registro: string | null
  }>
}

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
    // El endpoint devuelve directamente una lista, no envuelta en ApiResponse
    const response = await apiClient.get<Prestamo[]>(`${this.baseUrl}/cedula/${cedula}`)
    return response || []
  }

  // Obtener resumen de préstamos por cédula (saldo, mora, etc.)
  async getResumenPrestamos(cedula: string): Promise<ResumenPrestamos> {
    const response = await apiClient.get<ResumenPrestamos>(`${this.baseUrl}/cedula/${cedula}/resumen`)
    return response
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

  // Evaluar riesgo de un préstamo
  async evaluarRiesgo(prestamoId: number, datos: any): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/evaluar-riesgo`,
      datos
    )
    return response
  }

  // Obtener cuotas (tabla de amortización) de un préstamo
  async getCuotasPrestamo(prestamoId: number): Promise<any[]> {
    const response = await apiClient.get<any[]>(`${this.baseUrl}/${prestamoId}/cuotas`)
    return response
  }

  // Generar tabla de amortización
  async generarAmortizacion(prestamoId: number): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/generar-amortizacion`
    )
    return response
  }

  // Aplicar condiciones de aprobación
  async aplicarCondicionesAprobacion(prestamoId: number, condiciones: any): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/aplicar-condiciones-aprobacion`,
      condiciones
    )
    return response
  }
}

export const prestamoService = new PrestamoService()
logger.info('Servicio de préstamos inicializado')
