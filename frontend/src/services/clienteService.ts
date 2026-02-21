import { apiClient, ApiResponse, PaginatedResponse, buildUrl } from './api'
import { Cliente, ClienteForm, ClienteFilters } from '../types'
import { logger } from '../utils/logger'

// Constantes de configuración
const DEFAULT_PER_PAGE = 20

class ClienteService {
  private baseUrl = '/api/v1/clientes'

  // Obtener lista de clientes con filtros y paginación
  async getClientes(
    filters?: ClienteFilters,
    page: number = 1,
    perPage: number = DEFAULT_PER_PAGE
  ): Promise<PaginatedResponse<Cliente>> {
    const params = { ...filters, page, per_page: perPage }
    const url = buildUrl(this.baseUrl, params)

    const response = await apiClient.get<any>(url)

    // Adaptar respuesta del backend al formato esperado
    // ✅ CORRECCIÓN: Asegurar que data siempre sea un array
    const clientesArray = Array.isArray(response.clientes) 
      ? response.clientes 
      : (response.clientes ? [response.clientes] : [])
    
    const adaptedResponse = {
      data: clientesArray,
      total: response.total || 0,
      page: response.page || page,
      per_page: response.per_page || response.limit || perPage,
      total_pages: response.total_pages || Math.ceil((response.total || 0) / perPage)
    }

    return adaptedResponse
  }

  // Obtener cliente por ID
  async getCliente(id: string): Promise<Cliente> {
    // El endpoint devuelve ClienteResponse directamente, sin envolver en ApiResponse
    const response = await apiClient.get<Cliente>(`${this.baseUrl}/${id}`)
    return response
  }

  // Obtener estados de cliente desde BD (para dropdowns en formularios)
  async getEstadosCliente(): Promise<{ estados: Array<{ valor: string; etiqueta: string; orden: number }> }> {
    return await apiClient.get(`${this.baseUrl}/estados`)
  }

  // Comprobar qué cédulas ya existen (para carga masiva: advertir antes de guardar)
  async checkCedulas(cedulas: string[]): Promise<{ existing_cedulas: string[] }> {
    if (!cedulas.length) return { existing_cedulas: [] }
    const response = await apiClient.post<{ existing_cedulas: string[] }>(
      `${this.baseUrl}/check-cedulas`,
      { cedulas }
    )
    return response
  }

  // Crear nuevo cliente
  async createCliente(data: ClienteForm): Promise<Cliente> {
    // El endpoint devuelve ClienteResponse directamente
    const response = await apiClient.post<Cliente>(this.baseUrl, data)
    return response
  }


  // Actualizar cliente
  async updateCliente(id: string, data: Partial<ClienteForm>): Promise<Cliente> {
    // El endpoint devuelve ClienteResponse directamente
    const response = await apiClient.put<Cliente>(`${this.baseUrl}/${id}`, data)
    return response
  }

  // Eliminar cliente
  async deleteCliente(id: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  // Obtener cliente por cédula exacta (para carga masiva de préstamos)
  async getClienteByCedula(cedula: string): Promise<Cliente | null> {
    if (!cedula?.trim()) return null
    const list = await this.searchClientes(cedula.trim(), true)
    const exact = list.find((c) => (c.cedula || '').trim().toUpperCase() === cedula.trim().toUpperCase())
    return exact ?? null
  }

  // Buscar clientes por término (usando filtros en endpoint principal)
  // IMPORTANTE: Por defecto filtra solo clientes ACTIVOS para formularios de préstamos
  // Para buscar todos los estados, pasar incluirTodosEstados: true
  async searchClientes(query: string, incluirTodosEstados: boolean = false): Promise<Cliente[]> {
    const filters: ClienteFilters = { search: query }
    // Por defecto filtrar solo ACTIVOS (para formularios de préstamos)
    // Solo incluir todos los estados si se especifica explícitamente
    if (!incluirTodosEstados) {
      filters.estado = 'ACTIVO'
    }
    const response = await this.getClientes(filters, 1, 100)
    return response.data
  }

  // Obtener clientes por analista (usando filtros en endpoint principal)
  async getClientesByAnalista(analistaId: string): Promise<Cliente[]> {
    const filters: ClienteFilters = {}
    const response = await this.getClientes(filters, 1, 100)
    return response.data
  }

  // Obtener clientes en mora (usando filtro estado en endpoint principal)
  async getClientesEnMora(): Promise<Cliente[]> {
    const filters: ClienteFilters = { estado: 'MORA' }
    const response = await this.getClientes(filters, 1, 100)
    return response.data
  }

  // Obtener historial de pagos de un cliente
  async getHistorialPagos(clienteId: string): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>(`${this.baseUrl}/${clienteId}/pagos`)
    return response.data
  }

