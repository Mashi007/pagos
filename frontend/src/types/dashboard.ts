/**





 * Tipos para las respuestas del API del dashboard.





 * Alineados con los endpoints en backend/app/api/v1/endpoints/dashboard.py





 */

export interface KpiValor {
  valor_actual: number

  variacion_porcentual: number
}

/** Préstamos (mensual): cantidad aprobada en el periodo + financiamiento comprometido (fecha_aprobacion). */
export interface KpiPrestamosMensual extends KpiValor {
  financiamiento_total?: number
}

export interface KpisPrincipalesResponse {
  total_prestamos: KpiPrestamosMensual

  /** Pagos con conciliado=true y fecha_conciliacion en el día actual (Caracas). */
  pagos_conciliados_hoy: KpiValor

  total_clientes: KpiValor

  clientes_por_estado?: {
    activos: KpiValor

    inactivos: KpiValor

    finalizados: KpiValor
  }

  total_morosidad_usd: KpiValor

  /** Suma monto de cuotas con fecha_vencimiento = hoy (Caracas). */
  pagos_programados_hoy: KpiValor

  /** % de cuotas con vencimiento hoy que ya tienen fecha_pago. */
  porcentaje_cuotas_pagadas_hoy?: number
}

export interface OpcionesFiltrosResponse {
  analistas: string[]

  concesionarios: string[]

  modelos: string[]
}

export interface EvolucionMensualItem {
  mes: string

  /** Pagos programados: cuotas con vencimiento en el mes */
  cartera: number

  /** Pagos conciliados del mes: mismas cuotas (vencimiento en el mes) ya pagadas */
  cobrado: number

  /** Cobros en el mes de cuotas vencidas en meses anteriores (no entra en cuentas por cobrar de la línea) */
  pagos_atrasos: number

  /** Debe ser cartera - cobrado; la UI lo recalcula así para la línea roja */
  cuentas_por_cobrar: number
}

export interface DashboardAdminResponse {
  financieros?: {
    ingresosCapital: number

    ingresosInteres: number

    ingresosMora: number

    totalCobrado: number

    totalCobradoAnterior: number
  }

  meta_mensual?: number

  avance_meta?: number

  evolucion_mensual?: EvolucionMensualItem[]

  evolucion_origen?: 'demo' | 'bd'
}

export interface MorosidadPorDiaItem {
  fecha: string

  dia: string

  morosidad: number
}

export interface RangoFinanciamiento {
  categoria: string

  cantidad_prestamos: number

  monto_total: number

  porcentaje_cantidad: number

  porcentaje_monto: number
}

export interface FinanciamientoPorRangosResponse {
  rangos: RangoFinanciamiento[]

  total_prestamos: number

  total_monto: number
}

export interface ComposicionMorosidadPunto {
  categoria: string

  monto: number

  cantidad_cuotas: number

  cantidad_prestamos: number
}

export interface ComposicionMorosidadResponse {
  puntos: ComposicionMorosidadPunto[]

  total_morosidad: number

  total_cuotas: number

  total_prestamos?: number
}

export interface PrestamosPorConcesionarioResponse {
  por_mes: Array<{ mes: string; concesionario: string; cantidad: number }>

  acumulado: Array<{ concesionario: string; cantidad_acumulada: number }>
}

export interface PrestamosPorModeloResponse {
  por_mes: Array<{ mes: string; modelo: string; cantidad: number }>

  acumulado: Array<{ modelo: string; cantidad_acumulada: number }>
}

export interface MorosidadPorAnalistaItem {
  analista: string

  cantidad_cuotas_vencidas: number

  monto_vencido: number
}

export interface CobranzasSemanalesSemana {
  semana_inicio: string

  nombre_semana: string

  cobranzas_planificadas: number

  pagos_reales: number
}

export interface CobranzasSemanalesResponse {
  semanas: CobranzasSemanalesSemana[]

  fecha_inicio: string

  fecha_fin: string
}

export interface AnalisisCuentasPorCobrarItem {
  mes: string

  /** Cuotas con vencimiento en el mes (programado); mismo concepto que barra azul Evolución mensual */
  cartera: number

  /** Cuotas con vencimiento en el mes y pagadas; alinea con barra verde Evolución mensual */
  cobrado_mes: number

  pagos_atrasos: number
}

export interface AnalisisCuentasPorCobrarResponse {
  analisis: AnalisisCuentasPorCobrarItem[]

  origen: 'demo' | 'bd'
}

export interface TendenciaProgramadoTotalCobradoItem {
  mes: string

  cuotas_programadas: number

  total_cobrado: number

  conciliados_mes: number

  pagos_meses_anteriores: number
}

export interface TendenciaProgramadoTotalCobradoResponse {
  series: TendenciaProgramadoTotalCobradoItem[]

  origen: 'demo' | 'bd'
}

export interface RecibosPagosMensualUsdItem {
  mes: string

  /** Equivalente USD del mes (solo reportes en Bs., conciliado o tasa del día) */
  bs_en_usd: number

  cantidad: number
}

export interface RecibosPagosMensualUsdEstadistica {
  total_bs_en_usd: number

  total_reportes: number

  promedio_mensual_usd: number

  meses_con_datos: number

  primer_mes: string | null

  ultimo_mes: string | null
}

export interface RecibosPagosMensualUsdResponse {
  series: RecibosPagosMensualUsdItem[]

  estadistica: RecibosPagosMensualUsdEstadistica

  origen: 'demo' | 'bd'
}

/** GET /api/v1/dashboard/notificaciones-envios-por-dia */
export interface NotificacionesEnviosPorDiaItem {
  fecha: string

  dia: string

  enviados: number

  fallidos: number
}

export interface NotificacionesEnviosPorDiaResponse {
  tipo_tab: string

  serie: NotificacionesEnviosPorDiaItem[]
}
