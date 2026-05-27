import { apiClient } from './api'

const BASE = '/api/v1/finiquito'

export type FiniquitoCasoItem = {
  id: number
  prestamo_id: number
  cliente_id: number | null
  cedula: string
  total_financiamiento: string
  sum_total_pagado: string
  estado: string
  ultimo_refresh_utc: string | null
  /** ISO: ultima fecha_pago en pagos para este prestamo_id */
  ultima_fecha_pago?: string | null
  contacto_para_siguientes?: boolean | null
  cliente_nombres?: string | null
  cliente_email?: string | null
  cliente_telefono?: string | null
  /** ISO date: plazo 15 días laborales al pasar a En proceso (prestamos.finiquito_tramite_fecha_limite). */
  finiquito_tramite_fecha_limite?: string | null
  /** ISO date: fecha en que el préstamo fue declarado LIQUIDADO. */
  fecha_liquidado?: string | null
}

export type FiniquitoRevisionDatosResponse = {
  caso_id: number
  prestamo_id_finiquito?: number
  cedula: string
  prestamo_caso?: Record<string, unknown> | null
  cuotas_caso?: Record<string, unknown>[]
  prestamos: {
    prestamos: Record<string, unknown>[]
    total: number
    page: number
    per_page: number
    total_pages: number
  }
  pagos: {
    pagos: Record<string, unknown>[]
    total: number
    page: number
    per_page: number
    total_pages: number
  }
}

/** Detalle interno del caso: préstamo, cuotas, listados préstamos/pagos por cédula. */
export async function finiquitoAdminRevisionDatos(casoId: number) {
  return apiClient.get<FiniquitoRevisionDatosResponse>(
    `${BASE}/admin/casos/${casoId}/revision-datos`
  )
}

export type FiniquitoAdminListaResult = {
  items: FiniquitoCasoItem[]
  total: number
  limit: number
  offset: number
}

/** Ventana por defecto alineada con el backend (horas UTC hacia atrás). */
export const FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT = 72

export type FiniquitoConteoRevisionNuevos = {
  total: number
  ventana_horas: number
}

export type FiniquitoResumenEstado = {
  total: number
  revision: number
  aceptado: number
  rechazado: number
  en_proceso: number
  terminado: number
  max_ultimo_refresh_utc: string | null
  max_creado_en_utc: string | null
}

/** Casos en REVISION materializados recientemente (alarma de nuevos liquidados en finiquito). */
export async function finiquitoAdminConteoRevisionNuevos(
  cedula?: string,
  horas: number = FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT
): Promise<FiniquitoConteoRevisionNuevos> {
  const params = new URLSearchParams()
  params.set('horas', String(horas))
  const ced = (cedula ?? '').trim()
  if (ced) {
    params.set('cedula', ced)
  }
  const q = params.toString() ? `?${params.toString()}` : ''
  return apiClient.get<FiniquitoConteoRevisionNuevos>(
    `${BASE}/admin/casos/conteo-revision-nuevos${q}`
  )
}

/**
 * Snapshot ligero para polling: detecta cambios de estado/refresh sin traer listas.
 * Si cambia este digest, el frontend puede recargar las tablas en modo silencioso.
 */
export async function finiquitoAdminResumenEstado(
  cedula?: string
): Promise<FiniquitoResumenEstado> {
  const params = new URLSearchParams()
  const ced = (cedula ?? '').trim()
  if (ced) params.set('cedula', ced)
  const q = params.toString() ? `?${params.toString()}` : ''
  return apiClient.get<FiniquitoResumenEstado>(`${BASE}/admin/casos/resumen-estado${q}`)
}

export async function finiquitoAdminListar(
  estado?: string,
  cedula?: string,
  estadoIn?: string,
  pagination?: { limit?: number; offset?: number }
): Promise<FiniquitoAdminListaResult> {
  const params = new URLSearchParams()
  if (estadoIn && estadoIn.trim()) {
    params.set('estado_in', estadoIn.trim())
  } else if (estado) {
    params.set('estado', estado)
  }
  const ced = (cedula ?? '').trim()
  if (ced) params.set('cedula', ced)
  if (pagination?.limit != null) {
    params.set('limit', String(pagination.limit))
  }
  if (pagination?.offset != null) {
    params.set('offset', String(pagination.offset))
  }
  const q = params.toString() ? `?${params.toString()}` : ''
  return apiClient.get<FiniquitoAdminListaResult>(`${BASE}/admin/casos${q}`)
}

export async function finiquitoAdminPatchEstado(
  casoId: number,
  estado: string,
  contactoParaSiguientes?: boolean
) {
  const body: {
    estado: string
    contacto_para_siguientes?: boolean
  } = {
    estado,
  }
  if (contactoParaSiguientes !== undefined) {
    body.contacto_para_siguientes = contactoParaSiguientes
  }
  return apiClient.patch<{
    ok: boolean
    caso?: FiniquitoCasoItem
    error?: string
  }>(`${BASE}/admin/casos/${casoId}/estado`, body, { timeout: 120000 })
}

export type FiniquitoRefreshStats = {
  elegibles: number
  insertados: number
  actualizados: number
  eliminados: number
}

export async function finiquitoAdminRefreshMaterializado() {
  return apiClient.post<FiniquitoRefreshStats>(
    `${BASE}/admin/refresh-materializado`,
    undefined,
    { timeout: 180000 }
  )
}

export type FiniquitoTerminadoItem = {
  id: number
  prestamo_id: number
  cedula: string
  nombre: string
  total_financiamiento: string
  fecha_aprobacion?: string | null
  fecha_termino_pago?: string | null
  fecha_terminado?: string | null
  contacto_para_siguientes?: boolean | null
}

export type FiniquitoTerminadosListaResult = {
  items: FiniquitoTerminadoItem[]
  total: number
  limit: number
  offset: number
}

export type FiniquitoTerminadosSemana = {
  semana: string
  etiqueta: string
  cantidad: number
}

export type FiniquitoTerminadosResumenSemanal = {
  semanas: FiniquitoTerminadosSemana[]
  total_terminados: number
}

export async function finiquitoAdminListarTerminados(
  cedula?: string,
  pagination?: { limit?: number; offset?: number }
): Promise<FiniquitoTerminadosListaResult> {
  const params = new URLSearchParams()
  const ced = (cedula ?? '').trim()
  if (ced) params.set('cedula', ced)
  if (pagination?.limit != null) {
    params.set('limit', String(pagination.limit))
  }
  if (pagination?.offset != null) {
    params.set('offset', String(pagination.offset))
  }
  const q = params.toString() ? `?${params.toString()}` : ''
  return apiClient.get<FiniquitoTerminadosListaResult>(
    `${BASE}/admin/casos/terminados${q}`
  )
}

export async function finiquitoAdminResumenTerminadosSemanal(
  cedula?: string,
  semanas = 16
): Promise<FiniquitoTerminadosResumenSemanal> {
  const params = new URLSearchParams()
  params.set('semanas', String(semanas))
  const ced = (cedula ?? '').trim()
  if (ced) params.set('cedula', ced)
  return apiClient.get<FiniquitoTerminadosResumenSemanal>(
    `${BASE}/admin/casos/terminados/resumen-semanal?${params.toString()}`
  )
}
