import { lazy, type ComponentType, type LazyExoticComponent } from 'react'

const CHUNK_RELOAD_KEY = 'rapicredit_missing_chunk_reload_v1'
const LAZY_RETRY_PREFIX = 'rapicredit_lazy_retry_'

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => {
    setTimeout(resolve, ms)
  })
}

function clearChunkRecoveryKeys(chunkId: string) {
  try {
    sessionStorage.removeItem(CHUNK_RELOAD_KEY)
    sessionStorage.removeItem(`${LAZY_RETRY_PREFIX}${chunkId}`)
  } catch {
    /* private mode */
  }
}

function stripNocacheFromUrl() {
  try {
    const u = new URL(window.location.href)
    if (!u.searchParams.has('nocache')) return
    u.searchParams.delete('nocache')
    const next = `${u.pathname}${u.search}${u.hash}`
    window.history.replaceState(window.history.state, '', next)
  } catch {
    /* ignore */
  }
}

/** Limpia contadores de recuperación de chunks tras un arranque exitoso de la SPA. */
export function clearChunkRecoveryAfterAppReady() {
  try {
    for (let i = sessionStorage.length - 1; i >= 0; i -= 1) {
      const k = sessionStorage.key(i)
      if (k && k.startsWith(LAZY_RETRY_PREFIX)) {
        sessionStorage.removeItem(k)
      }
    }
    sessionStorage.removeItem(CHUNK_RELOAD_KEY)
  } catch {
    /* ignore */
  }
  stripNocacheFromUrl()
}

function isChunkLoadError(err: unknown): boolean {
  const msg = (
    err instanceof Error
      ? err.message
      : typeof err === 'string'
        ? err
        : ''
  ).toLowerCase()
  return (
    msg.includes('dynamically imported module') ||
    msg.includes('failed to fetch dynamically imported module') ||
    msg.includes('error loading dynamically imported module') ||
    msg.includes('failed to load module') ||
    msg.includes('missing js chunk') ||
    (msg.includes('text/html') && msg.includes('module'))
  )
}

/**
 * lazy() con reintentos y recarga con cache-busting si el chunk falló tras deploy.
 */
export function lazyWithRetry<T extends ComponentType<unknown>>(
  importer: () => Promise<{ default: T }>,
  chunkId: string
): LazyExoticComponent<T> {
  return lazy(async () => {
    const retryKey = `${LAZY_RETRY_PREFIX}${chunkId}`
    let attempts = 0
    const maxAttempts = 3

    while (attempts < maxAttempts) {
      try {
        const mod = await importer()
        clearChunkRecoveryKeys(chunkId)
        stripNocacheFromUrl()
        return mod
      } catch (err) {
        attempts += 1
        if (!isChunkLoadError(err) || attempts >= maxAttempts) {
          throw err
        }
        try {
          const prev = Number(sessionStorage.getItem(retryKey) || '0')
          sessionStorage.setItem(retryKey, String(prev + 1))
        } catch {
          /* ignore */
        }
        if (attempts >= maxAttempts - 1) {
          const u = new URL(window.location.href)
          u.searchParams.set('nocache', String(Date.now()))
          window.location.replace(`${u.pathname}${u.search}${u.hash}`)
          await sleep(60_000)
        }
        await sleep(400 * attempts)
      }
    }

    throw new Error(`No se pudo cargar el módulo ${chunkId}`)
  })
}
