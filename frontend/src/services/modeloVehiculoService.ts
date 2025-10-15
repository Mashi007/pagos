import { apiClient, ApiResponse } from './api'

export interface ModeloVehiculo {
  id: number
  modelo: string
  activo: boolean
  created_at: string
  updated_at?: string
}

export interface ModeloVehiculoCreate {
  modelo: string
  activo?: boolean
}

export interface ModeloVehiculoUpdate {
  modelo?: string
  activo?: boolean
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
    return await apiClient.get<ModeloVehiculoListResponse>(this.baseUrl, { params })
  }

  // Listar solo modelos activos (para formularios)
  async listarModelosActivos(): Promise<ModeloVehiculo[]> {
    return await apiClient.get<ModeloVehiculo[]>(`${this.baseUrl}/activos`)
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
}

export const modeloVehiculoService = new ModeloVehiculoService()
