/**
 * Caché de módulo del dashboard (misma idea que cobros listado+KPIs):
 * al volver a /dashboard/menu pinta al instante sin spinner si hay entry viva.
 */
export const DASHBOARD_MENU_CACHE_TTL_MS = 10 * 60 * 1000
/** Stale-while-revalidate en cliente (sigue pintando mientras refresca). */
export const DASHBOARD_MENU_CACHE_STALE_MS = 2 * 60 * 60 * 1000

type Entry = { storedAt: number; payload: unknown }

const store = new Map<string, Entry>()

function clonePayload<T>(data: T): T {
  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(data)
    } catch {
      /* JSON fallback */
    }
  }
  return JSON.parse(JSON.stringify(data)) as T
}

export function dashboardMenuCacheKey(parts: unknown[]): string {
  return JSON.stringify(parts)
}

export function putDashboardMenuCache(key: string, payload: unknown): void {
  try {
    store.set(key, { storedAt: Date.now(), payload: clonePayload(payload) })
  } catch {
    /* ignore */
  }
}

export function peekDashboardMenuCache<T>(key: string): T | null {
  try {
    const hit = store.get(key)
    if (!hit) return null
    if (Date.now() - hit.storedAt >= DASHBOARD_MENU_CACHE_TTL_MS) return null
    return clonePayload(hit.payload) as T
  } catch {
    return null
  }
}

export function peekDashboardMenuCacheStale<T>(key: string): T | null {
  try {
    const hit = store.get(key)
    if (!hit) return null
    if (Date.now() - hit.storedAt >= DASHBOARD_MENU_CACHE_STALE_MS) return null
    return clonePayload(hit.payload) as T
  } catch {
    return null
  }
}

export function peekDashboardMenuCacheMeta(
  key: string
): { storedAt: number } | null {
  const hit = store.get(key)
  if (!hit) return null
  if (Date.now() - hit.storedAt >= DASHBOARD_MENU_CACHE_STALE_MS) return null
  return { storedAt: hit.storedAt }
}

/** Hay alguna entry fresca (TTL) — sirve para saltar el stagger al remount. */
export function hasWarmDashboardMenuCache(): boolean {
  const now = Date.now()
  for (const hit of store.values()) {
    if (now - hit.storedAt < DASHBOARD_MENU_CACHE_TTL_MS) return true
  }
  return false
}

export function invalidateDashboardMenuCache(): void {
  store.clear()
}
