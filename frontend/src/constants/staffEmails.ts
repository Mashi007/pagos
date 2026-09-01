/** Administrador IT: acceso exclusivo a módulos sensibles (p. ej. importación extracto). */
export const IT_MASTER_EMAIL = 'itmaster@rapicreditca.com'

export function isItMasterEmail(email: string | null | undefined): boolean {
  return (email || '').trim().toLowerCase() === IT_MASTER_EMAIL
}
