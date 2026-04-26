/**
 * Misma idea que `_telefono_normalizado_drive_col_f` en servidor (columna F CONCILIACIÓN).
 * Solo dígitos, sin prefijo 58, sin ceros iniciales de más hasta quedar ≤10 dígitos base.
 */
export function normalizarTelefonoColumnaDrive(
  raw: string | null | undefined
): string {
  if (raw == null) return ''
  const digits = String(raw).replace(/\D/g, '')
  if (!digits) return ''
  let d = digits
  if (d.length >= 12 && d.startsWith('58')) {
    d = d.slice(2)
  }
  while (d.length > 10 && d.startsWith('0')) {
    d = d.slice(1)
  }
  return d
}

/**
 * Alineado con `validate_phone` del backend (11 dígitos 04xxxxxxxx / 02xxxxxxxx).
 * Vacío se considera válido aquí (la hoja puede dejar F vacío; el servidor decide importación).
 */
export function telefonoColumnaFDriveValidoTrasNormalizar(
  normalized: string
): boolean {
  if (!normalized) return true
  if (normalized.length !== 10) return false
  if (normalized[0] !== '2' && normalized[0] !== '4') return false
  return /^0[24]\d{9}$/.test(`0${normalized}`)
}
