import { apiClient } from './api'

export const TIMEOUT_MS_ESCANEAR_EVIDENCIAS = 180000

export type EvidenciaNotificacionItem = {
  id: number
  gmail_message_id: string
  gmail_thread_id?: string | null
  etiqueta_gmail: string
  email_cliente: string
  cedula?: string | null
  asunto?: string | null
  fecha_mensaje?: string | null
  fecha_registro?: string | null
  pdf_tamano_bytes: number
  /** chromium | xhtml2pdf | plain — fidelidad del PDF */
  pdf_motor?: string | null
  tiene_anexo: boolean
  fuente_anexo?: string | null
  procesado_por?: string | null
}

export type EvidenciaListResponse = {
  items: EvidenciaNotificacionItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  q: string
  etiqueta?: string | null
  fecha_desde?: string | null
  fecha_hasta?: string | null
}

export type ProcesarEvidenciasResponse = {
  ok: boolean
  error?: string | null
  mensaje?: string | null
  candidatos: number
  revisados: number
  guardados: number
  omitidos: number
  ya_existentes: number
  sin_correo: number
  sin_pdf: number
  etiquetados: number
  etiquetas_faltantes: string[]
  truncado: boolean
  emails_guardados?: string[]
  candidatos_por_etiqueta?: Record<string, number>
  etiqueta_escaneada?: string | null
  etiqueta_agotada?: boolean
  errores_marcados?: number
  sin_avance?: boolean
}

export type BuscarEvidenciasOpts = {
  etiqueta?: string
  fechaDesde?: string
  fechaHasta?: string
  page?: number
  pageSize?: number
}

const BASE = '/api/v1/notificaciones/evidencias'

export const evidenciasNotificacionService = {
  async escanear(
    etiqueta: string,
    maxMessages = 40
  ): Promise<ProcesarEvidenciasResponse> {
    const params = new URLSearchParams({
      etiqueta,
      max_messages: String(maxMessages),
    })
    return apiClient.post<ProcesarEvidenciasResponse>(
      `${BASE}/escanear?${params.toString()}`,
      {},
      { timeout: TIMEOUT_MS_ESCANEAR_EVIDENCIAS }
    )
  },

  async buscar(
    q: string,
    opts: BuscarEvidenciasOpts = {}
  ): Promise<EvidenciaListResponse> {
    const params = new URLSearchParams({
      q: q.trim(),
      page: String(opts.page ?? 1),
      page_size: String(opts.pageSize ?? 25),
    })
    if (opts.etiqueta) params.set('etiqueta', opts.etiqueta)
    if (opts.fechaDesde) params.set('fecha_desde', opts.fechaDesde)
    if (opts.fechaHasta) params.set('fecha_hasta', opts.fechaHasta)
    return apiClient.get<EvidenciaListResponse>(`${BASE}?${params.toString()}`)
  },

  async descargarPdf(id: number, filenameHint?: string): Promise<void> {
    const stamp = new Date().toISOString().slice(0, 10)
    const name = filenameHint || `evidencia_${id}_${stamp}.pdf`
    await apiClient.downloadFile(
      `${BASE}/${id}/pdf?disposition=attachment`,
      name
    )
  },

  /** Blob del PDF para vista previa / imprimir en la app (inline). */
  async obtenerPdfBlob(id: number): Promise<Blob> {
    return apiClient.getBlob(`${BASE}/${id}/pdf?disposition=inline`)
  },

  async regenerarPdf(id: number): Promise<EvidenciaNotificacionItem> {
    return apiClient.post<EvidenciaNotificacionItem>(
      `${BASE}/${id}/regenerar-pdf`,
      {},
      { timeout: TIMEOUT_MS_ESCANEAR_EVIDENCIAS }
    )
  },

  async eliminarSeleccionados(
    ids: number[]
  ): Promise<{ ok: boolean; deleted: number; gmail_reabiertos?: number; gmail_errores?: number }> {
    return apiClient.post<{
      ok: boolean
      deleted: number
      gmail_reabiertos?: number
      gmail_errores?: number
    }>(
      `${BASE}/eliminar-seleccionados`,
      { ids }
    )
  },
}
