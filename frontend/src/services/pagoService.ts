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
  referencia_pago: string
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
  referencia_pago: string
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
    return await apiClient.get(this.baseUrl + '?' + params.toString())
  }

  async createPago(data: PagoCreate): Promise<Pago> {
    return await apiClient.post(this.baseUrl, data)
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
}

export const pagoService = new PagoService()
