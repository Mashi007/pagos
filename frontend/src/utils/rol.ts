import type { User } from '../types'

/**
 * Variantes de rol que deben comportarse como operador (RBAC) en la UI.
 * El backend normaliza a `operator` en login/me; esto cubre caché local o datos viejos.
 */
const OPERATOR_ROLE_ALIASES = new Set([
  'operator',
  'operador',
  'operario',
  'operadora',
])

const CANON_USER_ROLES: readonly User['rol'][] = [
  'admin',
  'manager',
  'operator',
  'viewer',
]

export function canonicalRol(rol: string | null | undefined): string {
  const r = (rol || '').trim().toLowerCase()
  if (!r) return 'viewer'
  if (OPERATOR_ROLE_ALIASES.has(r)) return 'operator'
  if (
    r === 'administrador' ||
    r === 'finiquitador' ||
    r === 'administrator' ||
    r === 'root' ||
    r === 'superadmin'
  ) {
    return 'admin'
  }
  if (r === 'admin') return 'admin'
  if (r === 'gerente' || r === 'supervisor') return 'manager'
  if (r === 'operativo') return 'viewer'
  return r
}

/** Alinea `user.rol` al RBAC canónico tras login/me (sesiones o BD con variantes). */
export function normalizeAuthUser(user: User | null | undefined): User | null {
  if (!user) return null
  const r = canonicalRol(user.rol as unknown as string)
  const rol = (CANON_USER_ROLES as readonly string[]).includes(r)
    ? (r as User['rol'])
    : 'viewer'
  return { ...user, rol }
}

export function isOperatorRole(rol: string | null | undefined): boolean {
  return canonicalRol(rol) === 'operator'
}

/** Igual que el backend `canonical_rol` + comprobación admin (incluye administrador/finiquitador legados). */
export function isAdminRole(rol: string | null | undefined): boolean {
  return canonicalRol(rol) === 'admin'
}

export function isManagerRole(rol: string | null | undefined): boolean {
  return canonicalRol(rol) === 'manager'
}
