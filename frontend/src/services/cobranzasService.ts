import { apiClient } from './api'

export interface ClienteAtrasado {
  cedula: string
  nombres: string
  analista: string
  prestamo_id: number
  cuotas_vencidas: number
  total_adeudado: number
  fecha_primera_vencida?: string
  [key: string]: unknown // Firma de índice para compatibilidad con Record<string, unknown>
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

  // ============================================
  // MÉTODOS PARA INFORMES
  // ============================================

  // Informe 1: Clientes Atrasados Completo
  async getInformeClientesAtrasados(params?: {
    dias_retraso_min?: number
    dias_retraso_max?: number
    analista?: string
    formato?: 'json' | 'pdf' | 'excel'
  }): Promise<any> {
    const searchParams = new URLSearchParams()
    if (params?.dias_retraso_min) searchParams.append('dias_retraso_min', params.dias_retraso_min.toString())
    if (params?.dias_retraso_max) searchParams.append('dias_retraso_max', params.dias_retraso_max.toString())
    if (params?.analista) searchParams.append('analista', params.analista)
    if (params?.formato) searchParams.append('formato', params.formato)
    
    const url = `${this.baseUrl}/informes/clientes-atrasados?${searchParams.toString()}`
    
    if (params?.formato === 'pdf' || params?.formato === 'excel') {
      // Descargar archivo usando axios directamente
      const axiosInstance = apiClient.getAxiosInstance()
      const response = await axiosInstance.get(url, { responseType: 'blob' })
      const blob = new Blob([response.data], {
        type: params.formato === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const urlBlob = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = urlBlob
      link.download = `informe_clientes_atrasados_${new Date().toISOString().split('T')[0]}.${params.formato === 'pdf' ? 'pdf' : 'xlsx'}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(urlBlob)
      return { success: true }
    }
    
    return await apiClient.get(url)
  }

  // Informe 2: Rendimiento por Analista
  async getInformeRendimientoAnalista(formato: 'json' | 'pdf' | 'excel' = 'json'): Promise<any> {
    const url = `${this.baseUrl}/informes/rendimiento-analista?formato=${formato}`
    
    if (formato === 'pdf' || formato === 'excel') {
      const axiosInstance = apiClient.getAxiosInstance()
      const response = await axiosInstance.get(url, { responseType: 'blob' })
      const blob = new Blob([response.data], {
        type: formato === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const urlBlob = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = urlBlob
      link.download = `informe_rendimiento_analista_${new Date().toISOString().split('T')[0]}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(urlBlob)
      return { success: true }
    }
    
    return await apiClient.get(url)
  }

  // Informe 3: Montos Vencidos por Período
  async getInformeMontosPeriodo(params?: {
    fecha_inicio?: string
    fecha_fin?: string
    formato?: 'json' | 'pdf' | 'excel'
  }): Promise<any> {
    const searchParams = new URLSearchParams()
    if (params?.fecha_inicio) searchParams.append('fecha_inicio', params.fecha_inicio)
    if (params?.fecha_fin) searchParams.append('fecha_fin', params.fecha_fin)
    if (params?.formato) searchParams.append('formato', params.formato)
    
    const url = `${this.baseUrl}/informes/montos-vencidos-periodo?${searchParams.toString()}`
    
    if (params?.formato === 'pdf' || params?.formato === 'excel') {
      const axiosInstance = apiClient.getAxiosInstance()
      const response = await axiosInstance.get(url, { responseType: 'blob' })
      const blob = new Blob([response.data], {
        type: params.formato === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const urlBlob = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = urlBlob
      link.download = `informe_montos_periodo_${new Date().toISOString().split('T')[0]}.${params.formato === 'pdf' ? 'pdf' : 'xlsx'}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(urlBlob)
      return { success: true }
    }
    
    return await apiClient.get(url)
  }

  // Informe 4: Antigüedad de Saldos
  async getInformeAntiguedadSaldos(formato: 'json' | 'pdf' | 'excel' = 'json'): Promise<any> {
    const url = `${this.baseUrl}/informes/antiguedad-saldos?formato=${formato}`
    
    if (formato === 'pdf' || formato === 'excel') {
      const axiosInstance = apiClient.getAxiosInstance()
      const response = await axiosInstance.get(url, { responseType: 'blob' })
      const blob = new Blob([response.data], {
        type: formato === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const urlBlob = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = urlBlob
      link.download = `informe_antiguedad_saldos_${new Date().toISOString().split('T')[0]}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(urlBlob)
      return { success: true }
    }
    
    return await apiClient.get(url)
  }

  // Informe 5: Resumen Ejecutivo
  async getInformeResumenEjecutivo(formato: 'json' | 'pdf' | 'excel' = 'json'): Promise<any> {
    const url = `${this.baseUrl}/informes/resumen-ejecutivo?formato=${formato}`
    
    if (formato === 'pdf' || formato === 'excel') {
      const axiosInstance = apiClient.getAxiosInstance()
      const response = await axiosInstance.get(url, { responseType: 'blob' })
      const blob = new Blob([response.data], {
        type: formato === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const urlBlob = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = urlBlob
      link.download = `informe_resumen_ejecutivo_${new Date().toISOString().split('T')[0]}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(urlBlob)
      return { success: true }
    }
    
    return await apiClient.get(url)
  }

  // Procesar notificaciones de atrasos
  async procesarNotificacionesAtrasos(): Promise<{ mensaje: string, estadisticas: any }> {
    return await apiClient.post(`${this.baseUrl}/notificaciones/atrasos`)
  }
}

export const cobranzasService = new CobranzasService()

