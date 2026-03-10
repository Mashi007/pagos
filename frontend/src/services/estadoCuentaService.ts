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

/** Público: validar cédula (formato + existe en clientes). Sin auth. */
export async function validarCedulaEstadoCuenta(cedula: string): Promise<ValidarCedulaEstadoCuentaResponse> {
  const url = `${BASE}/validar-cedula?cedula=${encodeURIComponent(cedula.slice(0, 20))}`
  const res = await fetch(url, { credentials: 'same-origin' })
  if (res.status === 429) {
    return { ok: false, error: 'Demasiadas consultas. Espere un minuto e intente de nuevo.' }
  }
  return res.json()
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
