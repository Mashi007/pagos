import { Badge } from '../../components/ui/badge'
import {
  type Pago,
  type PagoInicialRegistrar,
} from '../../services/pagoService'
import { codigoEstadoCuotaParaUi } from '../../utils/cuotaEstadoDisplay'

/** Estados de negocio del préstamo (tabla prestamos.estado); alineado con backend y fechas obligatorias. */
const OPCIONES_ESTADO_PRESTAMO_REVISION: { value: string; label: string }[] = [
  { value: 'DRAFT', label: 'Borrador' },
  { value: 'EN_REVISION', label: 'En revisión' },
  { value: 'EVALUADO', label: 'Evaluado' },
  { value: 'APROBADO', label: 'Aprobado' },
  { value: 'DESEMBOLSADO', label: 'Desembolsado' },
  { value: 'LIQUIDADO', label: 'Liquidado' },
  { value: 'DESISTIMIENTO', label: 'Desistimiento' },
  { value: 'RECHAZADO', label: 'Rechazado' },
]

export function opcionesSelectEstadoPrestamoRevision(
  estadoRaw: string | undefined
) {
  const codigo = (estadoRaw ?? '').trim().toUpperCase()
  if (
    codigo &&
    !OPCIONES_ESTADO_PRESTAMO_REVISION.some(o => o.value === codigo)
  ) {
    return [
      { value: codigo, label: `${codigo} (legacy)` },
      ...OPCIONES_ESTADO_PRESTAMO_REVISION,
    ]
  }
  return OPCIONES_ESTADO_PRESTAMO_REVISION
}

/** Códigos que acepta PUT /revision-manual/cuotas/{id} (mayúsculas). */
const OPCIONES_ESTADO_CUOTA_REVISION: { value: string; label: string }[] = [
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'PARCIAL', label: 'Parcial' },
  { value: 'VENCIDO', label: 'Vencido' },
  { value: 'MORA', label: 'Mora' },
  { value: 'PAGADO', label: 'Pagado' },
  { value: 'PAGO_ADELANTADO', label: 'Pago adelantado' },
  { value: 'CANCELADA', label: 'Cancelada' },
]

export function opcionesSelectCuotaRevision(estadoRaw: string | undefined) {
  const codigo = codigoEstadoCuotaParaUi(estadoRaw)

  if (codigo && !OPCIONES_ESTADO_CUOTA_REVISION.some(o => o.value === codigo)) {
    return [
      { value: codigo, label: `${codigo} (legacy)` },
      ...OPCIONES_ESTADO_CUOTA_REVISION,
    ]
  }

  return OPCIONES_ESTADO_CUOTA_REVISION
}

export interface ClienteData {
  cliente_id: number

  nombres: string

  cedula: string

  telefono: string

  email: string

  direccion: string

  ocupacion: string

  estado: string

  fecha_nacimiento: string | null

  notas: string
}

export interface PrestamoData {
  prestamo_id: number

  cliente_id?: number

  cedula: string

  nombres: string

  total_financiamiento: number

  numero_cuotas: number

  tasa_interes: number

  producto: string

  observaciones: string

  fecha_requerimiento: string | null

  modalidad_pago: string

  cuota_periodo: number

  fecha_base_calculo: string | null

  fecha_aprobacion: string | null

  estado: string

  concesionario: string

  analista: string

  modelo_vehiculo: string

  valor_activo: number | null

  usuario_proponente: string

  usuario_aprobador: string
}

export interface CuotaData {
  cuota_id: number

  numero_cuota: number

  monto: number

  fecha_vencimiento: string | null

  fecha_pago: string | null

  total_pagado: number

  estado: string

  observaciones: string
}

/** Fecha comparable YYYY-MM-DD para detectar cambios vs carga inicial. */
export function normDateCmp(v: string | null | undefined): string {
  if (v == null || v === '') return ''
  if (typeof v === 'string' && v.length >= 10) return v.slice(0, 10)
  try {
    const d = new Date(v)
    return isNaN(d.getTime()) ? String(v) : d.toISOString().slice(0, 10)
  } catch {
    return String(v)
  }
}

