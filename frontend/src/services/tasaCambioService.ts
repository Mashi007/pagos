import { apiClient } from './api'
import { isAxiosError } from '../types/errors'

export interface TasaCambioResponse {
  id: number
  fecha: string
  tasa_oficial: number
  usuario_email?: string
  created_at: string
  updated_at: string
}

export interface TasaCambioEstado {
  debe_ingresar: boolean
  tasa_ya_ingresada: boolean
  hora_obligatoria_desde: string
  hora_obligatoria_hasta: string
}

export interface TasaCambioHistorial {
  id: number
  fecha: string
  tasa_oficial: number
  usuario_email?: string
  updated_at?: string
}

const ADMIN_TASAS = '/admin/tasas-cambio'

function throwFromAxios(e: unknown, fallback: string): never {
  if (isAxiosError(e)) {
    const status = e.response?.status
    const data = e.response?.data as { detail?: string } | undefined
    if (status === 401) throw new Error('No autenticado')
    if (status === 403) throw new Error('Sin permisos')
    if (status === 400 && data?.detail) throw new Error(String(data.detail))
    if (status) throw new Error('Error ' + String(status))
  }
  throw e instanceof Error ? e : new Error(fallback)
}

export async function getTasaHoy(): Promise<TasaCambioResponse | null> {
  try {
    return await apiClient.get<TasaCambioResponse | null>(ADMIN_TASAS + '/hoy')
  } catch (e) {
    if (isAxiosError(e) && e.response?.status === 404) return null
    console.error('Error fetching tasa hoy:', e)
    throwFromAxios(e, 'Error al obtener la tasa')
  }
}

export async function getEstadoTasa(): Promise<TasaCambioEstado> {
  try {
    return await apiClient.get<TasaCambioEstado>(ADMIN_TASAS + '/estado')
  } catch (e) {
    console.error('Error fetching estado tasa:', e)
    throwFromAxios(e, 'Error al obtener estado de tasa')
  }
}

export async function guardarTasa(
  tasa_oficial: number
): Promise<TasaCambioResponse> {
  try {
    return await apiClient.post<TasaCambioResponse>(ADMIN_TASAS + '/guardar', {
      tasa_oficial,
    })
  } catch (e) {
    console.error('Error guardando tasa:', e)
    throwFromAxios(e, 'Error al guardar la tasa')
  }
}

/** Tasa para una fecha concreta (ej. fecha de pago de reporte en Bs.). Solo admin. */
export async function guardarTasaPorFecha(
  fecha: string,
  tasa_oficial: number
): Promise<TasaCambioResponse> {
  try {
    return await apiClient.post<TasaCambioResponse>(
      ADMIN_TASAS + '/guardar-por-fecha',
      { fecha, tasa_oficial }
    )
  } catch (e) {
    console.error('Error guardando tasa por fecha:', e)
    throwFromAxios(e, 'Error al guardar la tasa para la fecha')
  }
}

export async function getTasaPorFecha(
  fecha: string
): Promise<TasaCambioResponse | null> {
  try {
    const url = ADMIN_TASAS + '/por-fecha?fecha=' + encodeURIComponent(fecha)
    return await apiClient.get<TasaCambioResponse | null>(url)
  } catch (e) {
    if (isAxiosError(e) && e.response?.status === 404) return null
    console.error('Error fetching tasa por fecha:', e)
    throwFromAxios(e, 'Error al obtener tasa por fecha')
  }
}

export async function getHistorialTasas(
  limite: number = 30
): Promise<TasaCambioHistorial[]> {
  try {
    return await apiClient.get<TasaCambioHistorial[]>(
      ADMIN_TASAS + '/historial?limite=' + String(limite)
    )
  } catch (e) {
    console.error('Error fetching historial:', e)
    throwFromAxios(e, 'Error al obtener historial de tasas')
  }
}
