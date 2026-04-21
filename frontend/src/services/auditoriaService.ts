import { apiClient } from './api'

/** POST ejecutar/corregir cartera recorre la BD y puede reaplicar muchas cascadas; 30s no alcanza en Render. */
const AUDITORIA_CARTERA_EJECUTAR_TIMEOUT_MS = 180000

const AUDITORIA_CARTERA_CORREGIR_TIMEOUT_MS = 300000

export interface Auditoria {
  id: number

  usuario_id?: number

  usuario_email?: string

  accion: string

  modulo: string

  tabla: string

  registro_id?: number

  descripcion?: string

  campo?: string // Campo modificado (para auditorías detalladas)

  datos_anteriores?: any

  datos_nuevos?: any

  ip_address?: string

  user_agent?: string

  resultado: string

  mensaje_error?: string

  fecha: string
}

export interface AuditoriaListResponse {
  items: Auditoria[]

  total: number

  page: number

  page_size: number

  total_pages: number
}

export interface AuditoriaStats {
  total_acciones: number

  acciones_por_modulo: Record<string, number>

  acciones_por_usuario: Record<string, number>

  acciones_hoy: number

  acciones_esta_semana: number

  acciones_este_mes: number
}

export interface AuditoriaFilters {
  skip?: number

  limit?: number

  usuario_email?: string

  modulo?: string

  accion?: string

  fecha_desde?: string

  fecha_hasta?: string

  ordenar_por?: string

  orden?: string
}

export interface ControlCartera {
  codigo: string
  titulo: string
  alerta: 'SI' | 'NO'
  detalle: string
}

export interface PrestamoCarteraChequeo {
  prestamo_id: number
  cliente_id: number
  cedula: string
  nombres: string
  estado_prestamo: string
  cliente_email: string
  tiene_alerta: boolean
  controles: ControlCartera[]
}

export interface AuditoriaCarteraResumenResponse {
  resumen: Record<string, unknown>

  meta_ultima_corrida: Record<string, unknown>
}

export interface PrestamoCarteraChequeoResponse {
  items: PrestamoCarteraChequeo[]
  resumen: Record<string, unknown>
  meta_ultima_corrida: Record<string, unknown>
  /** Presente en POST ejecutar/corregir: cuotas escaneadas y estados actualizados. */
  sincronizar_estado_cuotas?: {
    cuotas_escaneadas?: number
    estados_actualizados?: number
  } | null
}

/** GET /auditoria/prestamos/liquidados/auditoria-intensiva */
export interface LiquidadosCierreChequeoResponse {
  items: PrestamoCarteraChequeo[]

  resumen: Record<string, unknown>
}

export interface AuditoriaLiquidadosIntensivaResponse {
  cartera: PrestamoCarteraChequeoResponse

  cierre: LiquidadosCierreChequeoResponse
}

export interface AuditoriaLiquidadosIntensivaQuery {
  skip?: number

  limit?: number

  prestamo_id?: number

  cedula?: string

  excluir_marcar_ok?: boolean

  codigo_control?: string
}

/** GET /auditoria/prestamos/{id}/revision-descuadre-pagos-cuotas */
export interface RevisionDescuadrePagoItem {
  pago_id: number

  fecha_pago: string | null

  monto_pagado: string

  estado: string

  numero_documento: string

  referencia_pago: string

  moneda_registro: string

  conciliado: boolean

  cuenta_operativo_cartera: boolean

  sum_aplicado_cuotas: string

  saldo_sin_aplicar_usd: string
}

export interface RevisionDescuadreCuotaItem {
  cuota_id: number

  numero_cuota: number

  monto_cuota: string

  total_pagado: string

  estado: string
}

export interface RevisionDescuadrePagosCuotasResponse {
  prestamo_id: number

  estado_prestamo: string

  fecha_liquidado?: string | null

  sum_pagos_operativos_usd: string

  sum_aplicado_cuotas_usd: string

  diff_usd: string

  tolerancia_usd: string

  semaforo_cuadre: 'verde' | 'amarillo' | 'rojo' | string

  tiene_pago_operativo_sin_aplicar_fuera_tol: boolean

  pagos: RevisionDescuadrePagoItem[]

  cuotas: RevisionDescuadreCuotaItem[]
}

