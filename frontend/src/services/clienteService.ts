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
    const params = {
      ...filters,
      page,
      per_page: perPage,
    }
    
    const url = buildUrl(this.baseUrl, params)
    return apiClient.get<PaginatedResponse<Cliente>>(url)
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

  // Buscar clientes por término
  async searchClientes(query: string): Promise<Cliente[]> {
    const response = await apiClient.get<ApiResponse<Cliente[]>>(`${this.baseUrl}/search`, {
      params: { q: query }
    })
    return response.data
  }

  // Obtener clientes por asesor
  async getClientesByAsesor(asesorId: string): Promise<Cliente[]> {
    const response = await apiClient.get<ApiResponse<Cliente[]>>(`${this.baseUrl}/asesor/${asesorId}`)
    return response.data
  }

  // Obtener clientes en mora
  async getClientesEnMora(): Promise<Cliente[]> {
    const response = await apiClient.get<ApiResponse<Cliente[]>>(`${this.baseUrl}/mora`)
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
      { asesor_id: asesorId }
    )
    return response.data
  }

  // Exportar clientes
  async exportarClientes(filters?: ClienteFilters, format: 'excel' | 'pdf' = 'excel'): Promise<void> {
    const params = { ...filters, format }
    const url = buildUrl(`${this.baseUrl}/export`, params)
    
    await apiClient.downloadFile(url, `clientes.${format}`)
  }

  // Importar clientes desde Excel
  async importarClientes(file: File): Promise<{ success: number; errors: any[] }> {
    const response = await apiClient.uploadFile<ApiResponse<{ success: number; errors: any[] }>>(
      `${this.baseUrl}/import`,
      file
    )
    return response.data
  }
}

// Instancia singleton del servicio
export const clienteService = new ClienteService()
