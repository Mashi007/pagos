import { apiClient, ApiResponse } from './api'

export interface Auditoria {
  id: number
  usuario_id?: number
  usuario_email?: string
  accion: string
  modulo: string
  tabla: string
  registro_id?: number
  descripcion?: string
  datos_anteriores?: any
  datos_nuevos?: any
  ip_address?: string
  user_agent?: string
  resultado: string
  mensaje_error?: string
  fecha: string
}

export interface AuditoriaListResponse {
  items: Auditoria[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AuditoriaStats {
  total_acciones: number
  acciones_por_modulo: Record<string, number>
  acciones_por_usuario: Record<string, number>
  acciones_hoy: number
  acciones_esta_semana: number
  acciones_este_mes: number
}

export interface AuditoriaFilters {
  skip?: number
  limit?: number
  usuario_email?: string
  modulo?: string
  accion?: string
  fecha_desde?: string
  fecha_hasta?: string
  ordenar_por?: string
  orden?: string
}

class AuditoriaService {
  private baseUrl = '/api/v1/auditoria'

  // Listar auditoría con filtros y paginación
  async listarAuditoria(filters?: AuditoriaFilters): Promise<AuditoriaListResponse> {
    try {
      console.log('🔍 Filtros enviados:', filters)
      const response = await apiClient.get<AuditoriaListResponse>(this.baseUrl, { params: filters })
      console.log('📦 Respuesta recibida:', response)
      
      // Validar que la respuesta tenga la estructura esperada
      if (!response || typeof response !== 'object') {
        throw new Error('Respuesta inválida del servidor')
      }
      
      // Asegurar que tenga la estructura esperada
      const validResponse: AuditoriaListResponse = {
        items: response.items || [],
        total: response.total || 0,
        page: response.page || 1,
        page_size: response.page_size || 10,
        total_pages: response.total_pages || 1
      }
      
      return validResponse
    } catch (error) {
      console.error('❌ Error en listarAuditoria:', error)
      
      // Retornar respuesta vacía en caso de error
      return {
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 1
      }
    }
  }

  // Obtener estadísticas de auditoría
  async obtenerEstadisticas(): Promise<AuditoriaStats> {
    try {
      const response = await apiClient.get<AuditoriaStats>(`${this.baseUrl}/stats`)
      return response
    } catch (error) {
      console.error('❌ Error obteniendo estadísticas:', error)
      throw error
    }
  }

  // Exportar auditoría a Excel
  async exportarExcel(filters?: Omit<AuditoriaFilters, 'skip' | 'limit' | 'ordenar_por' | 'orden'>): Promise<Blob> {
    try {
      const response: any = await apiClient.get(`${this.baseUrl}/exportar`, {
        params: filters,
        responseType: 'blob'
      })
      return response.data as Blob
    } catch (error) {
      console.error('❌ Error exportando Excel:', error)
      throw error
    }
  }

  // Obtener un registro de auditoría por ID
  async obtenerAuditoria(id: number): Promise<Auditoria> {
    try {
      const response = await apiClient.get<Auditoria>(`${this.baseUrl}/${id}`)
      return response
    } catch (error) {
      console.error('❌ Error obteniendo auditoría:', error)
      throw error
    }
  }

  // Registrar evento genérico de auditoría (confirmaciones, acciones manuales)
  async registrarEvento(params: {
    modulo: string
    accion: string
    descripcion: string
    registro_id?: number
  }): Promise<Auditoria> {
    const response = await apiClient.post<Auditoria>(`${this.baseUrl}/registrar`, params)
    return response
  }

  // Descargar archivo Excel
  async descargarExcel(filters?: Omit<AuditoriaFilters, 'skip' | 'limit' | 'ordenar_por' | 'orden'>): Promise<void> {
    try {
      const blob = await this.exportarExcel(filters)
      
      // Crear URL del blob
      const url = window.URL.createObjectURL(blob)
      
      // Crear elemento de descarga
      const link = document.createElement('a')
      link.href = url
      
      // Generar nombre de archivo con timestamp
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')
      link.download = `auditoria_${timestamp}.xlsx`
      
      // Descargar archivo
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Limpiar URL
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('❌ Error descargando Excel:', error)
      throw error
    }
  }
}

export const auditoriaService = new AuditoriaService()
