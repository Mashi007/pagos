import axios from 'axios'

/** True si el error proviene de AbortController.abort() (axios / fetch). */
export function isRequestCanceled(e: unknown): boolean {
  if (axios.isCancel(e)) return true
  const err = e as { code?: string; name?: string }
  return err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError'
}
