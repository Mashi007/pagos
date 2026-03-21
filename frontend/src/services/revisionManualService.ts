import { apiClient } from './api'

export interface PrestamoDetalleRevision {
  prestamo_id: number
  cliente_id: number
  cedula: string
  nombres: string
  total_prestamo: number
  total_abonos: number
  saldo: number
  cuotas_vencidas: number
  cuotas_morosas: number
  estado_revision: string
  fecha_revision: string | null
}

export interface ResumenRevisionManual {
  total_prestamos: number
  prestamos_revisados: number
  prestamos_pendientes: number
  porcentaje_completado: number
  prestamos: PrestamoDetalleRevision[]
}

class RevisionManualService {
  private baseUrl = '/api/v1/revision-manual'

  /**
   * Obtiene lista de prÃ©stamos para revisiÃ³n manual (paginada, 20 por defecto)
   * @param cedula - BÃºsqueda por cÃ©dula para acceder a un caso especÃ­fico
   */
  async getPreslamosRevision(
    filtro?: 'todos' | 'pendientes' | 'revisados' | 'revisando',
    page = 1,
    perPage = 20,
    cedula?: string
  ): Promise<ResumenRevisionManual> {
    const params = new URLSearchParams()
    if (filtro && filtro !== 'todos') {
      const estadoMap: Record<string, string> = {
        'pendientes': 'pendiente',
        'revisados': 'revisado',
        'revisando': 'revisando'
      }
      params.set('filtro_estado', estadoMap[filtro])
    }
    params.set('limit', String(perPage))
    params.set('offset', String((page - 1) * perPage))
    if (cedula?.trim()) params.set('cedula', cedula.trim())
    return await apiClient.get(`${this.baseUrl}/prestamos?${params}`)
  }

  /**
   * Confirma un prÃ©stamo como revisado (Â¿SÃ­?)
   */
  async confirmarPrestamoRevisado(prestamoId: number): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/prestamos/${prestamoId}/confirmar`, {})
  }

  /**
   * Inicia revisiÃ³n de un prÃ©stamo (Â¿No? - cambia a 'revisando')
   */
  async iniciarRevision(prestamoId: number): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/prestamos/${prestamoId}/iniciar-revision`, {})
  }

  /**
   * Finaliza revisiÃ³n (Guardar y Cerrar - cambia a 'revisado')
   */
  async finalizarRevision(prestamoId: number): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/prestamos/${prestamoId}/finalizar-revision`, {})
  }

  /**
   * Edita datos del cliente
   */
  async editarCliente(clienteId: number, datos: any): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/clientes/${clienteId}`, datos, {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  /**
   * Edita datos del prÃ©stamo
   */
  async editarPrestamo(prestamoId: number, datos: any): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/prestamos/${prestamoId}`, datos, {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  /**
   * Elimina un prÃ©stamo (y sus cuotas)
   */
  async eliminarPrestamo(prestamoId: number): Promise<any> {
    return await apiClient.delete(`${this.baseUrl}/prestamos/${prestamoId}`)
  }

  /**
   * Obtiene pagos por cÃ©dula para ediciÃ³n
   */
  async getPagosPorCedula(cedula: string): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/pagos/${cedula}`)
  }

  /**
   * Obtiene datos completos de un prÃ©stamo para ediciÃ³n
   */
  async getDetallePrestamoRevision(prestamoId: number): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/prestamos/${prestamoId}/detalle`)
  }

  /**
   * Obtiene lista de estados de clientes desde la BD (para dropdown).
   * Usa endpoint de clientes para centralizar.
   */
  async getEstadosCliente(): Promise<{ estados: Array<{ valor: string; etiqueta: string; orden: number }> }> {
    return await apiClient.get('/api/v1/clientes/estados')
  }

  /**
   * Obtiene resumen rÃ¡pido de revisiÃ³n
   */
  async getResumenRapidoRevision(): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/resumen-rapido`)
  }

  /**
   * Edita datos de una cuota (fecha_pago, total_pagado, estado)
   */
  async editarCuota(cuotaId: number, datos: any): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/cuotas/${cuotaId}`, datos, {
      headers: { 'Content-Type': 'application/json' }
    })
  }
}

export const revisionManualService = new RevisionManualService()
