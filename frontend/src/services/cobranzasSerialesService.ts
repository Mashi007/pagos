import { apiClient } from './api'

export interface SerialDepositoIn {
  id: number
  fecha: string
  serial: string
  monto: string
}

export interface SerialPagoCreado {
  /** null en simulación. */
  pago_id: number | null
  deposito_id: number
  cuota_numero: number
  cuota_vencimiento: string
  saldo_cuota_antes: number
  mes: string
  fecha_deposito: string
  serial: string
  monto: number
  /** Otros depósitos del mismo mes que también cumplían la tolerancia. */
  alternativas: number
  cascada: string
}

export type SerialEstadoCedula =
  | 'CEDULA_INVALIDA'
  | 'SIN_ATRASO'
  | 'SIN_COINCIDENCIA'
  | 'PARCIAL'
  | 'COMPLETO'

export interface SerialResultadoCedula {
  cedula: string
  cedula_norm: string | null
  prestamo_id: number | null
  cuotas_atrasadas: number
  cuotas_cubiertas: number
  pagos: SerialPagoCreado[]
  estado: SerialEstadoCedula
  detalle: string
}

export interface SerialLoteResponse {
  simulado: boolean
  procesadas: number
  pagos_creados: number
  depositos_usados: number[]
  depositos_serial_en_bd: number[]
  depositos_en_otras_tablas: number[]
  resultados: SerialResultadoCedula[]
}

export interface SerialOpciones {
  simular: boolean
  tolerancia_pct: number
  max_meses_adelante: number
}

export interface SerialDeshacerResponse {
  eliminados: number[]
  omitidos: { pago_id: number; motivo: string }[]
  errores: { pago_id: number; error: string }[]
}

/** Cascada por pago: un lote de 20 préstamos puede tardar en Render. */
const LOTE_TIMEOUT_MS = 300000

export const cobranzasSerialesService = {
  procesarLote(
    body: {
      cedulas: string[]
      depositos: SerialDepositoIn[]
      usados: number[]
    } & SerialOpciones
  ): Promise<SerialLoteResponse> {
    return apiClient.post<SerialLoteResponse>(
      '/api/v1/cobranzas/seriales/procesar-lote',
      body,
      { timeout: LOTE_TIMEOUT_MS }
    )
  },

  deshacer(pagoIds: number[]): Promise<SerialDeshacerResponse> {
    return apiClient.post<SerialDeshacerResponse>(
      '/api/v1/cobranzas/seriales/deshacer',
      { pago_ids: pagoIds },
      { timeout: LOTE_TIMEOUT_MS }
    )
  },
}
