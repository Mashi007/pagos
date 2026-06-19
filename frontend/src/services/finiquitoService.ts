import { apiClient } from './api'

const BASE = '/api/v1/finiquito'
const FINIQUITO_TERMINADOS_PAGE_LIMIT = 2000

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
  /** ISO date: fin del ciclo (dia 30 desde alta del caso; prestamos.finiquito_tramite_fecha_limite). */
  finiquito_tramite_fecha_limite?: string | null
  /** ISO date: fecha en que el préstamo fue declarado LIQUIDADO. */
  fecha_liquidado?: string | null
  /** ISO datetime: alta del caso materializado. */
  creado_en?: string | null
  /** ISO datetime: ultimo paso a EN_PROCESO (area de trabajo). */
  fecha_entrada_en_proceso?: string | null
  /** ISO datetime: ultimo paso a ACEPTADO (area de revision). */
  fecha_entrada_aceptado?: string | null
  /** ISO datetime: ultimo paso a REVISION_CONTABLE. */
  fecha_entrada_revision_contable?: string | null
  /** Reserva temporal activa (flujo Visto conciliacion). */
  conciliacion_visto_activa?: boolean | null
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
  revision_contable?: number
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

export async function finiquitoAdminEliminarCaso(casoId: number) {
  return apiClient.delete<{ ok: boolean; error?: string }>(
    `${BASE}/admin/casos/${casoId}`
  )
}

/** Bandeja / área revisión: saca el caso de finiquito y deja el préstamo en cartera operativa. */
export async function finiquitoAdminLiberarProcesosNormales(casoId: number) {
  return apiClient.post<{
    ok: boolean
    error?: string
    prestamo_id?: number
    estado_prestamo_antes?: string | null
    estado_prestamo_despues?: string | null
    forzado_aprobado?: boolean
    mensaje?: string
  }>(`${BASE}/admin/casos/${casoId}/liberar-procesos-normales`)
}

export async function finiquitoAdminVistoIniciar(
  casoId: number,
  opts?: { confirmar_sin_comprobantes?: boolean }
) {
  return apiClient.post<{
    ok: boolean
    error?: string
    ya_iniciado?: boolean
    reservas?: number
    pagos_eliminados?: number
    mensaje?: string
    requiere_confirmacion_sin_comprobantes?: boolean
  }>(
    `${BASE}/admin/casos/${casoId}/conciliacion/visto-iniciar`,
    {
      confirmar_sin_comprobantes: opts?.confirmar_sin_comprobantes === true,
    },
    {
      timeout: 120000,
    }
  )
}

export async function finiquitoAdminRecrearOcr(casoId: number) {
  return apiClient.post<{
    ok: boolean
    error?: string
    total?: number
    ocr_ok?: number
    ocr_fallidos?: number
    pagos_recriados?: number
    mensaje?: string
    cascada?: {
      ok?: boolean
      pagos_con_aplicacion?: number
      prestamo_estado?: string
      mensaje?: string
      error?: string
    }
    detalle?: Array<{
      reserva_id: number
      ok: boolean
      error?: string
      pago_id?: number
    }>
  }>(`${BASE}/admin/casos/${casoId}/conciliacion/recrear-ocr`, undefined, {
    timeout: 300000,
  })
}

export async function finiquitoAdminPasarATrabajo(casoId: number) {
  return apiClient.post<{
    ok: boolean
    error?: string
    caso?: FiniquitoCasoItem
    reservas_eliminadas?: number
  }>(`${BASE}/admin/casos/${casoId}/pasar-a-trabajo`, undefined, {
    timeout: 120000,
  })
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

export type FiniquitoTerminadosDia = {
  fecha: string
  etiqueta: string
  /** Casos marcados Terminado ese dia (Caracas). */
  cantidad: number
  /** Entradas al area de trabajo (EN_PROCESO) ese dia (Caracas). */
  cantidad_ingresos: number
}

export type FiniquitoTerminadosResumenDiario = {
  dias: FiniquitoTerminadosDia[]
  total_terminados: number
  total_en_ventana: number
  total_ingresos_en_ventana: number
}

/** Ventana por defecto: hoy + 20 dias anteriores (calendario Caracas). */
export const FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT = 21

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

export async function finiquitoAdminListarTerminadosCompleto(
  cedula?: string
): Promise<FiniquitoTerminadosListaResult> {
  const items: FiniquitoTerminadoItem[] = []
  let offset = 0
  let total: number | null = null

  while (total == null || items.length < total) {
    const page = await finiquitoAdminListarTerminados(cedula, {
      limit: FINIQUITO_TERMINADOS_PAGE_LIMIT,
      offset,
    })
    const pageItems = page.items || []
    items.push(...pageItems)
    total = page.total ?? items.length

    if (
      pageItems.length === 0 ||
      pageItems.length < FINIQUITO_TERMINADOS_PAGE_LIMIT
    ) {
      break
    }
    offset += pageItems.length
  }

  return {
    items,
    total: total ?? items.length,
    limit: FINIQUITO_TERMINADOS_PAGE_LIMIT,
    offset: 0,
  }
}

export async function finiquitoAdminResumenTerminadosDiario(
  cedula?: string,
  dias = FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT
): Promise<FiniquitoTerminadosResumenDiario> {
  const params = new URLSearchParams()
  params.set('dias', String(dias))
  const ced = (cedula ?? '').trim()
  if (ced) params.set('cedula', ced)
  return apiClient.get<FiniquitoTerminadosResumenDiario>(
    `${BASE}/admin/casos/terminados/resumen-diario?${params.toString()}`
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