export function firmaSoloCliente(cliente: Partial<ClienteData>): string {
  return JSON.stringify({
    nombres: String(cliente.nombres ?? '').trim(),
    telefono: String(cliente.telefono ?? '').trim(),
    email: String(cliente.email ?? '').trim(),
    direccion: String(cliente.direccion ?? '').trim(),
    ocupacion: String(cliente.ocupacion ?? '').trim(),
    estado: String(cliente.estado ?? '').trim(),
    fn:
      cliente.fecha_nacimiento == null || cliente.fecha_nacimiento === ''
        ? ''
        : normDateCmp(String(cliente.fecha_nacimiento)),
    notas: String(cliente.notas ?? ''),
  })
}

export function firmaSoloPrestamo(p: Partial<PrestamoData>): string {
  return JSON.stringify({
    tf: Number(p.total_financiamiento) || 0,
    nc: Number(p.numero_cuotas) || 0,
    ti: Number(p.tasa_interes) || 0,
    producto: String(p.producto ?? '').trim(),
    obs: String(p.observaciones ?? ''),
    cedula: String(p.cedula ?? '').trim(),
    nombres: String(p.nombres ?? '').trim(),
    fr: normDateCmp(p.fecha_requerimiento as string | null | undefined),
    mod: String(p.modalidad_pago ?? '').trim(),
    cp: Number(p.cuota_periodo) || 0,
    fa: normDateCmp(p.fecha_aprobacion as string | null | undefined),
    fb: normDateCmp(p.fecha_base_calculo as string | null | undefined),
    estado: String(p.estado ?? '')
      .trim()
      .toUpperCase(),
    conc: String(p.concesionario ?? '').trim(),
    analista: String(p.analista ?? '').trim(),
    mv: String(p.modelo_vehiculo ?? '').trim(),
    va: p.valor_activo == null ? null : Number(p.valor_activo),
    up: String(p.usuario_proponente ?? '').trim(),
    ua: String(p.usuario_aprobador ?? '').trim(),
  })
}

export function firmaSoloCuotas(cuotas: Partial<CuotaData>[]): string {
  const sorted = [...cuotas].sort(
    (a, b) => (a.cuota_id ?? 0) - (b.cuota_id ?? 0)
  )
  return JSON.stringify(
    sorted.map(c => ({
      id: c.cuota_id,
      num: c.numero_cuota,
      m: Number(c.monto) || 0,
      fv: normDateCmp(c.fecha_vencimiento as string | null | undefined),
      fp: normDateCmp(c.fecha_pago as string | null | undefined),
      tp: Number(c.total_pagado) || 0,
      est: String(c.estado ?? '').trim(),
    }))
  )
}

/**
 * Alinea la tabla de cuotas al `numero_cuotas` del préstamo (condiciones): genera filas 1..N
 * y rellena huecos con placeholders editables (sin `cuota_id`). Las cuotas con número > N
 * o sin número válido se mantienen al final para no ocultar datos de BD.
 */
export function mergeCuotasParaMostrar(
  cuotas: Partial<CuotaData>[] | undefined,
  numeroCuotas: number | null | undefined
): Partial<CuotaData>[] {
  const lista = Array.isArray(cuotas) ? [...cuotas] : []
  lista.sort(
    (a, b) => (Number(a.numero_cuota) || 0) - (Number(b.numero_cuota) || 0)
  )
  const n = Math.floor(Number(numeroCuotas) || 0)
  if (n < 1) return lista

  const byNum = new Map<number, Partial<CuotaData>>()
  for (const c of lista) {
    const num = Math.floor(Number(c.numero_cuota) || 0)
    if (num >= 1 && !byNum.has(num)) byNum.set(num, c)
  }

  const head: Partial<CuotaData>[] = []
  for (let i = 1; i <= n; i++) {
    const existing = byNum.get(i)
    if (existing) {
      head.push({ ...existing, numero_cuota: i })
    } else {
      head.push({
        numero_cuota: i,
        monto: 0,
        fecha_vencimiento: null,
        fecha_pago: null,
        total_pagado: 0,
        estado: 'PENDIENTE',
        observaciones: '',
      })
    }
  }

  const extras = lista.filter(c => {
    const num = Math.floor(Number(c.numero_cuota) || 0)
    return num > n || num < 1
  })

  return [...head, ...extras]
}

