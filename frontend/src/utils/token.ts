/**
 * Utilidades para verificar token JWT (expiraciÃ³n, validez).
 * Usado por api.ts y por hooks que no deben hacer requests con sesiÃ³n expirada.
 */
import { safeGetItem, safeGetSessionItem } from './storage'

export function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return true
    const payload = parts[1]
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
    const decoded = JSON.parse(atob(padded))
    if (decoded.exp) {
      const expirationTime = decoded.exp * 1000
      return Date.now() >= (expirationTime - 5000)
    }
    return false
  } catch {
    return true
  }
}

/** True si hay token en storage y no estÃ¡ expirado (evita enviar requests que fallarÃ¡n por sesiÃ³n expirada). */
export function hasValidToken(): boolean {
  try {
    const rememberMe = safeGetItem('remember_me', false)
    const token = rememberMe
      ? safeGetItem('access_token', '')
      : safeGetSessionItem('access_token', '')
    if (!token || typeof token !== 'string') return false
    const t = token.trim().replace(/^Bearer\s+/i, '')
    return t.length > 0 && !isTokenExpired(t)
  } catch {
    return false
  }
}
