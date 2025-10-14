import { apiClient, ApiResponse } from './api'

export interface Concesionario {
  id: number
  nombre: string
  direccion?: string
  telefono?: string
  email?: string
  responsable?: string
  activo: boolean
  created_at: string
  updated_at?: string
}

export interface ConcesionarioCreate {
  nombre: string
  direccion?: string
  telefono?: string
  email?: string
  responsable?: string
  activo?: boolean
}

export interface ConcesionarioUpdate {
  nombre?: string
  direccion?: string
  telefono?: string
  email?: string
  responsable?: string
  activo?: boolean
}

export interface ConcesionarioListResponse {
  items: Concesionario[]
  total: number
  page: number
  size: number
  pages: number
}

class ConcesionarioService {
  private baseUrl = '/api/v1/concesionarios'

  // Listar concesionarios con paginación y filtros
  async listarConcesionarios(params?: {
    skip?: number
    limit?: number
    activo?: boolean
    search?: string
  }): Promise<ConcesionarioListResponse> {
    return await apiClient.get<ConcesionarioListResponse>(this.baseUrl, { params })
  }

  // Listar solo concesionarios activos (para formularios)
  async listarConcesionariosActivos(): Promise<Concesionario[]> {
    return await apiClient.get<Concesionario[]>(`${this.baseUrl}/activos`)
  }

  // Obtener un concesionario por ID
  async obtenerConcesionario(id: number): Promise<Concesionario> {
    return await apiClient.get<Concesionario>(`${this.baseUrl}/${id}`)
  }

  // Crear un nuevo concesionario
  async crearConcesionario(data: ConcesionarioCreate): Promise<Concesionario> {
    return await apiClient.post<Concesionario>(this.baseUrl, data)
  }

  // Actualizar un concesionario existente
  async actualizarConcesionario(id: number, data: ConcesionarioUpdate): Promise<Concesionario> {
    return await apiClient.put<Concesionario>(`${this.baseUrl}/${id}`, data)
  }

  // Eliminar un concesionario (soft delete)
  async eliminarConcesionario(id: number): Promise<{ message: string }> {
    return await apiClient.delete<{ message: string }>(`${this.baseUrl}/${id}`)
  }
}

export const concesionarioService = new ConcesionarioService()
