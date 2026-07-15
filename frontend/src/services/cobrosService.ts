/**









 * Servicio del modulo Cobros.









 * - Publico: validar cedula, enviar reporte (sin auth).









 * - Admin: listado, detalle, aprobar, rechazar (con auth).









 */

import { apiClient } from './api'

import { env } from '../config/env'

const API = env.API_URL || ''

const BASE_PUBLIC = `${API}/api/v1/cobros/public`

const BASE_COBROS = `${API}/api/v1/cobros`

/** Timeout (ms) para peticiones públicas ligeras. Sin timeout pueden quedar colgadas. */
const FETCH_TIMEOUT_MS = 30000

/** Validar cédula / OTP: alinear con pool_timeout del API (~60s) bajo carga. */
const FETCH_TIMEOUT_VALIDAR_CEDULA_MS = 65000

/** SMTP en solicitar-codigo-reporte puede superar 30s. */
const FETCH_TIMEOUT_SOLICITAR_CODIGO_MS = 90000

/**
 * POST multipart de reporte (público / Infopagos): en Render puede superar 30s
 * (validación, persistencia, PDF/recibo). Firefox muestra el abort como NS_BINDING_ABORTED.
 */
const FETCH_TIMEOUT_ENVIAR_REPORTE_MS = 180000
const ENVIAR_REPORTE_MAX_REINTENTOS = 2
const ENVIAR_REPORTE_REINTENTO_DELAY_MS = 1500

/** Descarga de recibo PDF tras guardar (puede ser lenta si el API está frío). */
const FETCH_TIMEOUT_RECIBO_INFOPAGOS_MS = 120000

/** Lecturas listado/KPIs cobros: alinear con SET LOCAL statement_timeout=240s del API. */
export const COBROS_LISTADO_READ_TIMEOUT_MS = 240_000

/**
 * Traduce fallos de red del navegador (no vienen del JSON del API).
 * Texto corto para móvil; en desarrollo se añade una pista técnica en consola.
 */
function mensajeErrorRedPublico(msg: string): string {
  const m = (msg || '').trim()
  if (
    /timeout|abort|ns_binding_aborted|aborted a request/i.test(m) ||
    /despu[eé]s de \d+s/i.test(m)
  ) {
    return 'El servidor tardó demasiado. Espere un momento e intente de nuevo.'
  }
  if (/failed to fetch|load failed|networkerror/i.test(m)) {
    const corto =
      'Sin conexión con el servidor. Revise la red o intente más tarde.'
    if (import.meta.env.DEV) {
      console.warn(
        '[cobros] fetch de red:',
        m,
        '| Si es local: proxy /api y API_BASE_URL; si es producción: API en reposo o CORS.'
      )
    }
    return corto
  }
  return m
}

/** Helper: fetch con timeout y mejor manejo de errores */
async function fetchWithTimeout(
  url: string,
  options?: RequestInit,
  timeoutMs: number = FETCH_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    return res
  } catch (err: unknown) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error(
        `Timeout después de ${timeoutMs / 1000}s. El servidor no responde.`
      )
    }
    throw err
  } finally {
    clearTimeout(timeout)
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function esFalloTransitorioEnvioReporte(status: number): boolean {
  return status === 502 || status === 503 || status === 504
}

/**
 * Extrae texto útil del JSON del proxy (502) o del backend público.
 */
function mensajeDesdeCuerpoJsonPublico(parsed: unknown): string {
  if (!parsed || typeof parsed !== 'object') return ''
  const o = parsed as { message?: unknown; error?: unknown; detail?: unknown }
  const parts = [o.message, o.error, o.detail]
    .filter(v => typeof v === 'string' && String(v).trim())
    .map(v => String(v).trim())
  return parts.length ? parts.join(' ') : ''
}

/**
 * Lee el body tras `fetch` en cobros público: distingue 5xx/proxy (Render), HTML de borde y 4xx.
 * No sustituye el `catch` de red (`Failed to fetch`); evita confundir 502 JSON con éxito HTTP.
 */
async function parsearJsonRespuestaCobrosPublic<
  T extends { ok?: boolean; error?: string },
>(
  res: Response
): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  const text = await res.text()
  let parsed: unknown
  try {
    parsed = text ? JSON.parse(text) : null
  } catch {
    const looksLikeHtml =
      typeof text === 'string' &&
      (text.includes('<html') ||
        text.toLowerCase().includes('cloudflare') ||
        text.toLowerCase().includes('bad request'))
    return {
      ok: false,
      error: looksLikeHtml
        ? `La petición devolvió HTML (HTTP ${res.status}). Suele ser proxy o bloqueo; pruebe otra red o más tarde.`
        : 'No se pudo procesar la respuesta del servidor.',
    }
  }
  const data = (parsed ?? {}) as T

  if (res.status >= 500) {
    const fromBody = mensajeDesdeCuerpoJsonPublico(parsed)
    const base =
      res.status === 503
        ? 'Servicio temporalmente no disponible.'
        : res.status === 504
          ? 'Tiempo de espera agotado en el servidor intermedio.'
          : 'No hubo respuesta del servidor de datos (502). Suele ser el API en arranque (p. ej. Render frío), un timeout hacia el backend o API_BASE_URL del frontend apuntando mal (no debe ser la misma URL que el sitio web).'
    return {
      ok: false,
      error: fromBody ? `${base} Detalle: ${fromBody}` : base,
    }
  }

  if (!res.ok) {
    const err =
      (typeof data.error === 'string' && data.error.trim()) ||
      mensajeDesdeCuerpoJsonPublico(parsed) ||
      `Error ${res.status}. Intente de nuevo.`
    return { ok: false, error: String(err) }
  }

  return { ok: true, data }
}

export interface ValidarCedulaResponse {
  ok: boolean

  nombre?: string

  /** Correo enmascarado para comprobación visual sin exponer PII completa. */
  email_enmascarado?: string

  error?: string

  /** True si esta cedula puede reportar pagos en Bolivares (Bs) en cobros/infopagos. */

  puede_reportar_bs?: boolean

  /** bcv | euro | binance según lista admin; solo si puede_reportar_bs. */
  fuente_tasa_cambio_lista_bs?: string
}

export interface SolicitarCodigoReporteResponse {
  ok: boolean

  mensaje?: string

  error?: string

  expira_en?: string
}

export interface VerificarCodigoReporteResponse {
  ok: boolean

  error?: string

  access_token?: string

  expires_in?: number

  nombre?: string

  puede_reportar_bs?: boolean

  email_enmascarado?: string

  fuente_tasa_cambio_lista_bs?: string
}

export interface EnviarReporteResponse {
  ok: boolean

  referencia_interna?: string

  mensaje?: string

  error?: string

  /** Backend: aprobado | en_revision | pendiente (segun flujo Gemini/import). */

  estado_reportado?: string | null

  /** True solo si hubo aprobacion automatica y SMTP acepto el envio del recibo. */

  recibo_enviado?: boolean | null
}

export interface DigitalizarComprobanteSugerencia {
  fecha_pago: string | null
  institucion_financiera: string
  numero_operacion: string
  monto: number | null
  moneda: 'BS' | 'USD'
  cedula_pagador_en_comprobante: string
  notas_modelo: string
}

