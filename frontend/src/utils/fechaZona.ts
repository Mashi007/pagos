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
