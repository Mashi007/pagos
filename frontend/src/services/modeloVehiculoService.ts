import { apiClient, ApiResponse } from './api'

export interface ModeloVehiculo {
  id: number
  modelo: string  // ✅ CORREGIDO: campo 'modelo', no 'nombre'
  activo: boolean
  precio: number | null
  created_at: string
  updated_at?: string
  fecha_actualizacion?: string | null
  actualizado_por?: string | null
}

export interface ModeloVehiculoCreate {
  modelo: string
  activo?: boolean
  precio?: number | null  // Opcional; si no se envía o es null, no se usa para Valor Activo hasta editarlo
}

export interface ModeloVehiculoUpdate {
  modelo?: string  // ✅ CORREGIDO: campo 'modelo', no 'nombre'
  activo?: boolean
  precio?: number
}

export interface ModeloVehiculoListResponse {
  items: ModeloVehiculo[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

class ModeloVehiculoService {
  private baseUrl = '/api/v1/modelos-vehiculos'

  // Listar modelos con paginación y filtros
  async listarModelos(params?: {
    skip?: number
    limit?: number
    activo?: boolean
    search?: string
  }): Promise<ModeloVehiculoListResponse> {
    try {
      console.log('🔍 Parámetros enviados:', params)
      const response = await apiClient.get<ModeloVehiculoListResponse>(this.baseUrl, { params })
      console.log('📦 Respuesta recibida:', response)
      return response
    } catch (error) {
      console.error('❌ Error en listarModelos:', error)
      throw error
    }
  }

  // Listar solo modelos activos (para formularios)
  async listarModelosActivos(): Promise<ModeloVehiculo[]> {
    return await apiClient.get<ModeloVehiculo[]>(`${this.baseUrl}/activos`)
  }

  // Método alias para compatibilidad
  async getModelosVehiculos(): Promise<ModeloVehiculo[]> {
    return await this.listarModelosActivos()
  }

  // Obtener un modelo por ID
  async obtenerModelo(id: number): Promise<ModeloVehiculo> {
    return await apiClient.get<ModeloVehiculo>(`${this.baseUrl}/${id}`)
  }

  // Crear un nuevo modelo
  async crearModelo(data: ModeloVehiculoCreate): Promise<ModeloVehiculo> {
    return await apiClient.post<ModeloVehiculo>(this.baseUrl, data)
  }

  // Actualizar un modelo existente
  async actualizarModelo(id: number, data: ModeloVehiculoUpdate): Promise<ModeloVehiculo> {
    return await apiClient.put<ModeloVehiculo>(`${this.baseUrl}/${id}`, data)
  }

  // Eliminar un modelo (soft delete)
  async eliminarModelo(id: number): Promise<{ message: string }> {
    return await apiClient.delete<{ message: string }>(`${this.baseUrl}/${id}`)
  }

  // Importación masiva desde Excel
  async importarDesdeExcel(file: File): Promise<{ message: string; creados: number; actualizados: number }> {
    const formData = new FormData()
    formData.append('archivo', file)
    return await apiClient.post(`${this.baseUrl}/importar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }
}

export const modeloVehiculoService = new ModeloVehiculoService()
