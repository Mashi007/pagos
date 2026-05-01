import { apiClient } from './api'

export interface PagoConError {
  id: number

  cedula_cliente: string

  prestamo_id: number | null

  fecha_pago: string | Date

  monto_pagado: number

  numero_documento: string

  codigo_documento?: string

  institucion_bancaria: string | null

  estado: string

  fecha_registro: string | Date | null

  fecha_conciliacion: string | Date | null

  conciliado: boolean

  verificado_concordancia?: string | null

  usuario_registro: string

  notas: string | null

  /** Presente cuando el registro se alinea con pagos en Bs. (misma semántica que Pago). */
  moneda_registro?: string | null

  monto_bs_original?: number | null

  documento_nombre: string | null

  documento_tipo: string | null

  documento_ruta: string | null

  errores_descripcion?: Record<string, unknown>[] | null

  observaciones?: string | null

  fila_origen?: number | null

  /** True si el comprobante almacenado ya existe en la tabla `pagos` (cartera). Calculado en API. */
  duplicado_documento_en_pagos?: boolean

  /** Préstamo y pago en `pagos` que ya usan el mismo Nº documento (si aplica). */
  duplicado_en_cartera_prestamo_id?: number | null

  duplicado_en_cartera_pago_id?: number | null
}

export interface PagoConErrorCreate {
  cedula_cliente: string

  prestamo_id?: number | null

  fecha_pago: string

  monto_pagado: number

  numero_documento?: string | null

  codigo_documento?: string | null

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

      fechaPago?: string

      numeroDocumento?: string

      tipoRevision?: 'anomalo' | 'irreal' | 'duplicado'

      conciliado?: string

      includeExportados?: boolean
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

      ...(filters?.fechaPago && { fecha_pago: filters.fechaPago }),

      ...(filters?.numeroDocumento && {
        numero_documento: filters.numeroDocumento,
      }),

      ...(filters?.tipoRevision && { tipo_revision: filters.tipoRevision }),

      ...(filters?.conciliado &&
        filters.conciliado !== 'all' && { conciliado: filters.conciliado }),
      ...(filters?.includeExportados ? { include_exportados: 'true' } : {}),
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

  async createBatch(pagos: PagoConErrorCreate[]): Promise<{
    results: Array<{
      success: boolean
      pago?: PagoConError
      error?: string
      payload_index?: number
    }>

    ok_count: number

    fail_count: number
  }> {
    return await apiClient.post(
      this.baseUrl + '/batch',
      { pagos },
      { timeout: 120000 }
    )
  }

  /**
   * Actualiza un PagoConError. **Caso especial**: el backend hace prechequeo estricto
   * (mismo Nº documento canónico + cuota_pagos aplicado + misma cédula/préstamo) y, si
   * detecta que la fila ya está cargada en cartera, la elimina y devuelve un payload
   * con `ya_cargado_eliminado: true` en lugar del registro actualizado. Las llamadas
   * deben verificar esa bandera antes de asumir que tienen un `PagoConError`.
   */
  async update(
    id: number,
    data: Partial<PagoConErrorCreate>
  ): Promise<
    | PagoConError
    | {
        ya_cargado_eliminado: true
        pago_con_error_id: number
        pago_id: number
        cedula?: string | null
        prestamo_id?: number | null
        numero_documento?: string | null
        mensaje: string
      }
  > {
    return await apiClient.put(`${this.baseUrl}/${id}`, data)
  }

  async delete(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  async moverAPagosNormales(ids: number[]): Promise<{
    movidos: number
    cuotas_aplicadas?: number
    errores?: string[]
    /** Filas eliminadas en silencio porque ya estaban cargadas y aplicadas en cartera. */
    ya_cargado_eliminados?: Array<{
      pago_con_error_id: number
      pago_id: number
      cedula?: string | null
      prestamo_id?: number | null
      numero_documento?: string | null
    }>
    ya_cargado_eliminados_count?: number
    mensaje: string
  }> {
    return await apiClient.post(`${this.baseUrl}/mover-a-pagos`, { ids })
  }

  /**
   * Limpia PagoConError redundantes: si su `numero_documento` canónico ya está en `pagos`
   * con `cuota_pagos` aplicado y misma cédula/préstamo, los elimina.
   * - `ids` ausente o vacío: barre todos los pendientes (limitado por `max_revisar`).
   * - `ids` con valores: solo evalúa esos.
   */
  async limpiarYaCargados(
    ids?: number[],
    maxRevisar = 5000
  ): Promise<{
    eliminados: number
    evaluados: number
    errores: string[]
    detalles: Array<{
      pago_con_error_id: number
      pago_id: number
      cedula?: string | null
      prestamo_id?: number | null
      numero_documento?: string | null
    }>
    mensaje: string
  }> {
    return await apiClient.post(
      `${this.baseUrl}/limpiar-ya-cargados`,
      { ids: ids && ids.length > 0 ? ids : null, max_revisar: maxRevisar },
      { timeout: 120000 }
    )
  }

  /** Archiva pagos exportados para mantener trazabilidad operativa. */
  async archivarPorDescarga(
    ids: number[]
  ): Promise<{ archivados: number; mensaje: string }> {
    return await apiClient.post(
      `${this.baseUrl}/archivar-por-descarga`,
      { ids },
      { timeout: 120000 }
    )
  }

  /** Mueve un pago con error a la tabla revisar_pago para análisis manual */

  async moveToReviewPagos(
    id: number
  ): Promise<{ id: number; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/${id}/mover-a-revisar`, {})
  }
}

export const pagoConErrorService = new PagoConErrorService()