/**
 * Campos de préstamo para PUT revisión manual o POST guardar+reconstruir cuotas,
 * alineado con el guardado parcial de `EditarRevisionManual` (condiciones + carátula).
 */
export function buildPrestamoPatchGuardarRevision(
  p: Partial<PrestamoData>,
  formatDateForInput: (iso: string | null | undefined) => string
): Record<string, unknown> {
  const prestamoUpdate: Record<string, unknown> = {}

  const faNorm = formatDateForInput(p.fecha_aprobacion ?? null)
  const fbNorm = formatDateForInput(p.fecha_base_calculo ?? null)
  if (faNorm) {
    prestamoUpdate.fecha_aprobacion = faNorm
    prestamoUpdate.fecha_base_calculo = faNorm
  } else if (fbNorm) {
    prestamoUpdate.fecha_aprobacion = fbNorm
    prestamoUpdate.fecha_base_calculo = fbNorm
  }

  if (p.total_financiamiento !== undefined && p.total_financiamiento >= 0) {
    prestamoUpdate.total_financiamiento = p.total_financiamiento
  }
  if (p.numero_cuotas !== undefined && p.numero_cuotas >= 1) {
    prestamoUpdate.numero_cuotas = p.numero_cuotas
  }
  // tasa_interes: producto sin interés (0%); no se envía desde el parche de revisión.
  if (p.producto !== undefined) {
    prestamoUpdate.producto = p.producto
  }
  if (p.cedula !== undefined) {
    prestamoUpdate.cedula = p.cedula
  }
  if (p.nombres !== undefined) {
    prestamoUpdate.nombres = p.nombres
  }
  if (p.fecha_requerimiento !== undefined) {
    prestamoUpdate.fecha_requerimiento = p.fecha_requerimiento || null
  }
  if (p.modalidad_pago !== undefined) {
    prestamoUpdate.modalidad_pago = p.modalidad_pago
  }
  if (p.cuota_periodo !== undefined && p.cuota_periodo >= 0) {
    prestamoUpdate.cuota_periodo = p.cuota_periodo
  }

  const estadoNorm = (p.estado ?? '').toString().trim().toUpperCase()
  if (estadoNorm) {
    prestamoUpdate.estado = estadoNorm
  }
  if (p.concesionario !== undefined) {
    prestamoUpdate.concesionario = p.concesionario
  }
  if (p.analista !== undefined) {
    prestamoUpdate.analista = p.analista
  }
  if (p.modelo_vehiculo !== undefined) {
    prestamoUpdate.modelo_vehiculo = p.modelo_vehiculo
  }
  if (p.valor_activo !== undefined && p.valor_activo !== null) {
    prestamoUpdate.valor_activo = p.valor_activo
  }
  if (p.usuario_proponente !== undefined) {
    prestamoUpdate.usuario_proponente = p.usuario_proponente
  }
  if (p.usuario_aprobador !== undefined) {
    prestamoUpdate.usuario_aprobador = p.usuario_aprobador
  }

  prestamoUpdate.observaciones = String(p.observaciones ?? '')

  return prestamoUpdate
}

export type FirmaCargaRevision = {
  cliente: string
  prestamo: string
  cuotas: string
}

