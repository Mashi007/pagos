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

class ReporteService {
  private baseUrl = '/api/v1/reportes'

  /**
   * Obtiene reporte de cartera
   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual
   */
  async getReporteCartera(fechaCorte?: string): Promise<ReporteCartera> {
    const params = fechaCorte ? `?fecha_corte=${fechaCorte}` : ''
    return await apiClient.get(`${this.baseUrl}/cartera${params}`)
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
    return await apiClient.get(
      `${this.baseUrl}/pagos?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`
    )
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
      const blob = response.data as Blob
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

