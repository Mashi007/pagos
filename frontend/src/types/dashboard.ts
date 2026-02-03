/**
 * Tipos para las respuestas del API del dashboard.
 * Alineados con los endpoints en backend/app/api/v1/endpoints/dashboard.py
 */

export interface KpiValor {
  valor_actual: number
  variacion_porcentual: number
}

export interface KpisPrincipalesResponse {
  total_prestamos: KpiValor
  creditos_nuevos_mes: KpiValor
  total_clientes: KpiValor
  clientes_por_estado?: {
    activos: KpiValor
    inactivos: KpiValor
    finalizados: KpiValor
  }
  total_morosidad_usd: KpiValor
  cuotas_programadas?: { valor_actual: number }
  porcentaje_cuotas_pagadas?: number
}

export interface OpcionesFiltrosResponse {
  analistas: string[]
  concesionarios: string[]
  modelos: string[]
}

export interface EvolucionMensualItem {
  mes: string
  cartera: number
  cobrado: number
  morosidad: number
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