/** Lotes de PUT de cuotas en revisión manual (evita ~12 s en serie contra el mismo host). */
export const CUOTAS_REVISION_PUT_CONCURRENCY = 6

export async function ejecutarEnLotes<T>(
  items: T[],
  tamanoLote: number,
  fn: (item: T) => Promise<void>
): Promise<void> {
  if (items.length === 0) return
  const n = Math.max(1, tamanoLote)
  for (let i = 0; i < items.length; i += n) {
    const lote = items.slice(i, i + n)
    await Promise.all(lote.map(item => fn(item)))
  }
}

/** Lista de préstamos (en producción: /pagos/prestamos vía basename). */
export const RUTA_LISTA_PRESTAMOS = '/prestamos'

export const PER_PAGE_PAGOS_REGISTRADOS = 20

/** Tolerancia USD para comparar totales (redondeos / centavos). */
export const COHERENCIA_USD_TOL = 0.02

export type EstadoValidadorCierreContacto = {
  listo: boolean
  validando: boolean
  mensaje?: string
}

export function mensajeValidacionServidor(
  v: { error?: string; mensaje?: string } | undefined
): string | undefined {
  const e = v?.error
  const m = v?.mensaje
  if (typeof e === 'string' && e.trim()) return e.trim()
  if (typeof m === 'string' && m.trim()) return m.trim()
  return undefined
}

export function fechaPagoPagoRowParaInput(pago: Pago): string {
  const fp = pago.fecha_pago
  if (fp == null || fp === '') {
    return new Date().toISOString().slice(0, 10)
  }
  if (typeof fp === 'string') {
    return fp.length >= 10 ? fp.slice(0, 10) : fp
  }
  try {
    return new Date(fp as Date).toISOString().slice(0, 10)
  } catch {
    return new Date().toISOString().slice(0, 10)
  }
}

/** Para ordenar filas: más reciente primero; sin fecha válida al final. */
export function timestampOrdenFechaPago(
  fp: string | Date | null | undefined
): number {
  if (fp == null || fp === '') return Number.NEGATIVE_INFINITY
  if (typeof fp === 'string') {
    const t = Date.parse(fp)
    if (Number.isFinite(t)) return t
    return Number.NEGATIVE_INFINITY
  }
  const t = fp instanceof Date ? fp.getTime() : Date.parse(String(fp))
  return Number.isFinite(t) ? t : Number.NEGATIVE_INFINITY
}

export function pagoRowAPagoCreateInicial(pago: Pago): PagoInicialRegistrar {
  const monedaBs = pago.moneda_registro === 'BS'
  const montoBs =
    monedaBs && pago.monto_bs_original != null
      ? Number(pago.monto_bs_original)
      : null
  const montoUsd =
    typeof pago.monto_pagado === 'number'
      ? pago.monto_pagado
      : parseFloat(String(pago.monto_pagado || 0)) || 0
  return {
    cedula_cliente: pago.cedula_cliente || '',
    prestamo_id: pago.prestamo_id ?? null,
    fecha_pago: fechaPagoPagoRowParaInput(pago),
    monto_pagado:
      monedaBs && montoBs != null && Number.isFinite(montoBs)
        ? montoBs
        : montoUsd,
    monto_bs_original:
      monedaBs && montoBs != null && Number.isFinite(montoBs) ? montoBs : null,
    numero_documento: pago.numero_documento || '',
    codigo_documento: pago.codigo_documento ?? null,
    institucion_bancaria: pago.institucion_bancaria ?? null,
    notas: pago.notas ?? null,
    moneda_registro: monedaBs ? 'BS' : 'USD',
    link_comprobante: pago.link_comprobante ?? null,
  }
}

