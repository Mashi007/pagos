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
    filters?: {
      search?: string
      estado?: string
      cedula?: string
      analista?: string
      concesionario?: string
      modelo?: string
      fecha_inicio?: string
      fecha_fin?: string
      requiere_revision?: boolean
    },
    page: number = 1,
    perPage: number = DEFAULT_PER_PAGE
  ): Promise<PaginatedResponse<Prestamo>> {
    const params: any = { ...filters, page, per_page: perPage }
    // Convertir fechas a formato ISO si existen
    if (params.fecha_inicio) {
      params.fecha_inicio = params.fecha_inicio
    }
    if (params.fecha_fin) {
      params.fecha_fin = params.fecha_fin
    }
    const url = buildUrl(this.baseUrl, params)

    const response = await apiClient.get<any>(url)

    // ✅ DEBUG: Log para diagnosticar problemas
    console.log('🔍 [PrestamoService] Respuesta de getPrestamos:', {
      url,
      responseType: typeof response,
      responseKeys: response && typeof response === 'object' ? Object.keys(response) : [],
      hasData: !!response?.data,
      dataIsArray: Array.isArray(response?.data),
      dataLength: Array.isArray(response?.data) ? response.data.length : 'N/A',
      total: response?.total,
      page: response?.page,
      per_page: response?.per_page,
      total_pages: response?.total_pages,
      fullResponse: response
    })

    // Adaptar respuesta del backend al formato esperado
    const result = {
      data: response.data || [],
      total: response.total || 0,
      page: response.page || page,
      per_page: response.per_page || perPage,
      total_pages: response.total_pages || Math.ceil((response.total || 0) / perPage)
    }

    console.log('🔍 [PrestamoService] Resultado adaptado:', {
      dataLength: Array.isArray(result.data) ? result.data.length : 'N/A',
      total: result.total,
      page: result.page,
      total_pages: result.total_pages
    })

    return result
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
    
    // ✅ DEBUG: Log para diagnosticar problemas
    console.log('🔍 [PrestamoService] Respuesta de préstamos por cédula:', {
      cedula,
      responseType: Array.isArray(response) ? 'array' : typeof response,
      responseLength: Array.isArray(response) ? response.length : 'N/A',
      response: response,
      responseKeys: response && typeof response === 'object' ? Object.keys(response) : []
    })
    
    // Asegurar que siempre devolvemos un array
    if (Array.isArray(response)) {
      return response
    }
    
    // Si la respuesta es un objeto con una propiedad 'prestamos' o 'data', extraer el array
    if (response && typeof response === 'object') {
      const prestamosArray = (response as any).prestamos || (response as any).data
      if (Array.isArray(prestamosArray)) {
        return prestamosArray
      }
    }
    
    return []
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

  // Obtener KPIs de préstamos
  async getKPIs(filters?: {
    analista?: string
    concesionario?: string
    modelo?: string
    fecha_inicio?: string
    fecha_fin?: string
  }): Promise<{
    totalFinanciamiento: number
    totalPrestamos: number
    promedioMonto: number
    totalCarteraVigente: number
  }> {
    const params = filters || {}
    const url = buildUrl('/api/v1/kpis/prestamos', params)
    const response = await apiClient.get<any>(url)
    return response
  }

  // Marcar/desmarcar préstamo como requiere revisión
  async marcarRevision(prestamoId: number, requiereRevision: boolean): Promise<any> {
    const response = await apiClient.patch<any>(
      `${this.baseUrl}/${prestamoId}/marcar-revision?requiere_revision=${requiereRevision}`
    )
    return response
  }
}

export const prestamoService = new PrestamoService()
logger.info('Servicio de préstamos inicializado')
