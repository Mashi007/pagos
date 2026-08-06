import { apiClient } from './api'

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
  etiquetas_faltantes: string[]
  truncado: boolean
}

const BASE = '/notificaciones/evidencias'

export const evidenciasNotificacionService = {
  async escanear(maxMessages = 40): Promise<ProcesarEvidenciasResponse> {
    return apiClient.post<ProcesarEvidenciasResponse>(
      `${BASE}/escanear?max_messages=${maxMessages}`,
      {}
    )
  },

  async buscar(q: string, page = 1, pageSize = 50): Promise<EvidenciaListResponse> {
    const params = new URLSearchParams({
      q: q.trim(),
      page: String(page),
      page_size: String(pageSize),
    })
    return apiClient.get<EvidenciaListResponse>(`${BASE}?${params.toString()}`)
  },

  async descargarPdf(id: number, filenameHint?: string): Promise<void> {
    const stamp = new Date().toISOString().slice(0, 10)
    const name = filenameHint || `evidencia_${id}_${stamp}.pdf`
    await apiClient.downloadFile(`${BASE}/${id}/pdf`, name)
  },
}