export function badgeEstadoPagoRegistrado(estado: string) {
  const estados: Record<string, { color: string; label: string }> = {
    PAGADO: { color: 'bg-green-500', label: 'Pagado' },
    PENDIENTE: { color: 'bg-yellow-500', label: 'Pendiente' },
    ATRASADO: { color: 'bg-red-500', label: 'Atrasado' },
    PARCIAL: { color: 'bg-blue-500', label: 'Parcial' },
    ADELANTADO: { color: 'bg-purple-500', label: 'Adelantado' },
  }
  const config = estados[estado] || { color: 'bg-gray-500', label: estado }
  return <Badge className={`${config.color} text-white`}>{config.label}</Badge>
}

/**
 * Misma familia que exclusión operativa en cascada (anulados, rechazados, duplicado declarado).
 * No se ofrece marcar conciliado en esos registros desde esta pantalla.
 */
export function pagoEstadoExcluyeToggleConciliadoRevision(
  estadoRaw: string | undefined
): boolean {
  const e = (estadoRaw ?? '').trim().toUpperCase()
  const el = (estadoRaw ?? '').trim().toLowerCase()
  if (
    [
      'DUPLICADO',
      'ANULADO_IMPORT',
      'CANCELADO',
      'RECHAZADO',
      'REVERSADO',
    ].includes(e)
  ) {
    return true
  }
  if (e.includes('ANUL') || e.includes('REVERS')) {
    return true
  }
  if (el === 'cancelado' || el === 'rechazado') {
    return true
  }
  return false
}

/** Conciliado o verificado Sí: criterio habitual de elegibilidad en cascada tras guardar en BD. */
export function pagoValidadoCarteraRevisionRow(pago: Pago): boolean {
  if (Boolean(pago.conciliado)) return true
  return (
    String(pago.verificado_concordancia ?? '')
      .trim()
      .toUpperCase() === 'SI'
  )
}

/**
 * Pago cerrado en operación: abonado en cuotas y cartera alineada.
 * Sin `tiene_aplicacion_cuotas` en la API se trata como false (compatibilidad).
 */
export function pagoCarteraRevisionBloquearToggleCerrado(pago: Pago): boolean {
  if (!pago.tiene_aplicacion_cuotas) return false
  if (!Boolean(pago.conciliado)) return false
  if (
    String(pago.verificado_concordancia ?? '')
      .trim()
      .toUpperCase() !== 'SI'
  ) {
    return false
  }
  const est = (pago.estado ?? '').trim().toUpperCase()
  return est === 'PAGADO' || est === 'PAGO_ADELANTADO' || est === 'ADELANTADO'
}

/** Segunda línea del toast tras «Aplicar a cuotas (cascada)» cuando el backend envía diagnostico. */
export function descripcionDiagnosticoCascada(d: {
  pagos_operativos_sin_cuota_pagos?: number
  pagos_elegibles_cascada_sin_cuota_pagos?: number
  pagos_no_elegibles_sin_cuota_pagos?: number
  pagos_con_intento_sin_abono_ids?: number[]
  errores_por_pago?: Array<{ pago_id: number; error: string }>
}): string | undefined {
  const partes: string[] = []
  const op = d.pagos_operativos_sin_cuota_pagos
  const el = d.pagos_elegibles_cascada_sin_cuota_pagos
  const noEl = d.pagos_no_elegibles_sin_cuota_pagos
  if (op != null || el != null || noEl != null) {
    partes.push(
      `Resumen: ${op ?? 0} pago(s) sin cuota_pagos (operativos), ${el ?? 0} elegible(s) cascada, ${noEl ?? 0} no elegible(s).`
    )
  }
  const ids = d.pagos_con_intento_sin_abono_ids
  if (ids != null && ids.length > 0) {
    const muestra = ids.slice(0, 12).join(', ')
    const suf = ids.length > 12 ? '…' : ''
    partes.push(`Intentados sin abono (IDs): ${muestra}${suf}`)
  }
  const errs = d.errores_por_pago
  if (errs != null && errs.length > 0) {
    partes.push(`${errs.length} pago(s) con error al aplicar.`)
  }
  if (partes.length === 0) return undefined
  return partes.join(' ')
}
