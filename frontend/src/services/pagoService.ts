import { apiClient } from './api'

export interface Pago {
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
  verificado_concordancia?: string | null  // SI/NO - Verificación de concordancia con módulo de pagos
  usuario_registro: string
  notas: string | null
  documento_nombre: string | null
  documento_tipo: string | null
  documento_ruta: string | null
  cuotas_atrasadas?: number  // ✅ Campo calculado: cuotas vencidas con pago incompleto
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
    const url = `${this.baseUrl}/?${params.toString()}`
    return await apiClient.get<{ pagos: Pago[]; total: number; page: number; per_page: number; total_pages: number }>(url)
  }

  async createPago(data: PagoCreate): Promise<Pago> {
    // Usar barra final para coincidir con el endpoint del backend
    return await apiClient.post(`${this.baseUrl}/`, data)
  }

  async updatePago(id: number, data: Partial<PagoCreate>): Promise<Pago> {
    return await apiClient.put(`${this.baseUrl}/${id}`, data)
  }

  async deletePago(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  async aplicarPagoACuotas(pagoId: number): Promise<{ success: boolean; cuotas_completadas: number; message: string }> {
    return await apiClient.post(`${this.baseUrl}/${pagoId}/aplicar-cuotas`)
  }

  async uploadExcel(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    return await apiClient.post(`${this.baseUrl}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  // Cargar Excel de conciliación (2 columnas: Fecha de Depósito, Número de Documento)
  async uploadConciliacion(file: File): Promise<{
    pagos_conciliados: number
    pagos_no_encontrados: number
    documentos_no_encontrados: string[]
    errores: number
    errores_detalle: string[]
  }> {
    const formData = new FormData()
    formData.append('file', file)
    return await apiClient.post(`${this.baseUrl}/conciliacion/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  async getStats(filters?: {
    analista?: string
    concesionario?: string
    modelo?: string
    fecha_inicio?: string
    fecha_fin?: string
  }, config?: { signal?: AbortSignal }): Promise<{
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
    return await apiClient.get(`${this.baseUrl}/stats${queryString ? '?' + queryString : ''}`, config)
  }

  // Obtener KPIs de pagos: 1) a cobrar en el mes, 2) cobrado en el mes, 3) morosidad %
  async getKPIs(mes?: number, año?: number, config?: { signal?: AbortSignal }): Promise<{
    montoACobrarMes: number
    montoCobradoMes: number
    morosidadMensualPorcentaje: number
    mes: number
    año: number
  }> {
    const params = new URLSearchParams()
    if (mes !== undefined) params.append('mes', mes.toString())
    if (año !== undefined) params.append('año', año.toString())

    const queryString = params.toString()
    return await apiClient.get(`${this.baseUrl}/kpis${queryString ? '?' + queryString : ''}`, config)
  }

  // Obtener últimos pagos por cédula (resumen)
  async getUltimosPagos(
    page = 1,
    perPage = 20,
    filters?: {
      cedula?: string
      estado?: string
    }
  ): Promise<{
    items: Array<{
      cedula: string
      pago_id: number
      prestamo_id: number | null
      estado_pago: string
      monto_ultimo_pago: number
      fecha_ultimo_pago: string | null
      cuotas_atrasadas: number
      saldo_vencido: number
      total_prestamos: number
    }>
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
    })
    return await apiClient.get(`${this.baseUrl}/ultimos?${params.toString()}`)
  }

  // Descargar PDF de pendientes por cliente
  async descargarPDFPendientes(cedula: string): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `/api/v1/reportes/cliente/${cedula}/pendientes.pdf`,
      {
        responseType: 'blob',
      }
    )
    return response.data as Blob
  }

  // Descargar PDF tabla de amortización completa por cédula
  async descargarPDFAmortizacion(cedula: string): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `/api/v1/reportes/cliente/${encodeURIComponent(cedula)}/amortizacion.pdf`,
      { responseType: 'blob' }
    )
    return response.data as Blob
  }
}

export const pagoService = new PagoService()