export interface DigitalizarComprobanteResponse {
  ok: boolean
  error?: string
  sugerencia?: DigitalizarComprobanteSugerencia | null
}

/** Respuesta de Infopagos: incluye token para descargar recibo en la misma pantalla. */

export interface EnviarReporteInfopagosResponse {
  ok: boolean

  referencia_interna?: string

  mensaje?: string

  error?: string

  recibo_descarga_token?: string

  pago_id?: number

  /** Ej. Cuota 1 / Cuotas 1, 2 si ya aplico en amortizacion. */

  aplicado_a_cuotas?: string | null

  /** Alineado con cobros publico: sin token/recibo hasta aprobacion si en_revision. */

  estado_reportado?: string | null

  /** `false` justo después de aprobar (cuando PDF/correo van en background). */
  recibo_listo?: boolean | null
}

/** Publico: validar cedula. Con accessToken (JWT cobros_public) tras verificar codigo por correo. */

export async function validarCedulaPublico(
  cedula: string,

  opts?: { origen?: string; accessToken?: string }
): Promise<ValidarCedulaResponse> {
  const o = (opts?.origen || '').trim()

  const q = new URLSearchParams({ cedula: cedula.slice(0, 20) })

  if (o) q.set('origen', o)

  const url = `${BASE_PUBLIC}/validar-cedula?${q.toString()}`

  const headers: Record<string, string> = {}

  const tok = (opts?.accessToken || '').trim()

  if (tok) headers.Authorization = `Bearer ${tok}`

  try {
    const res = await fetchWithTimeout(
      url,
      {
        credentials: 'same-origin',

        headers,
      },
      FETCH_TIMEOUT_VALIDAR_CEDULA_MS
    )

    if (res.status === 429) {
      return {
        ok: false,
        error: 'Demasiadas consultas. Espere un minuto e intente de nuevo.',
      }
    }

    const parsed =
      await parsearJsonRespuestaCobrosPublic<ValidarCedulaResponse>(res)
    if (!parsed.ok) return { ok: false, error: parsed.error }
    return parsed.data
  } catch (e: unknown) {
    const raw =
      e instanceof Error ? e.message : 'Error de conexión con el servidor.'
    return { ok: false, error: mensajeErrorRedPublico(raw) }
  }
}

export async function solicitarCodigoReportePublico(body: {
  cedula: string

  email: string
}): Promise<SolicitarCodigoReporteResponse> {
  const url = `${BASE_PUBLIC}/solicitar-codigo-reporte`

  try {
    const res = await fetchWithTimeout(
      url,
      {
        method: 'POST',

        credentials: 'same-origin',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(body),
      },
      FETCH_TIMEOUT_SOLICITAR_CODIGO_MS
    )

    if (res.status === 429) {
      return {
        ok: false,

        error:
          'Demasiadas solicitudes de codigo. Intente de nuevo en una hora.',
      }
    }

    const parsed =
      await parsearJsonRespuestaCobrosPublic<SolicitarCodigoReporteResponse>(
        res
      )
    if (!parsed.ok) return { ok: false, error: parsed.error }
    return parsed.data
  } catch (e: unknown) {
    const raw =
      e instanceof Error ? e.message : 'Error de conexion con el servidor.'

    return { ok: false, error: mensajeErrorRedPublico(raw) }
  }
}

export async function verificarCodigoReportePublico(body: {
  cedula: string

  email: string

  codigo: string
}): Promise<VerificarCodigoReporteResponse> {
  const url = `${BASE_PUBLIC}/verificar-codigo-reporte`

  try {
    const res = await fetchWithTimeout(
      url,
      {
        method: 'POST',

        credentials: 'same-origin',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(body),
      },
      FETCH_TIMEOUT_VALIDAR_CEDULA_MS
    )

    if (res.status === 429) {
      return {
        ok: false,

        error: 'Demasiados intentos. Espere unos minutos e intente de nuevo.',
      }
    }

    const parsed =
      await parsearJsonRespuestaCobrosPublic<VerificarCodigoReporteResponse>(
        res
      )
    if (!parsed.ok) return { ok: false, error: parsed.error }
    return parsed.data
  } catch (e: unknown) {
    const raw =
      e instanceof Error ? e.message : 'Error de conexion con el servidor.'

    return { ok: false, error: mensajeErrorRedPublico(raw) }
  }
}

/** Publico: enviar reporte de pago (multipart). Requiere accessToken salvo modo legacy en backend. */

export async function enviarReportePublico(
  formData: FormData,

  opts?: { accessToken?: string }
): Promise<EnviarReporteResponse> {
  const url = `${BASE_PUBLIC}/enviar-reporte`

  const headers: Record<string, string> = {}

  const tok = (opts?.accessToken || '').trim()

  if (tok) headers.Authorization = `Bearer ${tok}`

  for (let intento = 1; intento <= ENVIAR_REPORTE_MAX_REINTENTOS; intento++) {
    try {
      const res = await fetchWithTimeout(
        url,
        {
          method: 'POST',

          body: formData,

          credentials: 'same-origin',

          headers,

          // No Content-Type: el navegador fija multipart boundary
        },
        FETCH_TIMEOUT_ENVIAR_REPORTE_MS
      )

      if (res.status === 429) {
        return {
          ok: false,
          error:
            'Ha alcanzado el límite de envíos por hora. Intente más tarde.',
        }
      }

      if (
        esFalloTransitorioEnvioReporte(res.status) &&
        intento < ENVIAR_REPORTE_MAX_REINTENTOS
      ) {
        await sleep(ENVIAR_REPORTE_REINTENTO_DELAY_MS)
        continue
      }

      if (res.status === 503) {
        return {
          ok: false,

          error:
            'Servicio temporalmente no disponible. Intente más tarde o contacte por WhatsApp 424-4579934.',
        }
      }

      const parsed =
        await parsearJsonRespuestaCobrosPublic<EnviarReporteResponse>(res)
      if (!parsed.ok) return { ok: false, error: parsed.error }
      return parsed.data
    } catch (e: unknown) {
      const raw =
        e instanceof Error ? e.message : 'Error de conexión con el servidor.'
      const esUltimoIntento = intento >= ENVIAR_REPORTE_MAX_REINTENTOS
      if (
        !esUltimoIntento &&
        /timeout|fetch|network|abort|502|503|504/i.test(raw)
      ) {
        await sleep(ENVIAR_REPORTE_REINTENTO_DELAY_MS)
        continue
      }
      return { ok: false, error: mensajeErrorRedPublico(raw) }
    }
  }
  return {
    ok: false,
    error:
      'No se pudo procesar el reporte. Intente nuevamente en unos segundos.',
  }
}

function humanizarErrorEnvioComprobanteAxios(
  st: number | undefined,
  detail: string
): string {
  const d = (detail || '').trim()
  const lower = d.toLowerCase()
  const looksHtml =
    lower.includes('<html') ||
    lower.includes('cloudflare') ||
    lower.includes('bad request') ||
    lower.includes('<!doctype html')

  if (looksHtml) {
    const stLabel = typeof st === 'number' ? String(st) : '-'
    return `El envío fue rechazado en el borde (HTTP ${stLabel}). Suele ocurrir con comprobantes muy grandes o peticiones bloqueadas por el proxy. Intente con un PDF/imagen más liviana o reintente en unos minutos.`
  }

  return d
}

