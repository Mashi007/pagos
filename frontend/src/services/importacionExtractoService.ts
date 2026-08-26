import { apiClient } from './api'

const BASE = '/api/v1/importacion-extracto'

/** Bancos del extracto: un archivo completo pertenece al banco seleccionado en cabecera. */
export const BANCOS_EXTRACTO = [
  'Mercantil',
  'BNC',
  'Binance',
  'Zelle',
  'BNV',
] as const

export type BancoExtracto = (typeof BANCOS_EXTRACTO)[number]

export type ImportacionExtractoEstado =
  | 'IGUAL_100'
  | 'SE_PUEDE_IMPORTAR'
  | 'SEMEJANTE'
  | 'PARSE_ERROR'
  | 'SIN_PRESTAMO'
  | 'VARIOS_PRESTAMOS'
  | 'VISTO'
  | 'IMPORTADO'

export interface ImportacionExtractoLote {
  id: number
  archivo_nombre: string
  banco?: string | null
  estado: string
  usuario_id?: number | null
  creado_en?: string | null
  stats?: Record<string, number> | null
}

export interface ImportacionExtractoFila {
  id: number
  lote_id: number
  fila_excel: number
  fecha_deposito: string | null
  descripcion_raw: string | null
  cedula: string | null
  serial: string | null
  serial_norm: string | null
  monto_usd: number | null
  estado: ImportacionExtractoEstado | string
  similitud_pct: number | null
  pago_id_match: number | null
  prestamo_id: number | null
  pago_id_creado: number | null
  detalle: string | null
  /** True si el préstamo APROBADO tiene pagos con institución Drive (observación: «Drive»). */
  alerta_banco_drive?: boolean
  /** True si el serial coincide con un Nº documento compuesto (observación: «Serial compuesto»). */
  alerta_serial_mixto?: boolean
  visto: boolean
  importado: boolean
  /** True si la fila puede importarse con OK (faltante, semejante o visto). */
  puede_ok_importar?: boolean
}

export const importacionExtractoService = {
  async subirExcel(file: File, banco: string) {
    const fd = new FormData()
    fd.append('archivo', file)
    fd.append('banco', banco)
    return apiClient.post<{
      lote: ImportacionExtractoLote
      stats: Record<string, number>
      filas: number
    }>(`${BASE}/lotes`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  },

  async listarLotes() {
    const data = await apiClient.get<{ lotes: ImportacionExtractoLote[] }>(
      `${BASE}/lotes`
    )
    return data.lotes || []
  },

  async listarFilas(
    loteId: number,
    opts?: { estado?: string; solo_importables?: boolean }
  ) {
    const data = await apiClient.get<{
      lote_id: number
      filas: ImportacionExtractoFila[]
    }>(`${BASE}/lotes/${loteId}/filas`, { params: opts })
    return data.filas || []
  },

  async marcarVisto(filaIds: number[]) {
    return apiClient.post<{ ok: boolean; marcados: number }>(
      `${BASE}/filas/visto`,
      { fila_ids: filaIds }
    )
  },

  async ocultar(filaIds: number[]) {
    return apiClient.post<{ ok: boolean; ocultados: number }>(
      `${BASE}/filas/ocultar`,
      { fila_ids: filaIds }
    )
  },

  async importar(filaIds: number[]) {
    return apiClient.post<{
      ok: boolean
      importados: number
      resultados: Array<{
        ok: boolean
        fila_id: number
        motivo?: string
        pago_id?: number
      }>
    }>(`${BASE}/filas/importar`, { fila_ids: filaIds }, { timeout: 300000 })
  },
}
