/**
 * Rutas delegadas por rol (lista blanca). Fuera de estas, el usuario autenticado
 * es redirigido a su inicio por rol. Admin no se evalúa aquí (acceso total).
 */
import type { UserRol } from '../types'
import { canonicalRol, isAdminRole } from '../utils/rol'

/** Prefijos de ruta (sin basename). Coincidencia: igualdad o pathname.startsWith(prefix + '/') */
const MANAGER_PREFIXES = [
  '/dashboard',
  '/clientes',
  '/prestamos',
  '/pagos',
  '/infopagos',
  '/amortizacion',
  '/cobros',
  '/reportes',
  '/revision-manual',
  '/auditoria',
  '/comunicaciones',
  '/notificaciones',
  '/actualizaciones',
  '/conversaciones-whatsapp',
  '/crm',
  '/chat-ai',
  '/finiquitos',
]

const OPERATOR_PREFIXES = [
  '/prestamos',
  '/revision-manual',
  '/infopagos',
  /** Solo esta ruta de Pagos (cédulas Bs), no el listado general /pagos */
  '/pagos/pago-bs',
  '/finiquitos',
]

/** Visualizador: solo consulta general y reportes (ajustar aquí si se delegan más módulos) */
const VIEWER_PREFIXES = ['/dashboard', '/reportes']

function matchesDelegatedPath(pathname: string, prefixes: string[]): boolean {
  const p =
    pathname.length > 1 && pathname.endsWith('/')
      ? pathname.slice(0, -1)
      : pathname
  return prefixes.some(
    prefix =>
      p === prefix ||
      p.startsWith(prefix + '/') ||
      (prefix !== '/' && p.startsWith(prefix))
  )
}

/**
 * True si la ruta actual está permitida para el rol (admin siempre true aquí arriba).
 */
export function isDelegatedPathForRol(
  rol: string | null | undefined,
  pathname: string
): boolean {
  const r = canonicalRol(rol) as UserRol
  if (r === 'admin') return true
  if (r === 'manager') {
    return matchesDelegatedPath(pathname, MANAGER_PREFIXES)
  }
  if (r === 'operator') return matchesDelegatedPath(pathname, OPERATOR_PREFIXES)
  if (r === 'viewer') return matchesDelegatedPath(pathname, VIEWER_PREFIXES)
  return false
}

/** Redirección cuando intentan una ruta no delegada */
export function defaultHomePathForRol(rol: string | null | undefined): string {
  const r = canonicalRol(rol)
  if (r === 'operator') return '/prestamos'
  return '/dashboard/menu'
}

/** Para filtrar ítems del menú: href permitido para el rol actual */
export function isHrefDelegatedForRol(
  rol: string | null | undefined,
  href: string
): boolean {
  if (!href) return false
  if (isAdminRole(rol)) return true
  const pathOnly = href.split('?')[0] || href
  return isDelegatedPathForRol(rol, pathOnly)
}