export async function digitalizarComprobantePublico(
  formData: FormData
): Promise<DigitalizarComprobanteResponse> {
  const url = `${BASE_PUBLIC}/digitalizar-comprobante`

  try {
    const res = await fetchWithTimeout(
      url,
      {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
      },
      FETCH_TIMEOUT_ENVIAR_REPORTE_MS
    )

    if (res.status === 429) {
      return {
        ok: false,
        error: 'Demasiadas solicitudes. Espere un momento e intente de nuevo.',
      }
    }

    const parsed =
      await parsearJsonRespuestaCobrosPublic<DigitalizarComprobanteResponse>(
        res
      )
    if (!parsed.ok) return { ok: false, error: parsed.error }
    return parsed.data
  } catch (e: unknown) {
    const raw =
      e instanceof Error ? e.message : 'Error de conexión con el servidor.'
    return { ok: false, error: mensajeErrorRedPublico(raw) }
  }
}

/** Infopagos: enviar reporte a nombre del deudor (uso interno). Devuelve token para descargar recibo. */

export async function enviarReporteInfopagos(
  formData: FormData
): Promise<EnviarReporteInfopagosResponse> {
  try {
    return await apiClient.post<EnviarReporteInfopagosResponse>(
      `${BASE_PUBLIC}/infopagos/enviar-reporte`,
      formData,
      { timeout: FETCH_TIMEOUT_ENVIAR_REPORTE_MS }
    )
  } catch (e: unknown) {
    const st = (e as { response?: { status?: number } })?.response?.status
    const detailRaw = (e as { response?: { data?: unknown } })?.response?.data
    const detail =
      typeof detailRaw === 'string'
        ? detailRaw
        : typeof detailRaw === 'object' &&
            detailRaw !== null &&
            typeof (detailRaw as { detail?: unknown }).detail === 'string'
          ? String((detailRaw as { detail?: string }).detail)
          : typeof detailRaw === 'object' &&
              detailRaw !== null &&
              typeof (detailRaw as { message?: unknown }).message === 'string'
            ? String((detailRaw as { message?: string }).message)
            : ''

    if (st === 401) {
      return {
        ok: false,
        error:
          'Sesión expirada o no autorizada. Inicie sesión de nuevo para guardar en Infopagos.',
      }
    }
    if (st === 429) {
      return {
        ok: false,
        error: 'Ha alcanzado el límite de envíos por hora. Intente más tarde.',
      }
    }
    if (st === 503) {
      return {
        ok: false,
        error:
          'Servicio temporalmente no disponible. Intente más tarde o contacte por WhatsApp 424-4579934.',
      }
    }
    if (st === 502) {
      return {
        ok: false,
        error:
          'El servidor intermedio no pudo contactar al API. Intente de nuevo en un momento.',
      }
    }
    if (detail) {
      return {
        ok: false,
        error: humanizarErrorEnvioComprobanteAxios(st, String(detail)),
      }
    }

    const raw =
      e instanceof Error ? e.message : 'Error de conexión con el servidor.'
    return { ok: false, error: mensajeErrorRedPublico(raw) }
  }
}

/** Infopagos: descargar recibo PDF con el token devuelto tras registrar el pago. */

export interface EscanerInfopagosSugerencia {
  fecha_pago: string | null

  institucion_financiera: string

  numero_operacion: string

  monto: number | null

  moneda: 'BS' | 'USD'

  cedula_pagador_en_comprobante: string

  notas_modelo: string
}

export interface EscanerInfopagosExtraerResponse {
  ok: boolean

  error?: string | null

  sugerencia: EscanerInfopagosSugerencia | null

  validacion_campos?: string | null

  validacion_reglas?: string | null

  /** Colisión con `pagos` (misma lógica que detalle Cobros). */
  duplicado_en_pagos?: boolean

  pago_existente_id?: number | null

  prestamo_existente_id?: number | null

  /** Préstamo APROBADO único al que se aplicará el reporte (si aplica). */
  prestamo_objetivo_id?: number | null

  /** ID de borrador en BD (tabla temporal); enviar en `borrador_id` al guardar el reporte. */
  borrador_id?: string | null
}

/** Gemini + visión en escáner Infopagos (alinear con api.ts / server.js). */
export const COBROS_ESCANER_EXTRAER_TIMEOUT_MS = 180_000
/** Re-escaneo cartera: margen extra por cola Gemini en Render. */
export const COBROS_ESCANER_EXTRAER_REESCANEO_TIMEOUT_MS = 240_000

/** Escáner Infopagos (auth): Gemini sugiere campos desde el comprobante; no guarda el reporte. */
export async function escanerInfopagosExtraerComprobante(
  formData: FormData,
  opts?: { timeoutMs?: number }
): Promise<EscanerInfopagosExtraerResponse> {
  return apiClient.post<EscanerInfopagosExtraerResponse>(
    `${BASE_COBROS}/escaner/extraer-comprobante`,
    formData,
    {
      timeout: opts?.timeoutMs ?? COBROS_ESCANER_EXTRAER_TIMEOUT_MS,
    }
  )
}

export interface EscanerLoteContextoRevisionItem {
  pago_id: number
  ok: boolean
  error?: string | null
  cedula?: string
  prestamo_id?: number | null
  numero_documento?: string
  fecha_pago?: string | null
  monto_usd?: number | null
  institucion_bancaria?: string
  nombre_archivo?: string
  mime_type?: string
  archivo_b64?: string
}

export interface EscanerLoteContextoRevisionResponse {
  ok: boolean
  items: EscanerLoteContextoRevisionItem[]
  cedula_comun: string
  nombre_cliente: string
  cedulas_distintas: boolean
}

/** Precarga comprobantes desde pagos en revisión (?from=pagos&ids=). */
export async function escanerInfopagosLoteContextoRevision(
  pagoIds: number[]
): Promise<EscanerLoteContextoRevisionResponse> {
  const ids = pagoIds.filter(n => Number.isFinite(n) && n > 0).slice(0, 10)
  return apiClient.get<EscanerLoteContextoRevisionResponse>(
    `${BASE_COBROS}/escaner/lote/contexto-revision?ids=${ids.join(',')}`
  )
}

/** Listado de borradores con validación pendiente (mismo usuario autenticado). */
export interface InfopagosBorradorListItem {
  id: string
  cedula_normalizada: string
  tipo_cedula: string
  numero_cedula: string
  comprobante_nombre: string
  created_at: string | null
  resumen_validacion: string
  cliente_nombre?: string | null
}

export async function listInfopagosBorradoresEscaneer(
  limit = 30
): Promise<{ ok: boolean; items: InfopagosBorradorListItem[] }> {
  return apiClient.get<{ ok: boolean; items: InfopagosBorradorListItem[] }>(
    `${BASE_COBROS}/escaner/borradores?limit=${limit}`
  )
}

export interface InfopagosBorradorDetalle {
  id: string
  tipo_cedula: string
  numero_cedula: string
  cedula_normalizada: string
  fuente_tasa_cambio: string
  comprobante_nombre: string
  cliente_nombre?: string | null
  payload: Record<string, unknown>
}

