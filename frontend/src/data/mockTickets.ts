// Mock data para tickets - Ejemplos de configuraciÃÂ³n
// Este archivo contiene ejemplos de tickets de atenciÃÂ³n
// para mostrar cÃÂ³mo estÃÂ¡ estructurada la informaciÃÂ³n

import { Ticket } from '../services/ticketsService'

export const mockTickets: Ticket[] = [
  // Ticket 1: Consulta sobre prÃÂ©stamo - Abierto
  {
    id: 1,
    titulo: 'Consulta sobre estado de prÃÂ©stamo',
    descripcion: 'El cliente solicita informaciÃÂ³n sobre el estado actual de su prÃÂ©stamo #12345. Necesita saber cuÃÂ¡ntas cuotas le faltan por pagar y el monto pendiente.',
    cliente_id: 5,
    cliente: 'MarÃÂ­a GonzÃÂ¡lez',
    clienteData: {
      id: 5,
      nombres: 'MarÃÂ­a',
      apellidos: 'GonzÃÂ¡lez',
      cedula: 'V-12345678',
      telefono: '+584121234567',
      email: 'maria.gonzalez@email.com',
    },
    conversacion_whatsapp_id: 1,
    estado: 'abierto',
    prioridad: 'media',
    tipo: 'consulta',
    asignado_a: 'Juan PÃÂ©rez',
    asignado_a_id: 1,
    fecha_limite: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 dÃÂ­as desde ahora
    fechaCreacion: new Date('2025-11-18T10:30:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T10:30:00Z').toISOString(),
  },
  // Ticket 2: Incidencia con pago - En proceso
  {
    id: 2,
    titulo: 'Problema con registro de pago',
    descripcion: 'El cliente reporta que realizÃÂ³ un pago pero no aparece registrado en el sistema. Fecha del pago: 15/11/2025. Monto: $500 USD. NÃÂºmero de referencia: REF-123456.',
    cliente_id: 8,
    cliente: 'Carlos RodrÃÂ­guez',
    clienteData: {
      id: 8,
      nombres: 'Carlos',
      apellidos: 'RodrÃÂ­guez',
      cedula: 'V-87654321',
      telefono: '+584147891234',
      email: 'carlos.rodriguez@gmail.com',
    },
    conversacion_whatsapp_id: 5,
    estado: 'en_proceso',
    prioridad: 'urgente',
    tipo: 'incidencia',
    asignado_a: 'Ana MartÃÂ­nez',
    asignado_a_id: 2,
    fecha_limite: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 dÃÂ­as desde ahora
    fechaCreacion: new Date('2025-11-17T14:20:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T09:15:00Z').toISOString(),
  },
  // Ticket 3: Solicitud de informaciÃÂ³n - Resuelto
  {
    id: 3,
    titulo: 'Solicitud de informaciÃÂ³n sobre prÃÂ©stamos',
    descripcion: 'Cliente interesado en obtener un prÃÂ©stamo personal. Solicita informaciÃÂ³n sobre tasas de interÃÂ©s, requisitos y montos disponibles.',
    cliente_id: undefined,
    cliente: 'Pedro SÃÂ¡nchez',
    clienteData: {
      id: 12,
      nombres: 'Pedro',
      apellidos: 'SÃÂ¡nchez',
      cedula: 'V-11223344',
      telefono: '+584125678901',
      email: 'pedro.sanchez@email.com',
    },
    comunicacion_email_id: 4,
    estado: 'resuelto',
    prioridad: 'baja',
    tipo: 'solicitud',
    asignado_a: 'Juan PÃÂ©rez',
    asignado_a_id: 1,
    fecha_limite: new Date('2025-11-20T18:00:00Z').toISOString(),
    fechaCreacion: new Date('2025-11-16T12:00:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-17T16:30:00Z').toISOString(),
  },
  // Ticket 4: Reclamo sobre atenciÃÂ³n - Abierto
  {
    id: 4,
    titulo: 'Reclamo sobre atenciÃÂ³n recibida',
    descripcion: 'El cliente expresa su descontento con la atenciÃÂ³n recibida en la sucursal. Menciona que el personal no fue amable y no le proporcionÃÂ³ la informaciÃÂ³n solicitada.',
    cliente_id: 15,
    cliente: 'Laura FernÃÂ¡ndez',
    clienteData: {
      id: 15,
      nombres: 'Laura',
      apellidos: 'FernÃÂ¡ndez',
      cedula: 'V-55667788',
      telefono: '+584129876543',
      email: 'laura.fernandez@email.com',
    },
    estado: 'abierto',
    prioridad: 'urgente',
    tipo: 'reclamo',
    asignado_a: 'Ana MartÃÂ­nez',
    asignado_a_id: 2,
    escalado: true,
    escalado_a_id: 3, // Escalado a admin
    fecha_limite: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString(), // 1 dÃÂ­a desde ahora
    fechaCreacion: new Date('2025-11-18T08:45:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T08:45:00Z').toISOString(),
  },
  // Ticket 5: Contacto inicial - Cerrado
  {
    id: 5,
    titulo: 'Contacto inicial - Cliente nuevo',
    descripcion: 'Cliente nuevo se contactÃÂ³ para obtener informaciÃÂ³n general sobre los servicios. Se le proporcionÃÂ³ informaciÃÂ³n completa y se agendÃÂ³ una cita.',
    cliente_id: 20,
    cliente: 'Roberto MÃÂ©ndez',
    clienteData: {
      id: 20,
      nombres: 'Roberto',
      apellidos: 'MÃÂ©ndez',
      cedula: 'V-99887766',
      telefono: '+584123456789',
      email: 'roberto.mendez@email.com',
    },
    conversacion_whatsapp_id: 3,
    estado: 'cerrado',
    prioridad: 'baja',
    tipo: 'contacto',
    asignado_a: 'Juan PÃÂ©rez',
    asignado_a_id: 1,
    fecha_limite: new Date('2025-11-15T18:00:00Z').toISOString(),
    fechaCreacion: new Date('2025-11-15T10:00:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-15T17:30:00Z').toISOString(),
  },
  // Ticket 6: Consulta sobre cuotas - En proceso
  {
    id: 6,
    titulo: 'Consulta sobre reprogramaciÃÂ³n de cuotas',
    descripcion: 'El cliente solicita informaciÃÂ³n sobre la posibilidad de reprogramar sus cuotas pendientes debido a dificultades econÃÂ³micas temporales.',
    cliente_id: 7,
    cliente: 'SofÃÂ­a RamÃÂ­rez',
    clienteData: {
      id: 7,
      nombres: 'SofÃÂ­a',
      apellidos: 'RamÃÂ­rez',
      cedula: 'V-33445566',
      telefono: '+584144556677',
      email: 'sofia.ramirez@email.com',
    },
    estado: 'en_proceso',
    prioridad: 'media',
    tipo: 'consulta',
    asignado_a: 'Ana MartÃÂ­nez',
    asignado_a_id: 2,
    fecha_limite: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 dÃÂ­as desde ahora
    fechaCreacion: new Date('2025-11-17T15:30:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T11:00:00Z').toISOString(),
  },
  // Ticket 7: Incidencia tÃÂ©cnica - Abierto
  {
    id: 7,
    titulo: 'Error en plataforma de pagos en lÃÂ­nea',
    descripcion: 'El cliente reporta que al intentar realizar un pago a travÃÂ©s de la plataforma en lÃÂ­nea, recibe un error. El sistema no procesa su tarjeta de crÃÂ©dito.',
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
    asignado_a: 'Juan PÃÂ©rez',
    asignado_a_id: 1,
    fecha_limite: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 dÃÂ­as desde ahora
    fechaCreacion: new Date('2025-11-18T13:20:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-18T13:20:00Z').toISOString(),
  },
  // Ticket 8: Solicitud de documentos - Resuelto
  {
    id: 8,
    titulo: 'Solicitud de copia de documentos',
    descripcion: 'El cliente solicita una copia de los documentos de su prÃÂ©stamo para fines de declaraciÃÂ³n de impuestos. Necesita facturas y estados de cuenta.',
    cliente_id: 9,
    cliente: 'Carmen LÃÂ³pez',
    clienteData: {
      id: 9,
      nombres: 'Carmen',
      apellidos: 'LÃÂ³pez',
      cedula: 'V-44556677',
      telefono: '+584166778899',
      email: 'carmen.lopez@email.com',
    },
    estado: 'resuelto',
    prioridad: 'media',
    tipo: 'solicitud',
    asignado_a: 'Ana MartÃÂ­nez',
    asignado_a_id: 2,
    fecha_limite: new Date('2025-11-19T18:00:00Z').toISOString(),
    fechaCreacion: new Date('2025-11-16T09:00:00Z').toISOString(),
    fechaActualizacion: new Date('2025-11-17T14:00:00Z').toISOString(),
  },
]

// FunciÃÂ³n helper para obtener tickets mock con paginaciÃÂ³n
export const getMockTicketsResponse = (page: number = 1, per_page: number = 20, estado?: string, prioridad?: string) => {
  let filteredTickets = [...mockTickets]

  // Aplicar filtros
  if (estado && estado !== 'todos') {
    filteredTickets = filteredTickets.filter(t => t.estado === estado)
  }
  if (prioridad && prioridad !== 'todos') {
    filteredTickets = filteredTickets.filter(t => t.prioridad === prioridad)
  }

  // Calcular paginaciÃÂ³n
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

