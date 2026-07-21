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

  /**
   * Suma del monto del pago en USD (monto_pagado o BS/tasa del registro), un pago una vez,
   * solo si está vinculado a cuotas con vencimiento = hoy (Caracas) y conciliación ese día.
   */
  pagos_conciliados_hoy: KpiValor

  /**
   * Suma monto_cuota (USD) de cuotas vencidas antes de hoy (Caracas) con pago conciliado hoy.
   * Complemento de pagos_conciliados_hoy (solo vence hoy).
   */
  cuotas_atrasadas_conciliadas_hoy: KpiValor

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

  /** Cuotas programadas: Σ monto con fecha_vencimiento en el mes */
  cartera: number

  /** Cuotas del mes: vencimiento y fecha_pago en el mismo mes calendario */
  cobrado: number

  /** Cuotas atrasadas (otros meses): pago en el mes, vencimiento anterior (no entra en CxC) */
  pagos_atrasos: number

  /** Anticipos: pago en el mes, vencimiento en un mes posterior */
  pagos_anticipados?: number

  /** Pagos PENDIENTE aún no conciliados, aplicados a cuotas del mes o anticipadas */
  pagos_no_conciliados_a_tiempo?: number

  /** Pagos PENDIENTE aún no conciliados, cartera vencida */
  pagos_no_conciliados_atrasados?: number

  /** Cantidad de registros en tabla pagos con fecha_pago en el mes (cualquier estado/conciliado) */
  cantidad_pagos?: number

  /** Cuentas por cobrar = cartera - cobrado; la UI lo recalcula para la línea roja */
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

/** GET /api/v1/dashboard/tendencia-programado-total-cobrado-diario */
export interface TendenciaProgramadoCobradoDiarioItem {
  fecha: string
  dia: string
  cuotas_programadas: number
  /** Solo cuotas con vencimiento = dia y fecha_pago = dia (sin atrasos). */
  total_cobrado: number
  conciliados_dia: number
  /** Siempre 0 en este endpoint (atrasos excluidos a proposito). */
  pagos_dias_anteriores: number
}

export interface TendenciaProgramadoCobradoDiarioResponse {
  series: TendenciaProgramadoCobradoDiarioItem[]
  dias: TendenciaProgramadoCobradoDiarioItem[]
  desde?: string | null
  hasta?: string | null
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

/** GET /api/v1/dashboard/pagos-realizados-mensual — conteo de filas en `pagos` por mes. */
export interface PagosRealizadosMensualItem {
  mes: string
  cantidad_pagos: number
  /** Suma de monto_pagado (USD) del mes; informativo en tooltip. */
  monto_total: number
}

export interface PagosRealizadosMensualResponse {
  series: PagosRealizadosMensualItem[]
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

/** GET /api/v1/dashboard/pagos-ingresados-por-dia */
export interface PagosIngresadosPorDiaItem {
  fecha: string

  dia: string

  /** Suma de Pago.monto_pagado (USD) del día */
  monto: number
}

export interface PagosIngresadosPorDiaResponse {
  dias: number

  serie: PagosIngresadosPorDiaItem[]
}
