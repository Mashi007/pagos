import { apiClient } from './api'

export interface Cuota {
  id: number

  prestamo_id: number

  numero_cuota: number

  fecha_vencimiento: string | Date

  monto_cuota: number

  monto_capital?: number

  monto_interes?: number

  saldo_capital_inicial: number

  saldo_capital_final: number

  fecha_pago?: string | Date | null

  total_pagado: number

  capital_pagado?: number

  interes_pagado?: number

  capital_pendiente?: number

  interes_pendiente?: number

  dias_mora: number

  dias_morosidad?: number

  estado: string

  estado_etiqueta?: string

  observaciones?: string | null

  es_cuota_especial?: boolean

  esta_vencida?: boolean

  monto_pendiente_total?: number

  porcentaje_pagado?: number
}

export interface CuotaUpdate {
  fecha_vencimiento?: string | Date | null

  fecha_pago?: string | Date | null

  monto_cuota?: number

  total_pagado?: number

  estado?: string

  observaciones?: string | null
}

class CuotaService {
  private readonly prestamosBase = '/api/v1/prestamos'

  async getCuotasByPrestamo(
    prestamoId: number,
    estado?: string
  ): Promise<Cuota[]> {
    const params = estado ? `?estado=${encodeURIComponent(estado)}` : ''

    return await apiClient.get(
      `${this.prestamosBase}/${prestamoId}/cuotas${params}`
    )
  }

  /**
   * Varias amortizaciones: POST /prestamos/cuotas/by-prestamo-ids (una peticion).
   * El parametro `estado` no aplica al batch; filtrar en cliente si hiciera falta.
   */
  async getCuotasMultiplesPrestamos(
    prestamoIds: number[],
    _estado?: string
  ): Promise<Cuota[]> {
    if (!prestamoIds || prestamoIds.length === 0) {
      return []
    }

    return await apiClient.post(
      `${this.prestamosBase}/cuotas/by-prestamo-ids`,
      {
        prestamo_ids: prestamoIds,
      }
    )
  }

  async updateCuota(
    prestamoId: number,
    cuotaId: number,
    data: CuotaUpdate
  ): Promise<Cuota> {
    return await apiClient.put(
      `${this.prestamosBase}/${prestamoId}/cuotas/${cuotaId}`,
      data
    )
  }

  async deleteCuota(prestamoId: number, cuotaId: number): Promise<void> {
    await apiClient.delete(
      `${this.prestamosBase}/${prestamoId}/cuotas/${cuotaId}`
    )
  }
}

export const cuotaService = new CuotaService()
