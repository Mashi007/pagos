import { apiClient, buildUrl } from './api'
import { env } from '../config/env'

export type MotivoCobranza =
  | 'ATRASO_CRONICO'
  | 'SOBREPAGO'
  | 'NEGOCIACION'
  | 'OTRO'

export type EstadoCasoCobranza = 'ABIERTO' | 'EN_GESTION' | 'CERRADO'

export type EstadoAcuerdoCobranza = 'PENDIENTE' | 'CUMPLIDO' | 'INCUMPLIDO'

export interface CobranzaPrestamoResumen {
  id: number
  cliente_id?: number | null
  cedula: string
  nombres?: string | null
  total_financiamiento: number
  saldo_pendiente: number
  modalidad_pago?: string | null
  numero_cuotas?: number | null
  estado: string
  cuotas_atrasadas: number
  caso_id?: number | null
  caso_estado?: string | null
  caso_motivo?: string | null
}

export interface CobranzaBuscarResponse {
  cedula: string
  cliente_id?: number | null
  nombres?: string | null
  prestamos: CobranzaPrestamoResumen[]
}

export interface CobranzaImagenMeta {
  id: string
  descripcion?: string | null
  content_type: string
  creado_en?: string | null
}

export interface CobranzaAcuerdo {
  id: number
  caso_id: number
  fecha_acuerdo: string
  fecha_compromiso?: string | null
  notas: string
  estado: EstadoAcuerdoCobranza
  monto_compromiso?: number | null
  creado_en?: string | null
  actualizado_en?: string | null
}

export interface CobranzaCasoDetalle {
  id: number
  prestamo_id: number
  cliente_id?: number | null
  cedula: string
  nombres?: string | null
  motivo: MotivoCobranza
  estado: EstadoCasoCobranza
  observaciones?: string | null
  monto_financiamiento?: number | null
  saldo_pendiente_snapshot?: number | null
  cuotas_atrasadas_snapshot?: number | null
  saldo_pendiente_actual?: number | null
  cuotas_atrasadas_actual?: number | null
  total_financiamiento_actual?: number | null
  modalidad_pago?: string | null
  numero_cuotas?: number | null
  prestamo_estado?: string | null
  imagenes: CobranzaImagenMeta[]
  acuerdos: CobranzaAcuerdo[]
}

const base = '/api/v1/cobranzas'

export function cobranzaImagenUrl(imagenId: string): string {
  const path = buildUrl(`${base}/imagenes/${imagenId}`)
  const apiBase = (env.API_URL || '').replace(/\/$/, '')
  if (apiBase && path.startsWith('/')) {
    return `${apiBase}${path}`
  }
  return path
}

export async function buscarCobranzasPorCedula(
  cedula: string
): Promise<CobranzaBuscarResponse> {
  return apiClient.get<CobranzaBuscarResponse>(buildUrl(`${base}/buscar`), {
    params: { cedula: cedula.trim() },
  })
}

export async function obtenerCasoCobranza(
  casoId: number
): Promise<CobranzaCasoDetalle> {
  return apiClient.get<CobranzaCasoDetalle>(
    buildUrl(`${base}/casos/${casoId}`)
  )
}

export async function crearCasoCobranza(body: {
  prestamo_id: number
  motivo: MotivoCobranza
  observaciones?: string
}): Promise<CobranzaCasoDetalle> {
  return apiClient.post<CobranzaCasoDetalle>(buildUrl(`${base}/casos`), body)
}

export async function actualizarCasoCobranza(
  casoId: number,
  body: Partial<{
    motivo: MotivoCobranza
    estado: EstadoCasoCobranza
    observaciones: string
  }>
): Promise<CobranzaCasoDetalle> {
  return apiClient.patch<CobranzaCasoDetalle>(
    buildUrl(`${base}/casos/${casoId}`),
    body
  )
}

export async function crearAcuerdoCobranza(
  casoId: number,
  body: {
    fecha_acuerdo: string
    fecha_compromiso?: string
    notas: string
    monto_compromiso?: number
  }
): Promise<CobranzaAcuerdo> {
  return apiClient.post<CobranzaAcuerdo>(
    buildUrl(`${base}/casos/${casoId}/acuerdos`),
    body
  )
}

export async function sincronizarAcuerdosCobranza(
  casoId: number
): Promise<CobranzaCasoDetalle> {
  return apiClient.post<CobranzaCasoDetalle>(
    buildUrl(`${base}/casos/${casoId}/acuerdos/sincronizar-estados`)
  )
}

export async function subirImagenCobranza(
  casoId: number,
  file: File,
  descripcion?: string
): Promise<{ id: string; url: string }> {
  const form = new FormData()
  form.append('file', file)
  if (descripcion?.trim()) {
    form.append('descripcion', descripcion.trim())
  }
  return apiClient.post<{ id: string; url: string }>(
    buildUrl(`${base}/casos/${casoId}/imagenes`),
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

export async function eliminarImagenCobranza(
  casoId: number,
  imagenId: string
): Promise<void> {
  await apiClient.delete(buildUrl(`${base}/casos/${casoId}/imagenes/${imagenId}`))
}

export const MOTIVOS_COBRANZA_LABEL: Record<MotivoCobranza, string> = {
  ATRASO_CRONICO: 'Atraso cronico',
  SOBREPAGO: 'Sobrepago',
  NEGOCIACION: 'Negociacion',
  OTRO: 'Otro',
}

export const ESTADO_ACUERDO_LABEL: Record<EstadoAcuerdoCobranza, string> = {
  PENDIENTE: 'Pendiente',
  CUMPLIDO: 'Cumplido',
  INCUMPLIDO: 'Incumplido',
}