export async function getInfopagosBorradorEscaneer(
  borradorId: string
): Promise<{ ok: boolean; borrador: InfopagosBorradorDetalle }> {
  return apiClient.get<{ ok: boolean; borrador: InfopagosBorradorDetalle }>(
    `${BASE_COBROS}/escaner/borrador/${encodeURIComponent(borradorId)}`
  )
}

export async function deleteInfopagosBorradorEscaneer(
  borradorId: string
): Promise<{ ok: boolean }> {
  return apiClient.delete<{ ok: boolean }>(
    `${BASE_COBROS}/escaner/borrador/${encodeURIComponent(borradorId)}`
  )
}

/** Vista previa / nueva pestaña: mismo binario que el borrador en servidor. */
export async function getInfopagosBorradorComprobanteBlob(
  borradorId: string
): Promise<Blob> {
  return apiClient.getBlob(
    `${BASE_COBROS}/escaner/borrador/${encodeURIComponent(borradorId)}/comprobante`
  )
}

export async function openInfopagosBorradorComprobanteInNewTab(
  borradorId: string
): Promise<void> {
  const data = await getInfopagosBorradorComprobanteBlob(borradorId)

  const url = URL.createObjectURL(data)

  window.open(url, '_blank')

  window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
}

export interface EscanerInfopagosLoteDriveItem extends EscanerInfopagosExtraerResponse {
  drive_file_id: string
  nombre_archivo: string
  mime_type: string
  archivo_b64?: string | null
}

export interface EscanerInfopagosLoteDriveResponse {
  ok: boolean
  items: EscanerInfopagosLoteDriveItem[]
  total_leidos: number
  total_eliminados: number
  mensaje?: string
}

/** Escáner lote (auth): toma hasta 15 comprobantes desde carpeta Drive, digitaliza y borra origen. */
export async function escanerInfopagosLoteDesdeDrive(
  formData: FormData
): Promise<EscanerInfopagosLoteDriveResponse> {
  return apiClient.post<EscanerInfopagosLoteDriveResponse>(
    `${BASE_COBROS}/escaner/lote/drive-digitalizar`,
    formData
  )
}

export async function getReciboInfopagos(
  token: string,
  pagoId: number
): Promise<Blob> {
  const url = `${BASE_PUBLIC}/infopagos/recibo?pago_id=${pagoId}`

  try {
    const res = await fetchWithTimeout(
      url,
      {
        credentials: 'same-origin',
        headers: { Authorization: `Bearer ${token}` },
      },
      FETCH_TIMEOUT_RECIBO_INFOPAGOS_MS
    )

    if (!res.ok) {
      if (res.status === 401) {
        throw new Error('Enlace de descarga expirado.')
      }
      if (res.status === 502 || res.status === 503 || res.status === 504) {
        throw new Error(
          'El servidor de datos no respondió a tiempo (posible arranque en frío o proxy). Espere 20-60 s y reintente la descarga.'
        )
      }
      throw new Error('No se pudo descargar el recibo.')
    }

    return res.blob()
  } catch (e: unknown) {
    const raw =
      e instanceof Error
        ? e.message
        : 'Error de conexión al descargar el recibo.'
    throw new Error(mensajeErrorRedPublico(raw))
  }
}

export interface ReciboInfopagosStatusResponse {
  ok: boolean
  pago_id: number
  recibo_listo: boolean
  estado_reportado?: string | null
  mensaje?: string
}

export async function getReciboInfopagosStatus(
  token: string,
  pagoId: number
): Promise<ReciboInfopagosStatusResponse> {
  const url = `${BASE_PUBLIC}/infopagos/recibo-status?pago_id=${pagoId}`
  try {
    const res = await fetchWithTimeout(
      url,
      {
        credentials: 'same-origin',
        headers: { Authorization: `Bearer ${token}` },
      },
      FETCH_TIMEOUT_MS
    )
    const parsed =
      await parsearJsonRespuestaCobrosPublic<ReciboInfopagosStatusResponse>(res)
    if (!parsed.ok) throw new Error(parsed.error)
    return parsed.data
  } catch (e: unknown) {
    const raw =
      e instanceof Error
        ? e.message
        : 'No se pudo consultar el estado del recibo.'
    throw new Error(mensajeErrorRedPublico(raw))
  }
}

export interface PagoReportadoItem {
  id: number

  referencia_interna: string

  nombres: string

  apellidos: string

  cedula_display: string

  institucion_financiera: string

  monto: number

  moneda: string

  /** Tasa oficial Bs por 1 USD (día fecha_pago); ausente si USD o sin tasa en BD. */

  tasa_cambio_bs_usd?: number | null

  /** Monto en USD (Bs÷tasa si BS; si USD el monto). */

  equivalente_usd?: number | null

  fecha_pago: string

  numero_operacion: string

  fecha_reporte: string

  estado: string

  gemini_coincide_exacto?: string

  /** Divergencias de Gemini con lo ingresado (para columna Observaci├â┬│n y revisi├â┬│n manual) */

  observacion?: string

  /** Correo al que se envi├â┬│ (o se enviar├â┬¡a) el recibo; para icono estado en Acciones */

  correo_enviado_a?: string

  /** Si tiene recibo PDF generado (enviado o disponible) */

  tiene_recibo_pdf?: boolean

  /** Imagen/PDF del comprobante cargado por el cliente */

  tiene_comprobante?: boolean

  /** infopagos | cobros_publico | ausente (historico) */

  canal_ingreso?: string | null

  duplicado_en_pagos?: boolean

  pago_existente_id?: number | null

  prestamo_existente_id?: number | null

  /** Nº documento en `pagos` que ya ocupa el comprobante (listado enriquecido). */
  numero_documento_pago_existente?: string | null

  pago_existente_estado?: string | null

  prestamo_objetivo_id?: number | null

  prestamo_objetivo_multiple?: boolean | null

  prestamo_duplicado_es_objetivo?: boolean | null

  /** liquidado | sin_aprobado | cedula_no_registrada cuando no hay APROBADO objetivo. */
  prestamo_objetivo_motivo?: string | null

  /** Préstamo LIQUIDADO de referencia en BD (motivo=liquidado). */
  prestamo_referencia_id?: number | null
}

/** Etiqueta legible para columna Origen en Pagos reportados. */
export function etiquetaCanalReportado(canalIngreso?: string | null): string {
  if (canalIngreso === 'infopagos') return 'Infopagos'
  if (canalIngreso === 'cobros_publico') return 'Formulario público'
  return '-'
}

export interface ListPagosReportadosResponse {
  items: PagoReportadoItem[]

  total: number

  page: number

  per_page: number
}

export interface PagosReportadosKpis {
  pendiente: number

  en_revision: number

  /**
   * Aprobado: opcional porque el backend ya no lo emite por defecto.
   * El reporte aprobado ya esta en cartera (tabla pagos) y no requiere accion
   * en la cola manual; conservar el conteo costaba un barrido extra que
   * bloqueaba al unico worker en Render.
   */

  aprobado?: number

  rechazado: number

  /** Presente en respuesta API (agrupacion por estado) */

  importado?: number

