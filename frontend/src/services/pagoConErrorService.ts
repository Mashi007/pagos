import { apiClient } from './api'

export interface PagoConError {
  id: number
  cedula_cliente: string
  prestamo_id: number | null
  fecha_pago: string | Date
  monto_pagado: number
  numero_documento: string
  institucion_bancaria: string | null
  estado: string
  fecha_registro: string | Date | null
  fecha_conciliacion: string | Date | null
  conciliado: boolean
  verificado_concordancia?: string | null
  usuario_registro: string
  notas: string | null
  documento_nombre: string | null
  documento_tipo: string | null
  documento_ruta: string | null
  errores_descripcion?: Record<string, unknown>[] | null
  observaciones?: string | null
  fila_origen?: number | null
}

export interface PagoConErrorCreate {
  cedula_cliente: string
  prestamo_id?: number | null
  fecha_pago: string
  monto_pagado: number
  numero_documento?: string | null
  institucion_bancaria?: string | null
  notas?: string | null
  conciliado?: boolean
  errores_descripcion?: Record<string, unknown>[] | null
  observaciones?: string | null
  fila_origen?: number | null
}

class PagoConErrorService {
  private baseUrl = '/api/v1/pagos/con-errores'

  async getAll(
    page = 1,
    perPage = 20,
    filters?: {
      cedula?: string
      estado?: string
      fechaDesde?: string
      fechaHasta?: string
      conciliado?: string
    }
  ): Promise<{
    pagos: PagoConError[]
    total: number
    page: number
    per_page: number
    total_pages: number
  }> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
      ...(filters?.cedula && { cedula: filters.cedula }),
      ...(filters?.estado && { estado: filters.estado }),
      ...(filters?.fechaDesde && { fecha_desde: filters.fechaDesde }),
      ...(filters?.fechaHasta && { fecha_hasta: filters.fechaHasta }),
      ...(filters?.conciliado && filters.conciliado !== 'all' && { conciliado: filters.conciliado }),
    })
    return await apiClient.get(`${this.baseUrl}?${params.toString()}`)
  }

  async getAllForExport(filters?: {
    cedula?: string
    fechaDesde?: string
    fechaHasta?: string
  }): Promise<PagoConError[]> {
    const params = new URLSearchParams()
    if (filters?.cedula) params.append('cedula', filters.cedula)
    if (filters?.fechaDesde) params.append('fecha_desde', filters.fechaDesde)
    if (filters?.fechaHasta) params.append('fecha_hasta', filters.fechaHasta)
    const qs = params.toString()
    return await apiClient.get(`${this.baseUrl}/export${qs ? '?' + qs : ''}`)
  }

  async create(data: PagoConErrorCreate): Promise<PagoConError> {
    return await apiClient.post(this.baseUrl, data)
  }

  async update(id: number, data: Partial<PagoConErrorCreate>): Promise<PagoConError> {
    return await apiClient.put(`${this.baseUrl}/${id}`, data)
  }

  async delete(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  async moverAPagosNormales(ids: number[]): Promise<{ movidos: number; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/mover-a-pagos`, { ids })
  }

  /** Elimina de pagos_con_errores tras descargar Excel. La lista se vacía y se rellena al enviar desde Carga Masiva. */
  async eliminarPorDescarga(ids: number[]): Promise<{ eliminados: number; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/eliminar-por-descarga`, { ids })
  }
}

export const pagoConErrorService = new PagoConErrorService()
