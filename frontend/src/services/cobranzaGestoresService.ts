import { apiClient } from './api'

export type CobranzaGestor = {
  slug: string
  nombre: string
}

export type CobranzaGestorTotal = {
  slug: string
  nombre: string
  cantidad_casos: number
  total_cobranza_usd: number
  usd_vencidas: number
  usd_mora: number
}

export type CobranzaGestoresDashboard = {
  gestores: CobranzaGestor[]
  totales: CobranzaGestorTotal[]
  tendencia: Array<Record<string, string | number>>
  asignacion_cerrada: boolean
  asignacion_en_progreso?: boolean
  desde_cache?: boolean
  cache_ttl_segundos?: number
  fecha_inicio_cartera: string
  fecha_negocio: string
  filtro?: string
  email_diario?: {
    fecha_referencia_caracas?: string
    enviado_ok_hoy?: boolean
    ventana_cron_activa?: boolean
    hora_caracas?: string
    cron_habilitado?: boolean
    destino?: string
    estado_hoy?: {
      estado?: string
      error?: string
      asunto?: string
      origen?: string
      hora_caracas?: string
    }
  }
}

const BASE = '/api/v1/cobranzas/gestores'

export async function listarCobranzasGestores(opts?: {
  signal?: AbortSignal
}): Promise<CobranzaGestor[]> {
  const res = await apiClient.get<{ gestores: CobranzaGestor[] }>(BASE, {
    signal: opts?.signal,
  })
  return res?.gestores ?? []
}

export async function obtenerDashboardGestores(opts?: {
  signal?: AbortSignal
  forceRefresh?: boolean
}): Promise<CobranzaGestoresDashboard> {
  return await apiClient.get<CobranzaGestoresDashboard>(`${BASE}/dashboard`, {
    signal: opts?.signal,
    timeout: 120000,
    params: opts?.forceRefresh ? { force: true } : undefined,
  })
}

export async function descargarExcelGestor(
  slug: string,
  opts?: { signal?: AbortSignal }
): Promise<{ blob: Blob; filename: string }> {
  const axiosInstance = apiClient.getAxiosInstance()
  const response = await axiosInstance.get(`${BASE}/${encodeURIComponent(slug)}/excel`, {
    responseType: 'blob',
    timeout: 180000,
    signal: opts?.signal,
  })
  const cd = String(response.headers?.['content-disposition'] || '')
  const m = /filename="([^"]+)"/i.exec(cd)
  const filename = m?.[1] || `gestor_${slug}.xlsx`
  return { blob: response.data as Blob, filename }
}

export async function descargarInformeDiarioGestor(
  slug: string,
  opts?: { signal?: AbortSignal }
): Promise<{ blob: Blob; filename: string }> {
  const axiosInstance = apiClient.getAxiosInstance()
  const response = await axiosInstance.get(
    `${BASE}/${encodeURIComponent(slug)}/informe-diario`,
    {
      responseType: 'blob',
      timeout: 180000,
      signal: opts?.signal,
    }
  )
  const cd = String(response.headers?.['content-disposition'] || '')
  const m = /filename="([^"]+)"/i.exec(cd)
  const filename = m?.[1] || `informe_diario_${slug}.xlsx`
  return { blob: response.data as Blob, filename }
}

export async function descargarInformeDiarioTodos(opts?: {
  signal?: AbortSignal
}): Promise<{ blob: Blob; filename: string }> {
  const axiosInstance = apiClient.getAxiosInstance()
  const response = await axiosInstance.get(`${BASE}/informe-diario`, {
    responseType: 'blob',
    timeout: 180000,
    signal: opts?.signal,
  })
  const cd = String(response.headers?.['content-disposition'] || '')
  const m = /filename="([^"]+)"/i.exec(cd)
  const filename = m?.[1] || 'informe_diario_todos.xlsx'
  return { blob: response.data as Blob, filename }
}

export async function enviarListasGestoresAhora(opts?: {
  signal?: AbortSignal
}): Promise<{
  ok: boolean
  adjuntos?: number
  to?: string
  bcc?: string
  asunto?: string
  error?: string
}> {
  return await apiClient.post(`${BASE}/enviar-listas-ahora`, {}, {
    signal: opts?.signal,
    timeout: 300000,
  })
}

export function triggerDownloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
