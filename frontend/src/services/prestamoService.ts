import { apiClient, ApiResponse, PaginatedResponse, buildUrl } from './api'
import { Prestamo, PrestamoForm } from '../types'
import { logger } from '../utils/logger'

// Constantes de configuraciÃÂ³n
const DEFAULT_PER_PAGE = 20

// Tipo para el resumen de prÃÂ©stamos
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

class PrestamoService {
  private baseUrl = '/api/v1/prestamos'

  // Obtener lista de prÃÂ©stamos con filtros y paginaciÃÂ³n
  async getPrestamos(
    filters?: {
      search?: string
      estado?: string
      cedula?: string
      cliente_id?: number
      analista?: string
      concesionario?: string
      modelo?: string
      fecha_inicio?: string
      fecha_fin?: string
      requiere_revision?: boolean
    },
    page: number = 1,
    perPage: number = DEFAULT_PER_PAGE
  ): Promise<PaginatedResponse<Prestamo>> {
    const params: any = { ...filters, page, per_page: perPage }
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
    const items = Array.isArray(body?.prestamos) ? body.prestamos : (body?.data ? [])
    const total = body?.total ? 0
    const perPageResp = body?.per_page ? perPage

    const result = {
      data: items,
      total,
      page: body?.page ? page,
      per_page: perPageResp,
      total_pages: body?.total_pages ? (total ? Math.ceil(total / perPageResp) : 0)
    }

    return result
  }

  // Obtener prÃÂ©stamo por ID (backend devuelve el objeto directamente, no { data })
  async getPrestamo(id: number): Promise<Prestamo> {
    return await apiClient.get<Prestamo>(`${this.baseUrl}/${id}`)
  }

  // Crear nuevo prÃÂ©stamo (backend devuelve el prÃÂ©stamo creado directamente)
  async createPrestamo(data: PrestamoForm): Promise<Prestamo> {
    return await apiClient.post<Prestamo>(this.baseUrl, data)
  }

  // --- Revisar PrÃÂ©stamos (prestamos_con_errores) ---

