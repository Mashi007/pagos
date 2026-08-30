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
    | 'pagos_gmail'
    | 'pdf_only'
    | 'image_only'
    | ''
  attachmentMinKb?: number
  filenamePattern?: string
  /** Si true, excluye etiquetados ANALIZADOS. Por defecto false: escanea con o sin etiqueta. */
  excludeAnalizados?: boolean
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
  stopped?: boolean
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
      recibos_pending?: number
      por_ruta: Record<string, number>
      por_clase: Record<string, number>
      en_proceso?: number
      en_cola?: number
      pausado?: number
      escaneos_pausados: number
      mailbox: string
      label_analizados?: string
      gmail_connected?: boolean
      current?: {
        id?: number
        gmailMessageId?: string
        subject?: string
        fromEmail?: string
        scanId?: number
      } | null
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
  presetDefaults(preset: string) {
    return apiClient.get<AuditoriaEmailCriteria>(
      `${base}/scans/preset-defaults?preset=${encodeURIComponent(preset)}`
    )
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
  pauseScan(id: number) {
    return apiClient.post<AuditoriaEmailScan & { stopped?: boolean }>(
      `${base}/scans/${id}/pause`,
      undefined,
      { timeout: 60000 }
    )
  },
  resetCola() {
    return apiClient.post<{
      ok: boolean
      scansEliminados: number
      mensajesEliminados: number
      recibosEliminados: number
      recibosApprovedConservados: number
    }>(`${base}/reset-cola`, { confirm: true }, { timeout: 120000 })
  },
  bandeja(params: {
    skip?: number
    limit?: number
    q?: string
    route?: string
    classify?: string
    /** Valor de cédula, o 'NA' para sin cédula */
    cedula?: string
  }) {
    const sp = new URLSearchParams()
    if (params.skip != null) sp.set('skip', String(params.skip))
    if (params.limit != null) sp.set('limit', String(params.limit))
    if (params.q) sp.set('q', params.q)
    if (params.route) sp.set('route', params.route)
    if (params.classify) sp.set('classify', params.classify)
    if (params.cedula) sp.set('cedula', params.cedula)
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
  eliminarBandejaLote(messageIds: number[]) {
    return apiClient.post<{
      ok: boolean
      total: number
      eliminados: number
      recibosEliminados?: number
      errores: number
      omitidos: number
    }>(`${base}/bandeja/eliminar-lote`, { messageIds }, { timeout: 180000 })
  },
  recibos(skip = 0, limit = 500, status = 'pending', prestamoEstado = '') {
    const pe = encodeURIComponent(prestamoEstado || '')
    return apiClient.get<{
      total: number
      returned?: number
      items: Record<string, unknown>[]
      prestamoEstado?: string | null
      counts?: {
        pending: number
        approved: number
        revision: number
        omitidos_sin_aprobado: number
      }
    }>(
      `${base}/recibos?skip=${skip}&limit=${limit}&status=${encodeURIComponent(status)}&prestamoEstado=${pe}`,
      { timeout: 120000 }
    )
  },
  aprobarRecibo(id: number) {
    return apiClient.post<Record<string, unknown>>(
      `${base}/recibos/${id}/aprobar`,
      {},
      { timeout: 180000 }
    )
  },
  eliminarRecibo(id: number) {
    // POST lote (1 id): evita DELETE bloqueado/truncado por proxy; mismo backend.
    return apiClient
      .post<{
        ok: boolean
        eliminados: number
        errores: number
        omitidos: number
      }>(`${base}/recibos/eliminar-lote`, { receiptIds: [id] }, { timeout: 120000 })
      .then(res => {
        if (!res.eliminados) {
          const err = new Error(
            res.errores
              ? `No se pudo eliminar (#${id})`
              : res.omitidos
                ? `Recibo #${id} no estaba pendiente`
                : `No se pudo eliminar (#${id})`
          )
          throw err
        }
        return { ok: true, eliminado: true, id }
      })
  },
  aprobarRecibosLote(receiptIds: number[]) {
    return apiClient.post<{
      ok: boolean
      total: number
      aprobados: number
      revision: number
      errores: number
      omitidos: number
      redirectRevision?: string | null
      itemsAprobados?: Record<string, unknown>[]
      itemsRevision?: Record<string, unknown>[]
      itemsErrores?: Record<string, unknown>[]
    }>(`${base}/recibos/aprobar-lote`, { receiptIds }, { timeout: 300000 })
  },
  eliminarRecibosLote(receiptIds: number[]) {
    return apiClient.post<{
      ok: boolean
      total: number
      eliminados: number
      errores: number
      omitidos: number
    }>(`${base}/recibos/eliminar-lote`, { receiptIds }, { timeout: 180000 })
  },
  revisionManualRecibo(id: number) {
    return apiClient.post<Record<string, unknown>>(
      `${base}/recibos/${id}/revision-manual`,
      {},
      { timeout: 120000 }
    )
  },
}
