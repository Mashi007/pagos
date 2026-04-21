/**
 * Tipos y mapeo de extracción Gemini compartidos por la página de lote y el runner en segundo plano.
 */
import type { EscanerInfopagosExtraerResponse } from '../services/cobrosService'
import { formatMontoBsVe } from '../utils/montoLatam'

const INSTITUCIONES_FINANCIERAS = [
  'BINANCE',
  'BNC',
  'Banco de Venezuela',
  'Mercantil',
  'Recibos',
] as const

function formatoMontoParaMostrar(num: number, moneda: 'BS' | 'USD'): string {
  if (moneda === 'BS') return formatMontoBsVe(num)
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num)
}

export type EscanerColision = {
  duplicado_en_pagos: boolean
  pago_existente_id: number | null
  prestamo_existente_id: number | null
  prestamo_objetivo_id: number | null
}

export type ExtractEstado = 'pendiente' | 'extrayendo' | 'listo' | 'error'

export type FilaLote = {
  clientId: string
  archivo: File
  nombreArchivo: string
  extract: ExtractEstado
  errorExtraccion?: string
  fechaPago: string
  fechaDetectada: string
  confirmaFechaDetectada: null | 'si' | 'no'
  institucion: string
  otroInstitucion: string
  numeroOperacion: string
  montoStr: string
  moneda: 'BS' | 'USD'
  cedulaPagadorImg: string
  validacionCampos: string | null
  validacionReglas: string | null
  escanerColision: EscanerColision | null
  guardando: boolean
  guardado: boolean
  guardadoError?: string
  referencia?: string
  reciboToken?: string | null
  pagoId?: number | null
  enRevision?: boolean
  editando: boolean
  descargandoRecibo: boolean
}

export function newClientId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `f-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

export function filaVaciaDesdeArchivo(archivo: File): FilaLote {
  return {
    clientId: newClientId(),
    archivo,
    nombreArchivo: archivo.name || 'comprobante',
    extract: 'pendiente',
    fechaPago: '',
    fechaDetectada: '',
    confirmaFechaDetectada: null,
    institucion: '',
    otroInstitucion: '',
    numeroOperacion: '',
    montoStr: '',
    moneda: 'USD',
    cedulaPagadorImg: '',
    validacionCampos: null,
    validacionReglas: null,
    escanerColision: null,
    guardando: false,
    guardado: false,
    editando: false,
    descargandoRecibo: false,
  }
}

export function mapColision(res: EscanerInfopagosExtraerResponse): EscanerColision | null {
  return {
    duplicado_en_pagos: Boolean(res.duplicado_en_pagos),
    pago_existente_id:
      typeof res.pago_existente_id === 'number' ? res.pago_existente_id : null,
    prestamo_existente_id:
      typeof res.prestamo_existente_id === 'number' ? res.prestamo_existente_id : null,
    prestamo_objetivo_id:
      typeof res.prestamo_objetivo_id === 'number' ? res.prestamo_objetivo_id : null,
  }
}

export function filaTrasExtraccion(
  base: FilaLote,
  res: EscanerInfopagosExtraerResponse
): FilaLote {
  if (!res.ok || !res.sugerencia) {
    return {
      ...base,
      extract: 'error',
      errorExtraccion: res.error || 'No se pudo leer el comprobante.',
    }
  }
  const s = res.sugerencia
  const fechaExtraida = s.fecha_pago || ''
  const inst = (s.institucion_financiera || '').trim()
  const enLista = INSTITUCIONES_FINANCIERAS.includes(
    inst as (typeof INSTITUCIONES_FINANCIERAS)[number]
  )
  const mon = s.moneda === 'BS' ? 'BS' : 'USD'
  let montoStr = ''
  if (s.monto != null && Number.isFinite(s.monto)) {
    montoStr = formatoMontoParaMostrar(s.monto, mon)
  }
  return {
    ...base,
    extract: 'listo',
    errorExtraccion: undefined,
    fechaPago: fechaExtraida,
    fechaDetectada: fechaExtraida,
    confirmaFechaDetectada: null,
    institucion: enLista ? inst : inst,
    otroInstitucion: enLista ? '' : inst,
    numeroOperacion: s.numero_operacion || '',
    montoStr,
    moneda: mon,
    cedulaPagadorImg: s.cedula_pagador_en_comprobante || '',
    validacionCampos: res.validacion_campos ?? null,
    validacionReglas: res.validacion_reglas ?? null,
    escanerColision: mapColision(res),
  }
}

export function hayDuplicadoFila(f: FilaLote): boolean {
  const v = `${f.validacionCampos ?? ''} ${f.validacionReglas ?? ''}`
  if (/DUPLICADO/i.test(v)) return true
  return Boolean(f.escanerColision?.duplicado_en_pagos)
}
