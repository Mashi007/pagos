import { apiClient, ApiResponse, PaginatedResponse, buildUrl } from './api'

import {
  Cliente,
  ClienteForm,
  ClienteFilters,
  ActualizarClienteLoteItem,
} from '../types'

import { logger } from '../utils/logger'

import {
  extraerCaracteresCedulaPublica,
  normalizarBusquedaPrestamosSearch,
  normalizarCedulaParaProcesar,
} from '../utils/cedulaConsultaPublica'

// Constantes de configuración

const DEFAULT_PER_PAGE = 20

class ClienteService {
  private baseUrl = '/api/v1/clientes'

  // Obtener lista de clientes con filtros y paginación

  async getClientes(
    filters?: ClienteFilters,

    page: number = 1,

    perPage: number = DEFAULT_PER_PAGE
  ): Promise<PaginatedResponse<Cliente>> {
    const params: Record<string, any> = { ...filters, page, per_page: perPage }

    if (typeof params.search === 'string' && params.search.trim()) {
      params.search = normalizarBusquedaPrestamosSearch(params.search)
    }

    if (typeof params.cedula === 'string' && params.cedula.trim()) {
      const raw = params.cedula.trim()

      const v = normalizarCedulaParaProcesar(raw)

      if (v.valido && v.valorParaEnviar) {
        params.cedula = v.valorParaEnviar
      } else {
        const ext = extraerCaracteresCedulaPublica(raw)

        if (ext) params.cedula = ext
      }
    }

    const url = buildUrl(this.baseUrl, params)

    const response = await apiClient.get<any>(url)

    // Adaptar respuesta del backend al formato esperado

    // ✅ CORRECCIÓN: Asegurar que data siempre sea un array

    const clientesArray = Array.isArray(response.clientes)
      ? response.clientes
      : response.clientes
        ? [response.clientes]
        : []

    const adaptedResponse = {
      data: clientesArray,

      total: response.total || 0,

      page: response.page || page,

      per_page: response.per_page || response.limit || perPage,

      total_pages:
        response.total_pages || Math.ceil((response.total || 0) / perPage),
    }

    return adaptedResponse
  }

  // Obtener cliente por ID

  async getCliente(id: string): Promise<Cliente> {
    // El endpoint devuelve ClienteResponse directamente, sin envolver en ApiResponse

    const response = await apiClient.get<Cliente>(`${this.baseUrl}/${id}`)

    return response
  }

  // Obtener estados de cliente desde BD (para dropdowns en formularios)

  async getEstadosCliente(): Promise<{
    estados: Array<{ valor: string; etiqueta: string; orden: number }>
  }> {
    return await apiClient.get(`${this.baseUrl}/estados`)
  }

  // Comprobar qué cédulas ya existen (para carga masiva: advertir antes de guardar)

  async checkCedulas(
    cedulas: string[]
  ): Promise<{ existing_cedulas: string[] }> {
    if (!cedulas.length) return { existing_cedulas: [] }

    const response = await apiClient.post<{ existing_cedulas: string[] }>(
      `${this.baseUrl}/check-cedulas`,

      { cedulas }
    )

    return response
  }

  // Comprobar qué emails ya existen en clientes (correo 1 o correo 2; carga masiva)

  async checkEmails(emails: string[]): Promise<{ existing_emails: string[] }> {
    if (!emails.length) return { existing_emails: [] }

    const response = await apiClient.post<{ existing_emails: string[] }>(
      `${this.baseUrl}/check-emails`,

      { emails }
    )

    return response
  }

  // Crear nuevo cliente

  async createCliente(data: ClienteForm): Promise<Cliente> {
    // El endpoint devuelve ClienteResponse directamente

    const response = await apiClient.post<Cliente>(this.baseUrl, data)

    return response
  }

  // Actualizar cliente

  async updateCliente(
    id: string,
    data: Partial<ClienteForm>
  ): Promise<Cliente> {
    // El endpoint devuelve ClienteResponse directamente

    const response = await apiClient.put<Cliente>(`${this.baseUrl}/${id}`, data)

    return response
  }

  // Eliminar cliente

