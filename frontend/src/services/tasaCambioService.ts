import { apiClient } from './api'
import { isAxiosError } from '../types/errors'

export interface TasaCambioResponse {
  id: number
  fecha: string
  tasa_oficial: number
  tasa_bcv?: number | null
  tasa_binance?: number | null
  usuario_email?: string
  created_at: string
  updated_at: string
}

export interface TasaCambioEstado {
  debe_ingresar: boolean
  /** True si Euro, BCV y Binance están cargados y válidos para hoy (misma fila diaria). */
  tasa_ya_ingresada: boolean
  euro_ok?: boolean
  bcv_ok?: boolean
  binance_ok?: boolean
  hora_obligatoria_desde: string
  hora_obligatoria_hasta: string
}

export interface TasaCambioHistorial {
  id: number
  fecha: string
  tasa_oficial: number
  tasa_bcv?: number | null
  tasa_binance?: number | null
  usuario_email?: string
  updated_at?: string
}

export interface TasaProblematicaFila {
  fecha: string
  tasa_oficial: number | null
  usuario_email?: string | null
}

export interface TasasProblematicasResponse {
  total: number
  filas: TasaProblematicaFila[]
}

export interface RellenarTasasDesdeVecinoCambio {
  fecha: string
  tasa_anterior: number | null
  tasa_propuesta: number | null
  aplicable: boolean
}

export interface RellenarTasasDesdeVecinoResponse {
  dry_run: boolean
  filas_problematicas: number
  filas_con_propuesta: number
  cambios: RellenarTasasDesdeVecinoCambio[]
}

/** Misma convención que el resto de servicios: prefijo explícito /api/v1 (baseURL vacío en prod same-origin). */
const ADMIN_TASAS = '/api/v1/admin/tasas-cambio'
/**
 * Lectura y registro del día para cualquier usuario autenticado (operadores incl.).
 * Los GET intentan primero admin; si responde 403, repiten bajo esta ruta (mismo contrato).
 * Así los admins no generan 404 en logs cuando el API aún no monta /tasas-cambio.
 * POST /guardar: admin primero; 403 → POST aquí.
 */
const TASAS_CAMBIO_API = '/api/v1/tasas-cambio'

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

/**
 * GET tasas: admin primero (mayoría de despliegues). 403 → misma ruta bajo /tasas-cambio
 * para operadores cuando el backend la exponga. Si la ruta amplia no existe (404),
 * se propaga el error original del admin (p. ej. 403).
 */
async function getTasaLecturaFlexible<T>(rutaRelativa: string): Promise<T> {
  try {
    return await apiClient.get<T>(ADMIN_TASAS + rutaRelativa)
  } catch (e) {
    if (!isAxiosError(e) || e.response?.status !== 403) throw e
    try {
      return await apiClient.get<T>(TASAS_CAMBIO_API + rutaRelativa)
    } catch {
      throw e
    }
  }
}

export async function getTasaHoy(): Promise<TasaCambioResponse | null> {
  try {
    return await getTasaLecturaFlexible<TasaCambioResponse | null>('/hoy')
  } catch (e) {
    if (isAxiosError(e) && e.response?.status === 404) return null
    console.error('Error fetching tasa hoy:', e)
    throwFromAxios(e, 'Error al obtener la tasa')
  }
}

export async function getEstadoTasa(): Promise<TasaCambioEstado> {
  try {
    return await getTasaLecturaFlexible<TasaCambioEstado>('/estado')
  } catch (e) {
    console.error('Error fetching estado tasa:', e)
    throwFromAxios(e, 'Error al obtener estado de tasa')
  }
}

export async function guardarTasa(params: {
  tasa_oficial: number
  tasa_bcv: number
  tasa_binance: number
}): Promise<TasaCambioResponse> {
  const body = {
    tasa_oficial: params.tasa_oficial,
    tasa_bcv: params.tasa_bcv,
    tasa_binance: params.tasa_binance,
  }
  try {
    return await apiClient.post<TasaCambioResponse>(
      ADMIN_TASAS + '/guardar',
      body
    )
  } catch (e) {
    if (isAxiosError(e) && e.response?.status === 403) {
      try {
        return await apiClient.post<TasaCambioResponse>(
          TASAS_CAMBIO_API + '/guardar',
          body
        )
      } catch (e2) {
        console.error('Error guardando tasa (ruta amplia):', e2)
        throwFromAxios(e2, 'Error al guardar la tasa')
      }
    }
    console.error('Error guardando tasa:', e)
    throwFromAxios(e, 'Error al guardar la tasa')
  }
}

/** Tasa para una fecha concreta (ej. fecha de pago de reporte en Bs.). Solo admin. */
export async function guardarTasaPorFecha(
  fecha: string,
  tasa_oficial: number,
  opts?: { tasa_bcv?: number; tasa_binance?: number }
): Promise<TasaCambioResponse> {
  try {
    const body: Record<string, unknown> = { fecha, tasa_oficial }
    if (opts?.tasa_bcv != null && Number.isFinite(opts.tasa_bcv)) {
      body.tasa_bcv = opts.tasa_bcv
    }
    if (opts?.tasa_binance != null && Number.isFinite(opts.tasa_binance)) {
      body.tasa_binance = opts.tasa_binance
    }
    return await apiClient.post<TasaCambioResponse>(
      ADMIN_TASAS + '/guardar-por-fecha',
      body
    )
  } catch (e) {
    console.error('Error guardando tasa por fecha:', e)
    throwFromAxios(e, 'Error al guardar la tasa para la fecha')
  }
}

export async function getTasaPorFecha(
  fecha: string
): Promise<TasaCambioResponse | null> {
  const q = '/por-fecha?fecha=' + encodeURIComponent(fecha)
  try {
    return await getTasaLecturaFlexible<TasaCambioResponse | null>(q)
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

/** Tasas <= 0 o valor tipo placeholder de plantillas (ej. 99999.99). */
export async function getTasasProblematicas(): Promise<TasasProblematicasResponse> {
  try {
    return await apiClient.get<TasasProblematicasResponse>(
      ADMIN_TASAS + '/tasas-problematicas'
    )
  } catch (e) {
    console.error('Error tasas problematicas:', e)
    throwFromAxios(e, 'Error al listar tasas problematicas')
  }
}

/**
 * Propone o aplica tasa copiada desde la fecha valida mas cercana en la tabla.
 * dry_run=true solo simula.
 */
export async function rellenarTasasDesdeVecino(
  dryRun: boolean
): Promise<RellenarTasasDesdeVecinoResponse> {
  try {
    return await apiClient.post<RellenarTasasDesdeVecinoResponse>(
      ADMIN_TASAS + '/rellenar-desde-vecino',
      { dry_run: dryRun }
    )
  } catch (e) {
    console.error('Error rellenar tasas:', e)
    throwFromAxios(e, 'Error al rellenar tasas desde vecino')
  }
}
