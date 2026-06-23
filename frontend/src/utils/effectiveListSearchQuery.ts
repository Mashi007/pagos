/**
 * Evita GET ?search=1 / search=19 mientras el usuario arma cédula, email o nombre.
 * Vacío = sin filtro de búsqueda en API.
 */
export function effectiveListSearchQuery(
  raw: string | undefined | null
): string {
  const t = (raw ?? '').trim()
  if (!t) {
    return ''
  }
  if (/^v/i.test(t)) {
    return t
  }
  if (t.includes('@')) {
    return t
  }
  if (/^\d+$/.test(t)) {
    return t.length >= 6 ? t : ''
  }
  return t.length >= 3 ? t : ''
}