  async deleteCliente(id: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  // --- Revisar Clientes (clientes_con_errores) ---

  /** Lista de clientes enviados a revisión (paginado) */

  async getClientesConErrores(
    page = 1,

    perPage = 20
  ): Promise<{
    total: number
    page: number
    per_page: number
    items: Array<{
      id: number

      cedula: string | null

      nombres: string | null

      email: string | null

      telefono: string | null

      errores: string | null

      fila_origen: number | null

      estado: string | null

      fecha_registro: string | null
    }>
  }> {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    })

    return await apiClient.get(`${this.baseUrl}/revisar/lista?${params}`)
  }

  /** Enviar una fila a Revisar Clientes (desde carga masiva). Elimina de pantalla al enviar. */

  async agregarClienteARevisar(data: {
    cedula?: string | null

    nombres?: string | null

    direccion?: string | null

    fecha_nacimiento?: string | null

    ocupacion?: string | null

    email?: string | null

    telefono?: string | null

    errores_descripcion?: string | null

    fila_origen?: number | null
  }): Promise<{ id: number; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/revisar/agregar`, data)
  }

  /** Eliminar de la lista Revisar Clientes (marcar como resuelto) */

  async resolverClienteError(errorId: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/revisar/${errorId}`)
  }

  // Obtener cliente por cédula exacta (para carga masiva de préstamos)

  async getClienteByCedula(cedula: string): Promise<Cliente | null> {
    if (!cedula?.trim()) return null

    const rawTrim = cedula.trim()

    const nv = normalizarCedulaParaProcesar(rawTrim)

    const clave =
      nv.valido && nv.valorParaEnviar
        ? nv.valorParaEnviar
        : extraerCaracteresCedulaPublica(rawTrim)

    const list = await this.searchClientes(rawTrim, true)

    const exact = list.find(
      c => extraerCaracteresCedulaPublica(c.cedula || '') === clave
    )

    return exact ?? null
  }

  // Buscar clientes por término (usando filtros en endpoint principal)

  // IMPORTANTE: Por defecto filtra solo clientes ACTIVOS para formularios de préstamos

  // Para buscar todos los estados, pasar incluirTodosEstados: true

  async searchClientes(
    query: string,
    incluirTodosEstados: boolean = false
  ): Promise<Cliente[]> {
    const filters: ClienteFilters = { search: query }

    // Por defecto filtrar solo ACTIVOS (para formularios de préstamos)

    // Solo incluir todos los estados si se especifica explícitamente

    if (!incluirTodosEstados) {
      filters.estado = 'ACTIVO'
    }

    const response = await this.getClientes(filters, 1, 100)

    return response.data
  }

  // Obtener clientes por analista (usando filtros en endpoint principal)

  async getClientesByAnalista(analistaId: string): Promise<Cliente[]> {
    const filters: ClienteFilters = {}

    const response = await this.getClientes(filters, 1, 100)

    return response.data
  }

  // Obtener clientes en mora (usando filtro estado en endpoint principal)

  async getClientesEnMora(): Promise<Cliente[]> {
    const filters: ClienteFilters = { estado: 'MORA' }

    const response = await this.getClientes(filters, 1, 100)

    return response.data
  }

  // Obtener historial de pagos de un cliente

  async getHistorialPagos(clienteId: string): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>(
      `${this.baseUrl}/${clienteId}/pagos`
    )

    return response.data
  }

  // Obtener tabla de amortización de un cliente

  async getTablaAmortizacion(clienteId: string): Promise<any[]> {
    const response = await apiClient.get<ApiResponse<any[]>>(
      `${this.baseUrl}/${clienteId}/amortizacion`
    )

    return response.data
  }

  // Validar cédula

  async validateCedula(
    cedula: string
  ): Promise<{ valid: boolean; message?: string }> {
    const response = await apiClient.post<
      ApiResponse<{ valid: boolean; message?: string }>
    >(
      `${this.baseUrl}/validate-cedula`,

      { cedula }
    )

    return response.data
  }

  // Obtener estadísticas de cliente

  async getEstadisticasCliente(clienteId: string): Promise<any> {
    const response = await apiClient.get<ApiResponse<any>>(
      `${this.baseUrl}/${clienteId}/estadisticas`
    )

    return response.data
  }

  // Obtener estadísticas generales de todos los clientes

  /**
   * finalizados: clientes con estado FINALIZADO o con al menos un préstamo LIQUIDADO (sin duplicar).
   * nuevos_este_mes: filas en clientes con fecha_registro en el mes actual (calendario America/Caracas).
   */
  async getStats(): Promise<{
    total: number
    activos: number
    inactivos: number
    finalizados: number
    nuevos_este_mes: number
    ultima_actualizacion?: string | null
  }> {
    const response = await apiClient.get<{
      total: number
      activos: number
      inactivos: number
      finalizados: number
      nuevos_este_mes: number
      ultima_actualizacion?: string | null
    }>(`${this.baseUrl}/stats`)

    return response
  }

  // Obtener estadísticas del embudo de clientes

  // NOTA: El backend no tiene /embudo/estadisticas; se calculan desde stats de clientes

  async getEstadisticasEmbudo(): Promise<{
    total: number
    prospectos: number
    evaluacion: number
    aprobados: number
    rechazados: number
  }> {
    try {
      const stats = await this.getStats()

      return {
        total: stats.total,

        prospectos: stats.activos,

        evaluacion: stats.inactivos,

        aprobados: stats.finalizados,

        rechazados: 0,
      }
    } catch {
      return {
        total: 0,
        prospectos: 0,
        evaluacion: 0,
        aprobados: 0,
        rechazados: 0,
      }
    }
  }

  // Cambiar estado de cliente (el backend devuelve Cliente directamente, no envuelto en ApiResponse)

  async cambiarEstado(
    clienteId: string,
    estado: Cliente['estado']
  ): Promise<Cliente> {
    const response = await apiClient.patch<Cliente>(
      `${this.baseUrl}/${clienteId}/estado`,

      { estado }
    )

    return response
  }

  // Importar clientes desde Excel (usando endpoint de carga masiva)

  async importarClientes(
    file: File
  ): Promise<{ success: number; errors: any[] }> {
    const response = await apiClient.uploadFile<
      ApiResponse<{ success: number; errors: any[] }>
    >(
      '/api/v1/carga-masiva/clientes',

      file
    )

    return response.data
  }

  // Buscar cliente por número de teléfono

  async buscarClientePorTelefono(telefono: string): Promise<Cliente | null> {
    try {
      const filters: ClienteFilters = { search: telefono }

      const response = await this.getClientes(filters, 1, 1)

      return response.data.length > 0 ? response.data[0] : null
    } catch (error) {
      logger.error('Error buscando cliente por teléfono', { error, telefono })

      return null
    }
  }

  // Obtener clientes con problemas de validación (usa /casos-a-revisar del backend)

  async getClientesConProblemasValidacion(
    page: number = 1,

    perPage: number = 20
  ): Promise<PaginatedResponse<any>> {
    return this.getCasosARevisar(page, perPage)
  }

  // Obtener casos a revisar (clientes con placeholders: Z999999999, Revisar Nombres, +589999999999, revisar@email.com)

  async getCasosARevisar(
    page: number = 1,

    perPage: number = 50
  ): Promise<PaginatedResponse<Cliente>> {
    const url = buildUrl(`${this.baseUrl}/casos-a-revisar`, {
      page,
      per_page: perPage,
    })

    const response = await apiClient.get<any>(url)

    return {
      data: response.clientes || [],

      total: response.total || 0,

      page: response.page || page,

      per_page: response.per_page || perPage,

      total_pages:
        response.total_pages || Math.ceil((response.total || 0) / perPage),
    }
  }

  // Actualizar múltiples clientes en lote

  async actualizarClientesLote(
    actualizaciones: ActualizarClienteLoteItem[]
  ): Promise<{
    actualizados: number

    errores: Array<{ id: number | null; error: string }>

    total_procesados: number
  }> {
    const response = await apiClient.post<any>(
      `${this.baseUrl}/actualizar-lote`,
      actualizaciones
    )

    return response
  }

  // Eliminar clientes con errores tras su descarga en Excel

  async eliminarPorDescarga(ids: number[]): Promise<{ deleted: number }> {
    return apiClient.post(this.baseUrl + '/revisar/eliminar-por-descarga', ids)
  }

  /** Snapshot Drive (CONCILIACIÓN): candidatos a alta no presentes en tabla clientes. Solo admin. */
  async getDriveImportCandidatos(fresh?: boolean): Promise<{
    drive_synced_at: string | null
    total_candidatos: number
    from_cache?: boolean
    cache_computed_at?: string | null
    candidatos: Array<{
      sheet_row_number: number
      col_d_nombres: string | null
      col_e_cedula: string | null
      col_f_telefono: string | null
      col_g_email: string | null
      cedula_cmp: string
      cedula_valida: boolean
      cedula_error: string | null
      cedula_para_crear: string | null
      duplicada_en_hoja: boolean
      /** Columna D: nombre completo no duplicado en `clientes.nombres` (misma regla que POST /clientes). */
      nombres_valido?: boolean
      nombres_error?: string | null
      /** Columna G: correo no duplicado en `clientes.email` ni `email_secundario`. */
      email_valido?: boolean
      email_error?: string | null
      telefono_valida?: boolean
      telefono_error?: string | null
      seleccionable: boolean
      defaults: {
        nombres: string
        telefono: string
        email: string
        direccion: string
        fecha_nacimiento: string
        ocupacion: string
        estado: string
      }
    }>
  }> {
    const q = fresh ? '?fresh=true' : ''
    return apiClient.get(`${this.baseUrl}/drive-import/candidatos${q}`)
  }

  async postDriveImportRefreshCache(): Promise<{
    ok: boolean
    total_candidatos?: number
    drive_synced_at?: string | null
    computed_at?: string | null
  }> {
    return apiClient.post(`${this.baseUrl}/drive-import/refresh-cache`, {})
  }

  /** Alta de una fila con payload validado como ClienteCreate (mismo POST /clientes). Solo admin. */
  async postDriveImportImportarFila(body: {
    sheet_row_number: number
    cedula: string
    nombres: string
    telefono: string
    email: string
    email_secundario?: string | null
    direccion: string
    fecha_nacimiento: string
    ocupacion: string
    estado?: string
    notas?: string | null
    comentario?: string | null
  }): Promise<{
    ok: boolean
    batch_id: string
    cliente_id: number
    cedula: string
  }> {
    return apiClient.post(`${this.baseUrl}/drive-import/importar-fila`, body)
  }

  async postDriveImportImportar(body: {
    sheet_row_numbers: number[]
    comentario?: string | null
  }): Promise<{
    batch_id: string
    insertados_ok: number
    errores: number
    lote_abortado?: boolean
    resultados: Array<{
      sheet_row_number: number
      ok: boolean
      cliente_id?: number
      error?: string
    }>
  }> {
    return apiClient.post(`${this.baseUrl}/drive-import/importar`, body)
  }

  /**
   * Excel de candidatos Drive; en servidor borra las filas exportadas de `drive` en BD
   * (vuelven con el próximo sync desde Google). modo: solo_no_seleccionable = rojo/ámbar.
   */
  async postDriveImportExportarExcel(
    modo: 'solo_no_seleccionable' | 'todos_candidatos'
  ): Promise<void> {
    await apiClient.postDownloadFile(
      `${this.baseUrl}/drive-import/exportar-excel`,
      { modo },
      `drive_candidatos_${modo}.xlsx`
    )
  }

  async getDriveImportAuditoria(
    page: number = 1,
    per_page: number = 50
  ): Promise<{
    total: number
    page: number
    per_page: number
    items: Array<{
      id: number
      batch_id: string
      sheet_row_number: number
      cedula: string
      nombres: string | null
      telefono: string | null
      email: string | null
      comentario: string | null
      usuario_email: string
      estado: string
      detalle_error: string | null
      creado_en: string | null
    }>
  }> {
    return apiClient.get(
      `${this.baseUrl}/drive-import/auditoria?page=${page}&per_page=${per_page}`
    )
  }
}

// Instancia singleton del servicio

export const clienteService = new ClienteService()
