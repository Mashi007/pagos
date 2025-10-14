import { apiClient, ApiResponse } from './api'

export interface Asesor {
  id: number
  nombre: string
  apellido: string
  nombre_completo: string
  email: string
  telefono?: string
  especialidad?: string
  comision_porcentaje?: number
  activo: boolean
  notas?: string
  created_at: string
  updated_at?: string
}

export interface AsesorCreate {
  nombre: string
  apellido: string
  email: string
  telefono?: string
  especialidad?: string
  comision_porcentaje?: number
  activo?: boolean
  notas?: string
}

export interface AsesorUpdate {
  nombre?: string
  apellido?: string
  email?: string
  telefono?: string
  especialidad?: string
  comision_porcentaje?: number
  activo?: boolean
  notas?: string
}

export interface AsesorListResponse {
  items: Asesor[]
  total: number
  page: number
  size: number
  pages: number
}

class AsesorService {
  private baseUrl = '/api/v1/asesores'

  // Listar asesores con paginación y filtros
  async listarAsesores(params?: {
    skip?: number
    limit?: number
    activo?: boolean
    search?: string
    especialidad?: string
  }): Promise<AsesorListResponse> {
    return await apiClient.get<AsesorListResponse>(this.baseUrl, { params })
  }

  // Listar solo asesores activos (para formularios)
  async listarAsesoresActivos(especialidad?: string): Promise<Asesor[]> {
    const params = especialidad ? { especialidad } : undefined
    return await apiClient.get<Asesor[]>(`${this.baseUrl}/activos`, { params })
  }

  // Obtener un asesor por ID
  async obtenerAsesor(id: number): Promise<Asesor> {
    return await apiClient.get<Asesor>(`${this.baseUrl}/${id}`)
  }

  // Crear un nuevo asesor
  async crearAsesor(data: AsesorCreate): Promise<Asesor> {
    return await apiClient.post<Asesor>(this.baseUrl, data)
  }

  // Actualizar un asesor existente
  async actualizarAsesor(id: number, data: AsesorUpdate): Promise<Asesor> {
    return await apiClient.put<Asesor>(`${this.baseUrl}/${id}`, data)
  }

  // Eliminar un asesor (soft delete)
  async eliminarAsesor(id: number): Promise<{ message: string }> {
    return await apiClient.delete<{ message: string }>(`${this.baseUrl}/${id}`)
  }
}

export const asesorService = new AsesorService()
