/**





 * Tipos principales del sistema de préstamos y cobranza





 * Definiciones centralizadas para mantener consistencia entre frontend y backend





 */

export type UserRol = 'admin' | 'manager' | 'operator' | 'viewer'

export interface User {
  id: number

  email: string

  nombre: string

  apellido: string

  cargo?: string

  rol: UserRol

  is_active: boolean

  created_at: string

  updated_at?: string

  last_login?: string
}

export interface Cliente {
  id: number

  cedula: string

  nombres: string // ✅ Unificado: contiene nombres + apellidos (2-7 palabras)

  telefono?: string

  /** Correo 1 (prioridad). */
  email?: string

  /** Correo 2 (opcional). */
  email_secundario?: string | null

  correo_1?: string

  correo_2?: string | null

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

  nombres: string // ✅ Unifica nombres + apellidos

  telefono?: string

  email?: string

  email_secundario?: string | null

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

/** Payload de POST /api/v1/clientes/actualizar-lote (alineado con ActualizarLoteItem en backend). */
export interface ActualizarClienteLoteItem {
  id: number
  cedula?: string
  nombres?: string
  telefono?: string
  email?: string
  email_secundario?: string | null
  correo_1?: string
  correo_2?: string | null
  direccion?: string
  ocupacion?: string
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

  /** Suma monto de cuotas sin fecha_pago (listado / resumen). */
  saldo_pendiente?: number

  fecha_requerimiento: string

  modalidad_pago: 'MENSUAL' | 'QUINCENAL' | 'SEMANAL'

  numero_cuotas: number

  cuota_periodo: number

  tasa_interes: number

  fecha_base_calculo?: string

  producto: string

  concesionario?: string

  analista: string

  analista_id?: number | null

  modelo_vehiculo?: string

  estado:
    | 'DRAFT'
    | 'EN_REVISION'
    | 'EVALUADO'
    | 'APROBADO'
    | 'RECHAZADO'
    | 'LIQUIDADO'
    | 'DESISTIMIENTO'

  /** Fase finiquito (Antiguo / En proceso / Terminado), reflejada en el préstamo. */
  estado_gestion_finiquito?: 'ANTIGUO' | 'EN_PROCESO' | 'TERMINADO' | null

  /** Fecha límite del trámite (15 días laborales al pasar a En proceso), ISO date. */
  finiquito_tramite_fecha_limite?: string | null

  usuario_proponente: string

  usuario_aprobador?: string

  usuario_autoriza?: string

  observaciones?: string

  fecha_registro: string

  fecha_aprobacion?: string

  fecha_desistimiento?: string

  fecha_actualizacion: string

  estado_edicion?: 'EN_EDICION' | 'COMPLETADO'
}

export interface PrestamoForm {
  cedula: string

  valor_activo?: number

  total_financiamiento: number

  modalidad_pago: 'MENSUAL' | 'QUINCENAL' | 'SEMANAL'

  fecha_requerimiento: string

  /** Solo edicion: YYYY-MM-DD; PUT persiste fecha_aprobacion en BD */

  fecha_aprobacion?: string

  producto: string

  concesionario?: string

  analista: string

  analista_id?: number | null

  modelo_vehiculo?: string

  /** Solo edicion: estado del prestamo (PUT). Creacion usa default del backend. */

  estado?: Prestamo['estado']

  numero_cuotas?: number // Número de cuotas manual del formulario

  cuota_periodo?: number // Cuota por periodo (manual en formulario nuevo prestamo)

  tasa_interes?: number

  fecha_base_calculo?: string

  observaciones?: string

  usuario_autoriza?: string // Email del usuario que autoriza crear nuevo préstamo

  usuario_proponente?: string // Email del analista asignado
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

// Tipos del dashboard (respuestas API)

export * from './dashboard'

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
