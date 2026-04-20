/**









 * Servicio del modulo Cobros.









 * - Publico: validar cedula, enviar reporte (sin auth).









 * - Admin: listado, detalle, aprobar, rechazar, exportar Excel (con auth).









 */

import axios from 'axios'

import { apiClient } from './api'

import { env } from '../config/env'

const API = env.API_URL || ''

const BASE_PUBLIC = `${API}/api/v1/cobros/public`

const BASE_COBROS = `${API}/api/v1/cobros`

/** Timeout (ms) para peticiones públicas. Sin timeout pueden quedar colgadas. */
const FETCH_TIMEOUT_MS = 30000

/**
 * Traduce fallos de red del navegador (no vienen del JSON del API).
 * Texto corto para móvil; en desarrollo se añade una pista técnica en consola.
 */
function mensajeErrorRedPublico(msg: string): string {
  const m = (msg || '').trim()
  if (/timeout|abort/i.test(m) || /30\s*s/i.test(m)) {
    return 'El servidor tardó demasiado. Intente de nuevo en unos segundos.'
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
  options?: RequestInit
): Promise<Response> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    return res
  } catch (err: unknown) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error(
        `Timeout después de ${FETCH_TIMEOUT_MS / 1000}s. El servidor no responde.`
      )
    }
    throw err
  } finally {
    clearTimeout(timeout)
  }
}

export interface ValidarCedulaResponse {
  ok: boolean

  nombre?: string

  /** Correo completo para que el cliente lo compruebe (no enmascarado). */

  email?: string

  email_enmascarado?: string

  error?: string

  /** True si esta cedula puede reportar pagos en Bolivares (Bs) en cobros/infopagos. */

  puede_reportar_bs?: boolean
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
    const res = await fetchWithTimeout(url, {
      credentials: 'same-origin',

      headers,
    })

    if (res.status === 429) {
      return {
        ok: false,
        error: 'Demasiadas consultas. Espere un minuto e intente de nuevo.',
      }
    }

    return res.json().catch(() => ({
      ok: false,
      error: 'Error al procesar respuesta del servidor.',
    }))
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
    const res = await fetchWithTimeout(url, {
      method: 'POST',

      credentials: 'same-origin',

      headers: { 'Content-Type': 'application/json' },

      body: JSON.stringify(body),
    })

    if (res.status === 429) {
      return {
        ok: false,

        error:
          'Demasiadas solicitudes de codigo. Intente de nuevo en una hora.',
      }
    }

    return res.json().catch(() => ({
      ok: false,

      error: 'Error al procesar respuesta del servidor.',
    }))
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
    const res = await fetchWithTimeout(url, {
      method: 'POST',

      credentials: 'same-origin',

      headers: { 'Content-Type': 'application/json' },

      body: JSON.stringify(body),
    })

    if (res.status === 429) {
      return {
        ok: false,

        error: 'Demasiados intentos. Espere unos minutos e intente de nuevo.',
      }
    }

    return res.json().catch(() => ({
      ok: false,

      error: 'Error al procesar respuesta del servidor.',
    }))
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

