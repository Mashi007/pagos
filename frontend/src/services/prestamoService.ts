import { apiClient, ApiResponse, PaginatedResponse, buildUrl } from './api'

import { Prestamo, PrestamoForm } from '../types'

import { logger } from '../utils/logger'

import {
  extraerCaracteresCedulaPublica,
  normalizarBusquedaPrestamosSearch,
  normalizarCedulaParaProcesar,
} from '../utils/cedulaConsultaPublica'

// Constantes de configuración

const DEFAULT_PER_PAGE = 10

// Tipo para el resumen de préstamos

type ResumenPrestamos = {
  tiene_prestamos: boolean

  total_prestamos: number

  total_saldo_pendiente?: number

  total_cuotas_mora?: number

  prestamos?: Array<{
    id: number

    modelo_vehiculo: string

    total_financiamiento: number

    saldo_pendiente: number

    cuotas_en_mora: number

    estado: string

    fecha_registro: string | null
  }>
}

/** Fila de GET /api/v1/prestamos/{id}/cuotas (estado + estado_etiqueta desde backend). */
export interface CuotaPrestamoApi {
  id: number

  prestamo_id: number

  pago_id?: number | null

  numero_cuota: number

  fecha_vencimiento: string | null

  monto: number

  monto_cuota: number

  monto_capital: number

  monto_interes: number

  saldo_capital_inicial: number

  saldo_capital_final: number

  capital_pagado?: number | null

  interes_pagado?: number | null

  total_pagado: number

  fecha_pago?: string | null

  estado: string

  estado_etiqueta: string

  dias_mora: number

  dias_morosidad: number

  pago_conciliado?: boolean

  pago_monto_conciliado?: number
}

class PrestamoService {
  private baseUrl = '/api/v1/prestamos'

  // Obtener lista de préstamos con filtros y paginación

  async getPrestamos(
    filters?: {
      search?: string

      prestamo_id?: number

      estado?: string

      cedula?: string

      cliente_id?: number

      analista?: string

      concesionario?: string

      modelo?: string

      fecha_inicio?: string

      fecha_fin?: string

      requiere_revision?: boolean

      revision_manual_estado?: string
    },

    page: number = 1,

    perPage: number = DEFAULT_PER_PAGE
  ): Promise<PaginatedResponse<Prestamo>> {
    const params: any = { ...filters, page, per_page: perPage }

    if (typeof params.cedula === 'string' && params.cedula.trim()) {
      const raw = params.cedula.trim()

      const v = normalizarCedulaParaProcesar(raw)

      if (v.valido && v.valorParaEnviar) {
        params.cedula = v.valorParaEnviar
      } else {
        const ext = extraerCaracteresCedulaPublica(raw)

        if (ext) params.cedula = ext
      }
    }

    if (typeof params.search === 'string' && params.search.trim()) {
      params.search = normalizarBusquedaPrestamosSearch(params.search)
    }

    // Convertir fechas a formato ISO si existen

    if (params.fecha_inicio) {
      params.fecha_inicio = params.fecha_inicio
    }

    if (params.fecha_fin) {
      params.fecha_fin = params.fecha_fin
    }

    const url = buildUrl(this.baseUrl, params)

    // apiClient.get devuelve el cuerpo de la respuesta (backend devuelve { prestamos, total, page, per_page, total_pages })

    const body = await apiClient.get<any>(url)

    // Backend devuelve "prestamos", no "data"; el frontend espera result.data como array

    const items = Array.isArray(body?.prestamos)
      ? body.prestamos
      : (body?.data ?? [])

    const total = body?.total ?? 0

    const perPageResp = body?.per_page ?? perPage

    const result = {
      data: items,

      total,

      page: body?.page ?? page,

      per_page: perPageResp,

      total_pages:
        body?.total_pages ?? (total ? Math.ceil(total / perPageResp) : 0),
    }

    return result
  }

  // Obtener préstamo por ID (backend devuelve el objeto directamente, no { data })

  async getPrestamo(id: number): Promise<Prestamo> {
    const raw = await apiClient.get<Prestamo & { modelo?: string }>(
      `${this.baseUrl}/${id}`
    )

    const mv =
      raw.modelo_vehiculo != null && String(raw.modelo_vehiculo).trim() !== ''
        ? String(raw.modelo_vehiculo).trim()
        : raw.modelo != null && String(raw.modelo).trim() !== ''
          ? String(raw.modelo).trim()
          : ''

    return {
      ...raw,
      modelo_vehiculo: mv,
    }
  }

  // Crear nuevo préstamo (backend devuelve el préstamo creado directamente)

