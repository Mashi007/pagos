// Tipos principales del sistema

export interface User {
  id: string;
  email: string;
  nombre: string;
  apellido: string;
  rol: UserRole;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export type UserRole = 
  | 'ADMINISTRADOR_GENERAL'
  | 'COBRANZAS';

export interface Cliente {
  id: number;
  cedula: string;
  nombres: string;
  apellidos: string;
  telefono?: string;
  email?: string;
  direccion?: string;
  fecha_nacimiento?: string;
  ocupacion?: string;
  
  // Datos del vehículo (coincide con backend)
  modelo_vehiculo?: string;
  marca_vehiculo?: string;
  anio_vehiculo?: number;
  color_vehiculo?: string;
  chasis?: string;
  motor?: string;
  
  // Concesionario
  concesionario?: string;
  vendedor_concesionario?: string;
  
  // Datos del financiamiento (coincide con backend)
  total_financiamiento?: number;
  cuota_inicial?: number;
  monto_financiado?: number;
  fecha_entrega?: string;
  numero_amortizaciones?: number;
  modalidad_pago?: string;
  
  // Asignación y gestión
  asesor_config_id?: number;
  fecha_asignacion?: string;
  
  // Estados (coincide con backend)
  estado: 'ACTIVO' | 'INACTIVO' | 'MORA';
  activo: boolean;
  estado_financiero?: string;
  dias_mora: number;
  
  // Auditoría
  fecha_registro: string;
  fecha_actualizacion?: string;
  usuario_registro?: string;
  
  // Notas
  notas?: string;
}

export interface Pago {
  id: string;
  cliente_id: string;
  cliente_nombre?: string;
  monto_total: number;
  fecha_pago: string;
  forma_pago: 'EFECTIVO' | 'TRANSFERENCIA' | 'CHEQUE' | 'TARJETA';
  referencia?: string;
  observaciones?: string;
  
  // Distribución del pago
  monto_capital: number;
  monto_interes: number;
  monto_mora: number;
  monto_otros: number;
  
  // Datos de la cuota
  numero_cuota: number;
  cuota_id?: string;
  
  // Estado y auditoría
  estado: 'PENDIENTE' | 'CONFIRMADO' | 'ANULADO';
  usuario_registro_id: string;
  usuario_registro_nombre?: string;
  
  created_at: string;
  updated_at: string;
}

export interface Cuota {
  id: string;
  cliente_id: string;
  numero_cuota: number;
  fecha_vencimiento: string;
  monto_cuota: number;
  monto_capital: number;
  monto_interes: number;
  saldo_pendiente: number;
  
  // Estado de la cuota
  estado: 'PENDIENTE' | 'PAGADA' | 'VENCIDA' | 'PARCIAL';
  monto_pagado: number;
  fecha_pago?: string;
  dias_mora: number;
  monto_mora: number;
  
  created_at: string;
  updated_at: string;
}

export interface Reporte {
  id: string;
  nombre: string;
  descripcion: string;
  tipo: 'CARTERA' | 'FLUJO_CAJA' | 'MORA' | 'PRODUCTIVIDAD' | 'CONCILIACION';
  parametros: Record<string, any>;
  archivo_url?: string;
  estado: 'GENERANDO' | 'COMPLETADO' | 'ERROR';
  usuario_id: string;
  created_at: string;
}

export interface KPI {
  cartera_total: number;
  cartera_al_dia: number;
  cartera_vencida: number;
  porcentaje_mora: number;
  pagos_hoy: number;
  monto_pagos_hoy: number;
  clientes_activos: number;
  clientes_mora: number;
  meta_mensual: number;
  avance_meta: number;
}

export interface Notificacion {
  id: string;
  titulo: string;
  mensaje: string;
  tipo: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  leida: boolean;
  usuario_id: string;
  created_at: string;
}

// Tipos para formularios
export interface LoginForm {
  email: string;
  password: string;
  remember?: boolean;
}

export interface ClienteForm {
  // Datos personales (coincide con backend)
  cedula: string;
  nombres: string;
  apellidos: string;
  telefono?: string;
  email?: string;
  direccion?: string;
  fecha_nacimiento?: string;
  ocupacion?: string;
  
  // Datos del vehículo (coincide con backend)
  modelo_vehiculo?: string;
  marca_vehiculo?: string;
  anio_vehiculo?: number;
  color_vehiculo?: string;
  chasis?: string;
  motor?: string;
  
  // Concesionario
  concesionario?: string;
  vendedor_concesionario?: string;
  
  // Datos del financiamiento (coincide con backend)
  total_financiamiento?: number;
  cuota_inicial?: number;
  fecha_entrega?: string;
  numero_amortizaciones?: number;
  modalidad_pago?: string;
  
  // Asignación
   asesor_config_id?: number;
  
  // Notas
  notas?: string;
}

export interface PagoForm {
  cliente_id: string;
  monto_total: number;
  fecha_pago: string;
  forma_pago: 'EFECTIVO' | 'TRANSFERENCIA' | 'CHEQUE' | 'TARJETA';
  referencia?: string;
  observaciones?: string;
  numero_cuota?: number;
}

// Tipos para respuestas de API
export interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Tipos para filtros y búsquedas
export interface ClienteFilters {
  search?: string;
  estado?: Cliente['estado'];
  estado_financiero?: string;
  asesor_config_id?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  per_page?: number;
}

export interface PagoFilters {
  search?: string;
  cliente_id?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  forma_pago?: Pago['forma_pago'];
  estado?: Pago['estado'];
}

// Tipos para configuración
export interface AppConfig {
  app_name: string;
  version: string;
  environment: string;
  api_url: string;
  features: {
    notifications: boolean;
    reports: boolean;
    conciliation: boolean;
    ai: boolean;
  };
}
