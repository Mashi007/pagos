import { apiClient } from './api'

export type ConciliacionBancosMoneda = 'USD' | 'BS'

export type ConciliacionBancosBancoCategoria =
  | 'Mercantil'
  | 'BNC'
  | 'Binance'
  | 'BNV'
  | 'Recibos'
  | 'Drive'
  | 'Otros'

export const CONCILIACION_BANCOS_CATEGORIAS: ConciliacionBancosBancoCategoria[] =
  ['Mercantil', 'BNC', 'Binance', 'BNV', 'Recibos', 'Drive', 'Otros']

export interface ConciliacionBancosLote {
  id: number
  archivo_nombre: string
  fecha_desde: string
  fecha_hasta: string
  estado: string
  moneda_carga: string
  usuario_id?: number | null
  creado_en?: string | null
  bancos_filtro?: string[]
  filas_banco?: number | null
  stats?: Record<string, number> | null
  pagos_universo?: number | null
  comparar_elapsed_ms?: number | null
  comparar_error?: string | null
}

export interface ConciliacionBancosResultado {
  id: number
  lote_id: number
  banco_id?: number | null
  pago_id?: number | null
  cedula?: string | null
  prestamo_id?: number | null
  institucion_bancaria?: string | null
  institucion_categoria?: string | null
  fecha_banco?: string | null
  fecha_bd?: string | null
  referencia_banco?: string | null
  referencia_bd?: string | null
  monto_banco?: number | null
  monto_bd?: number | null
  similitud_pct?: number | null
  tipo_novedad: string
  decision: string
  fuente_elegida?: string | null
  aplicado: boolean
  detalle_aplicacion?: string | null
  candidatos?: Array<{
    pago_id: number
    cedula?: string | null
    prestamo_id?: number | null
    monto?: number | null
    institucion_categoria?: string | null
  }> | null
}

const BASE = '/api/v1/conciliacion-bancos'

export const conciliacionBancosService = {
  async crearLote(params: {
    file: File
    moneda_carga: ConciliacionBancosMoneda
    fecha_desde: string
    fecha_hasta: string
  }): Promise<{ ok: boolean; lote: ConciliacionBancosLote }> {
    const fd = new FormData()
    fd.append('file', params.file)
    fd.append('moneda_carga', params.moneda_carga)
    fd.append('fecha_desde', params.fecha_desde)
    fd.append('fecha_hasta', params.fecha_hasta)
    return apiClient.post(`${BASE}/lotes`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  },

  async comparar(
    loteId: number,
    bancos: ConciliacionBancosBancoCategoria[],
    fechas?: { fecha_desde?: string; fecha_hasta?: string }
  ): Promise<{
    ok: boolean
    async?: boolean
    lote_id: number
    estado: string
    message?: string
    stats?: Record<string, number>
    bancos_filtro?: string[]
    fecha_desde?: string
    fecha_hasta?: string
    pagos_universo?: number
  }> {
    // Arranca en background; el cliente hace polling del lote.
    return apiClient.post(
      `${BASE}/lotes/${loteId}/comparar`,
      {
        bancos,
        fecha_desde: fechas?.fecha_desde || undefined,
        fecha_hasta: fechas?.fecha_hasta || undefined,
      },
      { timeout: 60000 }
    )
  },

  async obtenerLote(
    loteId: number
  ): Promise<{ ok: boolean; lote: ConciliacionBancosLote }> {
    return apiClient.get(`${BASE}/lotes/${loteId}`, { timeout: 60000 })
  },

  async listarResultados(
    loteId: number,
    opts?: { page?: number; per_page?: number; tipo_novedad?: string[]; decision?: string }
  ): Promise<{
    ok: boolean
    items: ConciliacionBancosResultado[]
    total: number
    page: number
    per_page: number
    pages: number
  }> {
    const params: Record<string, string | number> = {
      page: opts?.page ?? 1,
      per_page: opts?.per_page ?? 200,
    }
    if (opts?.tipo_novedad?.length) {
      params.tipo_novedad = opts.tipo_novedad.join(',')
    }
    if (opts?.decision) {
      params.decision = opts.decision
    }
    return apiClient.get(`${BASE}/lotes/${loteId}/resultados`, {
      params,
      timeout: 120000,
    })
  },

  async decidir(
    resultadoId: number,
    body: {
      decision: 'VISTO' | 'CORREGIR' | 'OMITIR'
      fuente_elegida?: 'BD' | 'BANCO'
      pago_id_elegido?: number
      pago_ids_elegidos?: number[]
    }
  ): Promise<Record<string, unknown>> {
    return apiClient.post(`${BASE}/resultados/${resultadoId}/decidir`, body, {
      timeout: 180000,
    })
  },

  async decidirMasivo(body: {
    items: Array<{
      resultado_id: number
      fuente_elegida?: 'BD' | 'BANCO'
      pago_id_elegido?: number
      pago_ids_elegidos?: number[]
    }>
    fuente_default?: 'BD' | 'BANCO'
  }): Promise<{
    ok: boolean
    total: number
    exitosos: number
    errores: number
    sin_pago_vistos: number
    con_cambio: number
    detalle: Array<{
      resultado_id: number
      ok: boolean
      modo?: string
      fuente?: string
      cambio?: boolean
      error?: string
    }>
  }> {
    return apiClient.post(`${BASE}/resultados/decidir-masivo`, body, {
      timeout: 300000,
    })
  },

  async descargarExcel(loteId: number): Promise<void> {
    const blob = await apiClient.get(`${BASE}/lotes/${loteId}/exportar-excel`, {
      responseType: 'blob',
      timeout: 120000,
    })
    const url = window.URL.createObjectURL(blob as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `conciliacion_bancos_lote_${loteId}.xlsx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  },
}
