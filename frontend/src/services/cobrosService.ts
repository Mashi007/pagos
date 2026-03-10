/**
 * Servicio para el módulo Cobros.
 * - Público: validar cédula, enviar reporte (sin auth).
 * - Admin: listado, detalle, aprobar, rechazar, histórico (con auth).
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
}

export interface EnviarReporteResponse {
  ok: boolean
  referencia_interna?: string
  mensaje?: string
  error?: string
}

/** Público: validar cédula (formato + tiene préstamo). Sin auth. Sin envío de token. */
export async function validarCedulaPublico(cedula: string): Promise<ValidarCedulaResponse> {
  const url = `${BASE_PUBLIC}/validar-cedula?cedula=${encodeURIComponent(cedula.slice(0, 20))}`
  const res = await fetch(url, { credentials: 'same-origin' })
  if (res.status === 429) {
    return { ok: false, error: 'Demasiadas consultas. Espere un minuto e intente de nuevo.' }
  }
  return res.json()
}

/** Público: enviar reporte de pago (multipart). Sin auth. Sin envío de token. */
export async function enviarReportePublico(formData: FormData): Promise<EnviarReporteResponse> {
  const url = `${BASE_PUBLIC}/enviar-reporte`
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
    credentials: 'same-origin',
    // No Content-Type: el navegador fija multipart boundary
  })
  if (res.status === 429) {
    return { ok: false, error: 'Ha alcanzado el límite de envíos por hora. Intente más tarde.' }
  }
  if (res.status === 503) {
    return {
      ok: false,
      error: 'Servicio temporalmente no disponible. Intente más tarde o contacte por WhatsApp 424-4579934.',
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
      error: (text || `Error ${res.status}. Intente más tarde o contacte por WhatsApp 424-4579934.`).slice(0, 200),
    }
  }
  if (!res.ok && data && typeof data === 'object') {
    return { ok: false, error: (data as EnviarReporteResponse).error || `Error ${res.status}. Intente más tarde o contacte por WhatsApp 424-4579934.` }
  }
  return data
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
}

export interface ListPagosReportadosResponse {
  items: PagoReportadoItem[]
  total: number
  page: number
  per_page: number
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
  const data = await apiClient.get<ListPagosReportadosResponse>(`${BASE_COBROS}/pagos-reportados?${q}`)
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
  historial: Array<{ estado_anterior: string; estado_nuevo: string; usuario_email?: string; motivo?: string; created_at: string }>
}

export async function getPagoReportadoDetalle(pagoId: number): Promise<PagoReportadoDetalleResponse> {
  const data = await apiClient.get<PagoReportadoDetalleResponse>(`${BASE_COBROS}/pagos-reportados/${pagoId}`)
  return data
}

export async function aprobarPagoReportado(pagoId: number): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.post<{ ok: boolean; mensaje?: string }>(`${BASE_COBROS}/pagos-reportados/${pagoId}/aprobar`)
  return data
}

export async function rechazarPagoReportado(pagoId: number, motivo: string): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.post<{ ok: boolean; mensaje?: string }>(`${BASE_COBROS}/pagos-reportados/${pagoId}/rechazar`, { motivo })
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

export async function historicoPorCliente(cedula: string): Promise<{ cedula: string; items: HistoricoClienteItem[] }> {
  const data = await apiClient.get<{ cedula: string; items: HistoricoClienteItem[] }>(`${BASE_COBROS}/historico-cliente?cedula=${encodeURIComponent(cedula)}`)
  return data
}

/** Abre el comprobante (imagen/PDF) en nueva pestaña. Usa auth del apiClient. */
export async function openComprobanteInNewTab(pagoId: number): Promise<void> {
  const data = await apiClient.get<Blob>(`${BASE_COBROS}/pagos-reportados/${pagoId}/comprobante`, { responseType: 'blob' })
  const url = URL.createObjectURL(data)
  window.open(url, '_blank')
}

/** Abre o descarga el recibo PDF. Usa auth del apiClient. */
export async function openReciboPdfInNewTab(pagoId: number): Promise<void> {
  const data = await apiClient.get<Blob>(`${BASE_COBROS}/pagos-reportados/${pagoId}/recibo.pdf`, { responseType: 'blob' })
  const url = URL.createObjectURL(data)
  window.open(url, '_blank')
}

/** Envía por correo el recibo PDF (manual). Genera PDF si no existe. */
export async function enviarReciboManual(pagoId: number): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.post<{ ok: boolean; mensaje?: string }>(`${BASE_COBROS}/pagos-reportados/${pagoId}/enviar-recibo`)
  return data
}

/** Cambia el estado del pago (pendiente, en_revision, aprobado, rechazado). Motivo obligatorio si rechazado. */
export async function cambiarEstadoPago(
  pagoId: number,
  estado: string,
  motivo?: string
): Promise<{ ok: boolean; mensaje?: string }> {
  const data = await apiClient.patch<{ ok: boolean; mensaje?: string }>(`${BASE_COBROS}/pagos-reportados/${pagoId}/estado`, { estado, motivo })
  return data
}