export interface CarteraCorreccionResponse extends PrestamoCarteraChequeoResponse {
  reaplicar_cascada?: Array<Record<string, unknown>>
}

/** POST solo sincroniza columna cuotas.estado (sin ejecutar motor de controles ni meta). */
export interface SincronizarEstadosCuotasResponse {
  cuotas_escaneadas: number

  estados_actualizados: number
}

/** Query GET /auditoria/prestamos/cartera/chequeos (paginacion y filtros en servidor). */
export interface CarteraChequeosQuery {
  skip?: number

  limit?: number

  prestamo_id?: number

  cedula?: string

  /**
   * Vista operativa: true = no listar (prestamo, control) con ultimo MARCAR_OK.
   * Fuera de eso, un caso solo sale de la lista si el motor deja SI (datos corregidos).
   */
  excluir_marcar_ok?: boolean

  /** Lista y paginacion solo sobre prestamos con este control en SI (conteos en resumen siguen globales). */
  codigo_control?: string
}

export interface CarteraRevisionOcultoPar {
  prestamo_id: number

  codigo_control: string
}

export interface CarteraRevisionOcultosResponse {
  ocultos: CarteraRevisionOcultoPar[]
}

export interface CarteraRevisionItem {
  id: number

  prestamo_id: number

  codigo_control: string

  tipo: string

  usuario_id: number

  usuario_email?: string

  nota?: string

  creado_en: string

  /** Snapshot al MARCAR_OK o metadatos minimos en REVOCAR_OK. */
  payload_snapshot?: Record<string, unknown> | null
}

/** Control 5: pagos en grupo duplicado (misma fecha y monto) por prestamo. */
export interface Control5DuplicadoFechaMontoItem {
  pago_id: number

  prestamo_id?: number | null

  fecha_pago?: string | null

  monto_pagado?: number | null

  conciliado: boolean

  estado_pago: string

  numero_documento: string

  referencia_pago: string

  institucion_bancaria: string
}

export interface Control5DuplicadosListaResponse {
  items: Control5DuplicadoFechaMontoItem[]
}

export interface Control5VistoResponse {
  pago_id: number

  prestamo_id?: number | null

  numero_documento_anterior?: string | null

  numero_documento_nuevo: string

  sufijo_cuatro_digitos: string

  auditoria_id: number
}

/** Control 15: detalle por pago (misma regla que motor pagos_sin_aplicacion_a_cuotas). */
export interface Control15PagoSinAplicacionItem {
  pago_id: number

  prestamo_id: number

  fecha_pago?: string | null

  monto_pagado: number

  sum_monto_aplicado_cuotas: number

  saldo_sin_aplicar_usd: number

  motivo: string
}

class AuditoriaService {
  private baseUrl = '/api/v1/auditoria'

  // Listar auditoría con filtros y paginación

  async listarAuditoria(
    filters?: AuditoriaFilters
  ): Promise<AuditoriaListResponse> {
    const response = await apiClient.get<AuditoriaListResponse>(this.baseUrl, {
      params: filters,
    })

    if (!response || typeof response !== 'object') {
      throw new Error('Respuesta invalida del servidor')
    }

    return {
      items: Array.isArray(response.items) ? response.items : [],

      total: typeof response.total === 'number' ? response.total : 0,

      page: typeof response.page === 'number' ? response.page : 1,

      page_size:
        typeof response.page_size === 'number' ? response.page_size : 10,

      total_pages:
        typeof response.total_pages === 'number' ? response.total_pages : 1,
    }
  }

  // Obtener estadísticas de auditoría

  async obtenerEstadisticas(): Promise<AuditoriaStats> {
    try {
      const response = await apiClient.get<AuditoriaStats>(
        `${this.baseUrl}/stats`
      )

      return response
    } catch (error) {
      console.error('❌ Error obteniendo estadísticas:', error)

      throw error
    }
  }

  // Exportar auditoría a Excel

  async exportarExcel(
    filters?: Omit<AuditoriaFilters, 'skip' | 'limit' | 'ordenar_por' | 'orden'>
  ): Promise<Blob> {
    try {
      const response: any = await apiClient.get(`${this.baseUrl}/exportar`, {
        params: filters,

        responseType: 'blob',
      })

      return response.data as Blob
    } catch (error) {
      console.error('❌ Error exportando Excel:', error)

      throw error
    }
  }

