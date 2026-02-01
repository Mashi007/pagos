import { apiClient } from './api'

export interface ClienteAtrasado {
  cedula: string
  nombres: string
  analista?: string
  telefono?: string
  prestamo_id: number
  cuotas_vencidas: number
  total_adeudado: number
  fecha_primera_vencida?: string
  ml_impago?: {
    probabilidad_impago: number
    nivel_riesgo: string
    prediccion: string
    es_manual?: boolean
  } | null
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
  async getClientesAtrasados(
    diasRetraso?: number,
    diasRetrasoMin?: number,
    diasRetrasoMax?: number,
    incluirAdmin: boolean = false,
    incluirML: boolean = true // ✅ Permitir omitir ML para mejor rendimiento
  ): Promise<ClienteAtrasado[]> {
    const params = new URLSearchParams()
    if (diasRetraso) {
      params.append('dias_retraso', diasRetraso.toString())
    } else {
      // ✅ Usar el endpoint principal que ahora soporta rangos
      if (diasRetrasoMin !== undefined) params.append('dias_retraso_min', diasRetrasoMin.toString())
      if (diasRetrasoMax !== undefined) params.append('dias_retraso_max', diasRetrasoMax.toString())
    }
    if (incluirAdmin) params.append('incluir_admin', 'true')
    // ✅ Agregar parámetro para omitir ML si hay muchos registros (mejor rendimiento)
    if (!incluirML) params.append('incluir_ml', 'false')
    
    const url = `${this.baseUrl}/clientes-atrasados${params.toString() ? `?${params.toString()}` : ''}`

    try {
      // ✅ OPTIMIZACIÓN: Timeout aumentado a 120s para datasets grandes (2868+ clientes)
      // El endpoint puede tardar más cuando procesa muchos registros sin ML
      // El apiClient ya detecta este endpoint y aplica timeout de 120s automáticamente
      const result = await apiClient.get<ClienteAtrasado[] | { clientes_atrasados: ClienteAtrasado[] }>(url, { timeout: 120000 })
      // ✅ Manejar ambos formatos de respuesta (array directo o objeto con clientes_atrasados)
      const clientes = Array.isArray(result) ? result : (result.clientes_atrasados || [])
      console.log(`✅ [Cobranzas] Clientes atrasados cargados: ${clientes.length}`)
      return clientes
    } catch (error: any) {
      console.error('❌ [Cobranzas] Error cargando clientes atrasados:', error)
      throw error
    }
  }

  // Obtener clientes por cantidad de pagos atrasados
  async getClientesPorCantidadPagos(cantidadPagos: number): Promise<ClienteAtrasado[]> {
    return await apiClient.get(
      `${this.baseUrl}/clientes-por-cantidad-pagos?cantidad_pagos=${cantidadPagos}`
    )
  }

  // Obtener cobranzas por analista
  async getCobranzasPorAnalista(incluirAdmin: boolean = false): Promise<CobranzasPorAnalista[]> {
    const url = `${this.baseUrl}/por-analista${incluirAdmin ? '?incluir_admin=true' : ''}`

    try {
      const result = await apiClient.get<CobranzasPorAnalista[]>(url, { timeout: 60000 })
      console.log(`✅ [Cobranzas] Datos por analista cargados: ${result.length}`)
      return result
    } catch (error: any) {
      console.error('❌ [Cobranzas] Error cargando datos por analista:', error)
      throw error
    }
  }

  // Obtener clientes de un analista específico
  async getClientesPorAnalista(analista: string): Promise<ClienteAtrasado[]> {
    return await apiClient.get(`${this.baseUrl}/por-analista/${analista}/clientes`)
  }

  // Obtener montos vencidos por mes
  async getMontosPorMes(incluirAdmin: boolean = false): Promise<MontosPorMes[]> {
    const url = `${this.baseUrl}/montos-por-mes${incluirAdmin ? '?incluir_admin=true' : ''}`

    try {
      const result = await apiClient.get<MontosPorMes[]>(url, { timeout: 60000 })
      console.log(`✅ [Cobranzas] Montos por mes cargados: ${result.length}`)
      return result
    } catch (error: any) {
      console.error('❌ [Cobranzas] Error cargando montos por mes:', error)
      throw error
    }
  }

  // Obtener resumen general
  async getResumen(incluirAdmin: boolean = false): Promise<ResumenCobranzas> {
    const url = `${this.baseUrl}/resumen${incluirAdmin ? '?incluir_admin=true' : ''}`
    console.log('🔍 [Cobranzas] Iniciando petición a:', url)

    try {
      const startTime = Date.now()
      const result = await apiClient.get<ResumenCobranzas>(url, { timeout: 60000 })
      const duration = Date.now() - startTime
      console.log(`✅ [Cobranzas] Respuesta recibida en ${duration}ms:`, result)
      return result
    } catch (error: any) {
      console.error('❌ [Cobranzas] Error completo:', {
        message: error.message,
        code: error.code,
        response: error.response?.data,
        status: error.response?.status,
        url: url
      })
      throw error
    }
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

  // Obtener diagnóstico completo
  async getDiagnostico(): Promise<any> {
    const url = `${this.baseUrl}/diagnostico`
    console.log('🔍 [Cobranzas] Obteniendo diagnóstico completo...')

    try {
      const result = await apiClient.get(url, { timeout: 60000 })
      console.log('✅ [Cobranzas] Diagnóstico recibido:', result)
      return result
    } catch (error: any) {
      console.error('❌ [Cobranzas] Error obteniendo diagnóstico:', error)
      throw error
    }
  }

  // Obtener resumen con diagnóstico
  async getResumenConDiagnostico(): Promise<any> {
    const url = `${this.baseUrl}/resumen?incluir_diagnostico=true`
    console.log('🔍 [Cobranzas] Obteniendo resumen con diagnóstico...')

    try {
      const result = await apiClient.get(url, { timeout: 60000 })
      console.log('✅ [Cobranzas] Resumen con diagnóstico recibido:', result)
      return result
    } catch (error: any) {
      console.error('❌ [Cobranzas] Error obteniendo resumen con diagnóstico:', error)
      throw error
    }
  }

  // Actualizar analista de un préstamo
  // Si el valor contiene @ es un email (usuario_proponente), si no es un nombre (analista)
  async actualizarAnalista(prestamoId: number, analistaValue: string): Promise<any> {
    const { prestamoService } = await import('./prestamoService')
    const isEmail = analistaValue.includes('@')

    if (isEmail) {
      // Es un email, actualizar usuario_proponente
      return await prestamoService.updatePrestamo(prestamoId, { usuario_proponente: analistaValue })
    } else {
      // Es un nombre, actualizar analista
      return await prestamoService.updatePrestamo(prestamoId, { analista: analistaValue })
    }
  }

  // Actualizar ML Impago manual de un préstamo
  async actualizarMLImpago(
    prestamoId: number,
    nivelRiesgo: string,
    probabilidadImpago: number
  ): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/prestamos/${prestamoId}/ml-impago`, {
      nivel_riesgo: nivelRiesgo,
      probabilidad_impago: probabilidadImpago,
    })
  }

  // Eliminar ML Impago manual de un préstamo (volver a usar valores calculados)
  async eliminarMLImpagoManual(prestamoId: number): Promise<any> {
    return await apiClient.delete(`${this.baseUrl}/prestamos/${prestamoId}/ml-impago`)
  }
}

export const cobranzasService = new CobranzasService()

