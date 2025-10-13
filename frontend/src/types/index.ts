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
  | 'ADMIN'
  | 'GERENTE' 
  | 'DIRECTOR'
  | 'ASESOR_COMERCIAL'
  | 'COBRADOR'
  | 'CONTADOR'
  | 'AUDITOR'
  | 'USUARIO';

export interface Cliente {
  id: string;
  cedula: string;
  nombre: string;
  apellido: string;
  telefono: string;
  email?: string;
  direccion: string;
  fecha_nacimiento: string;
  ingresos_mensuales: number;
  estado_civil: string;
  profesion: string;
  
  // Datos del vehículo
  marca_vehiculo: string;
  modelo_vehiculo: string;
  año_vehiculo: number;
  placa_vehiculo: string;
  vin_vehiculo?: string;
  valor_vehiculo: number;
  
  // Datos del financiamiento
  monto_financiamiento: number;
  cuota_inicial: number;
  total_financiamiento: number;
  tasa_interes: number;
  plazo_meses: number;
  cuota_mensual: number;
  sistema_amortizacion: 'FRANCES' | 'ALEMAN' | 'AMERICANO';
  
  // Datos del asesor
  asesor_id: string;
  asesor_nombre?: string;
  
  // Estados y fechas
  estado: 'ACTIVO' | 'INACTIVO' | 'MORA' | 'CANCELADO';
  fecha_desembolso: string;
  proxima_cuota: string;
  
  created_at: string;
  updated_at: string;
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
  // Datos personales
  cedula: string;
  nombre: string;
  apellido: string;
  telefono: string;
  email?: string;
  direccion: string;
  fecha_nacimiento: string;
  ingresos_mensuales: number;
  estado_civil: string;
  profesion: string;
  
  // Datos del vehículo
  marca_vehiculo: string;
  modelo_vehiculo: string;
  año_vehiculo: number;
  placa_vehiculo: string;
  vin_vehiculo?: string;
  valor_vehiculo: number;
  
  // Datos del financiamiento
  monto_financiamiento: number;
  cuota_inicial: number;
  tasa_interes: number;
  plazo_meses: number;
  sistema_amortizacion: 'FRANCES' | 'ALEMAN' | 'AMERICANO';
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
  asesor_id?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
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
