import { apiClient } from './api'

export interface Cuota {
  id: number
  prestamo_id: number
  numero_cuota: number
  fecha_vencimiento: string | Date
  monto_cuota: number
  monto_capital?: number  // Opcional - puede calcularse desde saldo_capital_inicial y saldo_capital_final
  monto_interes?: number  // Opcional - puede calcularse desde monto_cuota y monto_capital
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
  private baseUrl = '/api/v1/amortizacion'

  async getCuotasByPrestamo(prestamoId: number, estado?: string): Promise<Cuota[]> {
    const params = estado ? `?estado=${estado}` : ''
    return await apiClient.get(`${this.baseUrl}/prestamo/${prestamoId}/cuotas${params}`)
  }

  /**
   * Obtiene cuotas de múltiples préstamos en una sola query.
   * Optimiza el problema N+1 queries.
   */
  async getCuotasMultiplesPrestamos(prestamoIds: number[], estado?: string): Promise<Cuota[]> {
    if (!prestamoIds || prestamoIds.length === 0) {
      return []
    }
    const params = estado ? `?estado=${estado}` : ''
    return await apiClient.post(`${this.baseUrl}/cuotas/multiples${params}`, prestamoIds)
  }

  async getCuotaById(cuotaId: number): Promise<Cuota> {
    return await apiClient.get(`${this.baseUrl}/cuota/${cuotaId}`)
  }

  async updateCuota(cuotaId: number, data: CuotaUpdate): Promise<Cuota> {
    return await apiClient.put(`${this.baseUrl}/cuota/${cuotaId}`, data)
  }

  async deleteCuota(cuotaId: number): Promise<{ message: string; cuota_id: number; prestamo_id: number }> {
    return await apiClient.delete(`${this.baseUrl}/cuota/${cuotaId}`)
  }
}

export const cuotaService = new CuotaService()
