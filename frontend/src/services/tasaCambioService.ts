import { API_BASE_URL } from './config'

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

/**





 * Obtiene la tasa de cambio del día actual





 */

export async function getTasaHoy(): Promise<TasaCambioResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/tasas-cambio/hoy`, {
      credentials: 'include',
    })

    if (res.status === 401) throw new Error('No autenticado')

    if (res.status === 403) throw new Error('Sin permisos')

    if (res.status === 404) return null

    if (!res.ok) throw new Error(`Error ${res.status}`)

    const data = await res.json()

    return data
  } catch (err: any) {
    console.error('Error fetching tasa hoy:', err)

    throw err
  }
}

/**





 * Obtiene el estado (si debe ingresar, si ya fue ingresada, horarios)





 */

export async function getEstadoTasa(): Promise<TasaCambioEstado> {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/tasas-cambio/estado`, {
      credentials: 'include',
    })

    if (res.status === 401) throw new Error('No autenticado')

    if (res.status === 403) throw new Error('Sin permisos')

    if (!res.ok) throw new Error(`Error ${res.status}`)

    const data = await res.json()

    return data
  } catch (err: any) {
    console.error('Error fetching estado tasa:', err)

    throw err
  }
}

/**





 * Guarda la tasa de cambio para hoy





 */

export async function guardarTasa(
  tasa_oficial: number
): Promise<TasaCambioResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/tasas-cambio/guardar`, {
      method: 'POST',

      headers: { 'Content-Type': 'application/json' },

      credentials: 'include',

      body: JSON.stringify({ tasa_oficial }),
    })

    if (res.status === 401) throw new Error('No autenticado')

    if (res.status === 403) throw new Error('Sin permisos')

    if (res.status === 400) {
      const errData = await res.json()

      throw new Error(errData.detail || 'Error al guardar')
    }

    if (!res.ok) throw new Error(`Error ${res.status}`)

    const data = await res.json()

    return data
  } catch (err: any) {
    console.error('Error guardando tasa:', err)

    throw err
  }
}

/**





 * Obtiene la tasa de cambio para una fecha específica





 */

export async function getTasaPorFecha(
  fecha: string
): Promise<TasaCambioResponse | null> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/admin/tasas-cambio/por-fecha?fecha=${encodeURIComponent(fecha)}`,

      { credentials: 'include' }
    )

    if (res.status === 404) return null

    if (!res.ok) throw new Error(`Error ${res.status}`)

    const data = await res.json()

    return data
  } catch (err: any) {
    console.error('Error fetching tasa por fecha:', err)

    throw err
  }
}

/**





 * Obtiene el historial de tasas (últimas N fechas)





 */

export async function getHistorialTasas(
  limite: number = 30
): Promise<TasaCambioHistorial[]> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/admin/tasas-cambio/historial?limite=${limite}`,

      { credentials: 'include' }
    )

    if (!res.ok) throw new Error(`Error ${res.status}`)

    const data = await res.json()

    return data
  } catch (err: any) {
    console.error('Error fetching historial:', err)

    throw err
  }
}