  total: number
}

/** Una sola peticion: listado + KPIs (mismos criterios que GET pagos-reportados + /kpis). */

export interface ListPagosReportadosConKpisResponse extends ListPagosReportadosResponse {
  kpis: PagosReportadosKpis
}

/** TTL compartido con el intervalo de refresco en CobrosPagosReportadosPage (15 min, alineado con cache backend). */
export const COBROS_LISTADO_KPIS_CACHE_TTL_MS = 15 * 60 * 1000
/** Datos viejos del cliente aún útiles para pintar mientras llega el fetch (alineado con stale Redis ~2h). */
export const COBROS_LISTADO_KPIS_STALE_CLIENT_MS = 2 * 60 * 60 * 1000

type CobrosListadoKpisParams = {
  estado?: string
  fecha_desde?: string
  fecha_hasta?: string
  cedula?: string
  institucion?: string
  page?: number
  per_page?: number
  incluir_exportados?: boolean
}

type CobrosListadoKpisCacheEntry = {
  storedAt: number
  payload: ListPagosReportadosConKpisResponse
}

const cobrosListadoKpisCache = new Map<string, CobrosListadoKpisCacheEntry>()

function cobrosListadoKpisCacheKey(params: CobrosListadoKpisParams): string {
  return JSON.stringify({
    e: params.estado ?? '',
    fd: params.fecha_desde ?? '',
    fh: params.fecha_hasta ?? '',
    c: params.cedula ?? '',
    i: params.institucion ?? '',
    p: params.page ?? 1,
    pp: params.per_page ?? 20,
    x: params.incluir_exportados ? 1 : 0,
  })
}

function cloneListadoConKpis(
  data: ListPagosReportadosConKpisResponse
): ListPagosReportadosConKpisResponse {
  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(data)
    } catch {
      /* JSON fallback */
    }
  }
  return JSON.parse(JSON.stringify(data)) as ListPagosReportadosConKpisResponse
}

/** Tras aprobar/rechazar/eliminar o exportar corrección masiva: forzar datos frescos en la siguiente carga. */
export function invalidateCobrosListadoKpisCache(): void {
  cobrosListadoKpisCache.clear()
}

/**
 * Lee el cache cliente del listado-y-kpis SIN disparar fetch ni await. Si hay una
 * entry viva (storedAt < TTL), devuelve una copia. Permite que `CobrosPagosReportadosPage`
 * hidrate `data`/`kpis` SINCRONO al montar (sin spinner full) cuando el operador
 * regresa al listado tras tratar un caso: el cache fue parchado quirurgicamente y
 * sigue siendo la fuente de verdad mas reciente que el operador vio.
 *
 * Retorna `null` si no hay cache, expiro, o el clon falla.
 */
export function peekListadoKpisCache(
  params: CobrosListadoKpisParams
): ListPagosReportadosConKpisResponse | null {
  try {
    const key = cobrosListadoKpisCacheKey(params)
    const hit = cobrosListadoKpisCache.get(key)
    if (!hit) return null
    if (Date.now() - hit.storedAt >= COBROS_LISTADO_KPIS_CACHE_TTL_MS) {
      return null
    }
    return cloneListadoConKpis(hit.payload)
  } catch {
    return null
  }
}

/** Cache cliente expirado pero reciente: stale-while-revalidate sin spinner en blanco. */
export function peekListadoKpisCacheStale(
  params: CobrosListadoKpisParams
): ListPagosReportadosConKpisResponse | null {
  try {
    const key = cobrosListadoKpisCacheKey(params)
    const hit = cobrosListadoKpisCache.get(key)
    if (!hit) return null
    if (Date.now() - hit.storedAt >= COBROS_LISTADO_KPIS_STALE_CLIENT_MS) {
      return null
    }
    return cloneListadoConKpis(hit.payload)
  } catch {
    return null
  }
}

/**
 * Parche quirurgico en el cache cliente (analogo al `_drop_pagos_from_listado_kpis_cache`
 * del backend): tras aprobar / rechazar / eliminar un pago reportado, en lugar de
 * limpiar TODO el cache (lo que obligaria a re-fetch + spinner al volver a la pantalla
 * principal), recorre las entries vivas y:
 *   - filtra el id del array `items` si esta presente,
 *   - decrementa `total` y `kpis[estadoPrevio]`/`kpis.total` aunque el id no este en
 *     `items` (el caso del card "Pendiente" desactualizado cuando la fila vivia en
 *     pagina >=2 del cache).
 *
 * Asi:
 *   1. La proxima carga del listado encuentra cache hit y la pantalla regresa AL
 *      INSTANTE con la fila ya filtrada y el KPI decrementado.
 *   2. El backend sigue con el cache caliente (el operador NO dispara el recompute
 *      de 20-30s) y el refresco real ocurre en background.
 *   3. Los TTL se respetan: si la entry ya vencio antes del parche, se elimina;
 *      si esta viva, conserva su storedAt original (no se rejuvenece artificialmente).
 *
 * Usar `invalidateCobrosListadoKpisCache()` solo para mutaciones que afectan a muchas
 * filas (export masivo, recibo regenerado): este parche cubre el caso 1 fila.
 */
export function patchListadoKpisCacheDropPagoReportado(
  pagoId: number,
  estadoPrevio?: string
): void {
  const now = Date.now()
  const previo = (estadoPrevio || '').trim()
  for (const [key, entry] of cobrosListadoKpisCache) {
    if (now - entry.storedAt >= COBROS_LISTADO_KPIS_CACHE_TTL_MS) {
      cobrosListadoKpisCache.delete(key)
      continue
    }
    const payload = entry.payload
    const itemIndex = payload.items.findIndex(r => r.id === pagoId)
    const wasInItems = itemIndex >= 0
    const removedEstado = wasInItems ? payload.items[itemIndex].estado : null
    const estadoParaDecrementar = removedEstado || previo
    if (!wasInItems && !estadoParaDecrementar) {
      continue
    }
    const nextItems = wasInItems
      ? payload.items.filter((_, idx) => idx !== itemIndex)
      : payload.items
    const totalActual = Number(payload.total ?? 0)
    const nextTotal = Math.max(0, totalActual - 1)
    const nextKpis = { ...(payload.kpis ?? {}) } as PagosReportadosKpis
    const totalKpiActual = Number(nextKpis.total ?? 0)
    nextKpis.total = Math.max(0, totalKpiActual - 1)
    if (estadoParaDecrementar) {
      const k = estadoParaDecrementar as keyof PagosReportadosKpis
      const v = nextKpis[k]
      if (typeof v === 'number') {
        ;(nextKpis[k] as number) = Math.max(0, v - 1)
      }
    }
    cobrosListadoKpisCache.set(key, {
      storedAt: entry.storedAt,
      payload: {
        ...payload,
        items: nextItems,
        total: nextTotal,
        kpis: nextKpis,
      },
    })
  }
}

