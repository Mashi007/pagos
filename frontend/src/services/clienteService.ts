import { apiClient, ApiResponse, PaginatedResponse, buildUrl } from './api'
import { Cliente, ClienteForm, ClienteFilters } from '@/types'

class ClienteService {
  private baseUrl = '/api/v1/clientes'

  // Obtener lista de clientes con filtros y paginación
  async getClientes(
    filters?: ClienteFilters,
    page: number = 1,
    perPage: number = 20
  ): Promise<PaginatedResponse<Cliente>> {
    console.log('🔄 Obteniendo clientes desde endpoint real...')
    const params = { ...filters, page, per_page: perPage }
    const url = buildUrl(this.baseUrl, params)
    
    const response = await apiClient.get<any>(url)
    console.log('✅ Clientes obtenidos correctamente:', response)
    
    // Adaptar respuesta del backend al formato esperado
    return {
      data: response.clientes || [],
      total: response.total || 0,
      page: response.page || page,
      per_page: response.limit || perPage,
      total_pages: response.total_pages || Math.ceil((response.total || 0) / perPage)
    }
  }

  // Obtener cliente por ID
  async getCliente(id: string): Promise<Cliente> {
    const response = await apiClient.get<ApiResponse<Cliente>>(`${this.baseUrl}/${id}`)
    return response.data
  }

  // Crear nuevo cliente
  async createCliente(data: ClienteForm): Promise<Cliente> {
    const response = await apiClient.post<ApiResponse<Cliente>>(this.baseUrl, data)
    return response.data
  }

  // Actualizar cliente
  async updateCliente(id: string, data: Partial<ClienteForm>): Promise<Cliente> {
    const response = await apiClient.put<ApiResponse<Cliente>>(`${this.baseUrl}/${id}`, data)
    return response.data
  }

  // Eliminar cliente
  async deleteCliente(id: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  // Buscar clientes por término (usando filtros en endpoint principal)
  async searchClientes(query: string): Promise<Cliente[]> {
    const filters: ClienteFilters = { search: query }
    const response = await this.getClientes(filters, 1, 100)
    return response.data
  }

  // Obtener clientes por asesor (usando filtros en endpoint principal)
  async getClientesByAsesor(asesorId: string): Promise<Cliente[]> {
    const filters: ClienteFilters = { asesor_config_id: parseInt(asesorId) }
    const response = await this.getClientes(filters, 1, 100)
    return response.data
  }

  // Obtener clientes en mora (usando filtros en endpoint principal)
  async getClientesEnMora(): Promise<Cliente[]> {
    const filters: ClienteFilters = { estado_financiero: 'MORA' }
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

  // Cambiar estado de cliente
  async cambiarEstado(clienteId: string, estado: Cliente['estado']): Promise<Cliente> {
    const response = await apiClient.patch<ApiResponse<Cliente>>(
      `${this.baseUrl}/${clienteId}/estado`,
      { estado }
    )
    return response.data
  }

  // Asignar asesor a cliente
  async asignarAsesor(clienteId: string, asesorId: string): Promise<Cliente> {
    const response = await apiClient.patch<ApiResponse<Cliente>>(
      `${this.baseUrl}/${clienteId}/asesor`,
       { asesor_config_id: asesorId }
    )
    return response.data
  }

  // Exportar clientes (usando endpoint de carga masiva)
  async exportarClientes(filters?: ClienteFilters, format: 'excel' | 'pdf' = 'excel'): Promise<void> {
    // TODO: Implementar cuando esté disponible el endpoint de exportación
    console.warn('Exportación de clientes no implementada aún')
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
}

// Instancia singleton del servicio
export const clienteService = new ClienteService()
