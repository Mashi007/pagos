import { apiClient } from './api'

export interface SerialDepositoIn {
  id: number
  fecha: string
  serial: string
  monto: string
}

export interface SerialPagoCreado {
  pago_id: number
  deposito_id: number
  cuota_numero: number
  cuota_vencimiento: string
  saldo_cuota_antes: number
  mes: string
  fecha_deposito: string
  serial: string
  monto: number
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
  procesadas: number
  pagos_creados: number
  depositos_usados: number[]
  depositos_serial_en_bd: number[]
  resultados: SerialResultadoCedula[]
}

/** Cascada por pago: un lote de 20 préstamos puede tardar en Render. */
const LOTE_TIMEOUT_MS = 300000

export const cobranzasSerialesService = {
  procesarLote(body: {
    cedulas: string[]
    depositos: SerialDepositoIn[]
    usados: number[]
  }): Promise<SerialLoteResponse> {
    return apiClient.post<SerialLoteResponse>(
      '/api/v1/cobranzas/seriales/procesar-lote',
      body,
      { timeout: LOTE_TIMEOUT_MS }
    )
  },
}
