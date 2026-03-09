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
  verificado_concordancia?: string | null  // SI/NO - VerificaciÃ³n de concordancia con mÃ³dulo de pagos
  usuario_registro: string
  notas: string | null
  documento_nombre: string | null
  documento_tipo: string | null
  documento_ruta: string | null
  cuotas_atrasadas?: number  // âœ… Campo calculado: cuotas vencidas con pago incompleto
}

export interface PagoCreate {
  cedula_cliente: string
  prestamo_id: number | null
  fecha_pago: string
  monto_pagado: number
  numero_documento: string
  institucion_bancaria: string | null
  notas?: string | null
  conciliado?: boolean
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
      conciliado?: string
      sin_prestamo?: string
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
      ...(filters?.conciliado && filters.conciliado !== 'all' && { conciliado: filters.conciliado }),
      ...(filters?.sin_prestamo === 'si' && { sin_prestamo: 'si' }),
    })
    const url = `${this.baseUrl}?${params.toString()}`
    return await apiClient.get<{ pagos: Pago[]; total: number; page: number; per_page: number; total_pages: number }>(url)
  }

  /** Mueve pagos exportados a revisar_pagos (dejan de mostrarse en Revisar Pagos) */
  async moverARevisarPagos(pagoIds: number[]): Promise<{ movidos: number; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/revisar-pagos/mover`, { pago_ids: pagoIds })
  }

  /** Obtiene el 100% de los pagos para exportar (paginaciÃ³n automÃ¡tica sin lÃ­mite) */
  async getAllPagosForExport(filters: {
    cedula?: string
    estado?: string
    fechaDesde?: string
    fechaHasta?: string
    analista?: string
    conciliado?: string
    sin_prestamo?: string
  }): Promise<Pago[]> {
    const all: Pago[] = []
    const perPage = 100
    let page = 1
    let totalPages = 1
    do {
      const res = await this.getAllPagos(page, perPage, filters)
      all.push(...res.pagos)
      totalPages = res.total_pages
      page++
    } while (page <= totalPages)
    return all
  }

  async createPago(data: PagoCreate): Promise<Pago> {
    return await apiClient.post(this.baseUrl, data)
  }

  async updatePago(id: number, data: Partial<PagoCreate>): Promise<Pago> {
    return await apiClient.put(`${this.baseUrl}/${id}`, data)
  }

  /** Actualiza solo el estado de conciliaciÃ³n (SÃ­/No) en BD */
  async updateConciliado(id: number, conciliado: boolean): Promise<Pago> {
    return await apiClient.put(`${this.baseUrl}/${id}`, { conciliado })
  }

  async deletePago(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  async aplicarPagoACuotas(pagoId: number): Promise<{ success: boolean; cuotas_completadas: number; cuotas_parciales: number; message: string }> {
    return await apiClient.post(`${this.baseUrl}/${pagoId}/aplicar-cuotas`)
  }

  async uploadExcel(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    return await apiClient.post(`${this.baseUrl}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  // Cargar Excel de conciliaciÃ³n (2 columnas: Fecha de DepÃ³sito, NÃºmero de Documento)
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

  async validarFilasBatch(data: {
    cedulas: string[]
    documentos: string[]
  }): Promise<{
    cedulas_existentes: string[]
    documentos_duplicados: Array<any>
  }> {
    return await apiClient.post(`${this.baseUrl}/validar-filas-batch`, data)
  }

  async guardarFilaEditable(data: {
    cedula: string
    prestamo_id: number | null
    monto_pagado: number
    fecha_pago: string // formato "DD-MM-YYYY"
    numero_documento: string | null
  }): Promise<{
    success: boolean
    pago_id: number
    message: string
    cuotas_completadas: number
    cuotas_parciales: number
  }> {
    return await apiClient.post(`${this.baseUrl}/guardar-fila-editable`, data)
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
  async getKPIs(mes?: number, anio?: number, config?: { signal?: AbortSignal }): Promise<{
    montoACobrarMes: number
    montoCobradoMes: number
    morosidadMensualPorcentaje: number
    mes: number
    anio: number
  }> {
    const params = new URLSearchParams()
    if (mes !== undefined) params.append('mes', mes.toString())
    if (anio !== undefined) params.append('anio', anio.toString())

    const queryString = params.toString()
    return await apiClient.get(`${this.baseUrl}/kpis${queryString ? '?' + queryString : ''}`, config)
  }

  // Obtener Ãºltimos pagos por cÃ©dula (resumen)
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
    }>,
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

  // Descargar PDF tabla de amortizaciÃ³n completa por cÃ©dula
  async descargarPDFAmortizacion(cedula: string): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `/api/v1/reportes/cliente/${encodeURIComponent(cedula)}/amortizacion.pdf`,
      { responseType: 'blob' }
    )
    return response.data as Blob
  }

/** Pagos Gmail: ejecutar pipeline (Gmail -> Drive -> Gemini -> Sheets). force=true permite ejecutar aunque la última sync fue hace poco. */
  async runGmailNow(force = true): Promise<{ sync_id: number | null; status: string }> {
    return await apiClient.post(`${this.baseUrl}/gmail/run-now?force=${force}`)
  }

  /** Pagos Gmail: estado última ejecución y próxima (cron cada 15 min). */
  async getGmailStatus(): Promise<{
    last_run: string | null
    last_status: string | null
    last_emails: number
    last_files: number
    next_run_approx: string | null
  }> {
    return await apiClient.get(`${this.baseUrl}/gmail/status`)
  }

  /** Pagos Gmail: confirmar día (sí/no). Si confirmado=true, se borran los datos del día en el servidor. */
  async confirmarDiaGmail(confirmado: boolean, fecha?: string): Promise<{ confirmado: boolean; mensaje: string; borrados?: number }> {
    const res = await apiClient.post<{ confirmado: boolean; mensaje: string; borrados?: number }>(
      `${this.baseUrl}/gmail/confirmar-dia`,
      { confirmado, fecha }
    )
    return res
  }

  /** Pagos Gmail: descargar Excel del día (datos del Sheet). */
  async downloadGmailExcel(): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(`${this.baseUrl}/gmail/download-excel`, {
      responseType: 'blob',
      timeout: 60000,
    })
    const blob = response.data as Blob
    const disposition = response.headers?.['content-disposition']
    let filename = 'Pagos_Gmail.xlsx'
    if (typeof disposition === 'string' && disposition.includes('filename=')) {
      const m = disposition.match(/filename=(.+?)(?:;|$)/)
      if (m) filename = m[1].replace(/^["']|["']$/g, '').trim()
    }
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }
}

export const pagoService = new PagoService()

