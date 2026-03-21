import { apiClient } from './api'

export interface Cuota {
  id: number

  prestamo_id: number

  numero_cuota: number

  fecha_vencimiento: string | Date

  monto_cuota: number

  monto_capital?: number // Opcional - puede calcularse desde saldo_capital_inicial y saldo_capital_final

  monto_interes?: number // Opcional - puede calcularse desde monto_cuota y monto_capital

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
  /** Lectura de cuotas: mismo contrato que GET /api/v1/prestamos/{id}/cuotas (estado + estado_etiqueta). */
  private readonly prestamosBase = '/api/v1/prestamos'

  /**
   * CRUD bajo /api/v1/amortizacion: no esta registrado en app/api/v1/__init__.py en este repo.
   * Si falla en runtime, exponer PUT/DELETE en prestamos o quitar esas acciones del UI.
   */
  private readonly amortizacionLegacyBase = '/api/v1/amortizacion'

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
   * Varias amortizaciones: paraleliza GET /prestamos/{id}/cuotas (sin endpoint batch en backend).
   */
  async getCuotasMultiplesPrestamos(
    prestamoIds: number[],
    estado?: string
  ): Promise<Cuota[]> {
    if (!prestamoIds || prestamoIds.length === 0) {
      return []
    }

    const lotes = await Promise.all(
      prestamoIds.map(id => this.getCuotasByPrestamo(id, estado))
    )

    return lotes.flat()
  }

  async getCuotaById(cuotaId: number): Promise<Cuota> {
    return await apiClient.get(
      `${this.amortizacionLegacyBase}/cuota/${cuotaId}`
    )
  }

  async updateCuota(cuotaId: number, data: CuotaUpdate): Promise<Cuota> {
    return await apiClient.put(
      `${this.amortizacionLegacyBase}/cuota/${cuotaId}`,
      data
    )
  }

  async deleteCuota(
    cuotaId: number
  ): Promise<{ message: string; cuota_id: number; prestamo_id: number }> {
    return await apiClient.delete(
      `${this.amortizacionLegacyBase}/cuota/${cuotaId}`
    )
  }
}

export const cuotaService = new CuotaService()
