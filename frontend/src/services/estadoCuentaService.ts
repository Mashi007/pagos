/**
 * Servicio público de consulta de estado de cuenta por cédula.
 * Sin autenticación. Solo validar cédula y solicitar PDF (envío al email del cliente).
 */
import { env } from '../config/env'

const API = env.API_URL || ''
const BASE = `${API}/api/v1/estado-cuenta/public`

export interface ValidarCedulaEstadoCuentaResponse {
  ok: boolean
  nombre?: string
  email?: string
  error?: string
}

export interface SolicitarEstadoCuentaResponse {
  ok: boolean
  pdf_base64?: string
  mensaje?: string
  error?: string
}

export interface SolicitarCodigoResponse {
  ok: boolean
  mensaje?: string
  error?: string
  /** ISO 8601 (ej. "2025-03-11T16:30:00Z") para mostrar "Código válido hasta las HH:MM" */
  expira_en?: string
}

export interface VerificarCodigoResponse {
  ok: boolean
  pdf_base64?: string
  error?: string
  /** ISO 8601 del código verificado (informativo) */
  expira_en?: string
}

/** Público: validar cédula (formato + existe en clientes). Sin auth. */
export async function validarCedulaEstadoCuenta(cedula: string): Promise<ValidarCedulaEstadoCuentaResponse> {
  const url = `${BASE}/validar-cedula?cedula=${encodeURIComponent(cedula.slice(0, 20))}`
  const res = await fetch(url, { credentials: 'same-origin' })
  if (res.status === 429) {
    return { ok: false, error: 'Demasiadas consultas. Espere un minuto e intente de nuevo.' }
  }
  return res.json()
}

/** Público: solicitar código por email. Sin auth. Rate limit 5/hora por IP. */
export async function solicitarCodigo(cedula: string): Promise<SolicitarCodigoResponse> {
  const url = `${BASE}/solicitar-codigo`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cedula: cedula.slice(0, 20).trim() }),
    credentials: 'same-origin',
  })
  if (res.status === 429) {
    return { ok: false, error: 'Ha alcanzado el límite de consultas por hora. Intente más tarde.' }
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) return { ok: false, error: (data as SolicitarCodigoResponse).error || `Error ${res.status}.` }
  return data
}

/** Público: verificar código y obtener PDF. Sin auth. Rate limit 15 intentos/15 min por IP. */
export async function verificarCodigo(cedula: string, codigo: string): Promise<VerificarCodigoResponse> {
  const url = `${BASE}/verificar-codigo`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cedula: cedula.slice(0, 20).trim(), codigo: (codigo || '').trim() }),
    credentials: 'same-origin',
  })
  if (res.status === 429) {
    return { ok: false, error: 'Demasiados intentos. Espere 15 minutos e intente de nuevo.' }
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) return { ok: false, error: (data as VerificarCodigoResponse).error || `Error ${res.status}.` }
  return data
}

/** Público: solicitar estado de cuenta (genera PDF, envía al email, devuelve PDF en base64). Sin auth. */
export async function solicitarEstadoCuenta(cedula: string): Promise<SolicitarEstadoCuentaResponse> {
  const url = `${BASE}/solicitar-estado-cuenta`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cedula: cedula.slice(0, 20).trim() }),
    credentials: 'same-origin',
  })
  if (res.status === 429) {
    return { ok: false, error: 'Ha alcanzado el límite de consultas por hora. Intente más tarde.' }
  }
  const text = await res.text()
  let data: SolicitarEstadoCuentaResponse
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    return { ok: false, error: (text || `Error ${res.status}. Intente más tarde.`).slice(0, 200) }
  }
  if (!res.ok && data && typeof data === 'object') {
    return { ok: false, error: (data as SolicitarEstadoCuentaResponse).error || `Error ${res.status}.` }
  }
  return data
}