export async function getPagosReportadosKpis(
  params: {
    fecha_desde?: string

    fecha_hasta?: string

    cedula?: string

    institucion?: string

    incluir_exportados?: boolean
  } = {},
  opts?: { timeoutMs?: number }
): Promise<PagosReportadosKpis> {
  const q = new URLSearchParams()

  if (params.fecha_desde) q.set('fecha_desde', params.fecha_desde)

  if (params.fecha_hasta) q.set('fecha_hasta', params.fecha_hasta)

  if (params.cedula) q.set('cedula', params.cedula)

  if (params.institucion) q.set('institucion', params.institucion)

  if (params.incluir_exportados) q.set('incluir_exportados', 'true')

  // Sin `_rq`: permite deduplicar GET concurrentes a `/kpis` (mismos filtros) en apiClient.

  const data = await apiClient.get<PagosReportadosKpis>(
    `${BASE_COBROS}/pagos-reportados/kpis?${q}`,
    opts?.timeoutMs != null ? { timeout: opts.timeoutMs } : undefined
  )

  return data
}

export async function listPagosReportados(
  params: {
    estado?: string

    fecha_desde?: string

    fecha_hasta?: string

    cedula?: string

    institucion?: string

    page?: number

    per_page?: number

    incluir_exportados?: boolean
  },
  opts?: { timeoutMs?: number }
): Promise<ListPagosReportadosResponse> {
  const q = new URLSearchParams()

  if (params.estado) q.set('estado', params.estado)

  if (params.fecha_desde) q.set('fecha_desde', params.fecha_desde)

  if (params.fecha_hasta) q.set('fecha_hasta', params.fecha_hasta)

  if (params.cedula) q.set('cedula', params.cedula)

  if (params.institucion) q.set('institucion', params.institucion)

  if (params.page != null) q.set('page', String(params.page))

  if (params.per_page != null) q.set('per_page', String(params.per_page))

  if (params.incluir_exportados) q.set('incluir_exportados', 'true')

  // Evita respuestas cacheadas por intermediarios desalineadas respecto a KPIs u otra pestaña.
  q.set('_rq', String(Date.now()))

  const data = await apiClient.get<ListPagosReportadosResponse>(
    `${BASE_COBROS}/pagos-reportados?${q}`,
    opts?.timeoutMs != null ? { timeout: opts.timeoutMs } : undefined
  )

  return data
}

export async function listPagosReportadosConKpis(
  params: CobrosListadoKpisParams,
  opts?: { bypassCache?: boolean }
): Promise<ListPagosReportadosConKpisResponse> {
  const q = new URLSearchParams()

  if (params.estado) q.set('estado', params.estado)

  if (params.fecha_desde) q.set('fecha_desde', params.fecha_desde)

  if (params.fecha_hasta) q.set('fecha_hasta', params.fecha_hasta)

  if (params.cedula) q.set('cedula', params.cedula)

  if (params.institucion) q.set('institucion', params.institucion)

  if (params.page != null) q.set('page', String(params.page))

  if (params.per_page != null) q.set('per_page', String(params.per_page))

  if (params.incluir_exportados) q.set('incluir_exportados', 'true')

  if (opts?.bypassCache) q.set('fresh', 'true')

  // Sin `_rq`: el listado va con Bearer y no debe cachearse en CDN; `_rq` impedía deduplicar
  // peticiones GET concurrentes idénticas en apiClient (misma pantalla / doble montaje).

  const url = `${BASE_COBROS}/pagos-reportados/listado-y-kpis?${q}`

  const cacheKey = cobrosListadoKpisCacheKey(params)

  const persist = (payload: ListPagosReportadosConKpisResponse) => {
    cobrosListadoKpisCache.set(cacheKey, {
      storedAt: Date.now(),
      payload: cloneListadoConKpis(payload),
    })
    return payload
  }

  if (!opts?.bypassCache) {
    const hit = cobrosListadoKpisCache.get(cacheKey)
    if (hit && Date.now() - hit.storedAt < COBROS_LISTADO_KPIS_CACHE_TTL_MS) {
      return cloneListadoConKpis(hit.payload)
    }
  }

  const listadoReadTimeoutMs = COBROS_LISTADO_READ_TIMEOUT_MS

  try {
    const data = await apiClient.get<ListPagosReportadosConKpisResponse>(url, {
      timeout: listadoReadTimeoutMs,
    })
    return persist(data)
  } catch (e: unknown) {
    if (!opts?.bypassCache) {
      const stale = peekListadoKpisCacheStale(params)
      if (stale) return stale
    }
    const ax = e as {
      response?: { status?: number }
      code?: string
      message?: string
    }
    const st = ax?.response?.status
    const isTimeout =
      ax?.code === 'ECONNABORTED' ||
      String(ax?.message ?? '')
        .toLowerCase()
        .includes('timeout')
    if (st === 404 || st === 405 || st === 500 || st === 503 || isTimeout) {
      const filterParams = {
        fecha_desde: params.fecha_desde,

        fecha_hasta: params.fecha_hasta,

        cedula: params.cedula,

        institucion: params.institucion,

        incluir_exportados: params.incluir_exportados,
      }

      const [lista, kpis] = await Promise.all([
        listPagosReportados(
          {
            estado: params.estado,

            ...filterParams,

            page: params.page,

            per_page: params.per_page,
          },
          { timeoutMs: listadoReadTimeoutMs }
        ),

        getPagosReportadosKpis(filterParams, {
          timeoutMs: listadoReadTimeoutMs,
        }),
      ])

      return persist({ ...lista, kpis })
    }

    throw e
  }
}

export interface PagoReportadoDetalleResponse {
  id: number

  referencia_interna: string

  nombres: string

  apellidos: string

  tipo_cedula: string

  numero_cedula: string

  fecha_pago: string

  institucion_financiera: string

  numero_operacion: string

  monto: number

  moneda: string

  /** Tasa oficial Bs por 1 USD (día fecha_pago); null si USD o sin tasa en BD. */
  tasa_cambio_bs_usd?: number | null

  /** Monto equivalente en USD (Bs÷tasa si BS; si USD es el mismo monto; null si BS sin tasa). */
  equivalente_usd?: number | null

  ruta_comprobante?: string | null

  tiene_comprobante: boolean

  tiene_recibo_pdf: boolean

  observacion?: string

  correo_enviado_a?: string

  estado: string

  motivo_rechazo?: string

  gemini_coincide_exacto?: string

  gemini_comentario?: string

  created_at: string

  updated_at: string

  historial: Array<{
    estado_anterior: string
    estado_nuevo: string
    usuario_email?: string
    motivo?: string
    created_at: string
  }>

  canal_ingreso?: string | null

  duplicado_en_pagos?: boolean

  pago_existente_id?: number | null

  prestamo_existente_id?: number | null

  pago_existente_estado?: string | null

  /** Fecha del pago ya en cartera (YYYY-MM-DD). */
  pago_existente_fecha_pago?: string | null

  prestamo_objetivo_id?: number | null

  prestamo_objetivo_multiple?: boolean | null

  prestamo_duplicado_es_objetivo?: boolean | null

  /** liquidado | sin_aprobado | cedula_no_registrada cuando no hay APROBADO objetivo. */
  prestamo_objetivo_motivo?: string | null

  /** Préstamo LIQUIDADO de referencia en BD (motivo=liquidado). */
  prestamo_referencia_id?: number | null
}

