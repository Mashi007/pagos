// Mock data para tickets - Ejemplos de configuración
// Este archivo contiene ejemplos de tickets de atención
// para mostrar cómo está estructurada la información

import { Ticket } from '@/services/ticketsService'

export const mockTickets: Ticket[] = [
  // Ticket 1: Consulta sobre préstamo - Abierto
  {
    id: 1,
    titulo: 'Consulta sobre estado de préstamo',
    descripcion: 'El cliente solicita información sobre el estado actual de su préstamo #12345. Necesita saber cuántas cuotas le faltan por pagar y el monto pendiente.',
    cliente_id: 5,
    cliente: 'María González',
    clienteData: {
      id: 5,
      nombres: 'María',
      apellidos: 'González',
      cedula: 'V-12345678',
      telefono: '+584121234567',
      email: 'maria.gonzalez@email.com',
    },
    conversacion_whatsapp_id: 1,
    estado: 'abierto',
    prioridad: 'media',
    tipo: 'consulta',
    asignado_a: 'Juan Pérez',
    asignado_a_id: 1,
    fecha_limite: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 días desde ahora
    fechaCreacion: new Date('2025-11-18T10:30:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T10:30:00Z').toISOString(),
  },
  // Ticket 2: Incidencia con pago - En proceso
  {
    id: 2,
    titulo: 'Problema con registro de pago',
    descripcion: 'El cliente reporta que realizó un pago pero no aparece registrado en el sistema. Fecha del pago: 15/11/2025. Monto: $500 USD. Número de referencia: REF-123456.',
    cliente_id: 8,
    cliente: 'Carlos Rodríguez',
    clienteData: {
      id: 8,
      nombres: 'Carlos',
      apellidos: 'Rodríguez',
      cedula: 'V-87654321',
      telefono: '+584147891234',
      email: 'carlos.rodriguez@gmail.com',
    },
    conversacion_whatsapp_id: 5,
    estado: 'en_proceso',
    prioridad: 'urgente',
    tipo: 'incidencia',
    asignado_a: 'Ana Martínez',
    asignado_a_id: 2,
    fecha_limite: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 días desde ahora
    fechaCreacion: new Date('2025-11-17T14:20:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T09:15:00Z').toISOString(),
  },
  // Ticket 3: Solicitud de información - Resuelto
  {
    id: 3,
    titulo: 'Solicitud de información sobre préstamos',
    descripcion: 'Cliente interesado en obtener un préstamo personal. Solicita información sobre tasas de interés, requisitos y montos disponibles.',
    cliente_id: undefined,
    cliente: 'Pedro Sánchez',
    clienteData: {
      id: 12,
      nombres: 'Pedro',
      apellidos: 'Sánchez',
      cedula: 'V-11223344',
      telefono: '+584125678901',
      email: 'pedro.sanchez@email.com',
    },
    comunicacion_email_id: 4,
    estado: 'resuelto',
    prioridad: 'baja',
    tipo: 'solicitud',
    asignado_a: 'Juan Pérez',
    asignado_a_id: 1,
    fecha_limite: new Date('2025-11-20T18:00:00Z').toISOString(),
    fechaCreacion: new Date('2025-11-16T12:00:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-17T16:30:00Z').toISOString(),
  },
  // Ticket 4: Reclamo sobre atención - Abierto
  {
    id: 4,
    titulo: 'Reclamo sobre atención recibida',
    descripcion: 'El cliente expresa su descontento con la atención recibida en la sucursal. Menciona que el personal no fue amable y no le proporcionó la información solicitada.',
    cliente_id: 15,
    cliente: 'Laura Fernández',
    clienteData: {
      id: 15,
      nombres: 'Laura',
      apellidos: 'Fernández',
      cedula: 'V-55667788',
      telefono: '+584129876543',
      email: 'laura.fernandez@email.com',
    },
    estado: 'abierto',
    prioridad: 'urgente',
    tipo: 'reclamo',
    asignado_a: 'Ana Martínez',
    asignado_a_id: 2,
    escalado: true,
    escalado_a_id: 3, // Escalado a admin
    fecha_limite: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString(), // 1 día desde ahora
    fechaCreacion: new Date('2025-11-18T08:45:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T08:45:00Z').toISOString(),
  },
  // Ticket 5: Contacto inicial - Cerrado
  {
    id: 5,
    titulo: 'Contacto inicial - Cliente nuevo',
    descripcion: 'Cliente nuevo se contactó para obtener información general sobre los servicios. Se le proporcionó información completa y se agendó una cita.',
    cliente_id: 20,
    cliente: 'Roberto Méndez',
    clienteData: {
      id: 20,
      nombres: 'Roberto',
      apellidos: 'Méndez',
      cedula: 'V-99887766',
      telefono: '+584123456789',
      email: 'roberto.mendez@email.com',
    },
    conversacion_whatsapp_id: 3,
    estado: 'cerrado',
    prioridad: 'baja',
    tipo: 'contacto',
    asignado_a: 'Juan Pérez',
    asignado_a_id: 1,
    fecha_limite: new Date('2025-11-15T18:00:00Z').toISOString(),
    fechaCreacion: new Date('2025-11-15T10:00:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-15T17:30:00Z').toISOString(),
  },
  // Ticket 6: Consulta sobre cuotas - En proceso
  {
    id: 6,
    titulo: 'Consulta sobre reprogramación de cuotas',
    descripcion: 'El cliente solicita información sobre la posibilidad de reprogramar sus cuotas pendientes debido a dificultades económicas temporales.',
    cliente_id: 7,
    cliente: 'Sofía Ramírez',
    clienteData: {
      id: 7,
      nombres: 'Sofía',
      apellidos: 'Ramírez',
      cedula: 'V-33445566',
      telefono: '+584144556677',
      email: 'sofia.ramirez@email.com',
    },
    estado: 'en_proceso',
    prioridad: 'media',
    tipo: 'consulta',
    asignado_a: 'Ana Martínez',
    asignado_a_id: 2,
    fecha_limite: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 días desde ahora
    fechaCreacion: new Date('2025-11-17T15:30:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T11:00:00Z').toISOString(),
  },
  // Ticket 7: Incidencia técnica - Abierto
  {
    id: 7,
    titulo: 'Error en plataforma de pagos en línea',
    descripcion: 'El cliente reporta que al intentar realizar un pago a través de la plataforma en línea, recibe un error. El sistema no procesa su tarjeta de crédito.',
    cliente_id: 11,
    cliente: 'Miguel Torres',
    clienteData: {
      id: 11,
      nombres: 'Miguel',
      apellidos: 'Torres',
      cedula: 'V-22334455',
      telefono: '+584155667788',
      email: 'miguel.torres@email.com',
    },
    estado: 'abierto',
    prioridad: 'urgente',
    tipo: 'incidencia',
    asignado_a: 'Juan Pérez',
    asignado_a_id: 1,
    fecha_limite: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 días desde ahora
    fechaCreacion: new Date('2025-11-18T13:20:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T13:20:00Z').toISOString(),
  },
  // Ticket 8: Solicitud de documentos - Resuelto
  {
    id: 8,
    titulo: 'Solicitud de copia de documentos',
    descripcion: 'El cliente solicita una copia de los documentos de su préstamo para fines de declaración de impuestos. Necesita facturas y estados de cuenta.',
    cliente_id: 9,
    cliente: 'Carmen López',
    clienteData: {
      id: 9,
      nombres: 'Carmen',
      apellidos: 'López',
      cedula: 'V-44556677',
      telefono: '+584166778899',
      email: 'carmen.lopez@email.com',
    },
    estado: 'resuelto',
    prioridad: 'media',
    tipo: 'solicitud',
    asignado_a: 'Ana Martínez',
    asignado_a_id: 2,
    fecha_limite: new Date('2025-11-19T18:00:00Z').toISOString(),
    fechaCreacion: new Date('2025-11-16T09:00:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-17T14:00:00Z').toISOString(),
  },
]

// Función helper para obtener tickets mock con paginación
export const getMockTicketsResponse = (page: number = 1, per_page: number = 20, estado?: string, prioridad?: string) => {
  let filteredTickets = [...mockTickets]

  // Aplicar filtros
  if (estado && estado !== 'todos') {
    filteredTickets = filteredTickets.filter(t => t.estado === estado)
  }
  if (prioridad && prioridad !== 'todos') {
    filteredTickets = filteredTickets.filter(t => t.prioridad === prioridad)
  }

  // Calcular paginación
  const total = filteredTickets.length
  const pages = Math.ceil(total / per_page)
  const startIndex = (page - 1) * per_page
  const endIndex = startIndex + per_page
  const paginatedTickets = filteredTickets.slice(startIndex, endIndex)

  return {
    tickets: paginatedTickets,
    paginacion: {
      page,
      per_page,
      total,
      pages,
    },
  }
}

