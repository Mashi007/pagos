/**









 * Servicio para el m├â┬│dulo Cobros.









 * - P├â┬║blico: validar c├â┬⌐dula, enviar reporte (sin auth).









 * - Admin: listado, detalle, aprobar, rechazar, hist├â┬│rico (con auth).









 */

import { apiClient } from './api'

import { env } from '../config/env'

const API = env.API_URL || ''

const BASE_PUBLIC = `${API}/api/v1/cobros/public`

const BASE_COBROS = `${API}/api/v1/cobros`

export interface ValidarCedulaResponse {
  ok: boolean

  nombre?: string

  /** Correo completo para que el cliente lo compruebe (no enmascarado). */

  email?: string

  email_enmascarado?: string

  error?: string

  /** True si esta c├â┬⌐dula puede reportar pagos en Bol├â┬¡vares (Bs) en cobros/infopagos. */

  puede_reportar_bs?: boolean
}

export interface EnviarReporteResponse {
  ok: boolean

  referencia_interna?: string

  mensaje?: string

  error?: string
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
}

/** P├â┬║blico: validar c├â┬⌐dula (formato + tiene pr├â┬⌐stamo). Sin auth. Sin env├â┬¡o de token. */

export async function validarCedulaPublico(
  cedula: string,

  opts?: { origen?: string }
): Promise<ValidarCedulaResponse> {
  const o = (opts?.origen || '').trim()

  const q = new URLSearchParams({ cedula: cedula.slice(0, 20) })

  if (o) q.set('origen', o)

  const url = `${BASE_PUBLIC}/validar-cedula?${q.toString()}`

  const res = await fetch(url, { credentials: 'same-origin' })

  if (res.status === 429) {
    return {
      ok: false,
      error: 'Demasiadas consultas. Espere un minuto e intente de nuevo.',
    }
  }

  return res.json()
}

/** P├â┬║blico: enviar reporte de pago (multipart). Sin auth. Sin env├â┬¡o de token. */

export async function enviarReportePublico(
  formData: FormData
): Promise<EnviarReporteResponse> {
  const url = `${BASE_PUBLIC}/enviar-reporte`

  const res = await fetch(url, {
    method: 'POST',

    body: formData,

    credentials: 'same-origin',

    // No Content-Type: el navegador fija multipart boundary
  })

  if (res.status === 429) {
    return {
      ok: false,
      error:
        'Ha alcanzado el l├â┬¡mite de env├â┬¡os por hora. Intente m├â┬ís tarde.',
    }
  }

  if (res.status === 503) {
    return {
      ok: false,

      error:
        'Servicio temporalmente no disponible. Intente m├â┬ís tarde o contacte por WhatsApp 424-4579934.',
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
        `Error ${res.status}. Intente m├â┬ís tarde o contacte por WhatsApp 424-4579934.`
      ).slice(0, 200),
    }
  }

  if (!res.ok && data && typeof data === 'object') {
    return {
      ok: false,
      error:
        (data as EnviarReporteResponse).error ||
        `Error ${res.status}. Intente m├â┬ís tarde o contacte por WhatsApp 424-4579934.`,
    }
  }

  return data
}

/** Infopagos: enviar reporte a nombre del deudor (uso interno). Devuelve token para descargar recibo. */

