import {
  FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT,
  type FiniquitoTerminadoItem,
  type FiniquitoTerminadosDia,
} from '../services/finiquitoService'
import {
  safeGetSessionItem,
  safeRemoveSessionItem,
  safeSetSessionItem,
} from './storage'

/** Evita rafagas al reabrir la seccion; el polling activo usa force y refresca ~cada 1 min. */
export const FINIQUITO_TERMINADOS_CACHE_TTL_MS = 5 * 60 * 1000

const SESSION_INDEX_KEY = 'finiquito_terminados_cache_index'
const SESSION_KEY_PREFIX = 'finiquito_terminados_cache:'

export type FiniquitoTerminadosCacheEntry = {
  fetchedAt: number
  cedula: string
  dias: number
  items: FiniquitoTerminadoItem[]
  totalTerminados: number
  resumenDias: FiniquitoTerminadosDia[]
  totalEnVentana: number
  totalTerminadosResumen: number
}

const memory = new Map<string, FiniquitoTerminadosCacheEntry>()

function cacheKey(cedula: string, dias: number): string {
  return `${cedula.trim().toLowerCase()}|${dias}`
}

function sessionStorageKey(key: string): string {
  return `${SESSION_KEY_PREFIX}${key}`
}

function readSessionIndex(): string[] {
  const raw = safeGetSessionItem(SESSION_INDEX_KEY, [])
  return Array.isArray(raw) ? (raw as string[]) : []
}

function writeSessionIndex(keys: string[]): void {
  safeSetSessionItem(SESSION_INDEX_KEY, keys)
}

function readSessionEntry(key: string): FiniquitoTerminadosCacheEntry | null {
  const raw = safeGetSessionItem(sessionStorageKey(key), null)
  if (!raw || typeof raw !== 'object' || typeof raw.fetchedAt !== 'number') {
    return null
  }
  return raw as FiniquitoTerminadosCacheEntry
}

function writeSessionEntry(
  key: string,
  entry: FiniquitoTerminadosCacheEntry
): void {
  safeSetSessionItem(sessionStorageKey(key), entry)
  const index = readSessionIndex()
  if (!index.includes(key)) {
    writeSessionIndex([...index, key])
  }
}

function evict(key: string): void {
  memory.delete(key)
  safeRemoveSessionItem(sessionStorageKey(key))
  writeSessionIndex(readSessionIndex().filter(k => k !== key))
}

function isFresh(entry: FiniquitoTerminadosCacheEntry): boolean {
  return Date.now() - entry.fetchedAt < FINIQUITO_TERMINADOS_CACHE_TTL_MS
}

export function readFiniquitoTerminadosCache(
  cedula: string,
  dias = FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT
): FiniquitoTerminadosCacheEntry | null {
  const key = cacheKey(cedula, dias)
  const entry = memory.get(key) ?? readSessionEntry(key)
  if (!entry || !isFresh(entry)) {
    if (entry) evict(key)
    return null
  }
  memory.set(key, entry)
  return entry
}

export function writeFiniquitoTerminadosCache(
  entry: FiniquitoTerminadosCacheEntry
): void {
  const key = cacheKey(entry.cedula, entry.dias)
  memory.set(key, entry)
  writeSessionEntry(key, entry)
}

export function invalidateFiniquitoTerminadosCache(
  cedula?: string,
  dias = FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT
): void {
  if (cedula === undefined) {
    for (const key of [...memory.keys()]) {
      evict(key)
    }
    for (const key of readSessionIndex()) {
      evict(key)
    }
    memory.clear()
    writeSessionIndex([])
    return
  }
  evict(cacheKey(cedula, dias))
}

export function minutosDesdeCache(fetchedAt: number): number {
  return Math.max(0, Math.floor((Date.now() - fetchedAt) / 60_000))
}