  // Obtener un registro de auditoría por ID

  async obtenerAuditoria(id: number): Promise<Auditoria> {
    try {
      const response = await apiClient.get<Auditoria>(`${this.baseUrl}/${id}`)

      return response
    } catch (error) {
      console.error('❌ Error obteniendo auditoría:', error)

      throw error
    }
  }

  // Registrar evento genérico de auditoría (confirmaciones, acciones manuales)

  async registrarEvento(params: {
    modulo: string

    accion: string

    descripcion: string

    registro_id?: number
  }): Promise<Auditoria> {
    const response = await apiClient.post<Auditoria>(
      `${this.baseUrl}/registrar`,
      params
    )

    return response
  }

  async listarCarteraChequeos(
    query?: CarteraChequeosQuery
  ): Promise<PrestamoCarteraChequeoResponse> {
    return apiClient.get<PrestamoCarteraChequeoResponse>(
      `${this.baseUrl}/prestamos/cartera/chequeos`,
      { params: query }
    )
  }

  /** Solo prestamos LIQUIDADO: cartera + hallazgos de cierre (finiquito, fecha, documentos). */
  async obtenerAuditoriaLiquidadosIntensiva(
    query?: AuditoriaLiquidadosIntensivaQuery
  ): Promise<AuditoriaLiquidadosIntensivaResponse> {
    return apiClient.get<AuditoriaLiquidadosIntensivaResponse>(
      `${this.baseUrl}/prestamos/liquidados/auditoria-intensiva`,
      { params: query }
    )
  }

  /** Detalle pagos vs aplicado cuotas (revision UI auditoria). */
  async obtenerRevisionDescuadrePagosCuotas(
    prestamoId: number
  ): Promise<RevisionDescuadrePagosCuotasResponse> {
    return apiClient.get<RevisionDescuadrePagosCuotasResponse>(
      `${this.baseUrl}/prestamos/${prestamoId}/revision-descuadre-pagos-cuotas`
    )
  }

  /** GET resumen sin items: mismos filtros opcionales que cartera (cedula, prestamo_id). */
  async obtenerCarteraResumen(params?: {
    cedula?: string

    prestamo_id?: number

    excluir_marcar_ok?: boolean

    codigo_control?: string
  }): Promise<AuditoriaCarteraResumenResponse> {
    return apiClient.get<AuditoriaCarteraResumenResponse>(
      `${this.baseUrl}/prestamos/cartera/resumen`,
      { params }
    )
  }

  /** POST: pares (prestamo_id, codigo_control) con ultimo evento MARCAR_OK en bitacora. */
  async listarRevisionesOcultos(
    prestamoIds: number[]
  ): Promise<CarteraRevisionOcultosResponse> {
    return apiClient.post<CarteraRevisionOcultosResponse>(
      `${this.baseUrl}/prestamos/cartera/revisiones/ocultos`,
      { prestamo_ids: prestamoIds }
    )
  }

  async crearRevisionCartera(body: {
    prestamo_id: number

    codigo_control: string

    tipo?: string

    nota?: string
  }): Promise<CarteraRevisionItem> {
    return apiClient.post<CarteraRevisionItem>(
      `${this.baseUrl}/prestamos/cartera/revisiones`,
      {
        prestamo_id: body.prestamo_id,
        codigo_control: body.codigo_control,
        tipo: body.tipo ?? 'MARCAR_OK',
        nota: body.nota,
      }
    )
  }

  async historialRevisionesCartera(
    prestamoId: number,
    limit = 100
  ): Promise<CarteraRevisionItem[]> {
    return apiClient.get<CarteraRevisionItem[]>(
      `${this.baseUrl}/prestamos/cartera/revisiones/historial`,
      { params: { prestamo_id: prestamoId, limit } }
    )
  }

  /** Controles con al menos un MARCAR_OK historico (para export). */
  async listarControlesConExcepcionesHistoricas(): Promise<string[]> {
    return apiClient.get<string[]>(
      `${this.baseUrl}/prestamos/cartera/revisiones/controles-con-excepciones`
    )
  }

