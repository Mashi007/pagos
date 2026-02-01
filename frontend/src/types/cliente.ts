/**
 * Tipos para Cliente
 * Evita el uso de 'any' en componentes que manejan clientes
 */

export interface Cliente {
  id: number
  cedula: string
  nombre: string
  apellido: string
  email?: string
  telefono?: string
  direccion?: string
  fecha_registro?: string
  estado?: string
  [key: string]: unknown // Para campos adicionales
}

export interface ClienteListItem extends Cliente {
  // Campos específicos para listas
}

