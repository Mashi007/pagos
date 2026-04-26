import * as XLSX from 'xlsx'

import { apiClient } from './api'

/** Evita guardar un .xlsx equivocado (p. ej. informe FECHAS de 8 columnas) cuando el API o la caché devuelven otra cosa. */
async function assertBlobEsFechaDriveConciliacion(blob: Blob): Promise<void> {
  const buf = await blob.arrayBuffer()

  const head = new Uint8Array(buf.slice(0, 2))

  if (head[0] !== 0x50 || head[1] !== 0x4b) {
    throw new Error(
      'La respuesta no es un Excel valido (.xlsx). Revise la sesion o el enlace del API.'
    )
  }

  const wb = XLSX.read(buf, { type: 'array', sheetRows: 2 })

  const name0 = wb.SheetNames[0]

  if (name0 !== 'Fecha Drive') {
    throw new Error(
      `Se recibio otro informe (primera hoja: "${name0 ?? '?'}"). ` +
        'El cruce Drive vs sistema debe mostrar la hoja "Fecha Drive" (5 columnas). ' +
        'Use el boton Fecha Drive en Contable y actualice la pagina (Ctrl+F5). ' +
        'Si persiste, el backend desplegado puede estar desactualizado.'
    )
  }

  const ws = wb.Sheets[name0]

  const c1Raw = ws['C1']?.w ?? ws['C1']?.v

  const c1 = String(c1Raw ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s/g, '')

  if (!c1.includes('cedula') || !c1.includes('sistema')) {
    throw new Error(
      'El Excel no tiene el encabezado esperado de Fecha Drive (columna C: Cédula Sistema).'
    )
  }
}

/** Valida que el blob sea el Excel "Análisis financiamiento" (5 columnas, hoja vs sistema). */
async function assertBlobEsAnalisisFinanciamiento(blob: Blob): Promise<void> {
  const buf = await blob.arrayBuffer()

  const head = new Uint8Array(buf.slice(0, 2))

  if (head[0] !== 0x50 || head[1] !== 0x4b) {
    throw new Error(
      'La respuesta no es un Excel valido (.xlsx). Revise la sesion o el enlace del API.'
    )
  }

  const wb = XLSX.read(buf, { type: 'array', sheetRows: 2 })

  const name0 = wb.SheetNames[0]

  if (name0 !== 'Análisis financiamiento') {
    throw new Error(
      `Se recibio otro informe (primera hoja: "${name0 ?? '?'}"). ` +
        'Use el boton Analisis financiamiento en Contable y actualice la pagina (Ctrl+F5). ' +
        'Si persiste, el backend desplegado puede estar desactualizado.'
    )
  }

  const ws = wb.Sheets[name0]

  const e1Raw = ws['E1']?.w ?? ws['E1']?.v

  const e1 = String(e1Raw ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s/g, '')

  if (
    !e1.includes('total') ||
    !e1.includes('financiamiento') ||
    !e1.includes('sistema')
  ) {
    throw new Error(
      'El Excel no tiene el encabezado esperado (columna E: Total financiamiento sistema).'
    )
  }
}

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

  /** Préstamos con cuotas vencidas 90+ días (backend: pagos_vencidos) */

  pagos_vencidos: number

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

export interface ResumenConciliacion {
  total_filas: number

  filas_procesadas: number

  monto_total_financiamiento: number

  monto_total_abonos: number

  diferencia_total: number

  cedulas_unicas: number

  filas_con_discrepancia: number

  fecha_inicio?: string

  fecha_fin?: string
}

/** GET /api/v1/conciliacion-sheet/status - snapshot hoja Drive vs BD (Fecha Drive). */
export interface ConciliacionSheetStatusResponse {
  timezone: string

  columns_range: string

  spreadsheet_configured: boolean

  expected_tab_name: string

  snapshot_row_count: number

  /** Filas en tabla drive (A..S plano); misma corrida que el snapshot JSON. */
  drive_row_count?: number

  fecha_drive_ready: boolean

  /** Código estable cuando no está listo (p. ej. never_synced, last_sync_failed). Opcional si el API es anterior. */
  fecha_drive_blocker?: string | null

  fecha_drive_hint: string | null

  /** True si CONCILIACION_SHEET_SYNC_SECRET está definido (cron POST /sync). */
  sync_secret_configured?: boolean

  /** True si ENABLE_AUTOMATIC_SCHEDULED_JOBS (job 04:01 Caracas, etc.). */
  scheduled_jobs_enabled?: boolean

