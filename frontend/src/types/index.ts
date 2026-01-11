/**
 * Tipos principales del sistema de préstamos y cobranza
 * Definiciones centralizadas para mantener consistencia entre frontend y backend
 */

export interface User {
  id: number
  email: string
  nombre: string
  apellido: string
  cargo?: string
  is_admin: boolean
  is_active: boolean
  created_at: string
  updated_at?: string
  last_login?: string
}

export interface Cliente {
  id: number
  cedula: string
  nombres: string
  apellidos: string
  telefono?: string
  email?: string
  direccion?: string
  fecha_nacimiento?: string
  ocupacion?: string

  // Datos del financiamiento (coincide con backend)
  total_financiamiento?: number
  cuota_inicial?: number
  monto_financiado?: number
  fecha_entrega?: string
  numero_amortizaciones?: number
  modalidad_pago?: string

  // Estados (coincide con backend)
  estado: 'ACTIVO' | 'INACTIVO' | 'MORA' | 'FINALIZADO'
  activo: boolean
  estado_financiero?: string
  dias_mora: number

  // Auditoría
  fecha_registro: string
  fecha_actualizacion?: string
  usuario_registro?: string

  // Notas
  notas?: string
}

// Tipos para formularios
export interface LoginForm {
  email: string
  password: string
  remember?: boolean
}

export interface ClienteForm {
  // Datos personales (coincide con backend)
  cedula: string
  nombres: string  // ✅ Unifica nombres + apellidos
  telefono?: string
  email?: string
  direccion?: string
  fecha_nacimiento?: string
  ocupacion?: string

  // Datos del financiamiento (coincide con backend)
  total_financiamiento?: number
  cuota_inicial?: number
  fecha_entrega?: string
  numero_amortizaciones?: number
  modalidad_pago?: string

  // Notas
  notas?: string
}

// Tipos de Préstamo
export interface Prestamo {
  requiere_revision?: boolean
  id: number
  cliente_id: number
  cedula: string
  nombres: string
  valor_activo?: number
  total_financiamiento: number
  fecha_requerimiento: string
  modalidad_pago: 'MENSUAL' | 'QUINCENAL' | 'SEMANAL'
  numero_cuotas: number
  cuota_periodo: number
  tasa_interes: number
  fecha_base_calculo?: string
  producto: string
  producto_financiero: string
  concesionario?: string
  analista?: string
  modelo_vehiculo?: string
  estado: 'DRAFT' | 'EN_REVISION' | 'APROBADO' | 'RECHAZADO'
  usuario_proponente: string
  usuario_aprobador?: string
  usuario_autoriza?: string
  observaciones?: string
  fecha_registro: string
  fecha_aprobacion?: string
  fecha_actualizacion: string
}

export interface PrestamoForm {
  cedula: string
  valor_activo?: number
  total_financiamiento: number
  modalidad_pago: 'MENSUAL' | 'QUINCENAL' | 'SEMANAL'
  fecha_requerimiento: string
  producto: string
  producto_financiero: string
  concesionario?: string
  analista?: string
  modelo_vehiculo?: string
  numero_cuotas?: number  // Número de cuotas manual del formulario
  cuota_periodo?: number  // Cuota calculada
  tasa_interes?: number
  fecha_base_calculo?: string
  observaciones?: string
  usuario_autoriza?: string  // Email del usuario que autoriza crear nuevo préstamo
  usuario_proponente?: string  // Email del analista asignado
}

// Tipos para respuestas de API
export interface ApiResponse<T> {
  data: T
  message: string
  success: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// Tipos para filtros y búsquedas
export interface ClienteFilters {
  search?: string
  cedula?: string
  estado?: 'ACTIVO' | 'INACTIVO' | 'MORA' | 'FINALIZADO'
  estado_financiero?: string
  email?: string
  telefono?: string
  ocupacion?: string
  usuario_registro?: string
  fecha_desde?: string
  fecha_hasta?: string
  per_page?: number
}
