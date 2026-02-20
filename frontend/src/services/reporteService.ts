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

export interface CarteraPorDiaItem {
  dia: number
  cantidad_cuotas: number
  monto_cobrar: number
}

export interface CarteraPorMes {
  meses: Array<{
    mes: number
    año: number
    label: string
    items: CarteraPorDiaItem[]
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

export interface PagoPorMesItem {
  pago_id?: number
  fecha: string
  prestamo_id: number | null
  cedula: string
  nombre: string
  monto_pago: number
  documento: string
}

export interface PagosPorMes {
  meses: Array<{
    mes: number
    año: number
    label: string
    items: PagoPorMesItem[]
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

export interface MorosidadPorRangosItem {
  prestamo_id: number
  cedula: string
  nombres: string
  total_financiamiento: number
  pagos_totales: number
  saldo: number
  ultimo_pago_fecha: string | null
  proximo_pago_fecha: string | null
  dias_atraso: number
}

export interface MorosidadPorRangos {
  fecha_corte: string
  rangos: Record<string, { label: string; items: MorosidadPorRangosItem[] }>
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

export interface AsesorPorMesItem {
  analista: string
  vencimiento_total: number
  total_prestamos: number
}

export interface AsesoresPorMes {
  meses: Array<{
    mes: number
    año: number
    label: string
    items: AsesorPorMesItem[]
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

export interface ProductoPorMesItem {
  modelo: string
  total_financiamiento: number
  valor_activo: number
}

export interface ProductosPorMes {
  meses: Array<{
    mes: number
    año: number
    label: string
    items: ProductoPorMesItem[]
  }>
}

class ReporteService {
  private baseUrl = '/api/v1/reportes'

  /**
   * Obtiene cuentas por cobrar por mes: por día cuándo debe cobrar
   */
  async getCarteraPorMes(meses: number = 12): Promise<CarteraPorMes> {
    const params = new URLSearchParams({ meses: meses.toString() })
    return await apiClient.get(`${this.baseUrl}/cartera/por-mes?${params.toString()}`)
  }

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
   * Obtiene pagos agrupados por mes/año. Cada mes tiene lista ordenada descendente por fecha.
   */
  async getPagosPorMes(meses: number = 12): Promise<PagosPorMes> {
    const params = new URLSearchParams({ meses: meses.toString() })
    return await apiClient.get(`${this.baseUrl}/pagos/por-mes?${params.toString()}`)
  }

  /**
   * Exporta reporte de cartera en Excel o PDF
   * @param filtros años y meses seleccionados (para Excel)
   */
  async exportarReporteCartera(
    formato: 'excel' | 'pdf',
    fechaCorte?: string,
    filtros?: { años: number[]; meses: number[] }
  ): Promise<Blob> {
    const params = new URLSearchParams({ formato })
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    if (filtros?.años?.length) params.set('años', filtros.años.join(','))
    if (filtros?.meses?.length) params.set('meses_list', filtros.meses.join(','))
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/cartera?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
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
   * Obtiene informe pago vencido por rangos de días (1 día, 15 días, 30 días, 2 meses, 90+ moroso)
   */
  async getMorosidadPorRangos(fechaCorte?: string): Promise<MorosidadPorRangos> {
    const params = new URLSearchParams()
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    const query = params.toString()
    return await apiClient.get(`${this.baseUrl}/morosidad/por-rangos${query ? `?${query}` : ''}`)
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
   * Obtiene asesores por mes: una pestaña por mes, orden descendente por morosidad
   */
  async getAsesoresPorMes(meses: number = 12): Promise<AsesoresPorMes> {
    const params = new URLSearchParams({ meses: meses.toString() })
    return await apiClient.get(`${this.baseUrl}/asesores/por-mes?${params.toString()}`)
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
   * Obtiene productos por mes: modelo y suma ventas (70% valor prestado) por modelo
   */
  async getProductosPorMes(meses: number = 12): Promise<ProductosPorMes> {
    const params = new URLSearchParams({ meses: meses.toString() })
    return await apiClient.get(`${this.baseUrl}/productos/por-mes?${params.toString()}`)
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
   * Exporta reporte de pagos. Excel: una pestaña por mes (Día | Cantidad pagos | Cantidad cédulas | Monto).
   */
  async exportarReportePagos(
    formato: 'excel' | 'pdf',
    fechaInicio?: string,
    fechaFin?: string,
    meses: number = 12,
    filtros?: { años: number[]; meses: number[] }
  ): Promise<Blob> {
    const params = new URLSearchParams({ formato })
    if (formato === 'excel') {
      params.set('meses', meses.toString())
      if (filtros?.años?.length) params.set('años', filtros.años.join(','))
      if (filtros?.meses?.length) params.set('meses_list', filtros.meses.join(','))
    } else if (fechaInicio && fechaFin) {
      params.set('fecha_inicio', fechaInicio)
      params.set('fecha_fin', fechaFin)
    }
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/pagos?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
    )
    return response.data as Blob
  }

  /**
   * Exporta reporte Morosidad (clientes con cuotas 90+ días): Nombre, Cédula, Cant cuotas, Total USD
   */
  async exportarReporteMorosidadClientes(fechaCorte?: string): Promise<Blob> {
    const params = new URLSearchParams()
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/morosidad-clientes?${params.toString()}`,
      { responseType: 'blob', timeout: 60000 }
    )
    return response.data as Blob
  }

  /**
   * Exporta reporte de morosidad (Vencimiento) en Excel o PDF
   */
  async exportarReporteMorosidad(
    formato: 'excel' | 'pdf',
    fechaCorte?: string,
    filtros?: { años: number[]; meses: number[] }
  ): Promise<Blob> {
    const params = new URLSearchParams({ formato })
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    if (filtros?.años?.length) params.set('años', filtros.años.join(','))
    if (filtros?.meses?.length) params.set('meses_list', filtros.meses.join(','))
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/morosidad?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
    )
    return response.data as Blob
  }

  /**
   * Exporta reporte financiero en Excel o PDF
   */
  async exportarReporteFinanciero(
    formato: 'excel' | 'pdf',
    fechaCorte?: string
  ): Promise<Blob> {
    const params = new URLSearchParams({ formato })
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/financiero?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
    )
    return response.data as Blob
  }

  /**
   * Exporta reporte de asesores en Excel o PDF
   */
  async exportarReporteAsesores(
    formato: 'excel' | 'pdf',
    fechaCorte?: string,
    filtros?: { años: number[]; meses: number[] }
  ): Promise<Blob> {
    const params = new URLSearchParams({ formato })
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    if (filtros?.años?.length) params.set('años', filtros.años.join(','))
    if (filtros?.meses?.length) params.set('meses_list', filtros.meses.join(','))
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/asesores?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
    )
    return response.data as Blob
  }

  /**
   * Exporta reporte de productos en Excel o PDF
   */
  async exportarReporteProductos(
    formato: 'excel' | 'pdf',
    fechaCorte?: string,
    filtros?: { años: number[]; meses: number[] }
  ): Promise<Blob> {
    const params = new URLSearchParams({ formato })
    if (fechaCorte) params.set('fecha_corte', fechaCorte)
    if (filtros?.años?.length) params.set('años', filtros.años.join(','))
    if (filtros?.meses?.length) params.set('meses_list', filtros.meses.join(','))
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/productos?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
    )
    return response.data as Blob
  }

  /**
   * Busca cédulas para filtrar reporte contable.
   */
  async buscarCedulasContable(q?: string): Promise<{ cedulas: Array<{ cedula: string; nombre: string }> }> {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    return await apiClient.get(`${this.baseUrl}/contable/cedulas?${params.toString()}`)
  }

  /**
   * Exporta reporte contable en Excel desde cache.
   * Filtros: años, meses, cedulas (opcional). Política: últimos 7 días se actualizan.
   */
  async exportarReporteContable(
    años: number[],
    meses: number[],
    cedulas?: string[] | 'todas'
  ): Promise<Blob> {
    const params = new URLSearchParams()
    if (años.length) params.set('años', años.join(','))
    if (meses.length) params.set('meses', meses.join(','))
    if (cedulas && cedulas !== 'todas' && cedulas.length > 0) {
      params.set('cedulas', cedulas.join(','))
    }
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/contable?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
    )
    return response.data as Blob
  }

  /**
   * Exporta reporte por cédula en Excel.
   * Columnas: ID préstamo | Cédula | Nombre | Total financiamiento | Total abono | Cuotas totales | Cuotas pagadas | Cuotas atrasadas | Cuotas atrasadas ($).
   */
  async exportarReporteCedula(): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/cedula`,
      { responseType: 'blob', timeout: 180000 }
    )
    return response.data as Blob
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
        timeout: 180000,
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

