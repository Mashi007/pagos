import { apiClient } from './api'

export interface CargaMasivaRequest {
  file: File
  type: 'clientes' | 'prestamos' | 'pagos'
}

export interface CargaMasivaResponse {
  success: boolean
  message: string
  data?: {
    totalRecords: number
    processedRecords: number
    errors: number
    fileName: string
    type?: string
    details?: any[]
  }
  errors?: string[]
  erroresDetallados?: Array<{
    row: number
    cedula: string
    error: string
    data: any
  }>
}

class CargaMasivaService {
  // Cargar archivo Excel
  async cargarArchivo(request: CargaMasivaRequest): Promise<CargaMasivaResponse> {
    try {
      const formData = new FormData()
      formData.append('file', request.file)
      formData.append('type', request.type)

      const response = await apiClient.post<CargaMasivaResponse>(
        '/api/v1/carga-masiva/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )

      if (!response.data) {
        return {
          success: false,
          message: 'No se recibió respuesta del servidor',
          errors: ['Error de comunicación']
        }
      }

      return response.data as unknown as CargaMasivaResponse
    } catch (error: any) {
      console.error('Error en carga masiva:', error)
      
      if (error.response?.status === 413) {
        return {
          success: false,
          message: 'Archivo demasiado grande',
          errors: ['El archivo excede el límite de tamaño permitido']
        }
      }

      if (error.response?.status === 400) {
        return {
          success: false,
          message: 'Formato de archivo inválido',
          errors: error.response.data?.errors || ['Formato de archivo no válido']
        }
      }

      return {
        success: false,
        message: 'Error al procesar el archivo',
        errors: [error.message || 'Error desconocido']
      }
    }
  }

  // Descargar template
  async descargarTemplate(type: 'clientes' | 'prestamos' | 'pagos'): Promise<Blob> {
    try {
      const response = await apiClient.get(`/api/v1/carga-masiva/template/${type}`, {
        responseType: 'blob'
      }) as any
      return response.data
    } catch (error: any) {
      console.error('Error al descargar template:', error)
      throw error
    }
  }

  // Validar archivo antes de cargar
  async validarArchivo(file: File): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = []

    // Validar extensión
    const validExtensions = ['.xlsx', '.xls', '.csv']
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    
    if (!validExtensions.includes(fileExtension)) {
      errors.push('Solo se permiten archivos Excel (.xlsx, .xls) o CSV (.csv)')
    }

    // Validar tamaño (máximo 10MB)
    if (file.size > 10 * 1024 * 1024) {
      errors.push('El archivo no puede superar los 10MB')
    }

    // Validar nombre
    if (file.name.length > 100) {
      errors.push('El nombre del archivo es demasiado largo')
    }

    return {
      valid: errors.length === 0,
      errors
    }
  }

  // Obtener historial de cargas
  async obtenerHistorial(): Promise<any[]> {
    try {
      const response = await apiClient.get('/api/v1/carga-masiva/historial') as any
      return response.data
    } catch (error: any) {
      console.error('Error al obtener historial:', error)
      return []
    }
  }
}

export const cargaMasivaService = new CargaMasivaService()
