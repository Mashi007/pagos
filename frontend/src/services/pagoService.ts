import { apiClient } from './api'

export interface Pago {
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

  verificado_concordancia?: string | null // SI/NO - Verificación de concordancia con módulo de pagos

  usuario_registro: string

  notas: string | null

  moneda_registro?: string | null

  monto_bs_original?: number | null

  tasa_cambio_bs_usd?: number | null

  fecha_tasa_referencia?: string | null

  documento_nombre: string | null

  documento_tipo: string | null

  documento_ruta: string | null

  /** URL del comprobante (foto/PDF); import desde Excel Link / Gmail. */
  link_comprobante?: string | null

  /** Si el Nº documento enlaza con un pago reportado en Cobros. */
  pago_reportado_id?: number | null

  /** True si existe al menos una fila en cuota_pagos para este pago (GET /pagos enriquecido). */
  tiene_aplicacion_cuotas?: boolean

  cuotas_atrasadas?: number // ✅ Campo calculado: cuotas vencidas con pago incompleto
}

export interface PagoCreate {
  cedula_cliente: string

  prestamo_id: number | null

  fecha_pago: string

  monto_pagado: number

  numero_documento: string

  codigo_documento?: string | null

  institucion_bancaria: string | null

  notas?: string | null

  conciliado?: boolean

  moneda_registro?: 'USD' | 'BS'

  tasa_cambio_manual?: number | null

  link_comprobante?: string | null
}

