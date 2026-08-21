import { apiClient } from './api'

export type ConciliacionBancosMoneda = 'USD' | 'BS'

export type ConciliacionBancosBancoCategoria =
  | 'Mercantil'
  | 'BNC'
  | 'Binance'
  | 'Zelle'
  | 'BNV'
  | 'Recibos'
  | 'Drive'
  | 'Otros'

export const CONCILIACION_BANCOS_CATEGORIAS: ConciliacionBancosBancoCategoria[] =
  ['Mercantil', 'BNC', 'Binance', 'Zelle', 'BNV', 'Recibos', 'Drive', 'Otros']

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
  comparar_huerfano?: boolean
  job_vivo?: boolean
  filas_extracto_upsert?: number | null
  extracto_error?: string | null
  fuente_carga?: string | null
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
    banco?: ConciliacionBancosBancoCategoria
  }): Promise<{ ok: boolean; lote: ConciliacionBancosLote }> {
    const fd = new FormData()
    fd.append('file', params.file)
    fd.append('moneda_carga', params.moneda_carga)
    fd.append('fecha_desde', params.fecha_desde)
    fd.append('fecha_hasta', params.fecha_hasta)
    if (params.banco) fd.append('banco', params.banco)
    return apiClient.post(`${BASE}/lotes`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  },

  async crearLoteDesdeHistorica(params: {
    bancos: ConciliacionBancosBancoCategoria[]
    fecha_desde: string
    fecha_hasta: string
    moneda_carga: ConciliacionBancosMoneda
  }): Promise<{ ok: boolean; lote: ConciliacionBancosLote }> {
    return apiClient.post(
      `${BASE}/lotes/desde-historica`,
      {
        bancos: params.bancos,
        fecha_desde: params.fecha_desde,
        fecha_hasta: params.fecha_hasta,
        moneda_carga: params.moneda_carga,
      },
      { timeout: 180000 }
    )
  },

  async buscarSerial(params: {
    serial: string
    moneda?: ConciliacionBancosMoneda
  }): Promise<{
    ok: boolean
    encontrado: boolean
    serial: string
    serial_norm?: string
    en_extracto: boolean
    filas_extracto: number
    filas_pendientes?: number
    filas_ya_cerradas?: number
    ya_visto_o_conciliado?: boolean
    items: Array<{
      id: number
      banco: string
      fecha?: string | null
      referencia: string
      referencia_norm?: string | null
      monto?: number | null
      moneda?: string
    }>
    en_pagos: boolean
    pagos_count: number
  }> {
    const q: Record<string, string> = { serial: params.serial }
    if (params.moneda) q.moneda = params.moneda
    return apiClient.get(`${BASE}/extracto/por-serial`, {
      params: q,
      timeout: 60000,
    })
  },

  async crearLoteDesdeSerial(params: {
    serial: string
    moneda_carga: ConciliacionBancosMoneda
    bancos?: ConciliacionBancosBancoCategoria[]
  }): Promise<{ ok: boolean; lote: ConciliacionBancosLote }> {
    return apiClient.post(
      `${BASE}/lotes/desde-serial`,
      {
        serial: params.serial,
        moneda_carga: params.moneda_carga,
        bancos: params.bancos || [],
      },
      { timeout: 120000 }
    )
  },

  async listarLotes(limit = 40): Promise<{
    ok: boolean
    items: Array<{
      id: number
      archivo_nombre: string
      estado: string
      fecha_desde?: string | null
      fecha_hasta?: string | null
      creado_en?: string | null
      bancos_filtro?: string[]
      sin_bd: number
    }>
  }> {
    return apiClient.get(`${BASE}/lotes`, {
      params: { limit },
      timeout: 60000,
    })
  },

  async resumenSinBd(loteId?: number | null): Promise<{
    ok: boolean
    tipo: 'SIN_BD'
    lote_id: number | null
    archivo_nombre?: string | null
    estado?: string | null
    bancos_filtro?: string[]
    total: number
    monto_total: number
    bancos: number
    por_banco: Array<{
      banco: string
      filas: number
      monto_total: number
      pct_filas?: number
      pct_monto?: number
      fecha_min?: string | null
      fecha_max?: string | null
    }>
    serie_diaria?: Array<{
      fecha: string
      label: string
      cantidad: number
      monto_usd: number
    }>
    message?: string
  }> {
    const q: Record<string, string> = {}
    if (loteId != null) q.lote_id = String(loteId)
    return apiClient.get(`${BASE}/resultados/resumen-sin-bd`, {
      params: q,
      timeout: 120000,
    })
  },

  async resumenNovedadesPorBanco(loteId?: number | null): Promise<{
    ok: boolean
    lote_id: number | null
    archivo_nombre?: string | null
    estado?: string | null
    bancos_filtro?: string[]
    fuente?: string
    totales: Record<string, number>
    monto_totales: Record<string, number>
    por_banco: Array<{
      banco: string
      filas: number
      MATCH_EXACTO: number
      MATCH_PARCIAL: number
      SIN_BD: number
      SIN_BANCO: number
      AMBIGUO: number
      SIN_TASA: number
      CONCILIADOS: number
      monto_total: number
      montos?: Record<string, number>
    }>
    message?: string
  }> {
    const q: Record<string, string> = {}
    if (loteId != null) q.lote_id = String(loteId)
    return apiClient.get(`${BASE}/resultados/resumen-novedades-por-banco`, {
      params: q,
      timeout: 120000,
    })
  },

  async resumenExtracto(params?: {
    bancos?: ConciliacionBancosBancoCategoria[]
    fecha_desde?: string
    fecha_hasta?: string
    moneda?: ConciliacionBancosMoneda
  }): Promise<{
    ok: boolean
    total: number
    monto_total: number
    bancos: number
    por_banco: Array<{
      banco: string
      filas: number
      monto_total: number
      pct_filas?: number
      pct_monto?: number
      fecha_min?: string | null
      fecha_max?: string | null
    }>
  }> {
    const q: Record<string, string> = {}
    if (params?.bancos?.length) q.bancos = params.bancos.join(',')
    if (params?.fecha_desde) q.fecha_desde = params.fecha_desde
    if (params?.fecha_hasta) q.fecha_hasta = params.fecha_hasta
    if (params?.moneda) q.moneda = params.moneda
    return apiClient.get(`${BASE}/extracto/resumen`, {
      params: q,
      timeout: 60000,
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
    opts?: {
      page?: number
      per_page?: number
      tipo_novedad?: string[]
      decision?: string
    }
  ): Promise<{
    ok: boolean
    items: ConciliacionBancosResultado[]
    total: number
    page: number
    per_page: number
    pages: number
    stats?: Record<string, number>
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
      // Tandas pequenias (front: 50). Evita 520 Cloudflare a los ~3 min.
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