  /** Pasos para quien despliega; vacío cuando fecha_drive_ready. */
  operator_checklist?: string[]

  meta: Record<string, unknown> | null

  last_run: Record<string, unknown> | null
}

/** GET /reportes/morosidad/auditoria/mora-por-cliente - cuotas.estado = MORA en BD (como el Excel). */
export interface AuditoriaMoraPorCliente {
  alcance: 'reporte_morosidad_cedulas'

  cliente_id: number

  cedula: string

  nombres: string

  cantidad_cuotas_mora: number

  total_monto_usd: number

  criterio: string

  cuotas: Array<{
    cuota_id: number

    prestamo_id: number

    numero_cuota: number

    monto_usd: number
  }>
}

/** Diagnostico por un solo prestamo (misma regla: cuotas.estado = MORA). */
export interface AuditoriaMoraPorPrestamo {
  alcance?: 'diagnostico_por_prestamo'

  reporte_morosidad_usar?: string

  prestamo_id: number

  cedula_prestamo: string

  cantidad_cuotas_mora: number

  total_monto_usd: number

  criterio: string

  cuotas: Array<{
    cuota_id: number

    numero_cuota: number

    monto_usd: number
  }>
}

class ReporteService {
  private baseUrl = '/api/v1/reportes'

  private conciliacionSheetBaseUrl = '/api/v1/conciliacion-sheet'

  // API expects query param 'anos' (no n-tilde); use 'meses_list' for months in cartera/pagos/morosidad/asesores.

  /**





   * Obtiene cuentas por cobrar por mes: por día cuándo debe cobrar





   */

  async getCarteraPorMes(meses: number = 12): Promise<CarteraPorMes> {
    const params = new URLSearchParams({ meses: meses.toString() })

    return await apiClient.get(
      `${this.baseUrl}/cartera/por-mes?${params.toString()}`
    )
  }

  /**





   * Obtiene reporte de cartera





   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual





   */

  async getReporteCartera(fechaCorte?: string): Promise<ReporteCartera> {
    const params = new URLSearchParams()

    if (fechaCorte) params.set('fecha_corte', fechaCorte)

    const query = params.toString()

    return await apiClient.get(
      `${this.baseUrl}/cartera${query ? `?${query}` : ''}`
    )
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
    const params = new URLSearchParams({
      fecha_inicio: fechaInicio,
      fecha_fin: fechaFin,
    })

    return await apiClient.get(`${this.baseUrl}/pagos?${params.toString()}`)
  }

  /**





   * Obtiene pagos agrupados por mes/año. Cada mes tiene lista ordenada descendente por fecha.





   */

  async getPagosPorMes(meses: number = 12): Promise<PagosPorMes> {
    const params = new URLSearchParams({ meses: meses.toString() })

    return await apiClient.get(
      `${this.baseUrl}/pagos/por-mes?${params.toString()}`
    )
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

    if (filtros?.años?.length) params.set('anos', filtros.años.join(','))

    if (filtros?.meses?.length)
      params.set('meses_list', filtros.meses.join(','))

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

    return await apiClient.get(
      `${this.baseUrl}/morosidad${query ? `?${query}` : ''}`
    )
  }

  /**





   * Obtiene informe pago vencido por rangos de días (1 día, 15 días, 30 días, 2 meses, 90+ moroso)





   */

  async getMorosidadPorRangos(
    fechaCorte?: string
  ): Promise<MorosidadPorRangos> {
    const params = new URLSearchParams()

    if (fechaCorte) params.set('fecha_corte', fechaCorte)

    const query = params.toString()

    return await apiClient.get(
      `${this.baseUrl}/morosidad/por-rangos${query ? `?${query}` : ''}`
    )
  }

  /**





   * Obtiene reporte financiero





   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual





   */

  async getReporteFinanciero(fechaCorte?: string): Promise<ReporteFinanciero> {
    const params = new URLSearchParams()

    if (fechaCorte) params.set('fecha_corte', fechaCorte)

    const query = params.toString()

    return await apiClient.get(
      `${this.baseUrl}/financiero${query ? `?${query}` : ''}`
    )
  }

  /**





   * Obtiene asesores por mes: una pestaña por mes, orden descendente por morosidad





   */

  async getAsesoresPorMes(meses: number = 12): Promise<AsesoresPorMes> {
    const params = new URLSearchParams({ meses: meses.toString() })

    return await apiClient.get(
      `${this.baseUrl}/asesores/por-mes?${params.toString()}`
    )
  }

  /**





   * Obtiene reporte de asesores





   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual





   */