  // Obtener tabla de amortización de un cliente
  async getTablaAmortizacion(clienteId: string): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>(`${this.baseUrl}/${clienteId}/amortizacion`)
    return response.data
  }

  // Validar cédula
  async validateCedula(cedula: string): Promise<{ valid: boolean; message?: string }> {
    const response = await apiClient.post<ApiResponse<{ valid: boolean; message?: string }>>(
      `${this.baseUrl}/validate-cedula`,
      { cedula }
    )
    return response.data
  }

  // Obtener estadísticas de cliente
  async getEstadisticasCliente(clienteId: string): Promise<any> {
    const response = await apiClient.get<ApiResponse<any>>(`${this.baseUrl}/${clienteId}/estadisticas`)
    return response.data
  }

  // Obtener estadísticas generales de todos los clientes
  async getStats(): Promise<{ total: number; activos: number; inactivos: number; finalizados: number }> {
    const response = await apiClient.get<{ total: number; activos: number; inactivos: number; finalizados: number }>(
      `${this.baseUrl}/stats`
    )
    return response
  }

  // Obtener estadísticas del embudo de clientes
  // NOTA: El backend no tiene /embudo/estadisticas; se calculan desde stats de clientes
  async getEstadisticasEmbudo(): Promise<{ total: number; prospectos: number; evaluacion: number; aprobados: number; rechazados: number }> {
    try {
      const stats = await this.getStats()
      return {
        total: stats.total,
        prospectos: stats.activos,
        evaluacion: stats.inactivos,
        aprobados: stats.finalizados,
        rechazados: 0,
      }
    } catch {
      return { total: 0, prospectos: 0, evaluacion: 0, aprobados: 0, rechazados: 0 }
    }
  }

  // Cambiar estado de cliente (el backend devuelve Cliente directamente, no envuelto en ApiResponse)
  async cambiarEstado(clienteId: string, estado: Cliente['estado']): Promise<Cliente> {
    const response = await apiClient.patch<Cliente>(
      `${this.baseUrl}/${clienteId}/estado`,
      { estado }
    )
    return response
  }

  // Asignar analista a cliente (FUNCIÓN OBSOLETA - eliminado)
  async asignarAsesor(clienteId: string, analistaId: string): Promise<Cliente> {
    // Función eliminada - ya no se asignan analistas a clientes
    throw new Error('La asignación de analistas a clientes ha sido eliminada')
  }

  // Exportar clientes (usando endpoint de carga masiva)
  async exportarClientes(filters?: ClienteFilters, format: 'excel' | 'pdf' = 'excel'): Promise<void> {
    // TODO: Implementar cuando esté disponible el endpoint de exportación
    logger.warn('Exportación de clientes no implementada aún', {
      action: 'export_clientes',
      service: 'ClienteService',
      method: 'exportClientes'
    })
    throw new Error('Exportación de clientes no disponible')
  }

  // Importar clientes desde Excel (usando endpoint de carga masiva)
  async importarClientes(file: File): Promise<{ success: number; errors: any[] }> {
    const response = await apiClient.uploadFile<ApiResponse<{ success: number; errors: any[] }>>(
      '/api/v1/carga-masiva/clientes',
      file
    )
    return response.data
  }

  // Buscar cliente por número de teléfono
  async buscarClientePorTelefono(telefono: string): Promise<Cliente | null> {
    try {
      const filters: ClienteFilters = { search: telefono }
      const response = await this.getClientes(filters, 1, 1)
      return response.data.length > 0 ? response.data[0] : null
    } catch (error) {
      logger.error('Error buscando cliente por teléfono', { error, telefono })
      return null
    }
  }

  // Obtener clientes con problemas de validación (usa /casos-a-revisar del backend)
  async getClientesConProblemasValidacion(
    page: number = 1,
    perPage: number = 20
  ): Promise<PaginatedResponse<any>> {
    return this.getCasosARevisar(page, perPage)
  }

  // Obtener clientes con valores por defecto (legacy - usar getCasosARevisar)
  async getClientesValoresPorDefecto(
    page: number = 1,
    perPage: number = 20
  ): Promise<PaginatedResponse<Cliente>> {
    return this.getCasosARevisar(page, perPage)
  }

  // Obtener casos a revisar (clientes con placeholders: Z999999999, Revisar Nombres, +589999999999, revisar@email.com)
  async getCasosARevisar(
    page: number = 1,
    perPage: number = 50
  ): Promise<PaginatedResponse<Cliente>> {
    const url = buildUrl(`${this.baseUrl}/casos-a-revisar`, { page, per_page: perPage })
    const response = await apiClient.get<any>(url)
    return {
      data: response.clientes || [],
      total: response.total || 0,
      page: response.page || page,
      per_page: response.per_page || perPage,
      total_pages: response.total_pages || Math.ceil((response.total || 0) / perPage)
    }
  }

  // Exportar clientes con valores por defecto (genera CSV desde casos-a-revisar)
  async exportarValoresPorDefecto(formato: 'csv' | 'excel' = 'csv'): Promise<Blob> {
    const res = await this.getCasosARevisar(1, 2000)
    const clientes = res.data || []
    const headers = ['id', 'cedula', 'nombres', 'telefono', 'email', 'direccion', 'ocupacion', 'estado', 'fecha_registro']
    const rows = clientes.map((c: any) =>
      headers.map((h) => {
        const v = c[h]
        const s = v == null ? '' : String(v)
        return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s
      }).join(',')
    )
    const csv = [headers.join(','), ...rows].join('\n')
    return new Blob([csv], { type: 'text/csv;charset=utf-8' })
  }

  // Actualizar múltiples clientes en lote
  async actualizarClientesLote(actualizaciones: Array<{ id: number; [key: string]: any }>): Promise<{
    actualizados: number
    errores: Array<{ id: number | null; error: string }>
    total_procesados: number
  }> {
    const response = await apiClient.post<any>(`${this.baseUrl}/actualizar-lote`, actualizaciones)
    return response
  }
}

// Instancia singleton del servicio
export const clienteService = new ClienteService()
