// Mock data para comunicaciones - Ejemplos de configuración
// Este archivo contiene 3 ejemplos de comunicaciones (WhatsApp y Email)
// para mostrar cómo está estructurada la información

import { ComunicacionUnificada } from '@/services/comunicacionesService'

export const mockComunicaciones: ComunicacionUnificada[] = [
  // Ejemplo 1: Comunicación WhatsApp INBOUND (requiere respuesta)
  {
    id: 1,
    tipo: 'whatsapp',
    from_contact: '+584121234567',
    to_contact: '+584129876543',
    subject: null,
    body: 'Buenos días, quisiera información sobre los requisitos para solicitar un préstamo. ¿Cuál es el monto mínimo?',
    timestamp: new Date('2025-11-18T09:15:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: null, // Cliente no identificado aún
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T09:15:00Z').toISOString(),
  },
  // Ejemplo 2: Comunicación Email INBOUND (requiere respuesta)
  {
    id: 2,
    tipo: 'email',
    from_contact: 'cliente.ejemplo@email.com',
    to_contact: 'atencion@rapicredit.com',
    subject: 'Consulta sobre estado de mi préstamo',
    body: 'Estimados, quisiera saber el estado actual de mi préstamo #12345. ¿Cuántas cuotas me faltan por pagar?',
    timestamp: new Date('2025-11-18T10:30:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: 5, // Cliente identificado
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T10:30:00Z').toISOString(),
  },
  // Ejemplo 3: Comunicación WhatsApp OUTBOUND (ya respondida)
  {
    id: 3,
    tipo: 'whatsapp',
    from_contact: '+584129876543',
    to_contact: '+584121234567',
    subject: null,
    body: 'Hola! El monto mínimo para préstamos es de 5,000 VES. Puede visitarnos en nuestra oficina o completar el formulario en línea. ¿Necesita más información?',
    timestamp: new Date('2025-11-18T09:45:00Z').toISOString(),
    direccion: 'OUTBOUND',
    cliente_id: null,
    ticket_id: 12, // Vinculado a un ticket
    requiere_respuesta: false,
    procesado: true,
    respuesta_enviada: true,
    creado_en: new Date('2025-11-18T09:45:00Z').toISOString(),
  },
]

// Ejemplo de estadísticas de comunicaciones
export const mockEstadisticasComunicaciones = {
  total: 156,
  porResponder: 23,
  whatsapp: 98,
  email: 58,
  inbound: 89,
  outbound: 67,
}

// Ejemplo de cliente creado automáticamente desde comunicación
export const mockClienteAutomatico = {
  id: 101,
  cedula: '12345678',
  nombres: 'Juan',
  apellidos: 'Pérez',
  telefono: '+584121234567',
  email: null,
  direccion: 'Caracas, Venezuela',
  estado: 'prospecto',
  notas: 'Cliente creado automáticamente desde comunicación WhatsApp recibida el 2025-11-18',
  creado_en: new Date('2025-11-18T09:20:00Z').toISOString(),
}

