import axios, { type AxiosInstance } from 'axios'

import { API_BASE_URL, apiClient } from './api'

import { FINIQUITO_ACCESS_TOKEN_KEY } from '../constants/finiquitoStorage'

const BASE = '/api/v1/finiquito'

function getFiniquitoToken(): string {
  try {
    return sessionStorage.getItem(FINIQUITO_ACCESS_TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

function createFiniquitoClient(): AxiosInstance {
  const c = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
    validateStatus: s => s < 500,
  })
  c.interceptors.request.use(cfg => {
    const t = getFiniquitoToken().trim()
    if (t) {
      cfg.headers.Authorization = `Bearer ${t.startsWith('Bearer ') ? t.slice(7) : t}`
    }
    return cfg
  })
  return c
}

const finiquitoAxios = createFiniquitoClient()

function detailToString(detail: unknown): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((x: unknown) => {
        if (typeof x === 'string') return x
        if (x && typeof x === 'object' && 'msg' in x) {
          const m = (x as { msg?: string }).msg
          return typeof m === 'string' ? m : ''
        }
        return ''
      })
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }
  return ''
}

/** Error HTTP 4xx/5xx del flujo Finiquito (axios no lanza en 4xx con validateStatus). */
export class FiniquitoHttpError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'FiniquitoHttpError'
    this.status = status
  }
}

function throwIfFiniquitoHttpError(status: number, data: unknown): void {
  if (status < 400) return
  const d = data as { detail?: unknown; message?: string }
  const fromDetail = detailToString(d?.detail)
  const msg =
    fromDetail ||
    (typeof d?.message === 'string' && d.message) ||
    'Solicitud no procesada'
  throw new FiniquitoHttpError(msg, status)
}

export function setFiniquitoAccessToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(FINIQUITO_ACCESS_TOKEN_KEY, token)
    else sessionStorage.removeItem(FINIQUITO_ACCESS_TOKEN_KEY)
  } catch {
    /* ignore */
  }
}

export function getFiniquitoAccessToken(): string | null {
  try {
    return sessionStorage.getItem(FINIQUITO_ACCESS_TOKEN_KEY)
  } catch {
    return null
  }
}

export type FiniquitoCasoItem = {
  id: number
  prestamo_id: number
  cliente_id: number | null
  cedula: string
  total_financiamiento: string
  sum_total_pagado: string
  estado: string
  ultimo_refresh_utc: string | null
  /** ISO: ultima fecha_pago en pagos para este prestamo_id */
  ultima_fecha_pago?: string | null
  contacto_para_siguientes?: boolean | null
  cliente_nombres?: string | null
  cliente_email?: string | null
  cliente_telefono?: string | null
}

export async function finiquitoRegistro(cedula: string, email: string) {
  const { data, status } = await finiquitoAxios.post(
    `${BASE}/public/registro`,
    {
      cedula,
      email,
    }
  )
  throwIfFiniquitoHttpError(status, data)
  return data as { ok: boolean; message: string }
}

export async function finiquitoSolicitarCodigo(cedula: string, email: string) {
  const { data, status } = await finiquitoAxios.post(
    `${BASE}/public/solicitar-codigo`,
    {
      cedula,
      email,
    }
  )
  throwIfFiniquitoHttpError(status, data)
  return data as { ok: boolean; message: string }
}

export async function finiquitoVerificarCodigo(
  cedula: string,
  email: string,
  codigo: string
) {
  const { data, status } = await finiquitoAxios.post(
    `${BASE}/public/verificar-codigo`,
    {
      cedula,
      email,
      codigo,
    }
  )
  throwIfFiniquitoHttpError(status, data)
  return data as {
    ok: boolean
    access_token?: string
    expires_in?: number
    error?: string
  }
}

/**
 * Lista casos materializados (suma abonos = financiamiento).
 * Sin filtro o `todos`: todos los registros. `entrada` / `desk`: solo ese estado.
 */
export async function finiquitoListarCasos(
  bandeja?: 'entrada' | 'desk' | 'todos'
) {
  const params: Record<string, string> = {}
  if (bandeja === 'entrada' || bandeja === 'desk') {
    params.bandeja = bandeja
  }
  const { data, status } = await finiquitoAxios.get(`${BASE}/public/casos`, {
    params,
  })
  if (status === 401) {
    throw new Error('Token inválido o expirado. Ingrese de nuevo.')
  }
  if (status >= 400) {
    const msg =
      (data as { detail?: string })?.detail || 'No se pudo cargar la lista'
    throw new Error(msg)
  }
  return data as { items: FiniquitoCasoItem[] }
}

