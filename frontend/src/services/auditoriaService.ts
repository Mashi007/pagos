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
  campo?: string  // Campo modificado (para auditorÃÂ­as detalladas)
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

  // Listar auditorÃÂ­a con filtros y paginaciÃÂ³n
  async listarAuditoria(filters?: AuditoriaFilters): Promise<AuditoriaListResponse> {
    try {
      console.log('Ã°ÂÂÂ Filtros enviados:', filters)
      const response = await apiClient.get<AuditoriaListResponse>(this.baseUrl, { params: filters })
      console.log('Ã°ÂÂÂ¦ Respuesta recibida del servidor:', response)

      // Validar que la respuesta tenga la estructura esperada
      if (!response || typeof response !== 'object') {
        console.error('Ã¢ÂÂ Respuesta invÃÂ¡lida:', response)
        throw new Error('Respuesta invÃÂ¡lida del servidor')
      }

      // Asegurar que tenga la estructura esperada
      const validResponse: AuditoriaListResponse = {
        items: Array.isArray(response.items) ? response.items : [],
        total: typeof response.total === 'number' ? response.total : 0,
        page: typeof response.page === 'number' ? response.page : 1,
        page_size: typeof response.page_size === 'number' ? response.page_size : 10,
        total_pages: typeof response.total_pages === 'number' ? response.total_pages : 1
      }

      console.log('Ã¢ÂÂ Respuesta validada:', validResponse)
      return validResponse
    } catch (error: any) {
      console.error('Ã¢ÂÂ Error en listarAuditoria:', error)
      console.error('Ã¢ÂÂ Detalles del error:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status
      })

      // Re-lanzar el error para que el componente pueda manejarlo
      throw error
    }
  }

  // Obtener estadÃÂ­sticas de auditorÃÂ­a
  async obtenerEstadisticas(): Promise<AuditoriaStats> {
    try {
      const response = await apiClient.get<AuditoriaStats>(`${this.baseUrl}/stats`)
      return response
    } catch (error) {
      console.error('Ã¢ÂÂ Error obteniendo estadÃÂ­sticas:', error)
      throw error
    }
  }

  // Exportar auditorÃÂ­a a Excel
  async exportarExcel(filters?: Omit<AuditoriaFilters, 'skip' | 'limit' | 'ordenar_por' | 'orden'>): Promise<Blob> {
    try {
      const response: any = await apiClient.get(`${this.baseUrl}/exportar`, {
        params: filters,
        responseType: 'blob'
      })
      return response.data as Blob
    } catch (error) {
      console.error('Ã¢ÂÂ Error exportando Excel:', error)
      throw error
    }
  }

  // Obtener un registro de auditorÃÂ­a por ID
  async obtenerAuditoria(id: number): Promise<Auditoria> {
    try {
      const response = await apiClient.get<Auditoria>(`${this.baseUrl}/${id}`)
      return response
    } catch (error) {
      console.error('Ã¢ÂÂ Error obteniendo auditorÃÂ­a:', error)
      throw error
    }
  }

  // Registrar evento genÃÂ©rico de auditorÃÂ­a (confirmaciones, acciones manuales)
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
      console.error('Ã¢ÂÂ Error descargando Excel:', error)
      throw error
    }
  }
}

export const auditoriaService = new AuditoriaService()
