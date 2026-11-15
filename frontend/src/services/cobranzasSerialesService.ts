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

export interface SerialCuotaRevision {
  id: number
  numero: number
  vencimiento: string
  monto: number
  pagado: number
  falta: number
  estado: string
  atrasada: boolean
}

export interface SerialCandidato {
  deposito_id: number
  fecha: string
  serial: string
  monto: number
}

export interface SerialMesRevision {
  mes: string
  clave: string
  candidatos: SerialCandidato[]
}

export interface SerialBloqueRevision {
  cuota_id: number
  cuota_numero: number
  vencimiento: string
  monto: number
  meses: SerialMesRevision[]
}

export type SerialEstadoRevision =
  | 'CEDULA_INVALIDA'
  | 'SIN_ATRASO'
  | 'SIN_CANDIDATOS'
  | 'CON_CANDIDATOS'

export interface SerialRevisionResponse {
  cedula: string
  cedula_norm: string | null
  prestamo_id: number | null
  cliente: string
  cuotas: SerialCuotaRevision[]
  bloques: SerialBloqueRevision[]
  sugeridos: number[]
  depositos_serial_en_bd: number[]
  depositos_en_otras_tablas: number[]
  estado: SerialEstadoRevision
  detalle: string
}

export interface SerialGuardarResponse {
  prestamo_id: number
  pagos: (SerialCandidato & { pago_id: number; cascada: string })[]
  error: string | null
  cuotas: SerialCuotaRevision[]
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

  revisionCedula(body: {
    cedula: string
    depositos: SerialDepositoIn[]
    usados: number[]
    tolerancia_pct: number
    meses_despues: number
  }): Promise<SerialRevisionResponse> {
    return apiClient.post<SerialRevisionResponse>(
      '/api/v1/cobranzas/seriales/revision-cedula',
      body,
      { timeout: LOTE_TIMEOUT_MS }
    )
  },

  guardarCedula(body: {
    cedula: string
    prestamo_id: number
    depositos: SerialDepositoIn[]
  }): Promise<SerialGuardarResponse> {
    return apiClient.post<SerialGuardarResponse>(
      '/api/v1/cobranzas/seriales/guardar-cedula',
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
