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
  
  // Datos del vehículo (coincide con backend)
  modelo_vehiculo?: string
  marca_vehiculo?: string
  anio_vehiculo?: number
  color_vehiculo?: string
  chasis?: string
  motor?: string
  
  // Concesionario
  concesionario?: string
  vendedor_concesionario?: string
  
  // Datos del financiamiento (coincide con backend)
  total_financiamiento?: number
  cuota_inicial?: number
  monto_financiado?: number
  fecha_entrega?: string
  numero_amortizaciones?: number
  modalidad_pago?: string
  
  // Asignación y gestión
  analista_config_id?: number
  fecha_asignacion?: string
  
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
  nombres: string
  apellidos: string
  telefono?: string
  email?: string
  direccion?: string
  fecha_nacimiento?: string
  ocupacion?: string
  
  // Datos del vehículo (coincide con backend)
  modelo_vehiculo?: string
  marca_vehiculo?: string
  anio_vehiculo?: number
  color_vehiculo?: string
  chasis?: string
  motor?: string
  
  // Concesionario
  concesionario?: string
  vendedor_concesionario?: string
  
  // Datos del financiamiento (coincide con backend)
  total_financiamiento?: number
  cuota_inicial?: number
  fecha_entrega?: string
  numero_amortizaciones?: number
  modalidad_pago?: string
  
  // Asignación
  analista_config_id?: number
  
  // Notas
  notas?: string
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
  estado?: 'ACTIVO' | 'INACTIVO' | 'MORA' | 'FINALIZADO'
  estado_financiero?: string
  analista_config_id?: number
  fecha_desde?: string
  fecha_hasta?: string
  per_page?: number
}