  async createPrestamo(data: PrestamoForm): Promise<Prestamo> {
    return await apiClient.post<Prestamo>(this.baseUrl, data)
  }

  // Validar cupo de cédulas en carga masiva
  async checkCupoCedulas(cedulas: string[]): Promise<{
    cedulas: Array<{
      cedula: string
      cedula_normalizada: string
      prefijo: string | null
      max_aprobados: number | null
      aprobados_actuales: number
      puede_agregar: boolean
      error: string | null
    }>
  }> {
    return await apiClient.post(`${this.baseUrl}/check-cupo-cedulas`, { cedulas })
  }

  // --- Revisar Préstamos (prestamos_con_errores) ---

  /** Lista de préstamos enviados a revisión (paginado) */

  async getPrestamosConErrores(
    page = 1,

    perPage = 20
  ): Promise<{
    total: number

    page: number

    per_page: number

    items: Array<{
      id: number

      cedula_cliente: string | null

      total_financiamiento: string | null

      modalidad_pago: string | null

      numero_cuotas: number | null

      producto: string | null

      analista: string | null

      concesionario: string | null

      errores: string | null

      fila_origen: number | null

      estado: string | null

      fecha_registro: string | null
    }>
  }> {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    })

    return await apiClient.get(`${this.baseUrl}/revisar/lista?${params}`)
  }

  /** Enviar una fila a Revisar Préstamos (desde carga masiva). */

  async agregarPrestamoARevisar(data: {
    cedula_cliente?: string | null

    total_financiamiento?: number | null

    modalidad_pago?: string | null

    numero_cuotas?: number | null

    producto?: string | null

    analista?: string | null

    concesionario?: string | null

    errores_descripcion?: string | null

    fila_origen?: number | null
  }): Promise<{ id: number; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/revisar/agregar`, data)
  }

  /** Eliminar de la lista Revisar Préstamos (marcar como resuelto) */

  async resolverPrestamoError(errorId: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/revisar/${errorId}`)
  }

  /** Elimina de prestamos_con_errores tras descargar Excel (misma regla que Pagos). La lista se vacía y se rellena al enviar desde Carga Masiva. */

  async eliminarPorDescarga(
    ids: number[]
  ): Promise<{ eliminados: number; mensaje: string }> {
    return await apiClient.post(
      `${this.baseUrl}/revisar/eliminar-por-descarga`,
      { ids },
      { timeout: 120000 }
    )
  }

  // Actualizar préstamo (backend devuelve el préstamo actualizado directamente)

  async updatePrestamo(
    id: number,
    data: Partial<PrestamoForm> & Record<string, unknown>
  ): Promise<Prestamo> {
    const body = this.buildPrestamoUpdatePayload(data)

    return await apiClient.put<Prestamo>(`${this.baseUrl}/${id}`, body)
  }

  /**
   * Cuerpo PUT alineado con PrestamoUpdate (FastAPI): sin claves extra, sin cadenas vacías
   * en fechas (evitan 422) y numéricos finitos.
   */
  private buildPrestamoUpdatePayload(
    raw: Record<string, unknown>
  ): Record<string, unknown> {
    const keys = [
      'cliente_id',
      'total_financiamiento',
      'estado',
      'concesionario',
      'modelo',
      'analista',
      'modalidad_pago',
      'numero_cuotas',
      'fecha_requerimiento',
      'fecha_aprobacion',
      'cuota_periodo',
      'producto',
      'valor_activo',
      'observaciones',
      'fecha_base_calculo',
      'tasa_interes',
    ] as const

    const dateKeys = new Set<string>([
      'fecha_requerimiento',
      'fecha_aprobacion',
      'fecha_base_calculo',
    ])

    const numericKeys = new Set<string>([
      'cliente_id',
      'numero_cuotas',
      'total_financiamiento',
      'cuota_periodo',
      'tasa_interes',
      'valor_activo',
    ])

    const out: Record<string, unknown> = {}

    for (const key of keys) {
      const v = raw[key]

      if (v === undefined) continue

      if (dateKeys.has(key) && (v === '' || v === null)) continue

      if (numericKeys.has(key)) {
        const n = typeof v === 'number' ? v : Number(v)

        if (!Number.isFinite(n)) continue

        out[key] = n

        continue
      }

      out[key] = v
    }

    // Debugging log para rastrear qué se envía
    if (import.meta.env.DEV) {
      console.log(
        '[prestamoService] Payload enviado al backend:',
        JSON.stringify(out, null, 2)
      )
      console.log(
        '[prestamoService] Raw data antes de filtrado:',
        JSON.stringify(raw, null, 2)
      )
    }

    return out
  }

  // Buscar préstamos por cédula (normaliza: sin guiones, trim)

  async getPrestamosByCedula(cedula: string): Promise<Prestamo[]> {
    const cedulaNorm = (cedula || '').trim().replace(/-/g, '')

    if (!cedulaNorm) return []

    const response = await apiClient.get<Prestamo[]>(
      `${this.baseUrl}/cedula/${encodeURIComponent(cedulaNorm)}`
    )

    if (Array.isArray(response)) return response

    if (response && typeof response === 'object') {
      const arr = (response as any).prestamos || (response as any).data

      if (Array.isArray(arr)) return arr
    }

    return []
  }

  /**









   * Batch: obtener préstamos para múltiples cédulas en una sola petición.









   * Evita timeouts cuando hay muchas cédulas en carga masiva.









   */

  async getPrestamosByCedulasBatch(
    cedulas: string[]
  ): Promise<Record<string, Prestamo[]>> {
    const cedulasNorm = [
      ...new Set(
        (cedulas || [])
          .map(c => (c || '').trim().replace(/-/g, ''))
          .filter(c => c.length >= 5)
      ),
    ]

    if (cedulasNorm.length === 0) return {}

    const response = await apiClient.post<{ prestamos: Record<string, any[]> }>(
      `${this.baseUrl}/cedula/batch`,

      { cedulas: cedulasNorm },

      { timeout: 60000 }
    )

    const prestamos = (response as any)?.prestamos || {}

    const result: Record<string, Prestamo[]> = {}

    for (const ced of cedulasNorm) {
      const arr = prestamos[ced] || []

      result[ced] = Array.isArray(arr) ? arr : []

      const cedSinGuion = ced.replace(/-/g, '')

      if (cedSinGuion !== ced) result[cedSinGuion] = result[ced]
    }

    return result
  }

  // Obtener resumen de préstamos por cédula (saldo, mora, etc.)

  async getResumenPrestamos(cedula: string): Promise<ResumenPrestamos> {
    const response = await apiClient.get<ResumenPrestamos>(
      `${this.baseUrl}/cedula/${cedula}/resumen`
    )

    return response
  }

  // Obtener historial de auditoría de un préstamo

  async getAuditoria(prestamoId: number): Promise<any[]> {
    const response = await apiClient.get<any[]>(
      `${this.baseUrl}/${prestamoId}/auditoria`
    )

    return response
  }

  // Eliminar préstamo (solo Admin)

  async deletePrestamo(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  // Búsqueda general

  async searchPrestamos(query: string): Promise<Prestamo[]> {
    const response = await apiClient.get<Prestamo[]>(
      buildUrl(this.baseUrl, { search: query })
    )

    return response
  }

  // Evaluar riesgo de un préstamo

  async evaluarRiesgo(prestamoId: number, datos: any): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/evaluar-riesgo`,

      datos
    )

    return response
  }

  // Obtener cuotas (tabla de amortización) de un préstamo

  async getCuotasPrestamo(prestamoId: number): Promise<CuotaPrestamoApi[]> {
    return await apiClient.get<CuotaPrestamoApi[]>(
      `${this.baseUrl}/${prestamoId}/cuotas`
    )
  }

  /**









   * Descarga la tabla de amortización en Excel (vía API, sin depender de exceljs en el frontend).









   */

  async descargarAmortizacionExcel(
    prestamoId: number,
    cedula: string
  ): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/${prestamoId}/amortizacion/excel`,

      { responseType: 'blob' }
    )

    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })

    const urlBlob = window.URL.createObjectURL(blob)

    const link = document.createElement('a')

    link.href = urlBlob

    link.download = `Tabla_Amortizacion_${cedula}_${prestamoId}.xlsx`

    document.body.appendChild(link)

    link.click()

    document.body.removeChild(link)

    window.URL.revokeObjectURL(urlBlob)
  }

  /**









   * Recibo PDF de una cuota (mismo formato que cobros). Abre en nueva pestana.









   */

  async getReciboCuotaPdf(prestamoId: number, cuotaId: number): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/${prestamoId}/cuotas/${cuotaId}/recibo.pdf`,

      { responseType: 'blob' }
    )

    const blob = new Blob([response.data], { type: 'application/pdf' })

    const url = window.URL.createObjectURL(blob)

    window.open(url, '_blank')
  }

  // Generar tabla de amortización

  async generarAmortizacion(prestamoId: number): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/generar-amortizacion`
    )

    return response
  }

  // Recalcular fechas de vencimiento de cuotas (cuando cambia fecha de aprobación)
  async recalcularFechasAmortizacion(prestamoId: number): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/recalcular-fechas-amortizacion`
    )

    return response
  }

  /**
   * Elimina y regenera filas de cuotas según datos del préstamo en BD (total, plazo,
   * modalidad, cuota por período si tasa 0, fecha base). Reaplica pagos pendientes.
   */
  async reconstruirTablaCuotasDesdePrestamo(prestamoId: number): Promise<any> {
    return await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/reconstruir-tabla-cuotas-desde-prestamo`
    )
  }

  /**









   * Reconciliar amortización masiva: aplica pagos conciliados a cuotas









   * (útil tras regenerar tabla de amortización). Si prestamoIds es vacío, procesa todos los que tengan pagos pendientes de aplicar.









   */

  async conciliarAmortizacionMasiva(prestamoIds?: number[]): Promise<{
    procesados: number

    pagos_aplicados_total: number

    errores: Array<{ prestamo_id: number; error: string }>

    mensaje: string
  }> {
    return await apiClient.post<{
      procesados: number

      pagos_aplicados_total: number

      errores: Array<{ prestamo_id: number; error: string }>

      mensaje: string
    }>(
      `${this.baseUrl}/conciliar-amortizacion-masiva`,
      { prestamo_ids: prestamoIds ?? null },
      { timeout: 120000 }
    )
  }

  // Aplicar condiciones de aprobación

  async aplicarCondicionesAprobacion(
    prestamoId: number,
    condiciones: any
  ): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/aplicar-condiciones-aprobacion`,

      condiciones
    )

    return response
  }

  // Obtener KPIs de préstamos mensuales desde /prestamos/stats (mes/año por defecto = actual)

  async getKPIs(filters?: {
    analista?: string

    concesionario?: string

    modelo?: string

    fecha_inicio?: string

    fecha_fin?: string

    mes?: number

    anio?: number
  }): Promise<{
    totalFinanciamiento: number

    totalPrestamos: number

    promedioMonto: number

    totalCarteraVigente: number

    mes?: number

    anio?: number
  }> {
    try {
      const now = new Date()

      const params: Record<string, string | number> = filters
        ? {
            ...(filters.analista && { analista: filters.analista }),

            ...(filters.concesionario && {
              concesionario: filters.concesionario,
            }),

            ...(filters.modelo && { modelo: filters.modelo }),

            mes: filters.mes ?? now.getMonth() + 1,

            anio: filters.anio ?? now.getFullYear(),
          }
        : { mes: now.getMonth() + 1, anio: now.getFullYear() }

      const url = buildUrl(`${this.baseUrl}/stats`, params)

      const body = await apiClient.get<{
        total?: number

        por_estado?: Record<string, number>

        total_financiamiento?: number

        promedio_monto?: number

        cartera_vigente?: number

        mes?: number

        anio?: number
      }>(url)

      const total = body?.total ?? 0

      return {
        totalFinanciamiento: body?.total_financiamiento ?? 0,

        totalPrestamos: total,

        promedioMonto: body?.promedio_monto ?? 0,

        totalCarteraVigente: body?.cartera_vigente ?? 0,

        mes: body?.mes,

        anio: body?.anio,
      }
    } catch (err) {
      logger.error('getKPIs prestamos/stats falló', {
        error: err,
        params: { mes: filters?.mes, anio: filters?.anio },
      })

      const now = new Date()

      return {
        totalFinanciamiento: 0,

        totalPrestamos: 0,

        promedioMonto: 0,

        totalCarteraVigente: 0,

        mes: now.getMonth() + 1,

        anio: now.getFullYear(),
      }
    }
  }

  // Marcar/desmarcar préstamo como requiere revisión

  async marcarRevision(
    prestamoId: number,
    requiereRevision: boolean
  ): Promise<any> {
    const response = await apiClient.patch<any>(
      `${this.baseUrl}/${prestamoId}/marcar-revision?requiere_revision=${requiereRevision}`
    )

    return response
  }

  // Asignar fecha de aprobación y recalcular tabla de amortización

  async asignarFechaAprobacion(
    prestamoId: number,
    fechaAprobacion: string
  ): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/asignar-fecha-aprobacion`,

      { fecha_aprobacion: fechaAprobacion }
    )

    return response
  }

  // Aprobación manual de riesgo (reemplaza evaluación 7 criterios + aplicar condiciones + asignar fecha)

  async aprobarManual(
    prestamoId: number,

    body: {
      fecha_aprobacion: string

      acepta_declaracion: boolean

      documentos_analizados: boolean

      total_financiamiento?: number

      numero_cuotas?: number

      modalidad_pago?: string

      cuota_periodo?: number

      tasa_interes?: number

      observaciones?: string
    }
  ): Promise<{ prestamo: Prestamo; cuotas_generadas: number }> {
    return await apiClient.post<{
      prestamo: Prestamo
      cuotas_generadas: number
    }>(
      `${this.baseUrl}/${prestamoId}/aprobar-manual`,

      body
    )
  }

  // Obtener evaluación de riesgo de un préstamo

  async getEvaluacionRiesgo(prestamoId: number): Promise<any> {
    const response = await apiClient.get<any>(
      `${this.baseUrl}/${prestamoId}/evaluacion-riesgo`
    )

    return response
  }

  // Descargar estado de cuenta PDF (privado, autenticado)

  /**
   * PDF de estado de cuenta (mismo formato que rapicredit-estadocuenta).
   * GET /api/v1/prestamos/{id}/estado-cuenta/pdf
   */
  async descargarEstadoCuentaPDF(prestamoId: number): Promise<void> {
    // En movil los navegadores bloquean window.open fuera de evento de usuario;
    // se detecta movil por ancho de pantalla o touch points y se fuerza descarga.
    const isMobileDevice =
      window.innerWidth < 768 || navigator.maxTouchPoints > 0

    const previewWindow = isMobileDevice
      ? null
      : window.open('', '_blank', 'noopener,noreferrer')

    try {
      const axiosInstance = apiClient.getAxiosInstance()

      const response = await axiosInstance.get(
        `${this.baseUrl}/${prestamoId}/estado-cuenta/pdf`,
        { responseType: 'blob' }
      )

      const raw: Blob =
        response.data instanceof Blob
          ? response.data
          : new Blob([response.data])
      // Un solo ArrayBuffer evita PDFs corruptos al guardar (Blob dentro de Blob).
      const pdfBuffer = await raw.arrayBuffer()
      const head = new Uint8Array(pdfBuffer.slice(0, 5))
      const looksPdf =
        head[0] === 0x25 &&
        head[1] === 0x50 &&
        head[2] === 0x44 &&
        head[3] === 0x46
      const ct = String(
        response.headers?.['content-type'] ||
          response.headers?.['Content-Type'] ||
          ''
      )
      const looksExcel =
        ct.includes('spreadsheet') ||
        ct.includes('excel') ||
        ct.includes('officedocument.spreadsheetml') ||
        (head[0] === 0x50 && head[1] === 0x4b)

      if (!looksPdf && looksExcel) {
        throw new Error(
          'La respuesta no es un PDF de estado de cuenta (se recibio Excel). Actualice la aplicacion o revise el despliegue.'
        )
      }
      if (!looksPdf && !ct.includes('pdf')) {
        throw new Error(
          'La respuesta no es un PDF valido. Verifique sesion e intente de nuevo.'
        )
      }

      const blob = new Blob([pdfBuffer], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      if (previewWindow) {
        previewWindow.location.href = url
      } else {
        const link = document.createElement('a')
        link.href = url
        link.download = `Estado_Cuenta_${prestamoId}.pdf`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000)
    } catch (error) {
      if (previewWindow && !previewWindow.closed) {
        previewWindow.close()
      }
      throw error
    }
  }

  /**
   * Mismo payload que el PDF de estado de cuenta (JSON).
   * GET /api/v1/prestamos/{id}/estado-cuenta
   */
  async getEstadoCuentaJson(
    prestamoId: number
  ): Promise<Record<string, unknown>> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/${prestamoId}/estado-cuenta`
    )
    return response.data as Record<string, unknown>
  }

  /**
   * Admin. Reset cuota_pagos del prestamo y reaplica pagos conciliados en cascada.
   * POST /api/v1/prestamos/{id}/reaplicar-cascada-aplicacion
   */
  async reaplicarCascadaAplicacion(
    prestamoId: number
  ): Promise<Record<string, unknown>> {
    return apiClient.post<Record<string, unknown>>(
      `${this.baseUrl}/${prestamoId}/reaplicar-cascada-aplicacion`,
      undefined,
      { timeout: 120000 }
    )
  }

  /** Admin. Igual que reaplicarCascadaAplicacion pero varios prestamos (max 500). */
  async reaplicarCascadaMasiva(
    prestamoIds: number[]
  ): Promise<Record<string, unknown>> {
    return apiClient.post<Record<string, unknown>>(
      `${this.baseUrl}/reaplicar-cascada-aplicacion-masiva`,
      { prestamo_ids: prestamoIds },
      { timeout: 300000 }
    )
  }
}

export const prestamoService = new PrestamoService()

logger.info('Servicio de préstamos inicializado')
