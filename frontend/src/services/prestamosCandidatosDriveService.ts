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
  /**
   * Motivos exactos por los que el servidor NO marca la fila como guardable
   * (lista vacía o ausente si la fila está lista). Permite que la UI muestre
   * el detalle real en lugar de un texto genérico.
   */
  motivos_no_guardable?: string[]
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
  /** Casos que requieren revisión operativa por huella incompleta/no comparable. */
  kpis_huella_no_comparable?: number
  total_sin_filtro?: number
  filtro_cedula?: string | null
  limit: number
  offset: number
  filas: PrestamoCandidatoDriveFila[]
}

export async function getPrestamosCandidatosDriveSnapshot(
  limit = 500,
  offset = 0,
  cedulaQ?: string,
  soloHuellaNoComparable = false
): Promise<PrestamoCandidatosDriveSnapshot> {
  const params: Record<string, string | number | boolean> = { limit, offset }
  const q = (cedulaQ ?? '').trim()
  if (q) params.cedula_q = q
  if (soloHuellaNoComparable) params.solo_huella_no_comparable = true
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
  omitidos: Array<{
    sheet_row_number: number
    cedula_cmp: string
    motivos: string[]
  }>
  errores: Array<{
    sheet_row_number: number
    cedula_cmp: string
    error: string
  }>
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
  return apiClient.post<PrestamoCandidatosDriveGuardarFilaResponse>(
    `${BASE}/guardar-fila`,
    {
      sheet_row_number: sheetRowNumber,
    }
  )
}

export type PrestamoCandidatosDriveCamposEditables = {
  col_e_cedula?: string
  col_i_modelo_vehiculo?: string
  col_j_analista?: string
  col_k_concesionario?: string
  col_n_total_financiamiento?: string
  col_q_fecha?: string
  col_r_numero_cuotas?: string
  col_s_modalidad_pago?: string
}

export type PrestamoCandidatosDriveActualizarCamposResponse = {
  ok: boolean
  id: number
  sheet_row_number: number
  cedula_cmp: string
  payload?: PrestamoCandidatoDrivePayload
  mensaje: string
}

/** Actualiza campos editables (E,I,J,K,N,Q,R,S) en snapshot y tabla drive. */
export async function postPrestamosCandidatosDriveActualizarCampos(
  id: number,
  campos: PrestamoCandidatosDriveCamposEditables
): Promise<PrestamoCandidatosDriveActualizarCamposResponse> {
  return apiClient.post<PrestamoCandidatosDriveActualizarCamposResponse>(
    `${BASE}/actualizar-campos`,
    { id, ...campos }
  )
}

export type PrestamoCandidatosDriveEliminarSeleccionadosResponse = {
  eliminados: number
  seleccionados: number
  mensaje: string
}

export async function postPrestamosCandidatosDriveEliminarSeleccionados(
  ids: number[]
): Promise<PrestamoCandidatosDriveEliminarSeleccionadosResponse> {
  return apiClient.post<PrestamoCandidatosDriveEliminarSeleccionadosResponse>(
    `${BASE}/eliminar-seleccionados`,
    { ids }
  )
}
