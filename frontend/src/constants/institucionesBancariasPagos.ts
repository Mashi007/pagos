/**
 * Instituciones para registrar/editar pago (`institucion_bancaria`).
 * Lista corta fija en UI; si en BD hay un valor distinto, se antepone a la lista.
 */
export const INSTITUCIONES_BANCARIAS_PAGO: readonly string[] = [
  'Mercantil',
  'BNC',
  'BNV',
  'Binance',
  'Recibo',
]

const SIN_ESPECIFICAR_VALUE = '__sin_especificar__'

export { SIN_ESPECIFICAR_VALUE }

/** Mismo orden que el catálogo (no orden alfabético). */
export function listaInstitucionesBancariasOrdenada(): string[] {
  return [...INSTITUCIONES_BANCARIAS_PAGO]
}

/** Incluye el valor actual si no está en el catálogo (datos legacy). */
export function opcionesBancoConValorActual(
  actual: string | null | undefined
): string[] {
  const base = listaInstitucionesBancariasOrdenada()
  const t = (actual || '').trim()
  if (!t) return base
  if (base.includes(t)) return base
  return [t, ...base]
}

/** Regla básica: sin banco emisor válido no se puede guardar. */
const PLACEHOLDERS_INSTITUCION = new Set([
  '',
  'otros',
  'otro',
  'n/a',
  'na',
  'pendiente',
  'sin especificar',
  'excel',
  'deposito',
  'depósito',
])

function compactInstitucion(s: string): string {
  return s.toLowerCase().replace(/[\s\-_,.]+/g, '')
}

const RAPICREDIT_COMPACT = new Set([
  'rapicredit',
  'rapicreditca',
  'rapcredit',
  'rapicredi',
  'bapicredit',
  'raphcredit',
  'softcredit',
])

export function esInstitucionBancariaValidaParaGuardar(
  valor: string | null | undefined
): boolean {
  const t = (valor || '').trim()
  if (!t) return false
  if (PLACEHOLDERS_INSTITUCION.has(t.toLowerCase())) return false
  const c = compactInstitucion(t)
  if (RAPICREDIT_COMPACT.has(c)) return false
  if (/^(?:bapi|raph|rapi)[\s\-_.]*credi(?:t)?/i.test(t)) return false
  return true
}

export function mensajeSiFaltaInstitucion(
  valor: string | null | undefined
): string | null {
  if (esInstitucionBancariaValidaParaGuardar(valor)) return null
  const t = (valor || '').trim()
  const c = compactInstitucion(t)
  if (t && (RAPICREDIT_COMPACT.has(c) || /rapi[\s\-_.]*credi/i.test(t))) {
    return 'RapiCredit es el beneficiario, no el banco. Indique la institución emisora.'
  }
  return 'La institución bancaria es obligatoria. Indique el banco emisor del comprobante.'
}
