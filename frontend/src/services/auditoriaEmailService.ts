import { apiClient } from './api'

export type AuditoriaEmailCriteria = {
  preset?: string
  dateFrom?: string
  dateTo?: string
  newerThanDays?: number
  subject?: string
  subjectMode?: 'contains' | 'exact' | 'any_word'
  subjectExclude?: string
  from?: string
  excludeFrom?: string
  attachments?:
    | 'none'
    | 'any'
    | 'receipt_strong'
    | 'pdf_or_image'
    | 'pdf_only'
    | 'image_only'
    | ''
  attachmentMinKb?: number
  filenamePattern?: string
}

export type AuditoriaEmailScan = {
  id: number
  mode: string
  status: string
  source: string
  criteria: AuditoriaEmailCriteria
  pipelineIds: string[]
  lotSize: number
  maxMessages: number
  gmailQuery?: string | null
  pageToken?: string | null
  processedTotal: number
  listedTotal: number
  rejectedTotal: number
  lotsDone: number
  lastError?: string | null
  createdBy?: string | null
  createdAt?: string | null
  updatedAt?: string | null
  finishedAt?: string | null
  paused?: boolean
}

const base = '/api/v1/auditoria/email'

export const auditoriaEmailService = {
  status() {
    return apiClient.get<Record<string, unknown>>(`${base}/status`)
  },
  oauthAuthorize() {
    return apiClient.get<{
      redirect_url: string
      mailbox: string
      redirect_uri: string
    }>(`${base}/oauth/authorize`)
  },
  oauthRedirectUri() {
    return apiClient.get<{ redirect_uri: string }>(`${base}/oauth/redirect-uri`)
  },
  kpis() {
    return apiClient.get<{
      mensajes: number
      recibos: number
      por_ruta: Record<string, number>
      por_clase: Record<string, number>
      escaneos_pausados: number
      mailbox: string
      label_analizados?: string
      gmail_connected?: boolean
    }>(`${base}/kpis`)
  },
  pipelines() {
    return apiClient.get<{
      items: Array<{ id: string; nombre: string; fase: string }>
    }>(`${base}/pipelines`)
  },
  alineamiento() {
    return apiClient.get<Record<string, unknown>>(`${base}/alineamiento`)
  },
  bitacora(limit = 50) {
    return apiClient.get<{ items: AuditoriaEmailScan[] }>(
      `${base}/bitacora?limit=${limit}`
    )
  },
  pausedScans() {
    return apiClient.get<{ items: AuditoriaEmailScan[] }>(
      `${base}/scans/paused`
    )
  },
  estimate(criteria: AuditoriaEmailCriteria) {
    return apiClient.post<{
      source: string
      gmail_query: string
      estimated: number
      exact: boolean
      mensaje?: string
    }>(`${base}/scans/estimate`, { criteria })
  },
  createScan(body: {
    mode: 'single' | 'batch'
    criteria: AuditoriaEmailCriteria
    pipelineIds?: string[]
    lotSize?: number
    maxMessages?: number
  }) {
    return apiClient.post<AuditoriaEmailScan>(`${base}/scans`, body, {
      timeout: 180000,
    })
  },
  getScan(id: number) {
    return apiClient.get<AuditoriaEmailScan>(`${base}/scans/${id}`)
  },
  advanceScan(id: number, maxLots = 1) {
    return apiClient.post<AuditoriaEmailScan>(
      `${base}/scans/${id}/advance?maxLots=${maxLots}&background=true`,
      undefined,
      { timeout: 60000 }
    )
  },
  bandeja(params: {
    skip?: number
    limit?: number
    q?: string
    route?: string
    classify?: string
  }) {
    const sp = new URLSearchParams()
    if (params.skip != null) sp.set('skip', String(params.skip))
    if (params.limit != null) sp.set('limit', String(params.limit))
    if (params.q) sp.set('q', params.q)
    if (params.route) sp.set('route', params.route)
    if (params.classify) sp.set('classify', params.classify)
    const q = sp.toString()
    return apiClient.get<{ total: number; items: Record<string, unknown>[] }>(
      `${base}/bandeja${q ? `?${q}` : ''}`
    )
  },
  bandejaItem(id: number) {
    return apiClient.get<Record<string, unknown>>(`${base}/bandeja/${id}`)
  },
  reescaneo(messageIds: number[], pipelineIds?: string[]) {
    return apiClient.post<{ ok: boolean; reescaneados: number }>(
      `${base}/bandeja/re-escanear`,
      { messageIds, pipelineIds }
    )
  },
  recibos(skip = 0, limit = 50) {
    return apiClient.get<{ total: number; items: Record<string, unknown>[] }>(
      `${base}/recibos?skip=${skip}&limit=${limit}`
    )
  },
}