export interface PagoReportadoDuplicadoDiagnostico {
  duplicado_en_pagos: boolean
  pago_existente_id?: number | null
  prestamo_existente_id?: number | null
  pago_existente_estado?: string | null
  pago_existente_fecha_pago?: string | null
  prestamo_objetivo_id?: number | null
  prestamo_objetivo_multiple?: boolean | null
  prestamo_duplicado_es_objetivo?: boolean | null
  prestamo_objetivo_motivo?: string | null
  prestamo_referencia_id?: number | null
}

/**
 * IDs de pagos reportados eliminados muy recientemente (este tab del navegador).
 *
 * Tras un DELETE exitoso, algunas piezas del cliente disparan un GET al mismo id
 * (BFCache al volver atrás, otro componente con efecto pendiente, refetch al
 * recuperar foco, navegación residual). El backend devuelve 404 legítimo y, como
 * `apiClient.get` pone `response.data.detail` en `error.message`, los catch
 * mostraban "Pago reportado no encontrado." sobre el toast de éxito → el usuario
 * cree que el borrado falló.
 *
 * Marcamos el id durante ~60s para que `getPagoReportadoDetalle` traduzca ese 404
 * en un error "silent" (no toast). 404 legítimos por URL inválida siguen
 * mostrándose porque ese id nunca estuvo en el set.
 */
/**
 * IDs de pagos reportados que el frontend ya no debe mostrar en el listado por
 * defecto (cola por gestionar) ni en pantallas de detalle, aunque el backend
 * temporalmente devuelva la fila o un 404 fresco. Se llenan tras DELETE / aprobar
 * / rechazar exitoso y vencen tras `RECENTLY_HIDDEN_TTL_MS`. Sirven a dos cosas:
 *   1. Suprimir el toast "Pago reportado no encontrado" cuando un GET 404 llega
 *      poco despues de un DELETE (carrera BFCache / refetch en vuelo).
 *   2. Filtrar la fila del listado mientras el backend termina de propagar el
 *      cambio (cache, replica, etc.), para que el operador vea la fila
 *      desaparecer al instante en lugar de tras varios segundos de refetch.
 */
const _recentlyHiddenPagoReportadoIds = new Map<number, number>()
const RECENTLY_HIDDEN_TTL_MS = 60_000

export function markPagoReportadoRecentlyHidden(pagoId: number): void {
  _recentlyHiddenPagoReportadoIds.set(
    pagoId,
    Date.now() + RECENTLY_HIDDEN_TTL_MS
  )
  if (_recentlyHiddenPagoReportadoIds.size > 128) {
    const now = Date.now()
    for (const [k, expiresAt] of _recentlyHiddenPagoReportadoIds) {
      if (expiresAt <= now) _recentlyHiddenPagoReportadoIds.delete(k)
    }
  }
}

export function isPagoReportadoRecentlyHidden(pagoId: number): boolean {
  const expiresAt = _recentlyHiddenPagoReportadoIds.get(pagoId)
  if (expiresAt == null) return false
  if (expiresAt <= Date.now()) {
    _recentlyHiddenPagoReportadoIds.delete(pagoId)
    return false
  }
  return true
}

/**
 * Devuelve una copia inmutable del set actual de IDs ocultos vigentes.
 * Util para `Array.filter` en el listado sin perder reactividad accidental
 * (el llamador puede memoizar con `Date.now()` como key barata cada render).
 */
export function getRecentlyHiddenPagoReportadoIds(): ReadonlySet<number> {
  const now = Date.now()
  const out = new Set<number>()
  for (const [k, expiresAt] of _recentlyHiddenPagoReportadoIds) {
    if (expiresAt <= now) {
      _recentlyHiddenPagoReportadoIds.delete(k)
      continue
    }
    out.add(k)
  }
  return out
}

// Alias historicos: la API previa usaba "RecentlyDeleted"; lo mantenemos como
// thin wrapper para no romper imports/llamadas existentes y semantica de
// suppression de toast tras DELETE.
function markPagoReportadoRecentlyDeleted(pagoId: number): void {
  markPagoReportadoRecentlyHidden(pagoId)
}

function isPagoReportadoRecentlyDeleted(pagoId: number): boolean {
  return isPagoReportadoRecentlyHidden(pagoId)
}

/**
 * Construye un error "silent" que evita superponer toast "Pago reportado no
 * encontrado." sobre el toast de exito "Pago reportado eliminado.". Llamadores
 * deben revisar `e.silent` antes de mostrar toast.
 */
function makeSilentPagoReportadoEliminadoError(): Error & {
  silent: boolean
  code: string
  response?: unknown
} {
  const err = new Error('Pago reportado eliminado.') as Error & {
    silent: boolean
    code: string
    response?: unknown
  }
  err.silent = true
  err.code = 'ERR_PAGO_REPORTADO_RECIEN_ELIMINADO'
  return err
}

/**
 * Helper compartido: cualquier GET a `/pagos-reportados/{id}/*` debe respetar el
 * set `recentlyHidden`. Si el id se acaba de eliminar / aprobar / rechazar en
 * este tab, lanzar silent error UPFRONT evita la peticion HTTP fantasma (y el
 * toast "Pago reportado no encontrado." que el backend devuelve con detail).
 * Si el GET ya salio y devolvio 404, traduce el error a silent.
 */
function silentIfRecentlyHiddenPreflight(pagoId: number): void {
  if (isPagoReportadoRecentlyHidden(pagoId)) {
    throw makeSilentPagoReportadoEliminadoError()
  }
}

function getPagoReportadoErrorStatus(e: unknown): number | undefined {
  const errObj = e as
    | { code?: string; response?: { status?: number } }
    | undefined
  return (
    errObj?.response?.status ??
    (errObj?.code === 'ERR_HTTP_404' ? 404 : undefined)
  )
}

function silentIfRecentlyHidden404(pagoId: number, e: unknown): never {
  const errObj = e as
    | { code?: string; response?: { status?: number } }
    | undefined
  const status = getPagoReportadoErrorStatus(e)
  if (status === 404 && isPagoReportadoRecentlyHidden(pagoId)) {
    const silentErr = makeSilentPagoReportadoEliminadoError()
    silentErr.response = errObj?.response
    throw silentErr
  }
  throw e
}

function silentAndHideIfDetalle404(pagoId: number, e: unknown): never {
  const errObj = e as { response?: unknown } | undefined
  if (getPagoReportadoErrorStatus(e) === 404) {
    // Fila obsoleta: pudo quedar en cache local/listado tras borrado en otra
    // pestana u operador. Ocultarla evita que vuelva a salir al regresar.
    markPagoReportadoRecentlyHidden(pagoId)
    patchListadoKpisCacheDropPagoReportado(pagoId)
    const silentErr = makeSilentPagoReportadoEliminadoError()
    silentErr.response = errObj?.response
    throw silentErr
  }
  throw e
}

export async function getPagoReportadoDetalle(
  pagoId: number
): Promise<PagoReportadoDetalleResponse> {
  silentIfRecentlyHiddenPreflight(pagoId)
  try {
    const data = await apiClient.get<PagoReportadoDetalleResponse>(
      `${BASE_COBROS}/pagos-reportados/${pagoId}`
    )
    return data
  } catch (e: unknown) {
    silentAndHideIfDetalle404(pagoId, e)
  }
}

