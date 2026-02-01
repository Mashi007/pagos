import { apiClient, ApiResponse } from './api'

export interface Analista {
  id: number
  nombre: string
  activo: boolean
  created_at: string
  updated_at?: string
}

export interface AnalistaCreate {
  nombre: string
  apellido?: string
  email?: string
  telefono?: string
  especialidad?: string
  comision_porcentaje?: number
  activo?: boolean
  notas?: string
}

export interface AnalistaUpdate {
  nombre?: string
  apellido?: string
  email?: string
  telefono?: string
  especialidad?: string
  comision_porcentaje?: number
  activo?: boolean
  notas?: string
}

export interface AnalistaListResponse {
  items: Analista[]
  total: number
  page: number
  size: number
  pages: number
}

class AnalistaService {
  private baseUrl = '/api/v1/analistas'

  // Listar analistas con paginación y filtros
  async listarAnalistas(params?: {
    skip?: number
    limit?: number
    activo?: boolean
    search?: string
    especialidad?: string
  }): Promise<AnalistaListResponse> {
    return await apiClient.get<AnalistaListResponse>(this.baseUrl, { params })
  }

  // Listar solo analistas activos (para formularios)
  async listarAnalistasActivos(especialidad?: string): Promise<Analista[]> {
    const params = especialidad ? { especialidad } : undefined
    return await apiClient.get<Analista[]>(`${this.baseUrl}/activos`, { params })
  }

  // Método alias para compatibilidad
  async getAnalistas(): Promise<Analista[]> {
    return await this.listarAnalistasActivos()
  }

  // Obtener un analista por ID
  async obtenerAnalista(id: number): Promise<Analista> {
    return await apiClient.get<Analista>(`${this.baseUrl}/${id}`)
  }

  // Crear un nuevo analista
  async crearAnalista(data: AnalistaCreate): Promise<Analista> {
    return await apiClient.post<Analista>(this.baseUrl, data)
  }

  // Actualizar un analista existente
  async actualizarAnalista(id: number, data: AnalistaUpdate): Promise<Analista> {
    return await apiClient.put<Analista>(`${this.baseUrl}/${id}`, data)
  }

  // Eliminar un analista (soft delete)
  async eliminarAnalista(id: number): Promise<{ message: string }> {
    return await apiClient.delete<{ message: string }>(`${this.baseUrl}/${id}`)
  }

  // Importación masiva desde Excel
  async importarDesdeExcel(file: File): Promise<{ message: string; creados: number; actualizados: number; errores?: string[] }> {
    const formData = new FormData()
    formData.append('archivo', file)
    return await apiClient.post(`${this.baseUrl}/importar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }
}

export const analistaService = new AnalistaService()
