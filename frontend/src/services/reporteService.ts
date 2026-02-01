import { apiClient } from './api'

export interface ReporteCartera {
  fecha_corte: string
  cartera_total: number
  capital_pendiente: number
  intereses_pendientes: number
  mora_total: number
  cantidad_prestamos_activos: number
  cantidad_prestamos_mora: number
  distribucion_por_monto: Array<{
    rango: string
    cantidad: number
    monto: number
  }>
  distribucion_por_mora: Array<{
    rango: string
    cantidad: number
    monto_total: number
  }>
}

export interface ReportePagos {
  fecha_inicio: string
  fecha_fin: string
  total_pagos: number
  cantidad_pagos: number
  pagos_por_metodo: Array<{
    metodo: string
    cantidad: number
    monto: number
  }>
  pagos_por_dia: Array<{
    fecha: string
    cantidad: number
    monto: number
  }>
}

export interface ResumenDashboard {
  total_clientes: number
  total_prestamos: number
  total_pagos: number
  cartera_activa: number
  prestamos_mora: number
  pagos_mes: number
  fecha_actualizacion: string
}

export interface ReporteMorosidad {
  fecha_corte: string
  total_prestamos_mora: number
  total_clientes_mora: number
  monto_total_mora: number
  promedio_dias_mora: number
  distribucion_por_rango: Array<{
    rango: string
    cantidad_prestamos: number
    cantidad_clientes: number
    cantidad_cuotas: number
    monto_total: number
  }>
  morosidad_por_analista: Array<{
    analista: string
    cantidad_prestamos: number
    cantidad_clientes: number
    monto_total_mora: number
    promedio_dias_mora: number
  }>
  detalle_prestamos: Array<{
    prestamo_id: number
    cedula: string
    nombres: string
    total_financiamiento: number
    analista: string
    concesionario: string
    cuotas_en_mora: number
    monto_total_mora: number
    max_dias_mora: number
    primera_cuota_vencida: string | null
  }>
}

export interface ReporteFinanciero {
  fecha_corte: string
  total_ingresos: number
  cantidad_pagos: number
  cartera_total: number
  cartera_pendiente: number
  morosidad_total: number
  saldo_pendiente: number
  porcentaje_cobrado: number
  ingresos_por_mes: Array<{
    mes: string
    cantidad_pagos: number
    monto_total: number
  }>
  egresos_programados: Array<{
    mes: string
    cantidad_cuotas: number
    monto_programado: number
  }>
  flujo_caja: Array<{
    mes: string
    ingresos: number
    egresos_programados: number
    flujo_neto: number
  }>
}

export interface ReporteAsesores {
  fecha_corte: string
  resumen_por_analista: Array<{
    analista: string
    total_prestamos: number
    total_clientes: number
    cartera_total: number
    morosidad_total: number
    total_cobrado: number
    porcentaje_cobrado: number
    porcentaje_morosidad: number
  }>
  desempeno_mensual: Array<{
    analista: string
    mes: string
    prestamos_aprobados: number
    monto_aprobado: number
    monto_cobrado: number
  }>
  clientes_por_analista: Array<{
    analista: string
    cedula: string
    nombres: string
    cantidad_prestamos: number
    monto_total_prestamos: number
    monto_total_pagado: number
    monto_mora: number
  }>
}

export interface ReporteProductos {
  fecha_corte: string
  resumen_por_producto: Array<{
    producto: string
    total_prestamos: number
    total_clientes: number
    cartera_total: number
    promedio_prestamo: number
    total_cobrado: number
    morosidad_total: number
    porcentaje_cobrado: number
  }>
  productos_por_concesionario: Array<{
    concesionario: string
    producto: string
    cantidad_prestamos: number
    monto_total: number
  }>
  tendencia_mensual: Array<{
    producto: string
    mes: string
    prestamos_aprobados: number
    monto_aprobado: number
  }>
}

class ReporteService {
  private baseUrl = '/api/v1/reportes'

  /**
   * Obtiene reporte de cartera
   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual
   */
  async getReporteCartera(fechaCorte?: string): Promise<ReporteCartera> {
    const params = new URLSearchParams()
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    const query = params.toString()
    return await apiClient.get(`${this.baseUrl}/cartera${query ? `?${query}` : ''}`)
  }

  /**
   * Obtiene reporte de pagos en un rango de fechas
   * @param fechaInicio Fecha de inicio (requerida)
   * @param fechaFin Fecha de fin (requerida)
   */
  async getReportePagos(
    fechaInicio: string,
    fechaFin: string
  ): Promise<ReportePagos> {
    const params = new URLSearchParams({ fecha_inicio: fechaInicio, fecha_fin: fechaFin })
    return await apiClient.get(`${this.baseUrl}/pagos?${params.toString()}`)
  }

  /**
   * Exporta reporte de cartera en Excel o PDF
   * @param formato 'excel' o 'pdf'
   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual
   */
  async exportarReporteCartera(
    formato: 'excel' | 'pdf',
    fechaCorte?: string
  ): Promise<Blob> {
    const params = new URLSearchParams({ formato })
    if (fechaCorte) {
      params.append('fecha_corte', fechaCorte)
    }
    // Usar directamente el cliente de axios para obtener el blob
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/cartera?${params.toString()}`,
      {
        responseType: 'blob',
      }
    )
    return response.data as Blob
  }

  /**
   * Obtiene resumen para dashboard
   */
  async getResumenDashboard(): Promise<ResumenDashboard> {
    return await apiClient.get(`${this.baseUrl}/dashboard/resumen`)
  }

  /**
   * Obtiene reporte de morosidad
   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual
   */
  async getReporteMorosidad(fechaCorte?: string): Promise<ReporteMorosidad> {
    const params = new URLSearchParams()
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    const query = params.toString()
    return await apiClient.get(`${this.baseUrl}/morosidad${query ? `?${query}` : ''}`)
  }

  /**
   * Obtiene reporte financiero
   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual
   */
  async getReporteFinanciero(fechaCorte?: string): Promise<ReporteFinanciero> {
    const params = new URLSearchParams()
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    const query = params.toString()
    return await apiClient.get(`${this.baseUrl}/financiero${query ? `?${query}` : ''}`)
  }

  /**
   * Obtiene reporte de asesores
   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual
   */
  async getReporteAsesores(fechaCorte?: string): Promise<ReporteAsesores> {
    const params = new URLSearchParams()
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    const query = params.toString()
    return await apiClient.get(`${this.baseUrl}/asesores${query ? `?${query}` : ''}`)
  }

  /**
   * Obtiene reporte de productos
   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual
   */
  async getReporteProductos(fechaCorte?: string): Promise<ReporteProductos> {
    const params = new URLSearchParams()
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    const query = params.toString()
    return await apiClient.get(`${this.baseUrl}/productos${query ? `?${query}` : ''}`)
  }

  /**
   * Descarga un archivo (Excel, PDF, CSV)
   */
  async downloadFile(
    url: string,
    filename: string
  ): Promise<void> {
    try {
      const axiosInstance = apiClient.getAxiosInstance()
      const response = await axiosInstance.get(url, {
        responseType: 'blob',
      })

      // Crear un enlace temporal para descargar
      const blob = new Blob([response.data as BlobPart], {
        type: response.headers['content-type'] || 'application/octet-stream'
      })
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (error) {
      console.error('Error descargando archivo:', error)
      throw error
    }
  }
}

export const reporteService = new ReporteService()

