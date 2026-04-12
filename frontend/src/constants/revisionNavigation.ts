/**
 * Tras editar revisión manual: volver al listado principal de notificaciones
 * (p. ej. https://rapicredit.onrender.com/pagos/notificaciones con basename /pagos).
 */
export const RUTA_RETORNO_NOTIFICACIONES = '/notificaciones'

const SESSION_REVISION_RETURN_TO = 'rapicredit-revision-return-to'

/** Rutas SPA permitidas para volver desde revisión manual si vienen en `location.state.returnTo`. */
export function esReturnToRevisionDesdeNotificaciones(p: string): boolean {
  return (
    p === RUTA_RETORNO_NOTIFICACIONES ||
    p.startsWith(`${RUTA_RETORNO_NOTIFICACIONES}/`) ||
    p.startsWith(`${RUTA_RETORNO_NOTIFICACIONES}?`)
  )
}

/** Ruta SPA interna; evita open redirect. */
export function normalizarReturnToRevisionPath(raw: unknown): string | null {
  if (typeof raw !== 'string') return null
  const t = raw.trim()
  if (!t.startsWith('/') || t.startsWith('//') || t.includes('\\')) return null
  if (t.length > 512) return null
  return t
}

/** Llamar al montar cualquier ruta de notificaciones (a1 día, a-3 cuotas, 2 días antes, etc.). */
export function marcarReturnRevisionDesdeNotificaciones(): void {
  try {
    sessionStorage.setItem(SESSION_REVISION_RETURN_TO, RUTA_RETORNO_NOTIFICACIONES)
  } catch {
    /* ignore */
  }
}

export function limpiarReturnRevisionSesion(): void {
  try {
    sessionStorage.removeItem(SESSION_REVISION_RETURN_TO)
  } catch {
    /* ignore */
  }
}

/**
 * Solo devuelve la ruta de notificaciones si estaba marcada; la consume para no dejar basura.
 */
export function leerYConsumirReturnRevisionSesion(): string | null {
  try {
    const raw = sessionStorage.getItem(SESSION_REVISION_RETURN_TO)
    sessionStorage.removeItem(SESSION_REVISION_RETURN_TO)
    if (normalizarReturnToRevisionPath(raw) !== RUTA_RETORNO_NOTIFICACIONES) {
      return null
    }
    return RUTA_RETORNO_NOTIFICACIONES
  } catch {
    return null
  }
}
