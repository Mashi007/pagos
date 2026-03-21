// Mock data para comunicaciones - Ejemplos de configuraciÃ³n
// Este archivo contiene ejemplos de comunicaciones (WhatsApp y Email)
// para mostrar cÃ³mo estÃ¡ estructurada la informaciÃ³n

import { ComunicacionUnificada } from '../services/comunicacionesService'

export const mockComunicaciones: ComunicacionUnificada[] = [
  // Ejemplo 1: ComunicaciÃ³n WhatsApp INBOUND (requiere respuesta) - NUEVO
  {
    id: 1,
    tipo: 'whatsapp',
    from_contact: '+584121234567',
    to_contact: '+584129876543',
    subject: null,
    body: 'Buenos dÃ­as, quisiera informaciÃ³n sobre los requisitos para solicitar un prÃ©stamo. Â¿CuÃ¡l es el monto mÃ­nimo?',
    timestamp: new Date('2025-11-18T14:30:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: null, // Cliente no identificado aÃºn
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T14:30:00Z').toISOString(),
  },
  // Ejemplo 2: ComunicaciÃ³n Email INBOUND (requiere respuesta) - Cliente identificado
  {
    id: 2,
    tipo: 'email',
    from_contact: 'maria.gonzalez@email.com',
    to_contact: 'atencion@rapicredit.com',
    subject: 'Consulta sobre estado de mi prÃ©stamo',
    body: 'Estimados, quisiera saber el estado actual de mi prÃ©stamo #12345. Â¿CuÃ¡ntas cuotas me faltan por pagar? Necesito esta informaciÃ³n para planificar mis pagos.',
    timestamp: new Date('2025-11-18T13:15:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: 5, // Cliente identificado
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T13:15:00Z').toISOString(),
  },
  // Ejemplo 3: ComunicaciÃ³n WhatsApp OUTBOUND (ya respondida)
  {
    id: 3,
    tipo: 'whatsapp',
    from_contact: '+584129876543',
    to_contact: '+584121234567',
    subject: null,
    body: 'Hola! El monto mÃ­nimo para prÃ©stamos es de 5,000 VES. Puede visitarnos en nuestra oficina o completar el formulario en lÃ­nea. Â¿Necesita mÃ¡s informaciÃ³n?',
    timestamp: new Date('2025-11-18T14:45:00Z').toISOString(),
    direccion: 'OUTBOUND',
    cliente_id: null,
    ticket_id: 12, // Vinculado a un ticket
    requiere_respuesta: false,
    procesado: true,
    respuesta_enviada: true,
    creado_en: new Date('2025-11-18T14:45:00Z').toISOString(),
  },
  // Ejemplo 4: ComunicaciÃ³n Email INBOUND - NUEVO
  {
    id: 4,
    tipo: 'email',
    from_contact: 'carlos.rodriguez@gmail.com',
    to_contact: 'atencion@rapicredit.com',
    subject: 'Solicitud de informaciÃ³n sobre prÃ©stamos',
    body: 'Buen dÃ­a, estoy interesado en obtener un prÃ©stamo personal. Â¿PodrÃ­an enviarme informaciÃ³n sobre las tasas de interÃ©s y los requisitos necesarios?',
    timestamp: new Date('2025-11-18T12:00:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: null,
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T12:00:00Z').toISOString(),
  },
  // Ejemplo 5: ComunicaciÃ³n WhatsApp INBOUND - Cliente identificado
  {
    id: 5,
    tipo: 'whatsapp',
    from_contact: '+584147891234',
    to_contact: '+584129876543',
    subject: null,
    body: 'Hola, tengo una duda sobre mi Ãºltimo pago. Â¿Pueden confirmarme si se registrÃ³ correctamente?',
    timestamp: new Date('2025-11-18T11:20:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: 8,
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T11:20:00Z').toISOString(),
  },
  // Ejemplo 6: ComunicaciÃ³n Email OUTBOUND (ya respondida)
  {
    id: 6,
    tipo: 'email',
    from_contact: 'atencion@rapicredit.com',
    to_contact: 'maria.gonzalez@email.com',
    subject: 'Re: Consulta sobre estado de mi prÃ©stamo',
    body: 'Estimada MarÃ­a, su prÃ©stamo #12345 tiene un saldo pendiente de 3 cuotas. La prÃ³xima cuota vence el 25 de noviembre. Puede realizar el pago a travÃ©s de nuestra plataforma en lÃ­nea.',
    timestamp: new Date('2025-11-18T13:30:00Z').toISOString(),
    direccion: 'OUTBOUND',
    cliente_id: 5,
    ticket_id: 15,
    requiere_respuesta: false,
    procesado: true,
    respuesta_enviada: true,
    creado_en: new Date('2025-11-18T13:30:00Z').toISOString(),
  },
  // Ejemplo 7: ComunicaciÃ³n WhatsApp INBOUND - NUEVO
  {
    id: 7,
    tipo: 'whatsapp',
    from_contact: '+584165432109',
    to_contact: '+584129876543',
    subject: null,
    body: 'Buenas tardes, necesito informaciÃ³n urgente sobre cÃ³mo puedo refinanciar mi prÃ©stamo actual.',
    timestamp: new Date('2025-11-18T10:45:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: null,
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T10:45:00Z').toISOString(),
  },
  // Ejemplo 8: ComunicaciÃ³n Email INBOUND - Cliente identificado
  {
    id: 8,
    tipo: 'email',
    from_contact: 'juan.perez@hotmail.com',
    to_contact: 'atencion@rapicredit.com',
    subject: 'Problema con mi cuenta en lÃ­nea',
    body: 'No puedo acceder a mi cuenta en la plataforma. He intentado recuperar mi contraseÃ±a pero no recibo el correo de recuperaciÃ³n. Â¿Pueden ayudarme?',
    timestamp: new Date('2025-11-18T09:30:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: 12,
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T09:30:00Z').toISOString(),
  },
]

// Mock data para nombres de clientes (para mejorar la visualizaciÃ³n)
export const mockNombresClientes: Record<number, string> = {
  5: 'MarÃ­a GonzÃ¡lez',
  8: 'Ana MartÃ­nez',
  12: 'Juan PÃ©rez',
}

// Mock data para tickets
export const mockTickets = [
  {
    id: 12,
    titulo: 'Consulta sobre requisitos de prÃ©stamo',
    descripcion: 'Cliente solicita informaciÃ³n sobre requisitos y monto mÃ­nimo',
    cliente_id: null,
    estado: 'abierto',
    prioridad: 'media',
    tipo: 'consulta',
    fecha_limite: new Date('2025-11-20T18:00:00Z').toISOString(),
  },
  {
    id: 15,
    titulo: 'Consulta estado de prÃ©stamo #12345',
    descripcion: 'Cliente solicita informaciÃ³n sobre cuotas pendientes',
    cliente_id: 5,
    estado: 'resuelto',
    prioridad: 'baja',
    tipo: 'consulta',
    fecha_limite: null,
  },
]
