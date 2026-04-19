import { apiClient, buildUrl } from './api'

const BASE = '/api/v1/prestamos/candidatos-drive'

export type PrestamoCandidatoDrivePayload = Record<string, unknown>

export type PrestamoCandidatoDriveFila = {
  id: number
  sheet_row_number: number
  cedula_cmp: string
  payload: PrestamoCandidatoDrivePayload
  /** Misma validación de servidor que «Guardar (100%)» antes de crear el préstamo. */
  listo_para_guardar?: boolean
  computed_at: string | null
}

export type PrestamoCandidatosDriveSnapshot = {
  drive_synced_at: string | null
  computed_at: string | null
  total: number
  /** Filas que pasan la misma validación de servidor que «Guardar (100%)» antes de crear el préstamo. */
  kpis_aprueban?: number
  /** Resto del snapshot (no pasan esa validación). */
  kpis_no_aprueban?: number
  total_sin_filtro?: number
  filtro_cedula?: string | null
  limit: number
  offset: number
  filas: PrestamoCandidatoDriveFila[]
}

export async function getPrestamosCandidatosDriveSnapshot(
  limit = 500,
  offset = 0,
  cedulaQ?: string
): Promise<PrestamoCandidatosDriveSnapshot> {
  const params: Record<string, string | number> = { limit, offset }
  const q = (cedulaQ ?? '').trim()
  if (q) params.cedula_q = q
  const url = buildUrl(`${BASE}/snapshot`, params)
  return apiClient.get<PrestamoCandidatosDriveSnapshot>(url)
}

export async function postPrestamosCandidatosDriveRefrescar(options?: {
  forzar?: boolean
}): Promise<Record<string, unknown>> {
  const forzar = options?.forzar === true
  const url = forzar ? `${BASE}/refrescar?forzar=true` : `${BASE}/refrescar`
  return apiClient.post<Record<string, unknown>>(url, {})
}

export type PrestamoCandidatosDriveGuardarValidados100Response = {
  insertados_ok: number
  omitidos_no_100: number
  errores_al_guardar: number
  /** Candidatos que siguen en el snapshot (no validaron o error al crear préstamo). */
  pendientes_en_snapshot?: number
  omitidos: Array<{ sheet_row_number: number; cedula_cmp: string; motivos: string[] }>
  errores: Array<{ sheet_row_number: number; cedula_cmp: string; error: string }>
  mensaje: string
}

/** Crea préstamos solo para filas del snapshot al 100% de validadores (sin selección manual). */
export async function postPrestamosCandidatosDriveGuardarValidados100(): Promise<PrestamoCandidatosDriveGuardarValidados100Response> {
  return apiClient.post<PrestamoCandidatosDriveGuardarValidados100Response>(
    `${BASE}/guardar-validados-100`,
    {}
  )
}

export type PrestamoCandidatosDriveGuardarFilaResponse = {
  ok: boolean
  insertados_ok: number
  sheet_row_number: number
  motivos: string[]
  mensaje: string
}

/** Crea un préstamo solo para la fila indicada si cumple el 100% de validadores (misma regla que el lote). */
export async function postPrestamosCandidatosDriveGuardarFila(
  sheetRowNumber: number
): Promise<PrestamoCandidatosDriveGuardarFilaResponse> {
  return apiClient.post<PrestamoCandidatosDriveGuardarFilaResponse>(`${BASE}/guardar-fila`, {
    sheet_row_number: sheetRowNumber,
  })
}