  async getReporteAsesores(fechaCorte?: string): Promise<ReporteAsesores> {
    const params = new URLSearchParams()

    if (fechaCorte) params.set('fecha_corte', fechaCorte)

    const query = params.toString()

    return await apiClient.get(
      `${this.baseUrl}/asesores${query ? `?${query}` : ''}`
    )
  }

  /**





   * Obtiene productos por mes: modelo y suma ventas (70% valor prestado) por modelo





   */

  async getProductosPorMes(meses: number = 12): Promise<ProductosPorMes> {
    const params = new URLSearchParams({ meses: meses.toString() })

    return await apiClient.get(
      `${this.baseUrl}/productos/por-mes?${params.toString()}`
    )
  }

  /**





   * Obtiene reporte de productos





   * @param fechaCorte Opcional. Si no se proporciona, usa la fecha actual





   */

  async getReporteProductos(fechaCorte?: string): Promise<ReporteProductos> {
    const params = new URLSearchParams()

    if (fechaCorte) params.set('fecha_corte', fechaCorte)

    const query = params.toString()

    return await apiClient.get(
      `${this.baseUrl}/productos${query ? `?${query}` : ''}`
    )
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

      if (filtros?.años?.length) params.set('anos', filtros.años.join(','))

      if (filtros?.meses?.length)
        params.set('meses_list', filtros.meses.join(','))
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





   * Exporta morosidad-clientes: solo estado MORA (mismo criterio que morosidad-cedulas). Excel con fila TOTAL.





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

  /**
   * Morosidad por cedula: solo estado calculado MORA (Mora 4+ meses). Vencido excluido.
   */
  async exportarReporteMorosidadCedulas(): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/morosidad-cedulas`,
      { responseType: 'blob', timeout: 120000 }
    )

    return response.data as Blob
  }

  /**
   * Auditoria: cuotas MORA por prestamo (mismo filtro que export morosidad-cedulas).
   */
  /**
   * Auditoria del reporte de morosidad (Excel por cedula): mismo criterio que exportar/morosidad-cedulas.
   */
  async getAuditoriaMoraPorCliente(params: {
    cedula?: string
    clienteId?: number
  }): Promise<AuditoriaMoraPorCliente> {
    const q = new URLSearchParams()
    if (params.cedula != null && params.cedula !== '')
      q.set('cedula', params.cedula.trim())
    if (params.clienteId != null) q.set('cliente_id', String(params.clienteId))

    return await apiClient.get(
      `${this.baseUrl}/morosidad/auditoria/mora-por-cliente?${q.toString()}`
    )
  }

  /** Diagnostico por un solo prestamo (opcional; el informe va por cedula). */
  async getAuditoriaMoraPorPrestamo(
    prestamoId: number
  ): Promise<AuditoriaMoraPorPrestamo> {
    const params = new URLSearchParams({
      prestamo_id: String(prestamoId),
    })

    return await apiClient.get(
      `${this.baseUrl}/morosidad/auditoria/mora-por-prestamo?${params.toString()}`
    )
  }

  async exportarReporteMorosidad(
    formato: 'excel' | 'pdf',

    fechaCorte?: string,

    filtros?: { años: number[]; meses: number[] }
  ): Promise<Blob> {
    const params = new URLSearchParams({ formato })

    if (fechaCorte) params.set('fecha_corte', fechaCorte)

    if (filtros?.años?.length) params.set('anos', filtros.años.join(','))

    if (filtros?.meses?.length)
      params.set('meses_list', filtros.meses.join(','))

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

    if (filtros?.años?.length) params.set('anos', filtros.años.join(','))

    if (filtros?.meses?.length)
      params.set('meses_list', filtros.meses.join(','))

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

    if (filtros?.años?.length) params.set('anos', filtros.años.join(','))

    if (filtros?.meses?.length)
      params.set('meses_list', filtros.meses.join(','))

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

  async buscarCedulasContable(
    q?: string
  ): Promise<{ cedulas: Array<{ cedula: string; nombre: string }> }> {
    const params = new URLSearchParams()

    if (q) params.set('q', q)

    return await apiClient.get(
      `${this.baseUrl}/contable/cedulas?${params.toString()}`
    )
  }

  /**





   * Exporta reporte contable en Excel desde cache.





   * Filtros: años, meses, cedulas (opcional). Política: últimos 7 días se actualizan.





   */

  async exportarReporteContable(
    años: number[],

    meses: number[],

    cedulas?: string[] | 'todas'
  ): Promise<{ blob: Blob; vacio: boolean }> {
    const params = new URLSearchParams()

    if (años.length) params.set('anos', años.join(','))

    if (meses.length) params.set('meses', meses.join(','))

    if (cedulas && cedulas !== 'todas' && cedulas.length > 0) {
      params.set('cedulas', cedulas.join(','))
    }

    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/contable?${params.toString()}`,

      { responseType: 'blob', timeout: 180000 }
    )

