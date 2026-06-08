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
  confirmaFechaManual: boolean
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
  /** Borrador en BD (escáner); enviar al guardar el reporte si existe. */
  borradorId?: string | null
  /** Origen revisión /pagos (re-escaneo masivo). */
  pagoRevisionId?: number | null
}

export function newClientId(): string {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID()
  }
  return `f-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

/** Fecha local (calendario) en ISO YYYY-MM-DD para inputs type="date". */
export function fechaLocalHoyISO(): string {
  const now = new Date()
  const y = now.getFullYear()
  const mo = String(now.getMonth() + 1).padStart(2, '0')
  const da = String(now.getDate()).padStart(2, '0')
  return `${y}-${mo}-${da}`
}

/** Valor a enviar al guardar: solo fecha explícita (campo o detectada por IA/serial); nunca «hoy». */
export function fechaPagoEfectivaParaGuardar(f: FilaLote): string {
  const m = f.fechaPago.trim()
  if (m) return m
  return f.fechaDetectada.trim()
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
    confirmaFechaManual: false,
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
    borradorId: null,
    pagoRevisionId: null,
  }
}

export type EscanerLoteRevisionContextoItem = {
  pago_id: number
  ok: boolean
  error?: string | null
  cedula?: string
  prestamo_id?: number | null
  numero_documento?: string
  fecha_pago?: string | null
  monto_usd?: number | null
  institucion_bancaria?: string
  nombre_archivo?: string
  mime_type?: string
  archivo_b64?: string
}

export function filaDesdeRevisionPago(
  archivo: File,
  item: EscanerLoteRevisionContextoItem
): FilaLote {
  const base = filaVaciaDesdeArchivo(archivo)
  const fecha = (item.fecha_pago || '').trim()
  const { institucion, otroInstitucion } = resolverInstitucionDesdeExtraccion(
    item.institucion_bancaria || '',
    '',
    ''
  )
  let montoStr = ''
  if (item.monto_usd != null && Number.isFinite(item.monto_usd)) {
    montoStr = formatoMontoParaMostrar(item.monto_usd, 'USD')
  }
  return {
    ...base,
    extract: 'pendiente',
    fechaPago: fecha,
    fechaDetectada: fecha,
    confirmaFechaDetectada: fecha ? 'si' : null,
    confirmaFechaManual: !fecha,
    institucion,
    otroInstitucion,
    numeroOperacion: (item.numero_documento || '').trim(),
    montoStr,
    moneda: 'USD',
    pagoRevisionId: item.pago_id,
    escanerColision: {
      duplicado_en_pagos: false,
      pago_existente_id: item.pago_id,
      prestamo_existente_id: item.prestamo_id ?? null,
      prestamo_objetivo_id: item.prestamo_id ?? null,
    },
  }
}

export function mapColision(
  res: EscanerInfopagosExtraerResponse
): EscanerColision | null {
  return {
    duplicado_en_pagos: Boolean(res.duplicado_en_pagos),
    pago_existente_id:
      typeof res.pago_existente_id === 'number' ? res.pago_existente_id : null,
    prestamo_existente_id:
      typeof res.prestamo_existente_id === 'number'
        ? res.prestamo_existente_id
        : null,
    prestamo_objetivo_id:
      typeof res.prestamo_objetivo_id === 'number'
        ? res.prestamo_objetivo_id
        : null,
  }
}

export function resolverInstitucionDesdeExtraccion(
  geminiInst: string,
  prevInst: string,
  prevOtro: string
): { institucion: string; otroInstitucion: string } {
  const inst =
    (geminiInst || '').trim() ||
    (prevInst || '').trim() ||
    (prevOtro || '').trim()
  const enLista = INSTITUCIONES_FINANCIERAS.includes(
    inst as (typeof INSTITUCIONES_FINANCIERAS)[number]
  )
  if (!inst) {
    return { institucion: '', otroInstitucion: '' }
  }
  if (enLista) {
    return { institucion: inst, otroInstitucion: '' }
  }
  return { institucion: inst, otroInstitucion: inst }
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
      borradorId: null,
    }
  }
  const s = res.sugerencia
  const fechaExtraida = (s.fecha_pago || '').trim()
  const tieneFechaDetectada = Boolean(fechaExtraida)
  const { institucion, otroInstitucion } = resolverInstitucionDesdeExtraccion(
    s.institucion_financiera || '',
    base.institucion,
    base.otroInstitucion
  )
  const mon = s.moneda === 'BS' ? 'BS' : 'USD'
  let montoStr = ''
  if (s.monto != null && Number.isFinite(s.monto)) {
    montoStr = formatoMontoParaMostrar(s.monto, mon)
  }
  const borradorId =
    typeof res.borrador_id === 'string' && res.borrador_id.trim()
      ? res.borrador_id.trim()
      : null
  return {
    ...base,
    extract: 'listo',
    errorExtraccion: undefined,
    fechaPago: tieneFechaDetectada ? fechaExtraida : '',
    fechaDetectada: tieneFechaDetectada ? fechaExtraida : '',
    confirmaFechaDetectada: tieneFechaDetectada ? 'si' : null,
    confirmaFechaManual: !tieneFechaDetectada,
    institucion,
    otroInstitucion,
    numeroOperacion: s.numero_operacion || '',
    montoStr,
    moneda: mon,
    cedulaPagadorImg: s.cedula_pagador_en_comprobante || '',
    validacionCampos: res.validacion_campos ?? null,
    validacionReglas: res.validacion_reglas ?? null,
    escanerColision: mapColision(res),
    borradorId,
  }
}

export function hayDuplicadoFila(f: FilaLote): boolean {
  const v = `${f.validacionCampos ?? ''} ${f.validacionReglas ?? ''}`
  if (/DUPLICADO/i.test(v)) return true
  return Boolean(f.escanerColision?.duplicado_en_pagos)
}
