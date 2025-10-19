import { apiClient } from './api'

export interface Pago {
  id: number
  cedula_cliente: string
  fecha_pago: string
  monto_pagado: number
  numero_documento: string
  documento_nombre?: string
  documento_tipo?: string
  documento_tamaño?: number
  documento_ruta?: string
  conciliado: boolean
  fecha_conciliacion?: string
  activo: boolean
  notas?: string
  fecha_registro: string
  fecha_actualizacion: string
}

export interface PagoCreate {
  cedula_cliente: string
  fecha_pago: string
  monto_pagado: number
  numero_documento: string
  documento_nombre?: string
  documento_tipo?: string
  documento_tamaño?: number
  documento_ruta?: string
  notas?: string
}

export interface PagoUpdate {
  fecha_pago?: string
  monto_pagado?: number
  numero_documento?: string
  documento_nombre?: string
  documento_tipo?: string
  documento_tamaño?: number
  documento_ruta?: string
  notas?: string
  activo?: boolean
}

export interface PagoListResponse {
  pagos: Pago[]
  total: number
  pagina: number
  por_pagina: number
  total_paginas: number
}

export interface KPIsPagos {
  total_pagos: number
  total_dolares: number
  numero_pagos: number
  cantidad_conciliada: number
  cantidad_no_conciliada: number
  fecha_actualizacion: string
}

export interface ResumenCliente {
  cedula_cliente: string
  total_pagado: number
  total_conciliado: number
  total_pendiente: number
  numero_pagos: number
  ultimo_pago?: string
  estado_conciliacion: string
}

export interface ConciliacionCreate {
  cedula_cliente: string
  numero_documento_anterior: string
  numero_documento_nuevo: string
  cedula_nueva: string
  nota: string
}

export interface ConciliacionResponse {
  id: number
  cedula_cliente: string
  numero_documento_anterior: string
  numero_documento_nuevo: string
  cedula_nueva: string
  nota: string
  fecha: string
  responsable: string
  pago_id: number
}

export interface EstadoConciliacion {
  estadisticas: {
    total_pagos: number
    pagos_conciliados: number
    pagos_pendientes: number
    porcentaje_conciliacion: number
  }
  fecha_actualizacion: string
}

export interface ResultadoConciliacion {
  success: boolean
  message: string
  resumen: {
    total_registros: number
    conciliados: number
    pendientes: number
  }
  resultados: Array<{
    fila: number
    fecha: string
    numero_documento: string
    estado: string
    pago_id?: number
  }>
}

class PagoService {
  private baseUrl = '/api/v1/pagos'
  private conciliacionUrl = '/api/v1/conciliacion-bancaria'

  // ============================================
  // CRUD PAGOS
  // ============================================

  async crearPago(pago: PagoCreate): Promise<Pago> {
    const response = await apiClient.post(`${this.baseUrl}/crear`, pago)
    return (response as any).data
  }

  async listarPagos(params?: {
    pagina?: number
    por_pagina?: number
    cedula?: string
    conciliado?: boolean
  }): Promise<PagoListResponse> {
    const response = await apiClient.get(this.baseUrl + '/listar', { params })
    return (response as any).data
  }

  async obtenerPago(id: number): Promise<Pago> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`)
    return (response as any).data
  }

  async actualizarPago(id: number, pago: PagoUpdate): Promise<Pago> {
    const response = await apiClient.put(`${this.baseUrl}/${id}`, pago)
    return (response as any).data
  }

  async eliminarPago(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  // ============================================
  // KPIs Y RESUMEN
  // ============================================

  async obtenerKPIs(): Promise<KPIsPagos> {
    const response = await apiClient.get(`${this.baseUrl}/kpis`)
    return (response as any).data
  }

  async obtenerResumenCliente(cedula: string): Promise<ResumenCliente> {
    const response = await apiClient.get(`${this.baseUrl}/resumen-cliente/${cedula}`)
    return (response as any).data
  }

  // ============================================
  // DOCUMENTOS
  // ============================================

  async subirDocumento(file: File): Promise<{
    success: boolean
    filename: string
    original_name: string
    size: number
    type: string
    path: string
  }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post(`${this.baseUrl}/subir-documento`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return (response as any).data
  }

  async descargarDocumento(filename: string): Promise<{
    success: boolean
    filename: string
    content_type: string
    download_url: string
  }> {
    const response = await apiClient.get(`${this.baseUrl}/descargar-documento/${filename}`)
    return (response as any).data
  }

  // ============================================
  // CONCILIACIÓN BANCARIA
  // ============================================

  async generarTemplateConciliacion(): Promise<{
    success: boolean
    message: string
    filename: string
    content: ArrayBuffer
  }> {
    const response = await apiClient.get(`${this.conciliacionUrl}/template-conciliacion`)
    return (response as any).data
  }

  async procesarConciliacion(file: File): Promise<ResultadoConciliacion> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post(`${this.conciliacionUrl}/procesar-conciliacion`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return (response as any).data
  }

  async desconciliarPago(conciliacion: ConciliacionCreate): Promise<ConciliacionResponse> {
    const response = await apiClient.post(`${this.conciliacionUrl}/desconciliar-pago`, conciliacion)
    return (response as any).data
  }

  async obtenerEstadoConciliacion(): Promise<EstadoConciliacion> {
    const response = await apiClient.get(`${this.conciliacionUrl}/estado-conciliacion`)
    return (response as any).data
  }

  // ============================================
  // UTILIDADES
  // ============================================

  async validarCedula(cedula: string): Promise<{ valido: boolean; mensaje?: string }> {
    try {
      const response = await apiClient.get(`/api/v1/validadores/cedula/${cedula}`)
      return (response as any).data
    } catch (error) {
      return { valido: false, mensaje: 'Error validando cédula' }
    }
  }

  async validarMonto(monto: number): Promise<{ valido: boolean; mensaje?: string }> {
    try {
      const response = await apiClient.get(`/api/v1/validadores/monto/${monto}`)
      return (response as any).data
    } catch (error) {
      return { valido: false, mensaje: 'Error validando monto' }
    }
  }

  async validarFecha(fecha: string): Promise<{ valido: boolean; mensaje?: string }> {
    try {
      const response = await apiClient.get(`/api/v1/validadores/fecha/${fecha}`)
      return (response as any).data
    } catch (error) {
      return { valido: false, mensaje: 'Error validando fecha' }
    }
  }

  // ============================================
  // DESCARGAR TEMPLATE
  // ============================================

  async descargarTemplateConciliacion(): Promise<void> {
    try {
      const response = await apiClient.get(`${this.conciliacionUrl}/template-conciliacion`, {
        responseType: 'blob'
      })
      
      const blob = new Blob([(response as any).data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Template_Conciliacion_${new Date().toISOString().split('T')[0]}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error descargando template:', error)
      throw new Error('Error al descargar el template')
    }
  }
}

export const pagoService = new PagoService()