/** Hidrata el modal de registro/edición (monto en Bs. al editar). */
export type PagoInicialRegistrar = Partial<PagoCreate> & {
  moneda_registro?: string | null
  monto_bs_original?: number | null
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

      /** activa (defecto en API): solo préstamo APROBADO o sin crédito. todos: incluye LIQUIDADO etc. */
      prestamo_cartera?: 'activa' | 'todos'

      /** Agregados de pagos de este crédito (todas las páginas); no filtra el listado principal. */
      resumen_prestamo_id?: number
    }
  ): Promise<{
    pagos: Pago[]
    total: number
    page: number
    per_page: number
    total_pages: number
    /** Presente solo si el listado se filtró por cédula: suma de monto_pagado de todos los registros que coinciden (no solo la página). */
    sum_monto_pagado_cedula?: number
    /** Presente si se envió resumen_prestamo_id: totales en BD para ese préstamo (y cédula si aplica). */
    resumen_prestamo?: {
      prestamo_id: number
      cantidad: number
      suma_monto_pagado: number
      cantidad_pendiente: number
      suma_monto_pendiente: number
      cantidad_pagado: number
      suma_monto_estado_pagado: number
    }
  }> {
    const params = new URLSearchParams({
      page: page.toString(),

      per_page: perPage.toString(),

      ...(filters?.cedula && { cedula: filters.cedula }),

      ...(filters?.estado && { estado: filters.estado }),

      ...(filters?.fechaDesde && { fecha_desde: filters.fechaDesde }),

      ...(filters?.fechaHasta && { fecha_hasta: filters.fechaHasta }),

      ...(filters?.analista && { analista: filters.analista }),

      ...(filters?.conciliado &&
        filters.conciliado !== 'all' && { conciliado: filters.conciliado }),

      ...(filters?.sin_prestamo === 'si' && { sin_prestamo: 'si' }),

      ...(filters?.prestamo_cartera === 'todos' && {
        prestamo_cartera: 'todos',
      }),

      ...(filters?.resumen_prestamo_id != null &&
        Number.isFinite(Number(filters.resumen_prestamo_id)) &&
        Number(filters.resumen_prestamo_id) > 0 && {
          resumen_prestamo_id: String(
            Math.trunc(Number(filters.resumen_prestamo_id))
          ),
        }),
    })

    const url = `${this.baseUrl}?${params.toString()}`

    return await apiClient.get<{
      pagos: Pago[]
      total: number
      page: number
      per_page: number
      total_pages: number
      sum_monto_pagado_cedula?: number
      resumen_prestamo?: {
        prestamo_id: number
        cantidad: number
        suma_monto_pagado: number
        cantidad_pendiente: number
        suma_monto_pendiente: number
        cantidad_pagado: number
        suma_monto_estado_pagado: number
      }
    }>(url)
  }

  async sugerirPagosConPréstamoFaltante(
    page = 1,
    perPage = 20
  ): Promise<{
    sugerencias: Array<{
      pago_id: number
      cedula_cliente: string
      fecha_pago: string | null
      monto_pagado: number
      numero_documento: string
      prestamo_sugerido: number | null
      num_creditos_activos: number
      acciones_necesarias: 'auto' | 'manual'
    }>
    total: number
    page: number
    per_page: number
    total_pages: number
    resumen: {
      total_pagos_sin_prestamo: number
      can_auto_asignar: number
      requieren_manual: number
    }
  }> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
    })

    return await apiClient.get<any>(
      `${this.baseUrl}/sin-prestamo/sugerir?${params.toString()}`
    )
  }

  async asignarAutomáticamentePréstamos(): Promise<{
    asignados: number
    no_asignables: number
    detalles_asignados: Array<{
      pago_id: number
      cedula_cliente: string
      prestamo_id_asignado: number
    }>
    detalles_no_asignables: Array<{
      pago_id: number
      cedula_cliente: string
      razon: string
    }>
    mensaje: string
  }> {
    return await apiClient.post(
      `${this.baseUrl}/sin-prestamo/asignar-automatico`,
      {}
    )
  }

  /** Mueve pagos exportados a revisar_pagos (dejan de mostrarse en Revisar Pagos) */

  async moverARevisarPagos(
    pagoIds: number[]
  ): Promise<{ movidos: number; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/revisar-pagos/mover`, {
      pago_ids: pagoIds,
    })
  }

  /** Obtiene el 100% de los pagos para exportar (paginación automática sin límite) */

  async getAllPagosForExport(filters: {
    cedula?: string

    estado?: string

    fechaDesde?: string

    fechaHasta?: string

    analista?: string

    conciliado?: string

    sin_prestamo?: string

    prestamo_cartera?: 'activa' | 'todos'
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

  /**





   * Crea varios pagos en una sola petición (Guardar todos). Máx. 500.





   * Devuelve resultados por índice (éxito/error) para actualizar la tabla sin múltiples rondas.





   */

  async createPagosBatch(pagos: PagoCreate[]): Promise<{
    results: Array<{
      index: number
      success: boolean
      pago?: Pago
      error?: string
      status_code?: number
    }>

    ok_count: number

    fail_count: number
  }> {
    return await apiClient.post(`${this.baseUrl}/batch`, { pagos })
  }

  async updatePago(
    id: number,
    data: Partial<PagoCreate & { verificado_concordancia?: string | null }>
  ): Promise<Pago> {
    return await apiClient.put(`${this.baseUrl}/${id}`, data)
  }

  /** Actualiza solo el estado de conciliación (Sí/No) en BD */

  async updateConciliado(id: number, conciliado: boolean): Promise<Pago> {
    return await apiClient.put(`${this.baseUrl}/${id}`, { conciliado })
  }

  async deletePago(id: number): Promise<void> {
    return await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  /** Elimina todos los pagos de un préstamo APROBADO (reemplazo antes de Excel). */

  async deleteTodosPagosPorPrestamo(prestamoId: number): Promise<{
    ok: boolean
    prestamo_id: number
    pagos_eliminados: number
    cuota_pagos_eliminadas?: number
  }> {
    return await apiClient.delete(
      `${this.baseUrl}/por-prestamo/${prestamoId}/todos`
    )
  }

  async aplicarPagoACuotas(pagoId: number): Promise<{
    success: boolean
    ya_aplicado?: boolean
    cuotas_completadas: number
    cuotas_parciales: number
    message: string
  }> {
    return await apiClient.post(`${this.baseUrl}/${pagoId}/aplicar-cuotas`)
  }

  /**
   * Aplica en cascada todos los pagos del préstamo elegibles que aún no tienen cuota_pagos
   * (misma lógica que jobs internos / revisión manual al cerrar saldo cero).
   */
  async aplicarPagosPendientesCuotasPorPrestamo(prestamoId: number): Promise<{
    prestamo_id: number
    pagos_con_aplicacion: number
    reaplicacion_completa?: boolean
    detalle_reaplicacion?: Record<string, unknown> | null
    mensaje: string
    diagnostico?: {
      pagos_operativos_sin_cuota_pagos?: number
      pagos_elegibles_cascada_sin_cuota_pagos?: number
      pagos_no_elegibles_sin_cuota_pagos?: number
      pagos_con_intento_sin_abono_ids?: number[]
      errores_por_pago?: Array<{ pago_id: number; error: string }>
    }
  }> {
    return await apiClient.post(
      `${this.baseUrl}/por-prestamo/${prestamoId}/aplicar-pagos-cuotas`
    )
  }

  async uploadExcel(file: File): Promise<any> {
    const formData = new FormData()

    formData.append('file', file)

    return await apiClient.post(`${this.baseUrl}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  /** Sube imagen de comprobante; la URL devuelta se guarda en link_comprobante. */
  async uploadComprobanteImagen(
    file: File
  ): Promise<{ url: string; id: string }> {
    return apiClient.uploadFile<{ url: string; id: string }>(
      `${this.baseUrl}/comprobante-imagen`,
      file
    )
  }

  /**





   * Importa pagos reportados aprobados (módulo Cobros) a la tabla pagos.





   * Mismas reglas que carga masiva; los que no cumplen van a Revisar Pagos.





   */

  async importarDesdeCobros(): Promise<{
    registros_procesados: number

    registros_con_error: number

    errores_detalle: Array<{ referencia: string; error: string }>

    ids_pagos_con_errores: number[]

    /** Suma de operaciones en cuotas (completadas + parciales), no cantidad de filas del cronograma. */

    cuotas_aplicadas?: number

    operaciones_cuota_total?: number

    pagos_con_aplicacion_a_cuotas?: number

    pagos_sin_aplicacion_cuotas?: Array<{
      pago_id: number | null

      cedula_cliente: string

      prestamo_id: number | null

      motivo: string

      detalle: string
    }>

    pagos_sin_aplicacion_cuotas_total?: number

    pagos_sin_aplicacion_cuotas_truncados?: boolean

    total_datos_revisar?: number

    mensaje: string
  }> {
    return await apiClient.post(
      `${this.baseUrl}/importar-desde-cobros`,
      undefined,
      { timeout: 120000 }
    )
  }

  /**





   * Descarga el Excel de registros que fallaron al "Importar reportados aprobados (Cobros)".





   * Los datos están en datos_importados_conerrores; el backend vacía la tabla tras generar el archivo.





   */

  async descargarExcelErroresImportacionCobros(): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()

    const url = `${this.baseUrl}/importar-desde-cobros/descargar-excel-errores`

    const response = await axiosInstance.get(url, {
      responseType: 'blob',
      timeout: 60000,
    })

    if (response.status !== 200) {
      try {
        const text = await (response.data as Blob).text()

        const json = JSON.parse(text) as { detail?: string }

        throw new Error(
          json.detail || `Error al descargar (${response.status}).`
        )
      } catch (e) {
        if (e instanceof Error) throw e

        throw new Error('No se pudo descargar el Excel de errores.')
      }
    }

    const blob = response.data as Blob

    const disposition = response.headers?.['content-disposition']

    let filename = `datos_importados_con_errores_${new Date().toISOString().slice(0, 10)}.xlsx`

    if (typeof disposition === 'string' && disposition.includes('filename=')) {
      const m = disposition.match(/filename=(.+?)(?:;|$)/)

      if (m) filename = m[1].replace(/^["']|["']$/g, '').trim()
    }

    const blobUrl = window.URL.createObjectURL(blob)

    const link = document.createElement('a')

    link.href = blobUrl

    link.download = filename

    document.body.appendChild(link)

    link.click()

    document.body.removeChild(link)

    window.URL.revokeObjectURL(blobUrl)
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

    return await apiClient.post(
      `${this.baseUrl}/conciliacion/upload`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    )
  }

  /** Cédulas que pueden reportar en Bs (rapicredit-cobros / infopagos). Paginado: más reciente primero. */

  async getCedulasReportarBs(params?: {
    page?: number
    page_size?: number
  }): Promise<{
    total: number
    page: number
    page_size: number
    items: { cedula: string; creado_en: string | null }[]
  }> {
    const sp = new URLSearchParams()
    if (params?.page != null) sp.set('page', String(params.page))
    if (params?.page_size != null) sp.set('page_size', String(params.page_size))
    const qs = sp.toString()
    return await apiClient.get(
      `${this.baseUrl}/cedulas-reportar-bs${qs ? `?${qs}` : ''}`
    )
  }

  async consultarCedulaReportarBs(cedula: string): Promise<{
    cedula_ingresada: string
    cedula_normalizada: string | null
    en_lista: boolean
    total_en_lista: number
  }> {
    const q = encodeURIComponent(cedula.trim())
    return await apiClient.get(
      `${this.baseUrl}/cedulas-reportar-bs/consultar?cedula=${q}`
    )
  }

  /** Varias cedulas en una sola peticion (evita N+1). */
  async consultarCedulasReportarBsBatch(cedulas: string[]): Promise<{
    total_en_lista: number
    por_cedula: Record<
      string,
      {
        cedula_ingresada: string
        cedula_normalizada: string | null
        en_lista: boolean
        total_en_lista: number
      }
    >
  }> {
    return await apiClient.post(
      `${this.baseUrl}/cedulas-reportar-bs/consultar-batch`,
      { cedulas }
    )
  }

  /** Agrega una cédula a la lista (nuevo cliente que paga en bolívares). */

  async addCedulaReportarBs(cedula: string): Promise<{
    agregada: boolean
    cedula: string
    total: number
    mensaje: string
  }> {
    return await apiClient.post(`${this.baseUrl}/cedulas-reportar-bs/agregar`, {
      cedula,
    })
  }

  /** Elimina una cédula de la lista (ya no podrá reportar en Bs). */

  async removeCedulaReportarBs(cedula: string): Promise<{
    eliminada: boolean
    cedula: string
    total: number
    mensaje: string
  }> {
    return await apiClient.delete(
      `${this.baseUrl}/cedulas-reportar-bs/eliminar`,
      {
        data: {
          cedula,
        },
      }
    )
  }

  /** Carga Excel con columna 'cedula' para definir quiénes pueden reportar en Bs. */

  async uploadCedulasReportarBs(
    file: File
  ): Promise<{ total: number; mensaje: string }> {
    const formData = new FormData()

    formData.append('file', file)

    return await apiClient.post(
      `${this.baseUrl}/cedulas-reportar-bs/upload`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    )
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

    codigo_documento?: string | null

    moneda_registro?: 'USD' | 'BS'

    tasa_cambio_manual?: number | null
  }): Promise<{
    success: boolean

    pago_id: number

    message: string

    cuotas_completadas: number

    cuotas_parciales: number
  }> {
    return await apiClient.post(`${this.baseUrl}/guardar-fila-editable`, data)
  }

  async getStats(
    filters?: {
      analista?: string

      concesionario?: string

      modelo?: string

      fecha_inicio?: string

      fecha_fin?: string
    },
    config?: { signal?: AbortSignal }
  ): Promise<{
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

    if (filters?.concesionario)
      params.append('concesionario', filters.concesionario)

    if (filters?.modelo) params.append('modelo', filters.modelo)

    if (filters?.fecha_inicio)
      params.append('fecha_inicio', filters.fecha_inicio)

    if (filters?.fecha_fin) params.append('fecha_fin', filters.fecha_fin)

    const queryString = params.toString()

    return await apiClient.get(
      `${this.baseUrl}/stats${queryString ? '?' + queryString : ''}`,
      config
    )
  }

  // Obtener KPIs de pagos: 1) a cobrar en el mes, 2) cobrado en el mes, 3) morosidad %

  async getKPIs(
    mes?: number,
    anio?: number,
    config?: { signal?: AbortSignal }
  ): Promise<{
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

    return await apiClient.get(
      `${this.baseUrl}/kpis${queryString ? '?' + queryString : ''}`,
      config
    )
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

  // Descargar PDF tabla de amortización completa por cédula

  async descargarPDFAmortizacion(cedula: string): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `/api/v1/reportes/cliente/${encodeURIComponent(cedula)}/amortizacion.pdf`,

      { responseType: 'blob' }
    )

    return response.data as Blob
  }

  /** Pagos Gmail: pipeline Gmail -> Drive -> Gemini -> BD. Por defecto el backend usa scan_filter=all (toda la bandeja en orden). */

  async runGmailNow(
    force = true,
    scanFilter?:
      | 'unread'
      | 'read'
      | 'all'
      | 'pending_identification'
      | 'error_email_rescan'
  ): Promise<{
    sync_id: number | null
    status: string
    emails_processed?: number
    files_processed?: number
  }> {
    const params = new URLSearchParams({ force: String(force) })

    if (
      scanFilter &&
      [
        'unread',
        'read',
        'all',
        'pending_identification',
        'error_email_rescan',
      ].includes(scanFilter)
    ) {
      params.set('scan_filter', scanFilter)
    }

    return await apiClient.post(
      `${this.baseUrl}/gmail/run-now?${params.toString()}`
    )
  }

  /** Pagos Gmail: estado última ejecución, última fecha con datos; next_run_approx = próximo job programado en servidor (si aplica). */

  async getGmailStatus(): Promise<{
    last_run: string | null

    last_status: string | null

    last_emails: number

    last_files: number

    last_error?: string | null

    next_run_approx: string | null

    latest_data_date?: string | null

    last_correos_marcados_revision?: number

    /** Métricas diagnóstico última corrida (p. ej. hilos listados vs omitidos). */
    last_run_summary?: {
      scan_filter?: string
      gmail_messages_listed?: number
      messages_skipped_invalid_sender?: number
      messages_skipped_drive_folder?: number
      list_error?: boolean
      pipeline_error?: boolean
      comprobantes_digitados?: number
      pagos_validos_alta_automatica?: number
      pagos_invalidos_pendientes_revision?: number
      gemini_model?: string
    } | null
  }> {
    return await apiClient.get(`${this.baseUrl}/gmail/status`)
  }

  /** Pagos Gmail: confirmar día (sí/no). Si confirmado=true, se borran los datos del día en el servidor. */

  async confirmarDiaGmail(
    confirmado: boolean,
    fecha?: string
  ): Promise<{
    confirmado: boolean
    mensaje: string
    borrados?: number
    /** True si aún hay un pipeline Gmail en BD en estado running (run-now puede dar 409). */
    pipeline_running?: boolean
    blocking_sync_id?: number | null
  }> {
    const res = await apiClient.post<{
      confirmado: boolean
      mensaje: string
      borrados?: number
      pipeline_running?: boolean
      blocking_sync_id?: number | null
    }>(
      `${this.baseUrl}/gmail/confirmar-dia`,

      { confirmado, fecha }
    )

    return res
  }

  /** Gmail: mueve pendientes no autoconciliados a `pagos_con_errores` (A/B sin limbo). */
  async migrarPendientesGmailAConErrores(): Promise<{
    migrados: number
    omitidos: number
    eliminados_temporal: number
    mensaje: string
  }> {
    return await apiClient.post(`${this.baseUrl}/gmail/migrar-pendientes-a-con-errores`)
  }

  /** Pagos Gmail: descargar Excel (solo lectura en servidor). No borra datos; las filas se siguen acumulando. */

  async downloadGmailExcel(fecha?: string): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()

    const url = fecha
      ? `${this.baseUrl}/gmail/download-excel?fecha=${encodeURIComponent(fecha)}`
      : `${this.baseUrl}/gmail/download-excel`

    const response = await axiosInstance.get(url, {
      responseType: 'blob',

      timeout: 60000,
    })

    if (response.status !== 200) {
      const data = response.data as Blob

      try {
        const text = await data.text()

        const json = JSON.parse(text) as { detail?: string }

        throw new Error(
          json.detail || `Error al descargar (${response.status}).`
        )
      } catch (e) {
        if (
          e instanceof Error &&
          (e.message.includes('Sin datos') ||
            e.message.includes('ejecutar') ||
            e.message.includes('Error al descargar'))
        )
          throw e

        throw new Error(
          response.status === 404
            ? 'Sin datos para descargar. Ejecute "Generar Excel desde Gmail" primero.'
            : `No se pudo descargar el archivo (${response.status}).`
        )
      }
    }

    const blob = response.data as Blob

    const disposition = response.headers?.['content-disposition']

    let filename = 'Pagos_Gmail.xlsx'

    if (typeof disposition === 'string' && disposition.includes('filename=')) {
      const m = disposition.match(/filename=(.+?)(?:;|$)/)

      if (m) filename = m[1].replace(/^["']|["']$/g, '').trim()
    }

    const blobUrl = window.URL.createObjectURL(blob)

    const link = document.createElement('a')

    link.href = blobUrl

    link.download = filename

    document.body.appendChild(link)

    link.click()

    document.body.removeChild(link)

    window.URL.revokeObjectURL(blobUrl)
  }

  /** Pagos Gmail: Excel desde gmail_temporal (orden cronológico). No vacía la tabla; solo POST confirmar-dia vacía. */

  async downloadGmailExcelTemporal(): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()

    const url = `${this.baseUrl}/gmail/download-excel-temporal`

    const response = await axiosInstance.get(url, {
      responseType: 'blob',
      timeout: 60000,
    })

    if (response.status !== 200) {
      try {
        const text = await (response.data as Blob).text()

        const json = JSON.parse(text) as { detail?: string }

        throw new Error(
          json.detail || 'Error al descargar (' + response.status + ').'
        )
      } catch (e) {
        if (e instanceof Error) throw e

        throw new Error(
          response.status === 404
            ? 'No hay datos en la tabla temporal.'
            : 'No se pudo descargar (' + response.status + ').'
        )
      }
    }

    const blob = response.data as Blob

    const disposition = response.headers?.['content-disposition']

    let filename = 'Pagos_Gmail_temporal.xlsx'

    if (typeof disposition === 'string' && disposition.includes('filename=')) {
      const m = disposition.match(/filename=(.+?)(?:;|$)/)

      if (m) filename = m[1].replace(/^["']|["']$/g, '').trim()
    }

    const blobUrl = window.URL.createObjectURL(blob)

    const link = document.createElement('a')

    link.href = blobUrl

    link.download = filename

    document.body.appendChild(link)

    link.click()

    document.body.removeChild(link)

    window.URL.revokeObjectURL(blobUrl)
  }
}

/**
 * Ruta API /api/v1/pagos/comprobante-imagen/{id32} extraida de URL absoluta o relativa.
 */
export function comprobanteImagenApiPathDesdeLink(link: string): string | null {
  const s = (link || '').trim()
  const needle = '/api/v1/pagos/comprobante-imagen/'
  const i = s.indexOf(needle)
  if (i === -1) return null
  const path = s.slice(i)
  if (!/^\/api\/v1\/pagos\/comprobante-imagen\/[a-f0-9]{32}$/i.test(path)) {
    return null
  }
  return path
}

export const pagoService = new PagoService()
