import { apiClient } from './api'

export interface Auditoria {
  id: number

  usuario_id?: number

  usuario_email?: string

  accion: string

  modulo: string

  tabla: string

  registro_id?: number

  descripcion?: string

  campo?: string // Campo modificado (para auditorías detalladas)

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

export interface ControlCartera {
  codigo: string
  titulo: string
  alerta: 'SI' | 'NO'
  detalle: string
}

export interface PrestamoCarteraChequeo {
  prestamo_id: number
  cliente_id: number
  cedula: string
  nombres: string
  estado_prestamo: string
  cliente_email: string
  tiene_alerta: boolean
  controles: ControlCartera[]
}

export interface PrestamoCarteraChequeoResponse {
  items: PrestamoCarteraChequeo[]
  resumen: Record<string, unknown>
  meta_ultima_corrida: Record<string, unknown>
  /** Presente en POST ejecutar/corregir: cuotas escaneadas y estados actualizados. */
  sincronizar_estado_cuotas?: {
    cuotas_escaneadas?: number
    estados_actualizados?: number
  } | null
}

export interface CarteraCorreccionResponse extends PrestamoCarteraChequeoResponse {
  reaplicar_cascada?: Array<Record<string, unknown>>
}

class AuditoriaService {
  private baseUrl = '/api/v1/auditoria'

  // Listar auditoría con filtros y paginación

  async listarAuditoria(
    filters?: AuditoriaFilters
  ): Promise<AuditoriaListResponse> {
    const response = await apiClient.get<AuditoriaListResponse>(this.baseUrl, {
      params: filters,
    })

    if (!response || typeof response !== 'object') {
      throw new Error('Respuesta invalida del servidor')
    }

    return {
      items: Array.isArray(response.items) ? response.items : [],

      total: typeof response.total === 'number' ? response.total : 0,

      page: typeof response.page === 'number' ? response.page : 1,

      page_size:
        typeof response.page_size === 'number' ? response.page_size : 10,

      total_pages:
        typeof response.total_pages === 'number' ? response.total_pages : 1,
    }
  }

  // Obtener estadísticas de auditoría

  async obtenerEstadisticas(): Promise<AuditoriaStats> {
    try {
      const response = await apiClient.get<AuditoriaStats>(
        `${this.baseUrl}/stats`
      )

      return response
    } catch (error) {
      console.error('❌ Error obteniendo estadísticas:', error)

      throw error
    }
  }

  // Exportar auditoría a Excel

  async exportarExcel(
    filters?: Omit<AuditoriaFilters, 'skip' | 'limit' | 'ordenar_por' | 'orden'>
  ): Promise<Blob> {
    try {
      const response: any = await apiClient.get(`${this.baseUrl}/exportar`, {
        params: filters,

        responseType: 'blob',
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
    const response = await apiClient.post<Auditoria>(
      `${this.baseUrl}/registrar`,
      params
    )

    return response
  }

  async listarCarteraChequeos(): Promise<PrestamoCarteraChequeoResponse> {
    return apiClient.get<PrestamoCarteraChequeoResponse>(
      `${this.baseUrl}/prestamos/cartera/chequeos`
    )
  }

  async ejecutarCartera(): Promise<PrestamoCarteraChequeoResponse> {
    return apiClient.post<PrestamoCarteraChequeoResponse>(
      `${this.baseUrl}/prestamos/cartera/ejecutar`,
      undefined
    )
  }

  /** Solo administrador. Reaplica cascada en prestamos con alerta pagos vs aplicado (opcional) y sincroniza estados. */
  async corregirCartera(body: {
    sincronizar_estados?: boolean
    reaplicar_cascada_desajuste_pagos?: boolean
    max_reaplicaciones?: number
  }): Promise<CarteraCorreccionResponse> {
    return apiClient.post<CarteraCorreccionResponse>(
      `${this.baseUrl}/prestamos/cartera/corregir`,
      {
        sincronizar_estados: body.sincronizar_estados ?? true,
        reaplicar_cascada_desajuste_pagos:
          body.reaplicar_cascada_desajuste_pagos ?? false,
        max_reaplicaciones: body.max_reaplicaciones ?? 50,
      }
    )
  }

  // Descargar archivo Excel

  async descargarExcel(
    filters?: Omit<AuditoriaFilters, 'skip' | 'limit' | 'ordenar_por' | 'orden'>
  ): Promise<void> {
    try {
      const blob = await this.exportarExcel(filters)

      // Crear URL del blob

      const url = window.URL.createObjectURL(blob)

      // Crear elemento de descarga

      const link = document.createElement('a')

      link.href = url

      // Generar nombre de archivo con timestamp

      const timestamp = new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/[:-]/g, '')

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
