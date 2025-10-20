import { apiClient } from './api'

export interface Prestamo {
  id: number
  cliente_id: number
  codigo_prestamo: string
  monto_total: number
  monto_financiado: number
  monto_inicial: number
  tasa_interes: number
  numero_cuotas: number
  monto_cuota: number
  cuotas_pagadas: number
  cuotas_pendientes: number
  fecha_aprobacion: string
  fecha_desembolso?: string
  fecha_primer_vencimiento: string
  fecha_ultimo_vencimiento?: string
  saldo_pendiente: number
  saldo_capital: number
  saldo_interes: number
  total_pagado: number
  estado: string
  categoria: string
  modalidad: string
  destino_credito?: string
  observaciones?: string
  creado_en: string
  actualizado_en: string
}

export interface PrestamoCreate {
  cliente_id: number
  monto_total: number
  monto_financiado: number
  monto_inicial?: number
  tasa_interes?: number
  numero_cuotas: number
  monto_cuota: number
  fecha_aprobacion: string
  fecha_desembolso?: string
  fecha_primer_vencimiento: string
  fecha_ultimo_vencimiento?: string
  modalidad?: string
  destino_credito?: string
  observaciones?: string
}

export interface PrestamoUpdate {
  monto_total?: number
  monto_financiado?: number
  monto_inicial?: number
  tasa_interes?: number
  numero_cuotas?: number
  monto_cuota?: number
  fecha_aprobacion?: string
  fecha_desembolso?: string
  fecha_primer_vencimiento?: string
  fecha_ultimo_vencimiento?: string
  estado?: string
  modalidad?: string
  destino_credito?: string
  observaciones?: string
}

export interface PrestamoListResponse {
  items: Prestamo[]
  total: number
  page: number
  size: number
  pages: number
}

export interface PrestamosStats {
  total_prestamos: number
  prestamos_activos: number
  prestamos_pendientes: number
  prestamos_completados: number
  prestamos_en_mora: number
  monto_total_prestado: number
  monto_total_pendiente: number
}

class PrestamoService {
  private baseUrl = '/api/v1/prestamos'

  // ============================================
  // CRUD PRÉSTAMOS
  // ============================================

  async crearPrestamo(prestamo: PrestamoCreate): Promise<Prestamo> {
    const response = await apiClient.post<Prestamo>(this.baseUrl, prestamo)
    return response
  }

  async listarPrestamos(params?: {
    skip?: number
    limit?: number
    cliente_id?: number
    estado?: string
  }): Promise<PrestamoListResponse> {
    return await apiClient.get<PrestamoListResponse>(this.baseUrl, { params })
  }

  async obtenerPrestamo(id: number): Promise<Prestamo> {
    return await apiClient.get<Prestamo>(`${this.baseUrl}/${id}`)
  }

  async actualizarPrestamo(id: number, prestamo: PrestamoUpdate): Promise<Prestamo> {
    return await apiClient.put<Prestamo>(`${this.baseUrl}/${id}`, prestamo)
  }

  async eliminarPrestamo(id: number): Promise<{ message: string }> {
    return await apiClient.delete<{ message: string }>(`${this.baseUrl}/${id}`)
  }

  // ============================================
  // ESTADÍSTICAS
  // ============================================

  async obtenerEstadisticas(): Promise<PrestamosStats> {
    return await apiClient.get<PrestamosStats>(`${this.baseUrl}/stats`)
  }

  // ============================================
  // BÚSQUEDA DE CLIENTE POR CÉDULA
  // ============================================

  async buscarClientePorCedula(cedula: string): Promise<any> {
    return await apiClient.get(`/api/v1/clientes/buscar-cedula/${cedula}`)
  }
}

export const prestamoService = new PrestamoService()
