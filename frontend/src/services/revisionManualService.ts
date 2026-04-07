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





   * Obtiene lista de préstamos para revisión manual (paginada, 20 por defecto)





   * @param cedula - Búsqueda por cédula para acceder a un caso específico





   */

  async getPrestamosRevision(
    filtro?: 'todos' | 'pendientes' | 'revisados' | 'revisando',

    page = 1,

    perPage = 20,

    cedula?: string
  ): Promise<ResumenRevisionManual> {
    const params = new URLSearchParams()

    if (filtro && filtro !== 'todos') {
      const estadoMap: Record<string, string> = {
        pendientes: 'pendiente',

        revisados: 'revisado',

        revisando: 'revisando',
      }

      params.set('filtro_estado', estadoMap[filtro])
    }

    params.set('limit', String(perPage))

    params.set('offset', String((page - 1) * perPage))

    if (cedula?.trim()) params.set('cedula', cedula.trim())

    return await apiClient.get(`${this.baseUrl}/prestamos?${params}`)
  }

  /**





   * Confirma un préstamo como revisado (¿Sí?)





   */

  async confirmarPrestamoRevisado(prestamoId: number): Promise<any> {
    return await apiClient.put(
      `${this.baseUrl}/prestamos/${prestamoId}/confirmar`,
      {}
    )
  }

  /**





   * Inicia revisión de un préstamo (¿No? - cambia a 'revisando')





   */

  async iniciarRevision(prestamoId: number): Promise<any> {
    return await apiClient.put(
      `${this.baseUrl}/prestamos/${prestamoId}/iniciar-revision`,
      {}
    )
  }

  /**





   * Finaliza revisión (Guardar y Cerrar - cambia a 'revisado')





   */

  async finalizarRevision(prestamoId: number): Promise<any> {
    return await apiClient.put(
      `${this.baseUrl}/prestamos/${prestamoId}/finalizar-revision`,
      {}
    )
  }

  /**





   * Edita datos del cliente





   */

  async editarCliente(
    clienteId: number,
    datos: any,
    opts?: { prestamoId: number }
  ): Promise<any> {
    const q =
      opts?.prestamoId != null
        ? `?prestamo_id=${encodeURIComponent(String(opts.prestamoId))}`
        : ''
    return await apiClient.put(
      `${this.baseUrl}/clientes/${clienteId}${q}`,
      datos,
      {
        headers: { 'Content-Type': 'application/json' },
      }
    )
  }

  /**





   * Edita datos del préstamo





   */

  async editarPrestamo(prestamoId: number, datos: any): Promise<any> {
    return await apiClient.put(
      `${this.baseUrl}/prestamos/${prestamoId}`,
      datos,
      {
        headers: { 'Content-Type': 'application/json' },
      }
    )
  }

  /**
   * Persiste préstamo (mismo payload que editarPrestamo) y reconstruye cuotas en una sola operación en BD.
   */
  async guardarPrestamoYReconstruirCuotas(
    prestamoId: number,
    datos: Record<string, unknown>
  ): Promise<any> {
    return await apiClient.post(
      `${this.baseUrl}/prestamos/${prestamoId}/guardar-prestamo-y-reconstruir-cuotas`,
      datos,
      { headers: { 'Content-Type': 'application/json' } }
    )
  }

  /**





   * Elimina un préstamo (y sus cuotas)





   */

  async eliminarPrestamo(prestamoId: number): Promise<any> {
    return await apiClient.delete(`${this.baseUrl}/prestamos/${prestamoId}`)
  }

  /**





   * Obtiene pagos por cédula para edición





   */

  async getPagosPorCedula(cedula: string): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/pagos/${cedula}`)
  }

  /**





   * Obtiene datos completos de un préstamo para edición





   */

  async getDetallePrestamoRevision(prestamoId: number): Promise<any> {
    return await apiClient.get(
      `${this.baseUrl}/prestamos/${prestamoId}/detalle`
    )
  }

  /**





   * Obtiene lista de estados de clientes desde la BD (para dropdown).





   * Usa endpoint de clientes para centralizar.





   */

  async getEstadosCliente(): Promise<{
    estados: Array<{ valor: string; etiqueta: string; orden: number }>
  }> {
    return await apiClient.get('/api/v1/clientes/estados')
  }

  /**





   * Obtiene resumen rápido de revisión





   */

  async getResumenRapidoRevision(): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/resumen-rapido`)
  }

  /**





   * Edita datos de una cuota (fecha_pago, total_pagado, estado)





   */

  async editarCuota(cuotaId: number, datos: any): Promise<any> {
    return await apiClient.put(`${this.baseUrl}/cuotas/${cuotaId}`, datos, {
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async eliminarCuota(prestamoId: number, cuotaId: number): Promise<any> {
    return await apiClient.delete(
      `${this.baseUrl}/prestamos/${prestamoId}/cuotas/${cuotaId}`
    )
  }

  /**
   * Cambia el estado de revisión de un préstamo
   * Estados: "revisando", "en_espera", "revisado"
   */
  async cambiarEstadoRevision(
    prestamoId: number,
    datos: {
      nuevo_estado: string
      observaciones?: string
      motivo_rechazo?: string
    }
  ): Promise<any> {
    return await apiClient.patch(
      `${this.baseUrl}/prestamos/${prestamoId}/estado-revision`,
      datos,
      {
        headers: { 'Content-Type': 'application/json' },
      }
    )
  }

  /**
   * Operario (no admin): préstamo en Visto (revisado) - registra solicitud para que un administrador reabra.
   */
  async solicitarReaperturaRevision(
    prestamoId: number,
    payload?: { mensaje?: string | null }
  ): Promise<{
    solicitud_id: number
    ya_registrada: boolean
    mensaje: string
  }> {
    return await apiClient.post(
      `${this.baseUrl}/prestamos/${prestamoId}/solicitar-reapertura-revision`,
      payload ?? {},
      { headers: { 'Content-Type': 'application/json' } }
    )
  }

  /** Solo administrador: cola de solicitudes de reapertura. */
  async getAutorizacionesReaperturaPendientes(): Promise<
    Array<{
      id: number
      prestamo_id: number
      cedula: string
      nombres_cliente: string
      solicitante_nombre: string
      solicitante_apellido: string
      solicitante_email: string | null
      mensaje: string | null
      creado_en: string
    }>
  > {
    const raw: unknown = await apiClient.get(
      `${this.baseUrl}/autorizaciones-reapertura/pendientes`
    )
    if (Array.isArray(raw)) {
      return raw as Array<{
        id: number
        prestamo_id: number
        cedula: string
        nombres_cliente: string
        solicitante_nombre: string
        solicitante_apellido: string
        solicitante_email: string | null
        mensaje: string | null
        creado_en: string
      }>
    }
    if (
      raw != null &&
      typeof raw === 'object' &&
      Array.isArray((raw as { items?: unknown }).items)
    ) {
      return (raw as { items: unknown[] }).items as Array<{
        id: number
        prestamo_id: number
        cedula: string
        nombres_cliente: string
        solicitante_nombre: string
        solicitante_apellido: string
        solicitante_email: string | null
        mensaje: string | null
        creado_en: string
      }>
    }
    return []
  }

  async aprobarSolicitudReapertura(
    solicitudId: number,
    payload?: { nota?: string | null }
  ): Promise<{
    mensaje: string
    prestamo_id: number
    solicitud_id: number
    nuevo_estado_revision: string
  }> {
    return await apiClient.patch(
      `${this.baseUrl}/autorizaciones-reapertura/${solicitudId}/aprobar`,
      payload ?? {},
      { headers: { 'Content-Type': 'application/json' } }
    )
  }

  async rechazarSolicitudReapertura(
    solicitudId: number,
    payload?: { nota?: string | null }
  ): Promise<{ mensaje: string; prestamo_id: number; solicitud_id: number }> {
    return await apiClient.patch(
      `${this.baseUrl}/autorizaciones-reapertura/${solicitudId}/rechazar`,
      payload ?? {},
      { headers: { 'Content-Type': 'application/json' } }
    )
  }
}

export const revisionManualService = new RevisionManualService()
