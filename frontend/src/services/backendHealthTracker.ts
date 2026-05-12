/**
 * Backend Health Tracker
 *
 * Registra señales de inestabilidad del backend (502/503 recientes en endpoints catalogados
 * como "cold-start safe") y expone dos ayudas para el resto del cliente:
 *
 *  1. UX: muestra/oculta un toast "Reconectando con el servidor…" cuando se acumulan
 *     reintentos sobre el MISMO endpoint, para que el usuario sepa que la app no está
 *     congelada y que el cliente está reintentando solo.
 *
 *  2. Defensa suave (soft circuit breaker): si hubo un 502/503 reciente, antes de enviar
 *     un write crítico (PATCH .../estado) añadimos un pequeño retraso para dar margen al
 *     backend a estabilizarse. NUNCA bloquea la operación: como mucho retrasa unos segundos.
 *
 * Diseño:
 * - Estado en memoria, scope ventana del navegador. No persiste entre recargas (es
 *   diagnóstico transitorio, no business state).
 * - El toast se reemplaza por ID fijo: no hay storm aunque varios requests fallen.
 * - Si la app no tiene `react-hot-toast` montado (server-side render, SSR), las llamadas
 *   son no-op gracias al try/catch.
 */
import toast from 'react-hot-toast'

/** ID estable del toast persistente para que se reemplace en lugar de apilarse. */
const RECONNECTING_TOAST_ID = 'backend-reconnecting'

/** Ventana para considerar un 502/503 "reciente". */
const RECENT_ERROR_WINDOW_MS = 15_000

/** Demora máxima que añadimos a un write crítico para dejar respirar al backend. */
const MAX_DEFER_MS = 3_000

/**
 * Último timestamp en el que recibimos un 502/503 sobre un endpoint catalogado.
 * 0 = nunca / hace mucho.
 */
let lastBackendErrorAt = 0

/**
 * Endpoints que cuentan como "señal" para los toast/circuit breaker. Mantener acotado:
 * 502/503 en endpoints fuera de esta lista no actualizan el estado (evita ruido por
 * endpoints públicos lentos, OTPs SMTP, etc.).
 */
function isHealthSignalUrl(url: string): boolean {
  return (
    url.includes('/cobros/pagos-reportados/listado-y-kpis') ||
    /\/cobros\/pagos-reportados\/\d+(?:\?|#|$)/.test(url) ||
    /\/cobros\/pagos-reportados\/\d+\/(?:comprobante|recibo\.pdf|estado)(?:\?|#|$)/.test(
      url
    ) ||
    url.includes('/api/v1/clientes') ||
    url.includes('/dashboard') ||
    url.includes('/prestamos/candidatos-drive/snapshot')
  )
}

/**
 * Marca que recibimos un 502/503 sobre un endpoint catalogado.
 * Llamar desde el response interceptor de axios ANTES de reintentar.
 */
export function markBackendError(
  status: number,
  url: string | undefined
): void {
  if (status !== 502 && status !== 503) return
  const u = String(url || '')
  if (!isHealthSignalUrl(u)) return
  lastBackendErrorAt = Date.now()
}

/**
 * Marca que un request acaba de tener éxito sobre un endpoint catalogado.
 * Si venía de >=1 reintento, cerramos el toast persistente y mostramos un mensaje
 * breve de recuperación.
 */
export function markBackendSuccessAfterRetries(
  retryCount: number,
  url: string | undefined
): void {
  const u = String(url || '')
  if (!isHealthSignalUrl(u)) return
  if (retryCount > 0) {
    // Hubo al menos 1 reintento; reseteamos ventana de error y damos feedback.
    lastBackendErrorAt = 0
    dismissReconnectingToast()
    try {
      // success silencioso (2s); evita ruido si la recuperación fue rápida.
      if (retryCount >= 2) {
        toast.success('Conexión con el servidor restablecida.', {
          id: `${RECONNECTING_TOAST_ID}-recovered`,
          duration: 2500,
        })
      }
    } catch {
      /* SSR / sin DOM: ignorar */
    }
  }
}

/**
 * Muestra (o actualiza) el toast persistente "Reconectando con el servidor…".
 * Llamar cuando un request lleva `retryCount >= 1` (es decir, ya falló al menos
 * una vez y va por el 2º intento).
 *
 * El toast se mantiene visible hasta que se cierre por `dismissReconnectingToast`
 * (éxito) o `dismissReconnectingTostByExhaustion` (agote reintentos sin éxito).
 */
export function showReconnectingToast(
  retryCount: number,
  maxRetries: number
): void {
  try {
    const nIntento = retryCount + 1
    const total = Math.max(maxRetries, 1)
    toast.loading(
      `Reconectando con el servidor… (intento ${nIntento} de ${total})`,
      {
        id: RECONNECTING_TOAST_ID,
      }
    )
  } catch {
    /* SSR / sin DOM: ignorar */
  }
}

/**
 * Cierra el toast persistente (lo invoca el response interceptor cuando un retry
 * triunfa, y también `markBackendSuccessAfterRetries`).
 */
export function dismissReconnectingToast(): void {
  try {
    toast.dismiss(RECONNECTING_TOAST_ID)
  } catch {
    /* SSR / sin DOM: ignorar */
  }
}

/**
 * Cierra el toast persistente sustituyéndolo por un error final (cuando se agotan
 * los reintentos sin recuperar el backend).
 */
export function dismissReconnectingToastByExhaustion(): void {
  try {
    toast.error(
      'No fue posible reconectar con el servidor. Intente la operación de nuevo en unos segundos.',
      { id: RECONNECTING_TOAST_ID, duration: 6000 }
    )
  } catch {
    /* SSR / sin DOM: ignorar */
  }
}

/**
 * Devuelve cuántos ms conviene esperar antes de enviar un write crítico (PATCH ...
 * /estado). El delay es proporcional a la "frescura" del último error: si fue muy
 * reciente, esperamos más; si fue hace rato, casi nada. Tope: MAX_DEFER_MS.
 *
 * Esto NO bloquea la operación: el cliente igual envía el PATCH. Solo añade margen
 * para reducir la probabilidad de chocar con el backend en mitad de un restart.
 */
export function suggestedDeferMsForCriticalWrite(): number {
  if (!lastBackendErrorAt) return 0
  const elapsed = Date.now() - lastBackendErrorAt
  if (elapsed >= RECENT_ERROR_WINDOW_MS) return 0
  const remaining = RECENT_ERROR_WINDOW_MS - elapsed
  // Curva lineal: 100% del MAX_DEFER al instante del error → 0 en RECENT_ERROR_WINDOW_MS.
  const ratio = remaining / RECENT_ERROR_WINDOW_MS
  return Math.min(MAX_DEFER_MS, Math.floor(MAX_DEFER_MS * ratio))
}

/**
 * Helper: detecta si una URL de request corresponde a un write crítico que debería
 * pasar por el soft circuit breaker.
 */
export function isCriticalCobrosWrite(
  method: string | undefined,
  url: string | undefined
): boolean {
  const m = String(method || '').toLowerCase()
  if (m !== 'patch' && m !== 'post' && m !== 'put' && m !== 'delete')
    return false
  const u = String(url || '')
  return (
    /\/cobros\/pagos-reportados\/\d+\/estado(?:\?|#|$)/.test(u) ||
    /\/cobros\/pagos-reportados\/\d+(?:\?|#|$)/.test(u)
  )
}
