import { apiClient } from './api'

export interface ClienteAtrasado {
  cedula: string
  nombres: string
  analista: string
  prestamo_id: number
  cuotas_vencidas: number
  total_adeudado: number
  fecha_primera_vencida?: string
}

export interface CobranzasPorAnalista {
  nombre: string
  cantidad_clientes: number
  monto_total: number
}

export interface MontosPorMes {
  mes: string
  mes_display: string
  cantidad_cuotas: number
  monto_total: number
}

export interface ResumenCobranzas {
  total_cuotas_vencidas: number
  monto_total_adeudado: number
  clientes_atrasados: number
}

class CobranzasService {
  private baseUrl = '/api/v1/cobranzas'

  // Obtener clientes atrasados
  async getClientesAtrasados(diasRetraso?: number): Promise<ClienteAtrasado[]> {
    const params = diasRetraso ? `?dias_retraso=${diasRetraso}` : ''
    return await apiClient.get(`${this.baseUrl}/clientes-atrasados${params}`)
  }

  // Obtener clientes por cantidad de pagos atrasados
  async getClientesPorCantidadPagos(cantidadPagos: number): Promise<ClienteAtrasado[]> {
    return await apiClient.get(
      `${this.baseUrl}/clientes-por-cantidad-pagos?cantidad_pagos=${cantidadPagos}`
    )
  }

  // Obtener cobranzas por analista
  async getCobranzasPorAnalista(): Promise<CobranzasPorAnalista[]> {
    return await apiClient.get(`${this.baseUrl}/por-analista`)
  }

  // Obtener clientes de un analista específico
  async getClientesPorAnalista(analista: string): Promise<ClienteAtrasado[]> {
    return await apiClient.get(`${this.baseUrl}/por-analista/${analista}/clientes`)
  }

  // Obtener montos vencidos por mes
  async getMontosPorMes(): Promise<MontosPorMes[]> {
    return await apiClient.get(`${this.baseUrl}/montos-por-mes`)
  }

  // Obtener resumen general
  async getResumen(): Promise<ResumenCobranzas> {
    return await apiClient.get(`${this.baseUrl}/resumen`)
  }
}

export const cobranzasService = new CobranzasService()