  try {
    const res = await fetchWithTimeout(url, {
      method: 'POST',

      body: formData,

      credentials: 'same-origin',

      headers,

      // No Content-Type: el navegador fija multipart boundary
    })

    if (res.status === 429) {
      return {
        ok: false,
        error: 'Ha alcanzado el límite de envíos por hora. Intente más tarde.',
      }
    }

    if (res.status === 503) {
      return {
        ok: false,

        error:
          'Servicio temporalmente no disponible. Intente más tarde o contacte por WhatsApp 424-4579934.',
      }
    }

    // Leer el body una sola vez (evita "body stream already read" si el servidor devuelve 500/HTML)

    const text = await res.text()

    let data: EnviarReporteResponse

    try {
      data = text ? JSON.parse(text) : {}
    } catch {
      return {
        ok: false,

        error: (
          text ||
          `Error ${res.status}. Intente más tarde o contacte por WhatsApp 424-4579934.`
        ).slice(0, 200),
      }
    }

    if (!res.ok && data && typeof data === 'object') {
      return {
        ok: false,
        error:
          (data as EnviarReporteResponse).error ||
          `Error ${res.status}. Intente más tarde o contacte por WhatsApp 424-4579934.`,
      }
    }

    return data
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
  const url = `${BASE_PUBLIC}/infopagos/enviar-reporte`

  try {
    const res = await fetchWithTimeout(url, {
      method: 'POST',

      body: formData,

      credentials: 'same-origin',
    })

    if (res.status === 429) {
      return {
        ok: false,
        error: 'Ha alcanzado el límite de envíos por hora. Intente más tarde.',
      }
    }

    if (res.status === 503) {
      return {
        ok: false,
        error:
          'Servicio temporalmente no disponible. Intente más tarde o contacte por WhatsApp 424-4579934.',
      }
    }

    if (res.status === 502) {
      return {
        ok: false,
        error:
          'El servidor intermedio no pudo contactar al API. Intente de nuevo en un momento.',
      }
    }

    const text = await res.text()

    let data: EnviarReporteInfopagosResponse

    try {
      data = text ? JSON.parse(text) : {}
    } catch {
      return {
        ok: false,

        error: (text || `Error ${res.status}. Intente más tarde.`).slice(
          0,
          200
        ),
      }
    }

    if (!res.ok && data && typeof data === 'object') {
      return {
        ok: false,
        error:
          (data as EnviarReporteInfopagosResponse).error ||
          `Error ${res.status}.`,
      }
    }

    return data
  } catch (e: unknown) {
    const raw =
      e instanceof Error ? e.message : 'Error de conexión con el servidor.'
    return { ok: false, error: mensajeErrorRedPublico(raw) }
  }
}

/** Infopagos: descargar recibo PDF con el token devuelto tras registrar el pago. */

export async function getReciboInfopagos(
  token: string,
  pagoId: number
): Promise<Blob> {
  const url = `${BASE_PUBLIC}/infopagos/recibo?token=${encodeURIComponent(token)}&pago_id=${pagoId}`

  try {
    const res = await fetchWithTimeout(url, { credentials: 'same-origin' })

    if (!res.ok)
      throw new Error(
        res.status === 401
          ? 'Enlace de descarga expirado.'
          : 'No se pudo descargar el recibo.'
      )

    return res.blob()
  } catch (e: unknown) {
    const raw =
      e instanceof Error
        ? e.message
        : 'Error de conexión al descargar el recibo.'
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

  aprobado: number

  rechazado: number

  /** Presente en respuesta API (agrupacion por estado) */

  importado?: number

  total: number
}

/** Una sola peticion: listado + KPIs (mismos criterios que GET pagos-reportados + /kpis). */

export interface ListPagosReportadosConKpisResponse extends ListPagosReportadosResponse {
  kpis: PagosReportadosKpis
}

export async function getPagosReportadosKpis(
  params: {
    fecha_desde?: string

    fecha_hasta?: string

    cedula?: string

    institucion?: string

    incluir_exportados?: boolean
  } = {}
): Promise<PagosReportadosKpis> {
  const q = new URLSearchParams()

  if (params.fecha_desde) q.set('fecha_desde', params.fecha_desde)

  if (params.fecha_hasta) q.set('fecha_hasta', params.fecha_hasta)

  if (params.cedula) q.set('cedula', params.cedula)

  if (params.institucion) q.set('institucion', params.institucion)

  if (params.incluir_exportados) q.set('incluir_exportados', 'true')

  const data = await apiClient.get<PagosReportadosKpis>(
    `${BASE_COBROS}/pagos-reportados/kpis?${q}`
  )

  return data
}

export interface TendenciaFalloGeminiPunto {
  fecha: string

  fallos_no: number

  verificados_gemini: number

  pct_fallo: number | null
}

export interface TendenciaFallosGeminiResponse {
  puntos: TendenciaFalloGeminiPunto[]

  fecha_desde: string

  fecha_hasta: string

  dias: number

  zona: string

  nota: string
}

export async function getTendenciaFallosGemini(
  dias?: number
): Promise<TendenciaFallosGeminiResponse> {
  const q = new URLSearchParams()

  if (dias != null) q.set('dias', String(dias))

  const qs = q.toString()

  return apiClient.get<TendenciaFallosGeminiResponse>(
    `${BASE_COBROS}/pagos-reportados/tendencia-fallos-gemini${qs ? `?${qs}` : ''}`
  )
}

export async function listPagosReportados(params: {
  estado?: string

  fecha_desde?: string

  fecha_hasta?: string

  cedula?: string

  institucion?: string

  page?: number

  per_page?: number

  incluir_exportados?: boolean
}): Promise<ListPagosReportadosResponse> {
  const q = new URLSearchParams()

  if (params.estado) q.set('estado', params.estado)

  if (params.fecha_desde) q.set('fecha_desde', params.fecha_desde)

  if (params.fecha_hasta) q.set('fecha_hasta', params.fecha_hasta)

  if (params.cedula) q.set('cedula', params.cedula)

  if (params.institucion) q.set('institucion', params.institucion)

  if (params.page != null) q.set('page', String(params.page))

  if (params.per_page != null) q.set('per_page', String(params.per_page))

  if (params.incluir_exportados) q.set('incluir_exportados', 'true')

  const data = await apiClient.get<ListPagosReportadosResponse>(
    `${BASE_COBROS}/pagos-reportados?${q}`
  )

  return data
}

export async function listPagosReportadosConKpis(params: {
  estado?: string

  fecha_desde?: string

  fecha_hasta?: string

  cedula?: string

  institucion?: string

  page?: number

  per_page?: number

  incluir_exportados?: boolean
}): Promise<ListPagosReportadosConKpisResponse> {
  const q = new URLSearchParams()

  if (params.estado) q.set('estado', params.estado)

  if (params.fecha_desde) q.set('fecha_desde', params.fecha_desde)

  if (params.fecha_hasta) q.set('fecha_hasta', params.fecha_hasta)

  if (params.cedula) q.set('cedula', params.cedula)

  if (params.institucion) q.set('institucion', params.institucion)

  if (params.page != null) q.set('page', String(params.page))

  if (params.per_page != null) q.set('per_page', String(params.per_page))

  if (params.incluir_exportados) q.set('incluir_exportados', 'true')

  const url = `${BASE_COBROS}/pagos-reportados/listado-y-kpis?${q}`

  try {
    return await apiClient.get<ListPagosReportadosConKpisResponse>(url)
  } catch (e: unknown) {
    const st = (e as { response?: { status?: number } })?.response?.status
    if (st === 404 || st === 405) {
      const filterParams = {
        fecha_desde: params.fecha_desde,

        fecha_hasta: params.fecha_hasta,

        cedula: params.cedula,

        institucion: params.institucion,

        incluir_exportados: params.incluir_exportados,
      }

      const [lista, kpis] = await Promise.all([
        listPagosReportados({
          estado: params.estado,

          ...filterParams,

          page: params.page,

          per_page: params.per_page,
        }),

        getPagosReportadosKpis(filterParams),
      ])

      return { ...lista, kpis }
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
}

export async function getPagoReportadoDetalle(
  pagoId: number
): Promise<PagoReportadoDetalleResponse> {
  const data = await apiClient.get<PagoReportadoDetalleResponse>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}`
  )

  return data
}

export async function aprobarPagoReportado(
  pagoId: number
): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.post<{ ok: boolean; mensaje?: string }>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}/aprobar`
  )

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

/** Abre el comprobante (imagen/PDF) en nueva pesta├â┬▒a. Usa auth del apiClient. */

export async function openComprobanteInNewTab(pagoId: number): Promise<void> {
  const path = `${BASE_COBROS}/pagos-reportados/${pagoId}/comprobante`
  const data = await apiClient.getBlob(path)

  const url = URL.createObjectURL(data)

  window.open(url, '_blank')
}

/** Abre o descarga el recibo PDF. Usa auth del apiClient. */

export async function openReciboPdfInNewTab(pagoId: number): Promise<void> {
  const path = `${BASE_COBROS}/pagos-reportados/${pagoId}/recibo.pdf`
  const data = await apiClient.getBlob(path)

  const url = URL.createObjectURL(data)

  window.open(url, '_blank')
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
  const data = await apiClient.patch<CambiarEstadoPagoResponse>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}/estado`,
    { estado, motivo }
  )

  return data
}

export async function eliminarPagoReportado(
  pagoId: number
): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.delete<{ ok: boolean; mensaje?: string }>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}`
  )

  return data
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

/**
 * Excel de reportes que no cumplen validadores (pendiente/en revisión con observación o Gemini NO/error),
 * aún no exportados. Misma transacción: marca exportados y limpia cola temporal (atómico).
 */
export async function exportarPagosReportadosAprobadosExcel(opts: {
  cedula?: string

  institucion?: string
}): Promise<{
  marcados: number

  yaExportados: number

  quitadosCola: number

  totalFilas: number
}> {
  const q = new URLSearchParams()

  if (opts.cedula?.trim()) q.set('cedula', opts.cedula.trim())

  if (opts.institucion?.trim()) q.set('institucion', opts.institucion.trim())

  const qs = q.toString()
  const url =
    `${BASE_COBROS}/pagos-reportados/exportar-aprobados-excel` +
    (qs ? `?${qs}` : '')

  try {
    const response = await apiClient.getAxiosInstance().get<ArrayBuffer>(url, {
      responseType: 'arraybuffer',
      validateStatus: status => status === 200,
    })

    const raw = new Uint8Array(response.data)

    if (!_esContenidoXlsxValido(raw)) {
      const head = new TextDecoder().decode(raw.slice(0, 800))
      let msg =
        'El archivo no es un Excel válido. Revise VITE_API_URL y la sesión.'

      try {
        const j = JSON.parse(head) as { detail?: string; message?: string }

        if (j.detail || j.message) msg = String(j.detail || j.message)
      } catch {
        /* mantener msg */
      }

      throw new Error(msg)
    }

    const hm = response.headers as Record<string, string | undefined>

    const stats = {
      marcados: Number(hm['x-export-marcados'] ?? 0),
      yaExportados: Number(hm['x-export-ya-exportados'] ?? 0),
      quitadosCola: Number(hm['x-export-quitados-cola'] ?? 0),
      totalFilas: Number(hm['x-export-total-filas'] ?? 0),
    }

    const blob = new Blob([raw], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })

    const cd = hm['content-disposition']
    let name = 'pagos_reportados_falla_validadores.xlsx'

    if (cd) {
      const m = /filename\*?=(?:UTF-8'')?["']?([^"';]+)/i.exec(cd)

      if (m?.[1]) name = decodeURIComponent(m[1].trim())
    }

    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(objectUrl)

    return stats
  } catch (err: unknown) {
    if (axios.isAxiosError(err)) {
      const st = err.response?.status
      const data = err.response?.data as ArrayBuffer | undefined

      if (st === 401 || st === 403) {
        throw new Error(
          'Sesión expirada o sin permiso. Vuelva a iniciar sesión.'
        )
      }

      if (data instanceof ArrayBuffer && data.byteLength > 0) {
        const text = new TextDecoder()
          .decode(new Uint8Array(data).slice(0, 2000))
          .trim()

        if (text.startsWith('{')) {
          try {
            const j = JSON.parse(text) as { detail?: string }

            if (typeof j.detail === 'string') throw new Error(j.detail)
          } catch (e) {
            if (!(e instanceof SyntaxError)) throw e
          }
        }
      }

      throw new Error(
        err.response?.statusText || err.message || 'Error exportando Excel'
      )
    }

    if (err instanceof Error) throw err

    throw new Error('Error exportando Excel')
  }
}

/** Los .xlsx son ZIP; deben empezar por PK (evita guardar HTML/JSON como .xlsx corrupto). */

function _esContenidoXlsxValido(buf: Uint8Array): boolean {
  return (
    buf.length >= 4 &&
    buf[0] === 0x50 &&
    buf[1] === 0x4b &&
    (buf[2] === 0x03 || buf[2] === 0x05 || buf[2] === 0x07) &&
    (buf[3] === 0x04 || buf[3] === 0x06 || buf[3] === 0x08)
  )
}

