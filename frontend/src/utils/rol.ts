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

export function canonicalRol(rol: string | null | undefined): string {
  const r = (rol || '').trim().toLowerCase()
  if (!r) return 'viewer'
  if (OPERATOR_ROLE_ALIASES.has(r)) return 'operator'
  if (r === 'administrador' || r === 'finiquitador') return 'admin'
  if (r === 'gerente' || r === 'supervisor') return 'manager'
  if (r === 'operativo') return 'viewer'
  return r
}

export function isOperatorRole(rol: string | null | undefined): boolean {
  return canonicalRol(rol) === 'operator'
}
