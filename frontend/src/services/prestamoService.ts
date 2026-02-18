import { apiClient, ApiResponse, PaginatedResponse, buildUrl } from './api'
import { Prestamo, PrestamoForm } from '../types'
import { logger } from '../utils/logger'

// Constantes de configuración
const DEFAULT_PER_PAGE = 20

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

class PrestamoService {
  private baseUrl = '/api/v1/prestamos'

  // Obtener lista de préstamos con filtros y paginación
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
    const items = Array.isArray(body?.prestamos) ? body.prestamos : (body?.data ?? [])
    const total = body?.total ?? 0
    const perPageResp = body?.per_page ?? perPage

    const result = {
      data: items,
      total,
      page: body?.page ?? page,
      per_page: perPageResp,
      total_pages: body?.total_pages ?? (total ? Math.ceil(total / perPageResp) : 0)
    }

    return result
  }

  // Obtener préstamo por ID (backend devuelve el objeto directamente, no { data })
  async getPrestamo(id: number): Promise<Prestamo> {
    return await apiClient.get<Prestamo>(`${this.baseUrl}/${id}`)
  }

  // Crear nuevo préstamo (backend devuelve el préstamo creado directamente)
  async createPrestamo(data: PrestamoForm): Promise<Prestamo> {
    return await apiClient.post<Prestamo>(this.baseUrl, data)
  }

  // Actualizar préstamo (backend devuelve el préstamo actualizado directamente)
  async updatePrestamo(id: number, data: Partial<PrestamoForm>): Promise<Prestamo> {
    return await apiClient.put<Prestamo>(`${this.baseUrl}/${id}`, data)
  }

  // Buscar préstamos por cédula
  async getPrestamosByCedula(cedula: string): Promise<Prestamo[]> {
    // El endpoint devuelve directamente una lista, no envuelta en ApiResponse
    const response = await apiClient.get<Prestamo[]>(`${this.baseUrl}/cedula/${cedula}`)
    
    if (Array.isArray(response)) return response
    if (response && typeof response === 'object') {
      const arr = (response as any).prestamos || (response as any).data
      if (Array.isArray(arr)) return arr
    }
    return []
  }

  // Obtener resumen de préstamos por cédula (saldo, mora, etc.)
  async getResumenPrestamos(cedula: string): Promise<ResumenPrestamos> {
    const response = await apiClient.get<ResumenPrestamos>(`${this.baseUrl}/cedula/${cedula}/resumen`)
    return response
  }

  // Obtener historial de auditoría de un préstamo
  async getAuditoria(prestamoId: number): Promise<any[]> {
    const response = await apiClient.get<any[]>(`${this.baseUrl}/${prestamoId}/auditoria`)
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
  async getCuotasPrestamo(prestamoId: number): Promise<any[]> {
    const response = await apiClient.get<any[]>(`${this.baseUrl}/${prestamoId}/cuotas`)
    return response
  }

  // Generar tabla de amortización
  async generarAmortizacion(prestamoId: number): Promise<any> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/${prestamoId}/generar-amortizacion`
    )
    return response
  }

  // Aplicar condiciones de aprobación
  async aplicarCondicionesAprobacion(prestamoId: number, condiciones: any): Promise<any> {
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
    año?: number
  }): Promise<{
    totalFinanciamiento: number
    totalPrestamos: number
    promedioMonto: number
    totalCarteraVigente: number
    mes?: number
    año?: number
  }> {
    try {
      const now = new Date()
      const params: Record<string, string | number> = filters
        ? {
            ...(filters.analista && { analista: filters.analista }),
            ...(filters.concesionario && { concesionario: filters.concesionario }),
            ...(filters.modelo && { modelo: filters.modelo }),
            mes: filters.mes ?? now.getMonth() + 1,
            año: filters.año ?? now.getFullYear(),
          }
        : { mes: now.getMonth() + 1, año: now.getFullYear() }
      const url = buildUrl(`${this.baseUrl}/stats`, params)
      const body = await apiClient.get<{
        total?: number
        por_estado?: Record<string, number>
        total_financiamiento?: number
        promedio_monto?: number
        cartera_vigente?: number
        mes?: number
        año?: number
      }>(url)
      const total = body?.total ?? 0
      return {
        totalFinanciamiento: body?.total_financiamiento ?? 0,
        totalPrestamos: total,
        promedioMonto: body?.promedio_monto ?? 0,
        totalCarteraVigente: body?.cartera_vigente ?? 0,
        mes: body?.mes,
        año: body?.año,
      }
    } catch {
      const now = new Date()
      return {
        totalFinanciamiento: 0,
        totalPrestamos: 0,
        promedioMonto: 0,
        totalCarteraVigente: 0,
        mes: now.getMonth() + 1,
        año: now.getFullYear(),
      }
    }
  }

  // Marcar/desmarcar préstamo como requiere revisión
  async marcarRevision(prestamoId: number, requiereRevision: boolean): Promise<any> {
    const response = await apiClient.patch<any>(
      `${this.baseUrl}/${prestamoId}/marcar-revision?requiere_revision=${requiereRevision}`
    )
    return response
  }

  // Asignar fecha de aprobación y recalcular tabla de amortización
  async asignarFechaAprobacion(prestamoId: number, fechaAprobacion: string): Promise<any> {
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
    return await apiClient.post<{ prestamo: Prestamo; cuotas_generadas: number }>(
      `${this.baseUrl}/${prestamoId}/aprobar-manual`,
      body
    )
  }

  // Obtener evaluación de riesgo de un préstamo
  async getEvaluacionRiesgo(prestamoId: number): Promise<any> {
    const response = await apiClient.get<any>(`${this.baseUrl}/${prestamoId}/evaluacion-riesgo`)
    return response
  }
}

export const prestamoService = new PrestamoService()
logger.info('Servicio de préstamos inicializado')
