// Mock data para comunicaciones - Ejemplos de configuración
// Este archivo contiene ejemplos de comunicaciones (WhatsApp y Email)
// para mostrar cómo está estructurada la información

import { ComunicacionUnificada } from '@/services/comunicacionesService'

export const mockComunicaciones: ComunicacionUnificada[] = [
  // Ejemplo 1: Comunicación WhatsApp INBOUND (requiere respuesta) - NUEVO
  {
    id: 1,
    tipo: 'whatsapp',
    from_contact: '+584121234567',
    to_contact: '+584129876543',
    subject: null,
    body: 'Buenos días, quisiera información sobre los requisitos para solicitar un préstamo. ¿Cuál es el monto mínimo?',
    timestamp: new Date('2025-11-18T14:30:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: null, // Cliente no identificado aún
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T14:30:00Z').toISOString(),
  },
  // Ejemplo 2: Comunicación Email INBOUND (requiere respuesta) - Cliente identificado
  {
    id: 2,
    tipo: 'email',
    from_contact: 'maria.gonzalez@email.com',
    to_contact: 'atencion@rapicredit.com',
    subject: 'Consulta sobre estado de mi préstamo',
    body: 'Estimados, quisiera saber el estado actual de mi préstamo #12345. ¿Cuántas cuotas me faltan por pagar? Necesito esta información para planificar mis pagos.',
    timestamp: new Date('2025-11-18T13:15:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: 5, // Cliente identificado
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T13:15:00Z').toISOString(),
  },
  // Ejemplo 3: Comunicación WhatsApp OUTBOUND (ya respondida)
  {
    id: 3,
    tipo: 'whatsapp',
    from_contact: '+584129876543',
    to_contact: '+584121234567',
    subject: null,
    body: 'Hola! El monto mínimo para préstamos es de 5,000 VES. Puede visitarnos en nuestra oficina o completar el formulario en línea. ¿Necesita más información?',
    timestamp: new Date('2025-11-18T14:45:00Z').toISOString(),
    direccion: 'OUTBOUND',
    cliente_id: null,
    ticket_id: 12, // Vinculado a un ticket
    requiere_respuesta: false,
    procesado: true,
    respuesta_enviada: true,
    creado_en: new Date('2025-11-18T14:45:00Z').toISOString(),
  },
  // Ejemplo 4: Comunicación Email INBOUND - NUEVO
  {
    id: 4,
    tipo: 'email',
    from_contact: 'carlos.rodriguez@gmail.com',
    to_contact: 'atencion@rapicredit.com',
    subject: 'Solicitud de información sobre préstamos',
    body: 'Buen día, estoy interesado en obtener un préstamo personal. ¿Podrían enviarme información sobre las tasas de interés y los requisitos necesarios?',
    timestamp: new Date('2025-11-18T12:00:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: null,
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T12:00:00Z').toISOString(),
  },
  // Ejemplo 5: Comunicación WhatsApp INBOUND - Cliente identificado
  {
    id: 5,
    tipo: 'whatsapp',
    from_contact: '+584147891234',
    to_contact: '+584129876543',
    subject: null,
    body: 'Hola, tengo una duda sobre mi último pago. ¿Pueden confirmarme si se registró correctamente?',
    timestamp: new Date('2025-11-18T11:20:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: 8,
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T11:20:00Z').toISOString(),
  },
  // Ejemplo 6: Comunicación Email OUTBOUND (ya respondida)
  {
    id: 6,
    tipo: 'email',
    from_contact: 'atencion@rapicredit.com',
    to_contact: 'maria.gonzalez@email.com',
    subject: 'Re: Consulta sobre estado de mi préstamo',
    body: 'Estimada María, su préstamo #12345 tiene un saldo pendiente de 3 cuotas. La próxima cuota vence el 25 de noviembre. Puede realizar el pago a través de nuestra plataforma en línea.',
    timestamp: new Date('2025-11-18T13:30:00Z').toISOString(),
    direccion: 'OUTBOUND',
    cliente_id: 5,
    ticket_id: 15,
    requiere_respuesta: false,
    procesado: true,
    respuesta_enviada: true,
    creado_en: new Date('2025-11-18T13:30:00Z').toISOString(),
  },
  // Ejemplo 7: Comunicación WhatsApp INBOUND - NUEVO
  {
    id: 7,
    tipo: 'whatsapp',
    from_contact: '+584165432109',
    to_contact: '+584129876543',
    subject: null,
    body: 'Buenas tardes, necesito información urgente sobre cómo puedo refinanciar mi préstamo actual.',
    timestamp: new Date('2025-11-18T10:45:00Z').toISOString(),
    direccion: 'INBOUND',
    cliente_id: null,
    ticket_id: null,
    requiere_respuesta: true,
    procesado: false,
    respuesta_enviada: false,
    creado_en: new Date('2025-11-18T10:45:00Z').toISOString(),
  },
  // Ejemplo 8: Comunicación Email INBOUND - Cliente identificado
  {
    id: 8,
    tipo: 'email',
    from_contact: 'juan.perez@hotmail.com',
    to_contact: 'atencion@rapicredit.com',
    subject: 'Problema con mi cuenta en línea',
    body: 'No puedo acceder a mi cuenta en la plataforma. He intentado recuperar mi contraseña pero no recibo el correo de recuperación. ¿Pueden ayudarme?',
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

// Mock data para nombres de clientes (para mejorar la visualización)
export const mockNombresClientes: Record<number, string> = {
  5: 'María González',
  8: 'Ana Martínez',
  12: 'Juan Pérez',
}

// Mock data para tickets
export const mockTickets = [
  {
    id: 12,
    titulo: 'Consulta sobre requisitos de préstamo',
    descripcion: 'Cliente solicita información sobre requisitos y monto mínimo',
    cliente_id: null,
    estado: 'abierto',
    prioridad: 'media',
    tipo: 'consulta',
    fecha_limite: new Date('2025-11-20T18:00:00Z').toISOString(),
  },
  {
    id: 15,
    titulo: 'Consulta estado de préstamo #12345',
    descripcion: 'Cliente solicita información sobre cuotas pendientes',
    cliente_id: 5,
    estado: 'resuelto',
    prioridad: 'baja',
    tipo: 'consulta',
    fecha_limite: null,
  },
]