export async function finiquitoPatchEstadoPublic(
  casoId: number,
  estado: string
) {
  const { data, status } = await finiquitoAxios.patch(
    `${BASE}/public/casos/${casoId}/estado`,
    { estado }
  )
  if (status >= 400) {
    const msg =
      (data as { detail?: string })?.detail ||
      (data as { error?: string })?.error ||
      'Error al actualizar'
    throw new Error(msg)
  }
  return data as { ok: boolean; caso?: FiniquitoCasoItem; error?: string }
}

export async function finiquitoDetalle(casoId: number) {
  const { data, status } = await finiquitoAxios.get(
    `${BASE}/public/casos/${casoId}/detalle`
  )
  if (status >= 400) {
    const msg = (data as { detail?: string })?.detail || 'No se pudo cargar'
    throw new Error(msg)
  }
  return data as {
    caso: FiniquitoCasoItem
    prestamo: Record<string, unknown> | null
    cuotas: Record<string, unknown>[] | null
  }
}

export type FiniquitoRevisionDatosResponse = {
  caso_id: number
  prestamo_id_finiquito?: number
  cedula: string
  prestamo_caso?: Record<string, unknown> | null
  cuotas_caso?: Record<string, unknown>[]
  prestamos: {
    prestamos: Record<string, unknown>[]
    total: number
    page: number
    per_page: number
    total_pages: number
  }
  pagos: {
    pagos: Record<string, unknown>[]
    total: number
    page: number
    per_page: number
    total_pages: number
  }
}

/** Detalle del caso: préstamo, cuotas, listados préstamos/pagos por cédula (portal colaborador). */
export async function finiquitoRevisionDatos(casoId: number) {
  const { data, status } = await finiquitoAxios.get(
    `${BASE}/public/revision-datos/${casoId}`
  )
  if (status === 401) {
    throw new Error('Token inválido o expirado. Ingrese de nuevo.')
  }
  if (status >= 400) {
    const msg =
      (data as { detail?: string })?.detail || 'No se pudo cargar la revision'
    throw new Error(msg)
  }
  return data as FiniquitoRevisionDatosResponse
}

/** Igual que finiquitoRevisionDatos; usa sesión administrador del panel. */
export async function finiquitoAdminRevisionDatos(casoId: number) {
  return apiClient.get<FiniquitoRevisionDatosResponse>(
    `${BASE}/admin/casos/${casoId}/revision-datos`
  )
}

export type FiniquitoAdminListaResult = {
  items: FiniquitoCasoItem[]
  total: number
  limit: number
  offset: number
}

export async function finiquitoAdminListar(
  estado?: string,
  cedula?: string,
  estadoIn?: string,
  pagination?: { limit?: number; offset?: number }
): Promise<FiniquitoAdminListaResult> {
  const params = new URLSearchParams()
  if (estadoIn && estadoIn.trim()) {
    params.set('estado_in', estadoIn.trim())
  } else if (estado) {
    params.set('estado', estado)
  }
  const ced = (cedula ?? '').trim()
  if (ced) params.set('cedula', ced)
  if (pagination?.limit != null) {
    params.set('limit', String(pagination.limit))
  }
  if (pagination?.offset != null) {
    params.set('offset', String(pagination.offset))
  }
  const q = params.toString() ? `?${params.toString()}` : ''
  return apiClient.get<FiniquitoAdminListaResult>(`${BASE}/admin/casos${q}`)
}

export async function finiquitoAdminPatchEstado(
  casoId: number,
  estado: string,
  contactoParaSiguientes?: boolean,
  notaAntiguo?: string
) {
  const body: {
    estado: string
    contacto_para_siguientes?: boolean
    nota_antiguo?: string
  } = {
    estado,
  }
  if (contactoParaSiguientes !== undefined) {
    body.contacto_para_siguientes = contactoParaSiguientes
  }
  if (notaAntiguo !== undefined && String(notaAntiguo).trim() !== '') {
    body.nota_antiguo = String(notaAntiguo).trim()
  }
  return apiClient.patch<{
    ok: boolean
    caso?: FiniquitoCasoItem
    error?: string
  }>(`${BASE}/admin/casos/${casoId}/estado`, body)
}

export type FiniquitoContactarClienteResult = {
  ok: boolean
  error?: string
  message?: string
}

/** Correo al cliente: finiquito en gestion y WhatsApp de contacto. */
export async function finiquitoAdminContactarCliente(casoId: number) {
  return apiClient.post<FiniquitoContactarClienteResult>(
    `${BASE}/admin/casos/${casoId}/contactar-cliente`,
    {}
  )
}

export type FiniquitoRefreshStats = {
  elegibles: number
  insertados: number
  actualizados: number
  eliminados: number
}

export async function finiquitoAdminRefreshMaterializado() {
  return apiClient.post<FiniquitoRefreshStats>(
    `${BASE}/admin/refresh-materializado`
  )
}