  /** Lista de prÃÂ©stamos enviados a revisiÃÂ³n (paginado) */
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
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) })
    return await apiClient.get(`${this.baseUrl}/revisar/lista?${params}`)
  }

  /** Enviar una fila a Revisar PrÃÂ©stamos (desde carga masiva). */
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

  /** Eliminar de la lista Revisar PrÃÂ©stamos (marcar como resuelto) */
  async resolverPrestamoError(errorId: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/revisar/${errorId}`)
  }

  /** Elimina de prestamos_con_errores tras descargar Excel (misma regla que Pagos). La lista se vacÃÂ­a y se rellena al enviar desde Carga Masiva. */
  async eliminarPorDescarga(ids: number[]): Promise<{ eliminados: number; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/revisar/eliminar-por-descarga`, { ids }, { timeout: 120000 })
  }

  // Actualizar prÃÂ©stamo (backend devuelve el prÃÂ©stamo actualizado directamente)
  async updatePrestamo(id: number, data: Partial<PrestamoForm>): Promise<Prestamo> {
    return await apiClient.put<Prestamo>(`${this.baseUrl}/${id}`, data)
  }

  // Buscar prÃÂ©stamos por cÃÂ©dula (normaliza: sin guiones, trim)
  async getPrestamosByCedula(cedula: string): Promise<Prestamo[]> {
    const cedulaNorm = (cedula || '').trim().replace(/-/g, '')
    if (!cedulaNorm) return []
    const response = await apiClient.get<Prestamo[]>(`${this.baseUrl}/cedula/${encodeURIComponent(cedulaNorm)}`)
    
    if (Array.isArray(response)) return response
    if (response && typeof response === 'object') {
      const arr = (response as any).prestamos || (response as any).data
      if (Array.isArray(arr)) return arr
    }
    return []
  }

  /**
   * Batch: obtener prÃÂ©stamos para mÃÂºltiples cÃÂ©dulas en una sola peticiÃÂ³n.
   * Evita timeouts cuando hay muchas cÃÂ©dulas en carga masiva.
   */
  async getPrestamosByCedulasBatch(cedulas: string[]): Promise<Record<string, Prestamo[]>> {
    const cedulasNorm = [...new Set((cedulas || []).map((c) => (c || '').trim().replace(/-/g, '')).filter((c) => c.length >= 5))]
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

  // Obtener resumen de prÃÂ©stamos por cÃÂ©dula (saldo, mora, etc.)
  async getResumenPrestamos(cedula: string): Promise<ResumenPrestamos> {
    const response = await apiClient.get<ResumenPrestamos>(`${this.baseUrl}/cedula/${cedula}/resumen`)
    return response
  }

  // Obtener historial de auditorÃÂ­a de un prÃÂ©stamo
  async getAuditoria(prestamoId: number): Promise<any[]> {
    const response = await apiClient.get<any[]>(`${this.baseUrl}/${prestamoId}/auditoria`)
    return response
  }

  // Eliminar prÃÂ©stamo (solo Admin)
  async deletePrestamo(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  // BÃÂºsqueda general
  async searchPrestamos(query: string): Promise<Prestamo[]> {
    const response = await apiClient.get<Prestamo[]>(
      buildUrl(this.baseUrl, { search: query })
    )
    return response
  }

  // Evaluar riesgo de un prÃÂ©stamo
  async evaluarRiesgo(prestamoId: number, datos: any): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/evaluar-riesgo`,
      datos
    )
    return response
  }

  // Obtener cuotas (tabla de amortizaciÃÂ³n) de un prÃÂ©stamo
  async getCuotasPrestamo(prestamoId: number): Promise<any[]> {
    const response = await apiClient.get<any[]>(`${this.baseUrl}/${prestamoId}/cuotas`)
    return response
  }

  /**
   * Descarga la tabla de amortizaciÃÂ³n en Excel (vÃÂ­a API, sin depender de exceljs en el frontend).
   */
  async descargarAmortizacionExcel(prestamoId: number, cedula: string): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/${prestamoId}/amortizacion/excel`,
      { responseType: 'blob' }
    )
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
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

  // Generar tabla de amortizaciÃÂ³n
  async generarAmortizacion(prestamoId: number): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/generar-amortizacion`
    )
    return response
  }

  /**
   * Reconciliar amortizaciÃÂ³n masiva: aplica pagos conciliados a cuotas
   * (ÃÂºtil tras regenerar tabla de amortizaciÃÂ³n). Si prestamoIds es vacÃÂ­o, procesa todos los que tengan pagos pendientes de aplicar.
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
    }>(`${this.baseUrl}/conciliar-amortizacion-masiva`, { prestamo_ids: prestamoIds ? null }, { timeout: 120000 })
  }

  // Aplicar condiciones de aprobaciÃÂ³n
  async aplicarCondicionesAprobacion(prestamoId: number, condiciones: any): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/aplicar-condiciones-aprobacion`,
      condiciones
    )
    return response
  }

  // Obtener KPIs de prÃÂ©stamos mensuales desde /prestamos/stats (mes/aÃÂ±o por defecto = actual)
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
            ...(filters.concesionario && { concesionario: filters.concesionario }),
            ...(filters.modelo && { modelo: filters.modelo }),
            mes: filters.mes ? now.getMonth() + 1,
            anio: filters.anio ? now.getFullYear(),
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
      const total = body?.total ? 0
      return {
        totalFinanciamiento: body?.total_financiamiento ? 0,
        totalPrestamos: total,
        promedioMonto: body?.promedio_monto ? 0,
        totalCarteraVigente: body?.cartera_vigente ? 0,
        mes: body?.mes,
        anio: body?.anio,
      }
    } catch (err) {
      logger.error('getKPIs prestamos/stats fallÃÂ³', { error: err, params: { mes: filters?.mes, anio: filters?.anio } })
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

  // Marcar/desmarcar prÃÂ©stamo como requiere revisiÃÂ³n
  async marcarRevision(prestamoId: number, requiereRevision: boolean): Promise<any> {
    const response = await apiClient.patch<any>(
      `${this.baseUrl}/${prestamoId}/marcar-revision?requiere_revision=${requiereRevision}`
    )
    return response
  }

  // Asignar fecha de aprobaciÃÂ³n y recalcular tabla de amortizaciÃÂ³n
  async asignarFechaAprobacion(prestamoId: number, fechaAprobacion: string): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/asignar-fecha-aprobacion`,
      { fecha_aprobacion: fechaAprobacion }
    )
    return response
  }

  // AprobaciÃÂ³n manual de riesgo (reemplaza evaluaciÃÂ³n 7 criterios + aplicar condiciones + asignar fecha)
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
    return await apiClient.post<{ prestamo: Prestamo; cuotas_generadas: number }>(
      `${this.baseUrl}/${prestamoId}/aprobar-manual`,
      body
    )
  }

  // Obtener evaluaciÃÂ³n de riesgo de un prÃÂ©stamo
  async getEvaluacionRiesgo(prestamoId: number): Promise<any> {
    const response = await apiClient.get<any>(`${this.baseUrl}/${prestamoId}/evaluacion-riesgo`)
    return response
  }

  // Descargar estado de cuenta PDF (privado, autenticado)
  async descargarEstadoCuentaPDF(prestamoId: number): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/${prestamoId}/estado-cuenta/pdf`,
      { responseType: 'blob' }
    )
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Estado_Cuenta_Prestamo_${prestamoId}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }
}

export const prestamoService = new PrestamoService()
logger.info('Servicio de prÃÂ©stamos inicializado')