export async function diagnosticoDuplicadoPagoReportado(
  pagoId: number,
  params: {
    numero_operacion?: string
    tipo_cedula?: string
    numero_cedula?: string
  }
): Promise<PagoReportadoDuplicadoDiagnostico> {
  const q = new URLSearchParams()
  if (params.numero_operacion)
    q.set('numero_operacion', params.numero_operacion)
  if (params.tipo_cedula) q.set('tipo_cedula', params.tipo_cedula)
  if (params.numero_cedula) q.set('numero_cedula', params.numero_cedula)
  return await apiClient.get<PagoReportadoDuplicadoDiagnostico>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}/diagnostico-duplicado?${q}`
  )
}

export async function aprobarPagoReportado(
  pagoId: number
): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.post<{ ok: boolean; mensaje?: string }>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}/aprobar`
  )
  // Tras aprobar, el pago pasa a `aprobado` y deja la cola por defecto. Marcar el
  // id como oculto recientemente permite que el listado lo filtre al instante,
  // antes de que el siguiente fetch al backend lo confirme.
  markPagoReportadoRecentlyHidden(pagoId)
  return data
}

export async function rechazarPagoReportado(
  pagoId: number,
  motivo: string
): Promise<CambiarEstadoPagoResponse> {
  const data = await apiClient.post<CambiarEstadoPagoResponse>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}/rechazar`,
    { motivo }
  )
  markPagoReportadoRecentlyHidden(pagoId)
  return data
}

export interface HistoricoClienteItem {
  id: number

  referencia_interna: string

  fecha_pago: string | null

  fecha_reporte: string

  monto: number

  moneda: string

  estado: string

  tiene_recibo: boolean
}

export async function historicoPorCliente(
  cedula: string
): Promise<{ cedula: string; items: HistoricoClienteItem[] }> {
  const data = await apiClient.get<{
    cedula: string
    items: HistoricoClienteItem[]
  }>(`${BASE_COBROS}/historico-cliente?cedula=${encodeURIComponent(cedula)}`)

  return data
}

/** Descarga el binario del comprobante (imagen/PDF) con la misma auth que el resto de Cobros. */
export async function getPagoReportadoComprobanteBlob(
  pagoId: number,
  config?: Parameters<typeof apiClient.getBlob>[1]
): Promise<Blob> {
  // Preflight: si el id se acaba de eliminar / aprobar / rechazar, evitar el GET
  // 404 que el backend responderia con detail "Pago reportado no encontrado.";
  // ese detail se propaga como error.message y handlers locales lo terminan
  // mostrando como toast incluso despues del exito del DELETE.
  silentIfRecentlyHiddenPreflight(pagoId)
  const path = `${BASE_COBROS}/pagos-reportados/${pagoId}/comprobante`
  try {
    return await apiClient.getBlob(path, config)
  } catch (e: unknown) {
    silentIfRecentlyHidden404(pagoId, e)
  }
}

/** Abre el comprobante (imagen/PDF) en nueva pestaña. Usa auth del apiClient. */

export async function openComprobanteInNewTab(pagoId: number): Promise<void> {
  const data = await getPagoReportadoComprobanteBlob(pagoId)

  const url = URL.createObjectURL(data)

  window.open(url, '_blank')
}

/** Abre o descarga el recibo PDF. Usa auth del apiClient. */

export async function openReciboPdfInNewTab(pagoId: number): Promise<void> {
  silentIfRecentlyHiddenPreflight(pagoId)
  const path = `${BASE_COBROS}/pagos-reportados/${pagoId}/recibo.pdf`
  try {
    const data = await apiClient.getBlob(path)
    const url = URL.createObjectURL(data)
    window.open(url, '_blank')
  } catch (e: unknown) {
    silentIfRecentlyHidden404(pagoId, e)
  }
}

/** Env├â┬¡a por correo el recibo PDF (manual). Genera PDF si no existe. */

export async function enviarReciboManual(
  pagoId: number
): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.post<{ ok: boolean; mensaje?: string }>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}/enviar-recibo`
  )

  return data
}

/** Respuesta al cambiar estado; si es rechazo, indica si el correo al cliente se envió. */
export interface CambiarEstadoPagoResponse {
  ok: boolean
  mensaje?: string
  /** true = enviado, false = intentó y falló, undefined/null = no hubo intento (sin correo o servicio off) */
  rechazo_correo_enviado?: boolean | null
  rechazo_correo_error?: string
}

/** Cambia el estado del pago (pendiente, en_revision, aprobado, rechazado). Motivo obligatorio si rechazado. */

export async function cambiarEstadoPago(
  pagoId: number,

  estado: string,

  motivo?: string
): Promise<CambiarEstadoPagoResponse> {
  const path = `${BASE_COBROS}/pagos-reportados/${pagoId}/estado`
  // Reintentos 502/503/504: interceptor global en api.ts (PATCH .../estado + backoff).
  const data = await apiClient.patch<CambiarEstadoPagoResponse>(path, {
    estado,
    motivo,
  })
  // Si el nuevo estado deja el item fuera de la cola por defecto, marcarlo como
  // oculto para que el listado lo filtre al instante sin esperar al refetch.
  const st = (estado || '').trim()
  if (st === 'aprobado' || st === 'rechazado' || st === 'importado') {
    markPagoReportadoRecentlyHidden(pagoId)
  }
  return data
}

export async function eliminarPagoReportado(
  pagoId: number
): Promise<{ ok: boolean; mensaje?: string }> {
  try {
    const data = await apiClient.delete<{ ok: boolean; mensaje?: string }>(
      `${BASE_COBROS}/pagos-reportados/${pagoId}`
    )
    markPagoReportadoRecentlyDeleted(pagoId)
    return data
  } catch (error: unknown) {
    // Tras un 500 post-commit el reintento del ApiClient devuelve 404: idempotente.
    const status = (error as { response?: { status?: number } })?.response
      ?.status
    if (status === 404) {
      markPagoReportadoRecentlyDeleted(pagoId)
      return { ok: true, mensaje: 'Pago reportado eliminado.' }
    }
    throw error
  }
}

export interface EditarPagoReportadoPayload {
  nombres?: string

  apellidos?: string

  tipo_cedula?: string

  numero_cedula?: string

  fecha_pago?: string

  institucion_financiera?: string

  numero_operacion?: string

  monto?: number

  moneda?: string

  correo_enviado_a?: string

  observacion?: string
}

export async function updatePagoReportado(
  pagoId: number,

  payload: EditarPagoReportadoPayload
): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.patch<{ ok: boolean; mensaje?: string }>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}`,
    payload
  )

  return data
}

export async function markPagosReportadosExportados(
  pagoReportadoIds: number[]
): Promise<{
  ok: boolean
  marcados: number
  ya_exportados: number
  total_solicitados: number
  quitados_cola_temporal?: number
}> {
  const data = await apiClient.post<{
    ok: boolean
    marcados: number
    ya_exportados: number
    total_solicitados: number
    quitados_cola_temporal?: number
  }>(
    `${BASE_COBROS}/pagos-reportados/marcar-exportados`,

    { pago_reportado_ids: pagoReportadoIds }
  )

  return data
}
