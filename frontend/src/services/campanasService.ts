import { apiClient, buildUrl } from './api'

const BASE = '/api/v1/crm/campanas'

export interface CampanaCrm {
  id: number
  nombre: string
  asunto: string
  cuerpo_texto: string
  cuerpo_html: string | null
  estado: string
  total_destinatarios: number
  enviados: number
  fallidos: number
  batch_size: number
  delay_entre_batches_seg: number
  cc_emails: string | null
  tiene_adjunto: boolean
  destinatarios_modo: string
  fecha_creacion: string | null
  fecha_actualizacion: string | null
  fecha_envio_inicio: string | null
  fecha_envio_fin: string | null
  usuario_creacion: string | null
}

export interface CampanaCreate {
  nombre: string
  asunto: string
  cuerpo_texto?: string
  cuerpo_html?: string | null
  batch_size?: number
  delay_entre_batches_seg?: number
  cc_emails?: string[] | null
  destinatarios_cliente_ids?: number[] | null
}

export interface DestinatarioPreview {
  email: string
  cliente_id: number | null
  nombres: string | null
}

export interface ListCampanasResponse {
  items: CampanaCrm[]
  paginacion: { page: number; per_page: number; total: number; pages: number }
}

export const campanasService = {
  async list(params?: { page?: number; per_page?: number; estado?: string }): Promise<ListCampanasResponse> {
    const url = buildUrl(BASE, params)
    return await apiClient.get<ListCampanasResponse>(url)
  },

  async get(id: number): Promise<CampanaCrm> {
    return await apiClient.get<CampanaCrm>(`${BASE}/${id}`)
  },

  async previewDestinatarios(limit = 50): Promise<{ total: number; muestra: DestinatarioPreview[] }> {
    return await apiClient.get<{ total: number; muestra: DestinatarioPreview[] }>(
      `${BASE}/preview-destinatarios`,
      { params: { limit } }
    )
  },

  async create(payload: CampanaCreate): Promise<CampanaCrm> {
    return await apiClient.post<CampanaCrm>(BASE, payload)
  },

  async iniciarEnvio(id: number): Promise<{ success: boolean; mensaje: string; total_destinatarios: number }> {
    return await apiClient.post<{ success: boolean; mensaje: string; total_destinatarios: number }>(
      `${BASE}/${id}/iniciar-envio`
    )
  },

  async getPreviewHtml(id: number): Promise<string> {
    return await apiClient.get<string>(`${BASE}/${id}/preview-html`, {
      responseType: 'text',
    })
  },

    previewHtmlUrl(id: number): string {
    const base = (import.meta.env.VITE_API_URL || '') || ''
    return `${base}${BASE}/${id}/preview-html`
  },
}