  async descargarRevisionesCarteraExcel(codigoControl: string): Promise<Blob> {
    return apiClient.get<Blob>(
      `${this.baseUrl}/prestamos/cartera/revisiones/export-excel`,
      {
        params: { codigo_control: codigoControl },
        responseType: 'blob',
      }
    )
  }

  async ejecutarCartera(): Promise<PrestamoCarteraChequeoResponse> {
    return apiClient.post<PrestamoCarteraChequeoResponse>(
      `${this.baseUrl}/prestamos/cartera/ejecutar`,
      undefined,
      { timeout: AUDITORIA_CARTERA_EJECUTAR_TIMEOUT_MS }
    )
  }

  /** Alinea cuotas.estado con vencimiento y pagos (misma regla que control estado_cuota_vs_calculo). */
  async sincronizarEstadosCuotasCartera(): Promise<SincronizarEstadosCuotasResponse> {
    return apiClient.post<SincronizarEstadosCuotasResponse>(
      `${this.baseUrl}/prestamos/cartera/sincronizar-estados-cuotas`,
      undefined
    )
  }

  /** Solo administrador. Reaplica cascada en prestamos con alerta pagos vs aplicado (opcional) y sincroniza estados. */
  async corregirCartera(body: {
    sincronizar_estados?: boolean
    reaplicar_cascada_desajuste_pagos?: boolean
    reaplicar_cascada_pagos_sin_aplicacion_cuotas?: boolean
    max_reaplicaciones?: number
  }): Promise<CarteraCorreccionResponse> {
    return apiClient.post<CarteraCorreccionResponse>(
      `${this.baseUrl}/prestamos/cartera/corregir`,
      {
        sincronizar_estados: body.sincronizar_estados ?? true,
        reaplicar_cascada_desajuste_pagos:
          body.reaplicar_cascada_desajuste_pagos ?? false,
        reaplicar_cascada_pagos_sin_aplicacion_cuotas:
          body.reaplicar_cascada_pagos_sin_aplicacion_cuotas ?? false,
        max_reaplicaciones: body.max_reaplicaciones ?? 50,
      },
      { timeout: AUDITORIA_CARTERA_CORREGIR_TIMEOUT_MS }
    )
  }

  // Descargar archivo Excel

  async descargarExcel(
    filters?: Omit<AuditoriaFilters, 'skip' | 'limit' | 'ordenar_por' | 'orden'>
  ): Promise<void> {
    try {
      const blob = await this.exportarExcel(filters)

      // Crear URL del blob

      const url = window.URL.createObjectURL(blob)

      // Crear elemento de descarga

      const link = document.createElement('a')

      link.href = url

      // Generar nombre de archivo con timestamp

      const timestamp = new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/[:-]/g, '')

      link.download = `auditoria_${timestamp}.xlsx`

      // Descargar archivo

      document.body.appendChild(link)

      link.click()

      document.body.removeChild(link)

      // Limpiar URL

      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('❌ Error descargando Excel:', error)

      throw error
    }
  }

  /** Solo admin. Lista pagos que participan en duplicado fecha+monto (control 5). */
  async listarControl5DuplicadosPorPrestamo(
    prestamoId: number
  ): Promise<Control5DuplicadosListaResponse> {
    return apiClient.get<Control5DuplicadosListaResponse>(
      `${this.baseUrl}/prestamos/cartera/control-5-pagos-duplicados-fecha-monto/${prestamoId}`
    )
  }

  /** Solo admin. Visto: sufijo _A#### o _P#### al documento (A mismo préstamo/cuotas; P otro préstamo). */
  async aplicarControl5VistoPago(
    pagoId: number
  ): Promise<Control5VistoResponse> {
    return apiClient.post<Control5VistoResponse>(
      `${this.baseUrl}/prestamos/cartera/control-5-pagos-duplicados-fecha-monto/${pagoId}/visto`,
      undefined
    )
  }

  /** Solo admin. Lista pagos del prestamo que disparan control 15. */
  async listarControl15PagosSinAplicacionCuotas(
    prestamoId: number
  ): Promise<{ items: Control15PagoSinAplicacionItem[] }> {
    return apiClient.get<{ items: Control15PagoSinAplicacionItem[] }>(
      `${this.baseUrl}/prestamos/cartera/control-15-pagos-sin-aplicacion-cuotas/${prestamoId}`
    )
  }
}

export const auditoriaService = new AuditoriaService()