    const vacio = response.headers['x-reporte-contable-vacio'] === '1'

    return { blob: response.data as Blob, vacio }
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

  /** Excel FECHAS: todos los prestamos, columnas ID, cedula, registro, aprobacion, calculo, total financiamiento. */

  async exportarReporteFechasPrestamos(): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/prestamos-fechas`,

      { responseType: 'blob', timeout: 180000 }
    )

    return response.data as Blob
  }

  /**
   * Excel Pagos Gmail: tabla `pagos_gmail_abcd_cuotas_traza` (plantilla A-D, Gemini, cuotas).
   * @param fechaDesde YYYY-MM-DD inclusive
   * @param fechaHasta YYYY-MM-DD inclusive
   */
  async exportarReportePagosGmailAbcd(
    fechaDesde: string,
    fechaHasta: string
  ): Promise<Blob> {
    const params = new URLSearchParams({
      fecha_desde: fechaDesde.trim(),
      fecha_hasta: fechaHasta.trim(),
    })
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/pagos-gmail-abcd?${params.toString()}`,
      { responseType: 'blob', timeout: 120000 }
    )
    return response.data as Blob
  }

  /** Excel Fecha Drive: hoja CONCILIACIÓN sincronizada vs préstamos (cedula, fechas aprobación). */
  async exportarReporteFechaDrive(): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()

    const cacheBust = `_cb=${Date.now()}`

    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/fecha-drive?${cacheBust}`,
      { responseType: 'blob', timeout: 180000 }
    )

    if (response.status !== 200) {
      let detail = `Error ${response.status}`

      try {
        const t = await (response.data as Blob).text()

        if (t && t.trim().startsWith('{')) {
          try {
            const j = JSON.parse(t) as { detail?: string; message?: string }

            detail = j.detail || j.message || detail
          } catch {
            detail = t.slice(0, 400)
          }
        } else if (t) {
          detail = t.slice(0, 400)
        }
      } catch {
        /* usar detail por defecto */
      }

      throw new Error(detail)
    }

    const blob = response.data as Blob

    await assertBlobEsFechaDriveConciliacion(blob)

    return blob
  }

  /** Excel Análisis financiamiento: hoja CONCILIACIÓN vs total_financiamiento en préstamos (5 columnas). */
  async exportarReporteAnalisisFinanciamiento(): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()

    const cacheBust = `_cb=${Date.now()}`

    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/analisis-financiamiento?${cacheBust}`,
      { responseType: 'blob', timeout: 180000 }
    )

    if (response.status !== 200) {
      let detail = `Error ${response.status}`

      try {
        const t = await (response.data as Blob).text()

        if (t && t.trim().startsWith('{')) {
          try {
            const j = JSON.parse(t) as { detail?: string; message?: string }

            detail = j.detail || j.message || detail
          } catch {
            detail = t.slice(0, 400)
          }
        } else if (t) {
          detail = t.slice(0, 400)
        }
      } catch {
        /* usar detail por defecto */
      }

      throw new Error(detail)
    }

    const blob = response.data as Blob

    await assertBlobEsAnalisisFinanciamiento(blob)

    return blob
  }

  /**
   * Excel Préstamos Drive: 11 columnas snake_case desde la hoja sincronizada,
   * filtradas por columna LOTE (query `lotes=70` o `lotes=70,71`).
   */
  async exportarReportePrestamosDrive(filtros: {
    lotes: number[]
  }): Promise<Blob> {
    const params = new URLSearchParams()

    if (filtros.lotes?.length) params.set('lotes', filtros.lotes.join(','))

    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/prestamos-drive?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
    )

    if (response.status !== 200) {
      let detail = `Error ${response.status}`

      try {
        const t = await (response.data as Blob).text()

        if (t && t.trim().startsWith('{')) {
          try {
            const j = JSON.parse(t) as { detail?: string; message?: string }

            detail = j.detail || j.message || detail
          } catch {
            detail = t.slice(0, 400)
          }
        } else if (t) {
          detail = t.slice(0, 400)
        }
      } catch {
        /* usar detail por defecto */
      }

      throw new Error(detail)
    }

    return response.data as Blob
  }

  /**
   * Excel Clientes: Cédula, Nombres, Teléfono, Email desde la hoja sincronizada,
   * filtradas por columna LOTE (query `lotes=70` o `lotes=70,71`).
   */
  async exportarReporteClientesHoja(filtros: {
    lotes: number[]
  }): Promise<Blob> {
    const params = new URLSearchParams()

    if (filtros.lotes?.length) params.set('lotes', filtros.lotes.join(','))

    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/clientes-hoja?${params.toString()}`,
      { responseType: 'blob', timeout: 180000 }
    )

    if (response.status !== 200) {
      let detail = `Error ${response.status}`

      try {
        const t = await (response.data as Blob).text()

        if (t && t.trim().startsWith('{')) {
          try {
            const j = JSON.parse(t) as { detail?: string; message?: string }

            detail = j.detail || j.message || detail
          } catch {
            detail = t.slice(0, 400)
          }
        } else if (t) {
          detail = t.slice(0, 400)
        }
      } catch {
        /* usar detail por defecto */
      }

      throw new Error(detail)
    }

    return response.data as Blob
  }

  /**





   * Descarga un archivo (Excel, PDF, CSV)





   */

  /**





   * Envía filas de conciliación (cedula, total_financiamiento, total_abonos, columna_e, columna_f) para guardar en BD temporal.





   */

  async cargarConciliacion(
    filas: Array<{
      cedula: string
      total_financiamiento: number
      total_abonos: number
      columna_e?: string
      columna_f?: string
    }>
  ): Promise<{ ok: boolean; filas_guardadas: number }> {
    return await apiClient.post(`${this.baseUrl}/conciliacion/cargar`, filas)
  }

  /**





   * Exporta reporte Conciliación en Excel. Al descargar se eliminan los datos temporales.





   */

  async cargarConciliacionExcel(file: File): Promise<{
    ok: boolean
    filas_ok: number
    filas_con_error: number
    errores: string[]
  }> {
    const formData = new FormData()

    formData.append('file', file)

    return await apiClient.post(
      `${this.baseUrl}/conciliacion/cargar-excel`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    )
  }

  async obtenerResumenConciliacion(
    fechaInicio?: string,

    fechaFin?: string
  ): Promise<ResumenConciliacion> {
    const params = new URLSearchParams()

    if (fechaInicio) params.set('fecha_inicio', fechaInicio)

    if (fechaFin) params.set('fecha_fin', fechaFin)

    const query = params.toString()

    return await apiClient.get(
      `${this.baseUrl}/conciliacion/resumen${query ? `?${query}` : ''}`
    )
  }

  async exportarReporteConciliacion(
    fechaInicio?: string,

    fechaFin?: string,

    cedulas?: string[],

    formato?: 'excel' | 'pdf'
  ): Promise<Blob> {
    const params = new URLSearchParams()

    if (fechaInicio) params.set('fecha_inicio', fechaInicio)

    if (fechaFin) params.set('fecha_fin', fechaFin)

    if (cedulas?.length) params.set('cedulas', cedulas.join(','))

    if (formato) params.set('formato', formato)

    const query = params.toString()

    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/conciliacion${query ? `?${query}` : ''}`,

      { responseType: 'blob', timeout: 180000 }
    )

    return response.data as Blob
  }

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
        type: response.headers['content-type'] || 'application/octet-stream',
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

  /** Estado del snapshot Google Sheets CONCILIACIÓN → BD (diagnóstico Fecha Drive). */
  async getConciliacionSheetStatus(): Promise<ConciliacionSheetStatusResponse> {
    return await apiClient.get<ConciliacionSheetStatusResponse>(
      `${this.conciliacionSheetBaseUrl}/status`
    )
  }

  /**
   * Ejecuta la misma sincronización que el cron (Sheets → conciliacion_sheet_*),
   * usando credenciales del servidor. Requiere rol admin, operador o gerente.
   */
  async syncConciliacionSheetDesdeDrive(): Promise<Record<string, unknown>> {
    return await apiClient.post<Record<string, unknown>>(
      `${this.conciliacionSheetBaseUrl}/sync-now`,
      undefined,
      { timeout: 120000 }
    )
  }

  /** Diagnóstico agregado (BD + ping metadatos Google); no modifica datos. */
  async getConciliacionSheetDiagnostico(): Promise<Record<string, unknown>> {
    return await apiClient.get<Record<string, unknown>>(
      `${this.conciliacionSheetBaseUrl}/diagnostico`,
      { timeout: 60000 }
    )
  }
}

export const reporteService = new ReporteService()
