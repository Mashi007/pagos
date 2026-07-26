import { apiClient } from './api'

export type ConciliacionBancosMoneda = 'USD' | 'BS'

export type ConciliacionBancosBancoCategoria =
  | 'Mercantil'
  | 'BNC'
  | 'Binance'
  | 'BNV'
  | 'Recibos'
  | 'Otros'

export const CONCILIACION_BANCOS_CATEGORIAS: ConciliacionBancosBancoCategoria[] =
  ['Mercantil', 'BNC', 'Binance', 'BNV', 'Recibos', 'Otros']

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
      timeout: 120000,
    })
  },

  async comparar(
    loteId: number,
    bancos: ConciliacionBancosBancoCategoria[]
  ): Promise<{
    ok: boolean
    lote_id: number
    estado: string
    stats: Record<string, number>
    bancos_filtro?: string[]
    pagos_universo?: number
  }> {
    return apiClient.post(
      `${BASE}/lotes/${loteId}/comparar`,
      { bancos },
      { timeout: 180000 }
    )
  },

  async listarResultados(
    loteId: number
  ): Promise<{ ok: boolean; items: ConciliacionBancosResultado[] }> {
    return apiClient.get(`${BASE}/lotes/${loteId}/resultados`)
  },

  async decidir(
    resultadoId: number,
    body: {
      decision: 'VISTO' | 'CORREGIR' | 'OMITIR'
      fuente_elegida?: 'BD' | 'BANCO'
    }
  ): Promise<Record<string, unknown>> {
    return apiClient.post(`${BASE}/resultados/${resultadoId}/decidir`, body, {
      timeout: 180000,
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
