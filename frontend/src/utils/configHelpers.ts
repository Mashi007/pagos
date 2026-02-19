/**
 * Centralized password/sensitive field masking utilities
 * Used across configuration components (Email, WhatsApp, etc.)
 */

/**
 * Returns masked value ("***") if isMasked is true, otherwise returns the original value
 * @param value - The sensitive field value (password, API key, etc.)
 * @param isMasked - Whether the field should be masked
 * @returns Masked value or original value
 */
export function maskSensitiveField(value: string | undefined | null, isMasked: boolean): string {
  if (!value) return ''
  return isMasked ? '***' : value
}

/**
 * Checks if a value is already masked (represents "***")
 * @param value - The value to check
 * @returns true if the value is masked ("***"), false otherwise
 */
export function isMaskedValue(value: string | undefined | null): boolean {
  return value === '***'
}

/**
 * Determines if a field should be saved to the backend
 * Returns false if the value is masked (***) or empty (means user didn't change it)
 * Returns true if the value is actual data that should be persisted
 * @param value - The field value
 * @returns true if the field should be saved, false otherwise
 */
export function shouldSaveField(value: string | undefined | null): boolean {
  if (!value || value.trim() === '') return false
  if (isMaskedValue(value)) return false
  return true
}

/**
 * Returns placeholder text for masked password fields
 * @param isMasked - Whether the field is currently masked
 * @returns Placeholder text
 */
export function getPasswordPlaceholder(isMasked: boolean): string {
  return isMasked
    ? '•••••••• (ya configurada — deja en blanco para no cambiar)'
    : 'Pega tu contraseña o API key aquí'
}

/**
 * Prepares sensitive field value for API submission
 * If masked or empty, returns "***" to indicate "don't change"
 * Otherwise returns the trimmed value
 * @param value - The field value
 * @param previousValue - The previous/stored value (for context)
 * @returns Value to send to backend
 */
export function prepareSensitiveFieldForApi(
  value: string | undefined | null,
  previousValue?: string | null
): string {
  // If value is masked or empty, return *** to indicate don't change
  if (isMaskedValue(value) || !value?.trim()) {
    return '***'
  }
  // Return the actual value
  return value.trim()
}