export async function enviarReporteInfopagos(
  formData: FormData
): Promise<EnviarReporteInfopagosResponse> {
  const url = `${BASE_PUBLIC}/infopagos/enviar-reporte`

  const res = await fetch(url, {
    method: 'POST',

    body: formData,

    credentials: 'same-origin',
  })

  if (res.status === 429) {
    return {
      ok: false,
      error:
        'Ha alcanzado el l├â┬¡mite de env├â┬¡os por hora. Intente m├â┬ís tarde.',
    }
  }

  const text = await res.text()

  let data: EnviarReporteInfopagosResponse

  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    return {
      ok: false,

      error: (text || `Error ${res.status}. Intente m├â┬ís tarde.`).slice(
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
}

/** Infopagos: descargar recibo PDF con el token devuelto tras registrar el pago. */

export async function getReciboInfopagos(
  token: string,
  pagoId: number
): Promise<Blob> {
  const url = `${BASE_PUBLIC}/infopagos/recibo?token=${encodeURIComponent(token)}&pago_id=${pagoId}`

  const res = await fetch(url, { credentials: 'same-origin' })

  if (!res.ok)
    throw new Error(
      res.status === 401
        ? 'Enlace de descarga expirado.'
        : 'No se pudo descargar el recibo.'
    )

  return res.blob()
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

  total: number
}

export async function getPagosReportadosKpis(
  params: {
    fecha_desde?: string

    fecha_hasta?: string

    cedula?: string

    institucion?: string
  } = {}
): Promise<PagosReportadosKpis> {
  const q = new URLSearchParams()

  if (params.fecha_desde) q.set('fecha_desde', params.fecha_desde)

  if (params.fecha_hasta) q.set('fecha_hasta', params.fecha_hasta)

  if (params.cedula) q.set('cedula', params.cedula)

  if (params.institucion) q.set('institucion', params.institucion)

  const data = await apiClient.get<PagosReportadosKpis>(
    `${BASE_COBROS}/pagos-reportados/kpis?${q}`
  )

  return data
}

export async function listPagosReportados(params: {
  estado?: string

  fecha_desde?: string

  fecha_hasta?: string

  cedula?: string

  institucion?: string

  page?: number

  per_page?: number
}): Promise<ListPagosReportadosResponse> {
  const q = new URLSearchParams()

  if (params.estado) q.set('estado', params.estado)

  if (params.fecha_desde) q.set('fecha_desde', params.fecha_desde)

  if (params.fecha_hasta) q.set('fecha_hasta', params.fecha_hasta)

  if (params.cedula) q.set('cedula', params.cedula)

  if (params.institucion) q.set('institucion', params.institucion)

  if (params.page != null) q.set('page', String(params.page))

  if (params.per_page != null) q.set('per_page', String(params.per_page))

  const data = await apiClient.get<ListPagosReportadosResponse>(
    `${BASE_COBROS}/pagos-reportados?${q}`
  )

  return data
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
): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.post<{ ok: boolean; mensaje?: string }>(
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
  const data = await apiClient.get<Blob>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}/comprobante`,
    { responseType: 'blob' }
  )

  const url = URL.createObjectURL(data)

  window.open(url, '_blank')
}

/** Abre o descarga el recibo PDF. Usa auth del apiClient. */

export async function openReciboPdfInNewTab(pagoId: number): Promise<void> {
  const data = await apiClient.get<Blob>(
    `${BASE_COBROS}/pagos-reportados/${pagoId}/recibo.pdf`,
    { responseType: 'blob' }
  )

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

/** Cambia el estado del pago (pendiente, en_revision, aprobado, rechazado). Motivo obligatorio si rechazado. */

export async function cambiarEstadoPago(
  pagoId: number,

  estado: string,

  motivo?: string
): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.patch<{ ok: boolean; mensaje?: string }>(
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
}> {
  const data = await apiClient.post<{
    ok: boolean
    marcados: number
    ya_exportados: number
    total_solicitados: number
  }>(
    `${BASE_COBROS}/pagos-reportados/marcar-exportados`,

    { pago_reportado_ids: pagoReportadoIds }
  )

  return data
}

export async function descargarPagosAprobadosExcel(): Promise<void> {
  const url = `${BASE_COBROS}/descargar-pagos-aprobados-excel`
  const token =
    typeof localStorage !== 'undefined'
      ? localStorage.getItem('access_token')
      : null
  const response = await fetch(url, {
    method: 'GET',
    credentials: 'same-origin',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || 'Error descargando Excel')
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = 'pagos_aprobados_.xlsx'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}
