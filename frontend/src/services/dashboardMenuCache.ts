/**
 * Caché del dashboard (/dashboard/menu): memoria + sessionStorage (sobrevive F5 en la pestaña).
 * TTL 10 min alineado con backend `menu_grafico_cached` y worker de refresco.
 */
export const DASHBOARD_MENU_CACHE_TTL_MS = 10 * 60 * 1000
/** Stale-while-revalidate en cliente (sigue pintando mientras refresca). */
export const DASHBOARD_MENU_CACHE_STALE_MS = 2 * 60 * 60 * 1000

/** Opciones React Query compartidas por todos los gráficos del menú. */
export const DASHBOARD_MENU_QUERY_OPTIONS = {
  staleTime: DASHBOARD_MENU_CACHE_TTL_MS,
  gcTime: DASHBOARD_MENU_CACHE_TTL_MS * 3,
  refetchOnMount: false,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
  retry: 1,
} as const

type Entry = { storedAt: number; payload: unknown }

const store = new Map<string, Entry>()
const SESSION_PREFIX = 'rapicredit-dashboard-menu-v1:'
/** Evita quota de sessionStorage (p. ej. universo/analisis muy grande). */
const SESSION_MAX_BYTES = 800_000

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

function readEntry(key: string): Entry | null {
  const mem = store.get(key)
  if (mem) return mem
  if (typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(SESSION_PREFIX + key)
    if (!raw) return null
    const entry = JSON.parse(raw) as Entry
    store.set(key, entry)
    return entry
  } catch {
    return null
  }
}

function writeEntry(key: string, entry: Entry): void {
  store.set(key, entry)
  if (typeof sessionStorage === 'undefined') return
  try {
    const raw = JSON.stringify(entry)
    if (raw.length > SESSION_MAX_BYTES) return
    sessionStorage.setItem(SESSION_PREFIX + key, raw)
  } catch {
    /* quota — memoria sigue válida en la sesión SPA */
  }
}

function clearSessionEntries(): void {
  if (typeof sessionStorage === 'undefined') return
  try {
    const keys: string[] = []
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i)
      if (k?.startsWith(SESSION_PREFIX)) keys.push(k)
    }
    keys.forEach(k => sessionStorage.removeItem(k))
  } catch {
    /* ignore */
  }
}

export function dashboardMenuCacheKey(parts: unknown[]): string {
  return JSON.stringify(parts)
}

export function putDashboardMenuCache(key: string, payload: unknown): void {
  try {
    writeEntry(key, { storedAt: Date.now(), payload: clonePayload(payload) })
  } catch {
    /* ignore */
  }
}

export function peekDashboardMenuCache<T>(key: string): T | null {
  try {
    const hit = readEntry(key)
    if (!hit) return null
    if (Date.now() - hit.storedAt >= DASHBOARD_MENU_CACHE_TTL_MS) return null
    return clonePayload(hit.payload) as T
  } catch {
    return null
  }
}

export function peekDashboardMenuCacheStale<T>(key: string): T | null {
  try {
    const hit = readEntry(key)
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
  const hit = readEntry(key)
  if (!hit) return null
  if (Date.now() - hit.storedAt >= DASHBOARD_MENU_CACHE_STALE_MS) return null
  return { storedAt: hit.storedAt }
}

/** Hay alguna entry fresca (TTL) — salta stagger al remount o tras F5 con sessionStorage. */
export function hasWarmDashboardMenuCache(): boolean {
  const now = Date.now()
  for (const hit of store.values()) {
    if (now - hit.storedAt < DASHBOARD_MENU_CACHE_TTL_MS) return true
  }
  if (typeof sessionStorage === 'undefined') return false
  try {
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i)
      if (!k?.startsWith(SESSION_PREFIX)) continue
      const raw = sessionStorage.getItem(k)
      if (!raw) continue
      const entry = JSON.parse(raw) as Entry
      if (now - entry.storedAt < DASHBOARD_MENU_CACHE_TTL_MS) return true
    }
  } catch {
    /* ignore */
  }
  return false
}

export function invalidateDashboardMenuCache(): void {
  store.clear()
  clearSessionEntries()
}
