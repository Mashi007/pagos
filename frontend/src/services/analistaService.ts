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
    const endpoints = [
      this.baseUrl,                    // Endpoint principal
      `${this.baseUrl}/backup1`,       // Respaldo 1 con cache
      `${this.baseUrl}/backup2`,       // Respaldo 2 simple
      `${this.baseUrl}/emergency`,     // Emergencia
      `${this.baseUrl}/test-no-auth`   // Test sin auth
    ]
    
    let lastError: any = null
    
    for (const endpoint of endpoints) {
      try {
        console.log(`Intentando endpoint: ${endpoint}`)
        const result = await apiClient.get<AnalistaListResponse>(endpoint, { params })
        console.log(`✅ Éxito con endpoint: ${endpoint}`)
        return result
      } catch (error) {
        console.warn(`❌ Falló endpoint ${endpoint}:`, error)
        lastError = error
        
        // Si es un error 503, esperar un poco antes del siguiente intento
        if ((error as any)?.response?.status === 503) {
          console.log('Esperando 2 segundos antes del siguiente intento...')
          await new Promise(resolve => setTimeout(resolve, 2000))
        }
      }
    }
    
    // Si todos los endpoints fallan, lanzar el último error
    throw lastError || new Error('Todos los endpoints de analistas fallaron')
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
    return await apiClient.post<Analista>(`${this.baseUrl}/crear`, data)
  }

  // Actualizar un analista existente
  async actualizarAnalista(id: number, data: AnalistaUpdate): Promise<Analista> {
    return await apiClient.put<Analista>(`${this.baseUrl}/${id}`, data)
  }

  // Eliminar un analista (soft delete)
  async eliminarAnalista(id: number): Promise<{ message: string }> {
    return await apiClient.delete<{ message: string }>(`${this.baseUrl}/${id}`)
  }
}

export const analistaService = new AnalistaService()
