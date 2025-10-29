import { apiClient } from './api'

export interface Pago {
  id: number
  cedula_cliente: string
  prestamo_id: number | null
  fecha_pago: string
  fecha_registro: string
  monto_pagado: number
  numero_documento: string
  institucion_bancaria: string | null
  estado: string
  conciliado: boolean
  notas: string | null
  documento_nombre: string | null
  documento_tipo: string | null
  documento_ruta: string | null
}

export interface PagoCreate {
  cedula_cliente: string
  prestamo_id: number | null
  fecha_pago: string
  monto_pagado: number
  numero_documento: string
  institucion_bancaria: string | null
  notas?: string | null
}

export interface ApiResponse<T> {
  data: T
  message?: string
}

class PagoService {
  private baseUrl = '/api/v1/pagos'

  async getAllPagos(
    page = 1,
    perPage = 20,
    filters?: {
      cedula?: string
      estado?: string
      fechaDesde?: string
      fechaHasta?: string
      analista?: string
    }
  ): Promise<{ pagos: Pago[]; total: number; page: number; per_page: number; total_pages: number }> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
      ...(filters?.cedula && { cedula: filters.cedula }),
      ...(filters?.estado && { estado: filters.estado }),
      ...(filters?.fechaDesde && { fecha_desde: filters.fechaDesde }),
      ...(filters?.fechaHasta && { fecha_hasta: filters.fechaHasta }),
      ...(filters?.analista && { analista: filters.analista }),
    })
    // Usar barra final para coincidir con el endpoint del backend
    return await apiClient.get(`${this.baseUrl}/?${params.toString()}`)
  }

  async createPago(data: PagoCreate): Promise<Pago> {
    // Usar barra final para coincidir con el endpoint del backend
    return await apiClient.post(`${this.baseUrl}/`, data)
  }

  async updatePago(id: number, data: Partial<PagoCreate>): Promise<Pago> {
    return await apiClient.put(`${this.baseUrl}/${id}`, data)
  }

  async getAuditoria(pagoId: number): Promise<any[]> {
    return await apiClient.get(`${this.baseUrl}/auditoria/${pagoId}`)
  }

  async uploadExcel(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    return await apiClient.post(`${this.baseUrl}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  async getStats(filters?: {
    analista?: string
    concesionario?: string
    modelo?: string
    fecha_inicio?: string
    fecha_fin?: string
  }): Promise<{
    total_pagos: number
    pagos_por_estado: Record<string, number>
    total_pagado: number
    pagos_hoy: number
    cuotas_pagadas: number
    cuotas_pendientes: number
    cuotas_atrasadas: number
  }> {
    const params = new URLSearchParams()
    if (filters?.analista) params.append('analista', filters.analista)
    if (filters?.concesionario) params.append('concesionario', filters.concesionario)
    if (filters?.modelo) params.append('modelo', filters.modelo)
    if (filters?.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio)
    if (filters?.fecha_fin) params.append('fecha_fin', filters.fecha_fin)
    
    const queryString = params.toString()
    return await apiClient.get(`${this.baseUrl}/stats${queryString ? '?' + queryString : ''}`)
  }
}

export const pagoService = new PagoService()
