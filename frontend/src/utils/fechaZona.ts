/**
 * Fecha calendario (YYYY-MM-DD) en una zona IANA, para alinear reglas con el backend (America/Caracas).
 */
export const TZ_CARACAS = 'America/Caracas'

export function fechaYmdEnZonaHoraria(fecha: Date, timeZone: string): string {
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const parts = fmt.formatToParts(fecha)
  const y = parts.find(p => p.type === 'year')?.value ?? '1970'
  const m = parts.find(p => p.type === 'month')?.value ?? '01'
  const d = parts.find(p => p.type === 'day')?.value ?? '01'
  return `${y}-${m}-${d}`
}

/** Hoy en America/Caracas como YYYY-MM-DD (comparable con input type="date"). */
export function hoyYmdCaracas(): string {
  return fechaYmdEnZonaHoraria(new Date(), TZ_CARACAS)
}

/**
 * Valor para `<input type="date">`: mismo día civil que el backend / API.
 * - `YYYY-MM-DD` sin hora: no pasa por `Date` (evita desplazar el día por UTC).
 * - ISO con hora / `Date`: día calendario en America/Caracas.
 */
export function fechaPagoParaInputDate(v: unknown): string {
  if (v == null || v === '') return ''
  if (typeof v === 'string') {
    const t = v.trim()
    if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t
    const d = new Date(t)
    if (Number.isNaN(d.getTime())) {
      const m = t.match(/^(\d{4}-\d{2}-\d{2})/)
      return m ? m[1] : ''
    }
    return fechaYmdEnZonaHoraria(d, TZ_CARACAS)
  }
  if (v instanceof Date) {
    if (Number.isNaN(v.getTime())) return ''
    return fechaYmdEnZonaHoraria(v, TZ_CARACAS)
  }
  return ''
}
