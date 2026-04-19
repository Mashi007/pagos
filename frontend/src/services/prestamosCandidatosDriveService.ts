import { apiClient, buildUrl } from './api'

const BASE = '/api/v1/prestamos/candidatos-drive'

export type PrestamoCandidatoDrivePayload = Record<string, unknown>

export type PrestamoCandidatoDriveFila = {
  id: number
  sheet_row_number: number
  cedula_cmp: string
  payload: PrestamoCandidatoDrivePayload
  computed_at: string | null
}

export type PrestamoCandidatosDriveSnapshot = {
  drive_synced_at: string | null
  computed_at: string | null
  total: number
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
