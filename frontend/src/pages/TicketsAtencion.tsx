import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  Filter,
  Plus,
  Eye,
  Edit,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  AlertTriangle,
  User,
  MessageSquare,
  Calendar,
  Phone,
  Mail,
  XCircle as XCircleIcon,
  Loader2,
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog'
import { Label } from '../components/ui/label'
import { formatDate } from '../utils'
import { useSearchClientes } from '../hooks/useClientes'
import { Cliente } from '../types'
import { LoadingSpinner } from '../components/ui/loading-spinner'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { ticketsService, Ticket, TicketCreate } from '../services/ticketsService'
import { toast } from 'sonner'

// Estados de tickets
const ESTADOS_TICKET = [
  { id: 'abierto', label: 'Abierto', color: 'bg-blue-100 text-blue-800', icon: AlertCircle },
  { id: 'en_proceso', label: 'En Proceso', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  { id: 'resuelto', label: 'Resuelto', color: 'bg-green-100 text-green-800', icon: CheckCircle },
  { id: 'cerrado', label: 'Cerrado', color: 'bg-gray-100 text-gray-800', icon: XCircle },
]

// Prioridades
const PRIORIDADES = [
  { id: 'baja', label: 'Baja', color: 'bg-gray-100 text-gray-800' },
  { id: 'media', label: 'Media', color: 'bg-yellow-100 text-yellow-800' },
  { id: 'urgente', label: 'Urgente', color: 'bg-red-100 text-red-800' },
]

// Tipos de ticket
const TIPOS_TICKET = [
  { id: 'consulta', label: 'Consulta' },
  { id: 'incidencia', label: 'Incidencia' },
  { id: 'solicitud', label: 'Solicitud' },
  { id: 'reclamo', label: 'Reclamo' },
  { id: 'contacto', label: 'Contacto' },
]

// La interfaz Ticket ahora viene del servicio, pero la adaptamos para compatibilidad
type TicketLocal = Ticket & {
  clienteId?: number
  asignadoA?: string
  fechaCreacion?: Date
  fechaActualizacion?: Date
}

export function TicketsAtencion() {
  const { user } = useSimpleAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [filtroEstado, setFiltroEstado] = useState<string>('todos')
  const [filtroPrioridad, setFiltroPrioridad] = useState<string>('todos')
  const [page, setPage] = useState(1)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [ticketSeleccionado, setTicketSeleccionado] = useState<Ticket | null>(null)
  const [searchCliente, setSearchCliente] = useState('')
  const [clienteSeleccionado, setClienteSeleccionado] = useState<Cliente | null>(null)
  const [nuevoTicket, setNuevoTicket] = useState<Partial<TicketCreate>>({
    titulo: '',
    descripcion: '',
    estado: 'abierto',
    prioridad: 'media',
    tipo: 'consulta',
    asignado_a: user ? `${user.nombre} ${user.apellido}` : '',
    fecha_limite: '',
  })

  // Búsqueda de clientes para agregar al ticket (incluir todos los estados)
  const { data: clientesBuscados = [], isLoading: isLoadingSearch } = useSearchClientes(searchCliente, true)

  // Query para obtener tickets desde la BD (API real; sin mock)
  const {
    data: ticketsData,
    isLoading: isLoadingTickets,
    error: errorTickets,
    refetch: refetchTickets,
  } = useQuery({
    queryKey: ['tickets', page, filtroEstado, filtroPrioridad],
    queryFn: async () => {
      const response = await ticketsService.getTickets({
        page,
        per_page: 20,
        estado: filtroEstado !== 'todos' ? filtroEstado : undefined,
        prioridad: filtroPrioridad !== 'todos' ? filtroPrioridad : undefined,
      })
      return response ?? { tickets: [], paginacion: { page: 1, per_page: 20, total: 0, pages: 0 } }
    },
  })

  const tickets: TicketLocal[] = ticketsData?.tickets?.map((t) => ({
    ...t,
    clienteId: t.cliente_id,
    cliente: t.cliente || undefined,
    clienteData: t.clienteData || undefined,
    asignadoA: t.asignado_a || 'Sin asignar',
    fechaCreacion: t.fechaCreacion ? new Date(t.fechaCreacion) : new Date(),
    fechaActualizacion: t.fechaActualizacion ? new Date(t.fechaActualizacion) : new Date(),
  })) || []

  // Mutation para crear ticket
  const createTicketMutation = useMutation({
    mutationFn: (ticket: TicketCreate) => ticketsService.createTicket(ticket),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      setShowAddDialog(false)
      setNuevoTicket({
        titulo: '',
        descripcion: '',
        estado: 'abierto',
        prioridad: 'media',
        tipo: 'consulta',
        asignado_a: user ? `${user.nombre} ${user.apellido}` : '',
      })
      setClienteSeleccionado(null)
      toast.success('Ticket creado exitosamente')
    },
    onError: (error: any) => {
      const d = error?.response?.data?.detail
      const msg = typeof d === 'string' ? d : Array.isArray(d) ? d.map((x: any) => x?.msg ?? x?.message ?? JSON.stringify(x)).join('. ') : (d && typeof d === 'object' ? JSON.stringify(d) : 'Error creando ticket')
      toast.error(msg)
    },
  })

  // Mutation para actualizar ticket
  const updateTicketMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<TicketCreate> }) =>
      ticketsService.updateTicket(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      setShowEditDialog(false)
      setTicketSeleccionado(null)
      toast.success('Ticket actualizado exitosamente')
    },
    onError: (error: any) => {
      const d = error?.response?.data?.detail
      const msg = typeof d === 'string' ? d : Array.isArray(d) ? d.map((x: any) => x?.msg ?? x?.message ?? JSON.stringify(x)).join('. ') : (d && typeof d === 'object' ? JSON.stringify(d) : 'Error actualizando ticket')
      toast.error(msg)
    },
  })

  const ticketsFiltrados = tickets.filter(ticket => {
    const titulo = typeof ticket.titulo === 'string' ? ticket.titulo : ''
    const descripcion = typeof ticket.descripcion === 'string' ? ticket.descripcion : ''
    const clienteStr = typeof ticket.cliente === 'string' ? ticket.cliente : ''
    const matchSearch =
      titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (clienteStr && clienteStr.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (ticket.clienteData && (
        (String(ticket.clienteData.cedula ?? '').toLowerCase().includes(searchTerm.toLowerCase())) ||
        (ticket.clienteData.telefono && String(ticket.clienteData.telefono).includes(searchTerm))
      )) ||
      descripcion.toLowerCase().includes(searchTerm.toLowerCase())
    const matchEstado = filtroEstado === 'todos' || ticket.estado === filtroEstado
    const matchPrioridad = filtroPrioridad === 'todos' || ticket.prioridad === filtroPrioridad
    return matchSearch && matchEstado && matchPrioridad
  })

  const estadisticas = {
    total: ticketsData?.paginacion?.total || 0,
    abiertos: tickets.filter(t => t.estado === 'abierto').length,
    enProceso: tickets.filter(t => t.estado === 'en_proceso').length,
    resueltos: tickets.filter(t => t.estado === 'resuelto').length,
    cerrados: tickets.filter(t => t.estado === 'cerrado').length,
  }

  // âœ… Calcular tickets vencidos y próximos a vencer
  const ahora = new Date()
  const enUnaHora = new Date(ahora.getTime() + 60 * 60 * 1000)
  
  const ticketsVencidos = tickets.filter(ticket => {
    if (!ticket.fecha_limite || (ticket.estado !== 'abierto' && ticket.estado !== 'en_proceso')) {
      return false
    }
    const fechaLimite = new Date(ticket.fecha_limite)
    return fechaLimite <= ahora
  })

  const ticketsProximosAVencer = tickets.filter(ticket => {
    if (!ticket.fecha_limite || (ticket.estado !== 'abierto' && ticket.estado !== 'en_proceso')) {
      return false
    }
    const fechaLimite = new Date(ticket.fecha_limite)
    return fechaLimite > ahora && fechaLimite <= enUnaHora
  })

  const getEstadoInfo = (estado: string) => {
    return ESTADOS_TICKET.find(e => e.id === estado) || ESTADOS_TICKET[0]
  }

  const getPrioridadInfo = (prioridad: string) => {
    return PRIORIDADES.find(p => p.id === prioridad) || PRIORIDADES[0]
  }

  const handleSeleccionarCliente = (cliente: Cliente) => {
    // Capturar rápidamente todos los datos del cliente
    const nombreCompleto = cliente.nombres?.trim() || 'Sin nombre'
    setClienteSeleccionado(cliente)
    setNuevoTicket(prev => ({
      ...prev,
      clienteId: cliente.id,
      cliente: nombreCompleto,
      clienteData: cliente,
      // Pre-llenar descripción con datos del cliente si está vacía para agilizar
      descripcion: prev.descripcion || `Cliente: ${nombreCompleto}\nCédula: ${cliente.cedula}${cliente.telefono ? `\nTeléfono: ${cliente.telefono}` : ''}${cliente.email ? `\nEmail: ${cliente.email}` : ''}${cliente.direccion ? `\nDirección: ${cliente.direccion}` : ''}${cliente.ocupacion ? `\nOcupación: ${cliente.ocupacion}` : ''}\n\n`,
    }))
    setSearchCliente('')
  }

  const handleCrearTicket = () => {
    if (!nuevoTicket.titulo || !nuevoTicket.descripcion) {
      toast.error('Por favor completa el título y descripción del ticket')
      return
    }

    const ticketData: TicketCreate = {
      titulo: nuevoTicket.titulo!,
      descripcion: nuevoTicket.descripcion!,
      estado: nuevoTicket.estado || 'abierto',
      prioridad: nuevoTicket.prioridad || 'media',
      tipo: nuevoTicket.tipo || 'consulta',
      cliente_id: clienteSeleccionado?.id,
      asignado_a: nuevoTicket.asignado_a || (user ? `${user.nombre} ${user.apellido}` : undefined),
      asignado_a_id: user?.id,
      fecha_limite: nuevoTicket.fecha_limite || undefined,
    }

    createTicketMutation.mutate(ticketData)
  }

  const handleEditarTicket = (ticket: Ticket) => {
    setTicketSeleccionado(ticket)
    setNuevoTicket({
      titulo: ticket.titulo,
      descripcion: ticket.descripcion,
      estado: ticket.estado,
      prioridad: ticket.prioridad,
      tipo: ticket.tipo,
      asignado_a: ticket.asignado_a,
      fecha_limite: ticket.fecha_limite || '',
    })
    if (ticket.clienteData) {
      // Convertir clienteData parcial a Cliente completo con valores por defecto
      const clienteCompleto: Cliente = {
        ...ticket.clienteData,
        email: ticket.clienteData.email,
        estado: 'ACTIVO',
        activo: true,
        dias_mora: 0,
        fecha_registro: new Date().toISOString(),
      }
      setClienteSeleccionado(clienteCompleto)
    }
    setShowEditDialog(true)
  }

  const handleActualizarTicket = () => {
    if (!ticketSeleccionado) {
      toast.error('No hay ticket seleccionado')
      return
    }

    updateTicketMutation.mutate({
      id: ticketSeleccionado.id,
      data: {
        estado: nuevoTicket.estado,
        prioridad: nuevoTicket.prioridad,
        asignado_a: nuevoTicket.asignado_a,
        fecha_limite: nuevoTicket.fecha_limite || undefined,
      },
    })
  }

  const handleVerConversacion = (conversacionId?: number) => {
    if (conversacionId) {
      navigate(`/comunicaciones?conversacion_id=${conversacionId}`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="h-8 w-8 text-blue-600" />
            CRM — Centro de tickets
          </h1>
          <p className="text-gray-600 mt-1">
            Tickets conectados a la base de clientes. Se notifica por correo al crear o actualizar.
          </p>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nuevo Ticket
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Crear Nuevo Ticket</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              {/* Buscar Cliente */}
              <div className="space-y-2">
                <Label>Cliente</Label>
                {clienteSeleccionado ? (
                  <Card className="p-4 bg-green-50 border-2 border-green-300 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-3">
                          <CheckCircle className="h-5 w-5 text-green-600" />
                          <p className="font-semibold text-base text-green-900">
                            {typeof clienteSeleccionado.nombres === 'string' ? clienteSeleccionado.nombres : (clienteSeleccionado as any).nombre ?? 'Sin nombre'}
                          </p>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm ml-7">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-600 font-medium">Cédula:</span>
                            <span className="text-gray-900 font-semibold">{String(clienteSeleccionado.cedula ?? '')}</span>
                          </div>
                          {clienteSeleccionado.telefono && (
                            <div className="flex items-center gap-2">
                              <span className="text-gray-600 font-medium">Teléfono:</span>
                              <span className="text-gray-900 font-semibold">{String(clienteSeleccionado.telefono)}</span>
                            </div>
                          )}
                          {clienteSeleccionado.email && (
                            <div className="flex items-center gap-2 sm:col-span-2">
                              <span className="text-gray-600 font-medium">Email:</span>
                              <span className="text-gray-900 font-semibold break-all">{String(clienteSeleccionado.email)}</span>
                            </div>
                          )}
                          {clienteSeleccionado.direccion && (
                            <div className="flex items-center gap-2 sm:col-span-2">
                              <span className="text-gray-600 font-medium">Dirección:</span>
                              <span className="text-gray-900">{String(clienteSeleccionado.direccion)}</span>
                            </div>
                          )}
                          {clienteSeleccionado.ocupacion && (
                            <div className="flex items-center gap-2">
                              <span className="text-gray-600 font-medium">Ocupación:</span>
                              <span className="text-gray-900">{String(clienteSeleccionado.ocupacion)}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setClienteSeleccionado(null)
                          setNuevoTicket(prev => ({ ...prev, clienteId: undefined, cliente: undefined, clienteData: undefined }))
                          setSearchCliente('')
                        }}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <XCircleIcon className="h-4 w-4" />
                      </Button>
                    </div>
                  </Card>
                ) : (
                  <div className="space-y-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                      <Input
                        placeholder="Buscar cliente por nombre, cédula o teléfono (mín. 2 caracteres)..."
                        value={searchCliente}
                        onChange={(e) => setSearchCliente(e.target.value)}
                        className="pl-10"
                        autoFocus
                      />
                    </div>
                    {isLoadingSearch ? (
                      <div className="flex justify-center py-4">
                        <LoadingSpinner />
                      </div>
                    ) : searchCliente.length >= 2 && clientesBuscados.length === 0 ? (
                      <div className="text-center py-4 text-sm text-gray-500">
                        <AlertCircle className="h-5 w-5 mx-auto mb-2 text-gray-400" />
                        <p>No se encontraron clientes</p>
                      </div>
                    ) : searchCliente.length >= 2 && clientesBuscados.length > 0 ? (
                      <div className="max-h-64 overflow-y-auto border-2 border-blue-200 rounded-lg shadow-lg bg-white z-50">
                        <div className="p-2 bg-blue-50 border-b border-blue-200 sticky top-0">
                          <p className="text-xs font-semibold text-blue-700">
                            {clientesBuscados.length} {clientesBuscados.length === 1 ? 'resultado encontrado' : 'resultados encontrados'}
                          </p>
                        </div>
                        <div className="space-y-1 p-2">
                          {clientesBuscados.map((cliente) => (
                            <div
                              key={cliente.id}
                              className="cursor-pointer p-3 rounded-lg border border-gray-200 hover:bg-blue-50 hover:border-blue-300 hover:shadow-md transition-all"
                              onClick={() => handleSeleccionarCliente(cliente)}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <User className="h-4 w-4 text-blue-600 flex-shrink-0" />
                                    <p className="font-semibold text-sm text-gray-900 truncate">
                                      {typeof cliente.nombres === 'string' ? cliente.nombres : (cliente as any).nombre ?? 'Sin nombre'}
                                    </p>
                                  </div>
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 ml-6 text-xs">
                                    <div className="flex items-center gap-1.5">
                                      <span className="text-gray-500">Cédula:</span>
                                      <span className="font-medium text-gray-700">{String(cliente.cedula ?? '')}</span>
                                    </div>
                                    {cliente.telefono && (
                                      <div className="flex items-center gap-1.5">
                                        <span className="text-gray-500">Tel:</span>
                                        <span className="font-medium text-gray-700">{String(cliente.telefono)}</span>
                                      </div>
                                    )}
                                    {cliente.email && (
                                      <div className="flex items-center gap-1.5 sm:col-span-2">
                                        <span className="text-gray-500">Email:</span>
                                        <span className="font-medium text-gray-700 truncate">{String(cliente.email)}</span>
                                      </div>
                                    )}
                                    {cliente.direccion && (
                                      <div className="flex items-center gap-1.5 sm:col-span-2">
                                        <span className="text-gray-500">Dirección:</span>
                                        <span className="font-medium text-gray-700 truncate">{String(cliente.direccion)}</span>
                                      </div>
                                    )}
                                    {cliente.ocupacion && (
                                      <div className="flex items-center gap-1.5">
                                        <span className="text-gray-500">Ocupación:</span>
                                        <span className="font-medium text-gray-700">{String(cliente.ocupacion)}</span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="ml-2 flex-shrink-0"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleSeleccionarCliente(cliente)
                                  }}
                                >
                                  Seleccionar
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : searchCliente.length > 0 && searchCliente.length < 2 ? (
                      <div className="text-xs text-gray-500 mt-1 px-2 py-1 bg-gray-50 rounded border border-gray-200">
                        <AlertCircle className="h-3 w-3 inline mr-1" />
                        Escribe al menos 2 caracteres para buscar
                      </div>
                    ) : null}
                  </div>
                )}
              </div>

              {/* Título */}
              <div className="space-y-2">
                <Label htmlFor="titulo">Título *</Label>
                <Input
                  id="titulo"
                  placeholder="Ej: Consulta sobre estado de préstamo"
                  value={nuevoTicket.titulo}
                  onChange={(e) => setNuevoTicket(prev => ({ ...prev, titulo: e.target.value }))}
                />
              </div>

              {/* Descripción */}
              <div className="space-y-2">
                <Label htmlFor="descripcion">Descripción *</Label>
                <Textarea
                  id="descripcion"
                  placeholder="Describe el problema o consulta..."
                  value={nuevoTicket.descripcion}
                  onChange={(e) => setNuevoTicket(prev => ({ ...prev, descripcion: e.target.value }))}
                  rows={4}
                />
              </div>

              {/* Tipo, Estado, Prioridad */}
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="tipo">Tipo</Label>
                  <Select
                    value={nuevoTicket.tipo}
                    onValueChange={(value) => setNuevoTicket(prev => ({ ...prev, tipo: value }))}
                  >
                    <SelectTrigger id="tipo">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIPOS_TICKET.map((tipo) => (
                        <SelectItem key={tipo.id} value={tipo.id}>
                          {tipo.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="estado">Estado</Label>
                  <Select
                    value={nuevoTicket.estado}
                    onValueChange={(value) => setNuevoTicket(prev => ({ ...prev, estado: value }))}
                  >
                    <SelectTrigger id="estado">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ESTADOS_TICKET.map((estado) => (
                        <SelectItem key={estado.id} value={estado.id}>
                          {estado.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="prioridad">Prioridad</Label>
                  <Select
                    value={nuevoTicket.prioridad}
                    onValueChange={(value) => setNuevoTicket(prev => ({ ...prev, prioridad: value }))}
                  >
                    <SelectTrigger id="prioridad">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PRIORIDADES.map((prioridad) => (
                        <SelectItem key={prioridad.id} value={prioridad.id}>
                          {prioridad.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Fecha Límite */}
              <div className="space-y-2">
                <Label htmlFor="fecha_limite">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Fecha y Hora Límite
                  </div>
                </Label>
                <Input
                  id="fecha_limite"
                  type="datetime-local"
                  value={nuevoTicket.fecha_limite ? new Date(nuevoTicket.fecha_limite).toISOString().slice(0, 16) : ''}
                  onChange={(e) => {
                    const fechaHora = e.target.value
                    if (fechaHora) {
                      // Convertir a ISO format con timezone
                      const fechaISO = new Date(fechaHora).toISOString()
                      setNuevoTicket(prev => ({ ...prev, fecha_limite: fechaISO }))
                    } else {
                      setNuevoTicket(prev => ({ ...prev, fecha_limite: '' }))
                    }
                  }}
                  placeholder="Selecciona fecha y hora límite"
                />
                <p className="text-xs text-gray-500">
                  El sistema alertará cuando se alcance esta fecha y hora
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddDialog(false)} disabled={createTicketMutation.isPending}>
                Cancelar
              </Button>
              <Button
                onClick={handleCrearTicket}
                disabled={!nuevoTicket.titulo || !nuevoTicket.descripcion || createTicketMutation.isPending}
              >
                {createTicketMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creando...
                  </>
                ) : (
                  'Crear Ticket'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </motion.div>

      {/* âœ… Alertas de Tickets Vencidos */}
      {(ticketsVencidos.length > 0 || ticketsProximosAVencer.length > 0) && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-2"
        >
          {ticketsVencidos.length > 0 && (
            <Card className="border-red-500 bg-red-50">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-6 w-6 text-red-600" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-red-900">
                      {ticketsVencidos.length} Ticket{ticketsVencidos.length > 1 ? 's' : ''} Vencido{ticketsVencidos.length > 1 ? 's' : ''}
                    </h3>
                    <p className="text-sm text-red-700">
                      {ticketsVencidos.map(t => `#${t.id}: ${typeof t.titulo === 'string' ? t.titulo : ''}`).join(', ')}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          {ticketsProximosAVencer.length > 0 && (
            <Card className="border-yellow-500 bg-yellow-50">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <Clock className="h-6 w-6 text-yellow-600" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-yellow-900">
                      {ticketsProximosAVencer.length} Ticket{ticketsProximosAVencer.length > 1 ? 's' : ''} Próximo{ticketsProximosAVencer.length > 1 ? 's' : ''} a Vencer
                    </h3>
                    <p className="text-sm text-yellow-700">
                      {ticketsProximosAVencer.map(t => {
                        const fechaLimite = new Date(t.fecha_limite!)
                        const minutosRestantes = Math.round((fechaLimite.getTime() - new Date().getTime()) / (60 * 1000))
                        const titulo = typeof t.titulo === 'string' ? t.titulo : ''
                        return `#${t.id}: ${titulo} (${minutosRestantes} min)`
                      }).join(', ')}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </motion.div>
      )}

      {/* Estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{estadisticas.total}</div>
            <p className="text-xs text-gray-600 mt-1">Total Tickets</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{estadisticas.abiertos}</div>
            <p className="text-xs text-gray-600 mt-1">Abiertos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-yellow-600">{estadisticas.enProceso}</div>
            <p className="text-xs text-gray-600 mt-1">En Proceso</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{estadisticas.resueltos}</div>
            <p className="text-xs text-gray-600 mt-1">Resueltos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">{estadisticas.cerrados}</div>
            <p className="text-xs text-gray-600 mt-1">Cerrados</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Buscar por título, cliente o descripción..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={filtroEstado} onValueChange={setFiltroEstado}>
              <SelectTrigger className="w-full md:w-[200px]">
                <SelectValue placeholder="Filtrar por estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos los estados</SelectItem>
                {ESTADOS_TICKET.map((estado) => (
                  <SelectItem key={estado.id} value={estado.id}>
                    {estado.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filtroPrioridad} onValueChange={setFiltroPrioridad}>
              <SelectTrigger className="w-full md:w-[200px]">
                <SelectValue placeholder="Filtrar por prioridad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todas las prioridades</SelectItem>
                {PRIORIDADES.map((prioridad) => (
                  <SelectItem key={prioridad.id} value={prioridad.id}>
                    {prioridad.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Timeline de Tickets */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Tickets de Atención</CardTitle>
              <CardDescription>
                Gestión de incidencias y actividades que generan seguimiento
              </CardDescription>
            </div>
            {isLoadingTickets && (
              <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingTickets ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <span className="ml-3 text-gray-600">Cargando tickets...</span>
            </div>
          ) : errorTickets ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
              <p className="text-red-600 mb-4">Error cargando tickets</p>
              <Button variant="outline" onClick={() => refetchTickets()}>
                Reintentar
              </Button>
            </div>
          ) : ticketsFiltrados.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              {tickets.length === 0 ? (
                <>
                  <p className="text-lg font-medium mb-2">No hay tickets creados</p>
                  <p className="text-sm text-gray-400 mb-4">Crea tu primer ticket usando el botón "Nuevo Ticket"</p>
                </>
              ) : (
                <p>No se encontraron tickets con los filtros aplicados</p>
              )}
            </div>
          ) : (
            <div className="relative">
              {/* Línea vertical de la timeline */}
              <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-200 via-blue-300 to-blue-200" />

              {/* Lista de tickets en timeline */}
              <div className="space-y-6">
                {ticketsFiltrados
                  .sort((a, b) => {
                    // Ordenar por fecha más reciente primero
                    const fechaA = a.fechaCreacion ? new Date(a.fechaCreacion).getTime() : 0
                    const fechaB = b.fechaCreacion ? new Date(b.fechaCreacion).getTime() : 0
                    return fechaB - fechaA
                  })
                  .map((ticket, index) => {
                    const estadoStr = typeof ticket.estado === 'string' ? ticket.estado : 'abierto'
                    const prioridadStr = typeof ticket.prioridad === 'string' ? ticket.prioridad : 'media'
                    const estadoInfo = getEstadoInfo(estadoStr)
                    const prioridadInfo = getPrioridadInfo(prioridadStr)
                    const EstadoIcon = estadoInfo.icon
                    const isLast = index === ticketsFiltrados.length - 1

                    // Verificar si el ticket está vencido o próximo a vencer
                    const ahora = new Date()
                    const enUnaHora = new Date(ahora.getTime() + 60 * 60 * 1000)
                    let estadoFecha: 'vencido' | 'proximo' | 'normal' = 'normal'
                    let minutosRestantes = 0
                    
                    if (ticket.fecha_limite && (estadoStr === 'abierto' || estadoStr === 'en_proceso')) {
                      const fechaLimite = new Date(ticket.fecha_limite)
                      if (fechaLimite <= ahora) {
                        estadoFecha = 'vencido'
                      } else if (fechaLimite <= enUnaHora) {
                        estadoFecha = 'proximo'
                        minutosRestantes = Math.round((fechaLimite.getTime() - ahora.getTime()) / (60 * 1000))
                      }
                    }

                    const ticketTitulo = typeof ticket.titulo === 'string' ? ticket.titulo : ''
                    const ticketDescripcion = typeof ticket.descripcion === 'string' ? ticket.descripcion : ''
                    const ticketCliente = typeof ticket.cliente === 'string' ? ticket.cliente : 'N/A'
                    const ticketAsignadoA = typeof ticket.asignadoA === 'string' ? ticket.asignadoA : 'Sin asignar'

                    return (
                      <motion.div
                        key={ticket.id != null ? String(ticket.id) : `ticket-${index}`}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="relative flex items-start gap-6"
                      >
                        {/* Punto en la línea de tiempo */}
                        <div className="relative z-10 flex-shrink-0">
                          <div className={`w-16 h-16 rounded-full flex items-center justify-center border-4 border-white shadow-lg ${
                            estadoFecha === 'vencido' ? 'bg-red-500 animate-pulse' :
                            estadoFecha === 'proximo' ? 'bg-orange-500' :
                            estadoStr === 'resuelto' ? 'bg-green-500' :
                            estadoStr === 'cerrado' ? 'bg-gray-500' :
                            estadoStr === 'en_proceso' ? 'bg-yellow-500' :
                            'bg-blue-500'
                          }`}>
                            <span className="text-white font-bold text-sm">#{ticket.id}</span>
                          </div>
                          {!isLast && (
                            <div className="absolute left-1/2 top-16 w-0.5 h-6 bg-gradient-to-b from-blue-300 to-blue-200 transform -translate-x-1/2" />
                          )}
                        </div>

                        {/* Contenido del ticket */}
                        <div className="flex-1 min-w-0">
                          <motion.div
                            whileHover={{ scale: 1.01 }}
                            className={`bg-white rounded-lg border-2 shadow-md hover:shadow-lg transition-all duration-200 p-6 ${
                              estadoFecha === 'vencido' ? 'border-red-500 bg-red-50' :
                              estadoFecha === 'proximo' ? 'border-orange-500 bg-orange-50' :
                              'border-gray-200'
                            }`}
                          >
                            {/* Header del ticket */}
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-2">
                                  <h3 className="text-lg font-bold text-gray-900">
                                    {ticketTitulo}
                                  </h3>
                                  {estadoFecha === 'vencido' && (
                                    <Badge className="bg-red-600 text-white animate-pulse">
                                      <AlertTriangle className="h-3 w-3 mr-1" />
                                      Vencido
                                    </Badge>
                                  )}
                                  {estadoFecha === 'proximo' && (
                                    <Badge className="bg-orange-600 text-white">
                                      <Clock className="h-3 w-3 mr-1" />
                                      Vence en {minutosRestantes} min
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-sm text-gray-600 line-clamp-2">
                                  {ticketDescripcion}
                                </p>
                              </div>
                              <div className="flex gap-2 ml-4">
                                {ticket.conversacion_whatsapp_id && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleVerConversacion(ticket.conversacion_whatsapp_id)}
                                    className="text-green-600 hover:text-green-700 hover:bg-green-50"
                                    title="Ver conversación de WhatsApp"
                                  >
                                    <MessageSquare className="h-4 w-4 mr-1" />
                                    WhatsApp
                                  </Button>
                                )}
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  onClick={() => handleEditarTicket(ticket)}
                                  title="Editar ticket"
                                >
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>

                            {/* Información del ticket */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                              {/* Cliente */}
                              <div className="flex items-start gap-3">
                                <User className="h-5 w-5 text-gray-400 mt-0.5 flex-shrink-0" />
                                <div className="min-w-0 flex-1">
                                  <p className="text-xs text-gray-500 mb-1">Cliente</p>
                                  {ticket.clienteData ? (
                                    <div>
                                      <p className="font-semibold text-sm text-gray-900">{ticketCliente}</p>
                                      <div className="mt-1 space-y-0.5">
                                        <p className="text-xs text-gray-600">Cédula: <span className="font-medium">{String(ticket.clienteData.cedula ?? '')}</span></p>
                                        {ticket.clienteData.telefono && (
                                          <p className="text-xs text-gray-600">Tel: <span className="font-medium">{String(ticket.clienteData.telefono)}</span></p>
                                        )}
                                        {ticket.clienteData.email && (
                                          <p className="text-xs text-gray-600">Email: <span className="font-medium">{String(ticket.clienteData.email)}</span></p>
                                        )}
                                      </div>
                                      {ticket.clienteId != null && (
                                        <Button
                                          variant="link"
                                          size="sm"
                                          className="h-auto p-0 text-xs mt-1 text-blue-600 hover:text-blue-700"
                                          onClick={() => window.open(`/clientes/${ticket.clienteId}`, '_blank')}
                                        >
                                          Ver cliente completo → â†’
                                        </Button>
                                      )}
                                    </div>
                                  ) : (
                                    <p className="font-semibold text-sm text-gray-900">{ticketCliente}</p>
                                  )}
                                </div>
                              </div>

                              {/* Asignado a */}
                              <div className="flex items-start gap-3">
                                <User className="h-5 w-5 text-gray-400 mt-0.5 flex-shrink-0" />
                                <div className="min-w-0">
                                  <p className="text-xs text-gray-500 mb-1">Asignado a</p>
                                  <p className="font-semibold text-sm text-gray-900">{ticketAsignadoA}</p>
                                </div>
                              </div>
                            </div>

                            {/* Badges y metadata */}
                            <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-gray-200">
                              <Badge className={`${estadoInfo.color} flex items-center gap-1`}>
                                <EstadoIcon className="h-3 w-3" />
                                {estadoInfo.label}
                              </Badge>
                              <Badge className={prioridadInfo.color}>
                                {prioridadInfo.label}
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {typeof ticket.tipo === 'string' ? ticket.tipo : 'consulta'}
                              </Badge>
                              {ticket.conversacion_whatsapp_id && (
                                <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                                  <MessageSquare className="h-3 w-3 mr-1" />
                                  Vinculado a WhatsApp
                                </Badge>
                              )}
                              {ticket.fecha_limite && (
                                <Badge 
                                  variant="outline" 
                                  className={`text-xs ${
                                    estadoFecha === 'vencido' ? 'bg-red-50 text-red-700 border-red-200' :
                                    estadoFecha === 'proximo' ? 'bg-orange-50 text-orange-700 border-orange-200' :
                                    'bg-blue-50 text-blue-700 border-blue-200'
                                  }`}
                                >
                                  <Clock className="h-3 w-3 mr-1" />
                                  Límite: {formatDate(ticket.fecha_limite)}
                                </Badge>
                              )}
                              <div className="flex items-center gap-1 text-xs text-gray-500 ml-auto">
                                <Calendar className="h-3 w-3" />
                                <span>{ticket.fechaCreacion ? formatDate(ticket.fechaCreacion) : 'N/A'}</span>
                              </div>
                            </div>
                          </motion.div>
                        </div>
                      </motion.div>
                    )
                  })}
              </div>
            </div>
          )}

          {/* Paginación */}
          {ticketsData?.paginacion && ticketsData.paginacion.pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t mt-6">
              <div className="text-sm text-gray-600">
                Página {ticketsData.paginacion.page} de {ticketsData.paginacion.pages} ({ticketsData.paginacion.total} total)
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1 || isLoadingTickets}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(ticketsData.paginacion.pages, p + 1))}
                  disabled={page === ticketsData.paginacion.pages || isLoadingTickets}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal para editar ticket */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Editar Ticket #{ticketSeleccionado?.id}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {/* Mismo formulario que crear, pero con datos precargados */}
            <div className="space-y-2">
              <Label htmlFor="titulo-edit">Título *</Label>
              <Input
                id="titulo-edit"
                placeholder="Ej: Consulta sobre estado de préstamo"
                value={nuevoTicket.titulo || ''}
                onChange={(e) => setNuevoTicket(prev => ({ ...prev, titulo: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="descripcion-edit">Descripción *</Label>
              <Textarea
                id="descripcion-edit"
                placeholder="Describe el problema o consulta..."
                value={nuevoTicket.descripcion || ''}
                onChange={(e) => setNuevoTicket(prev => ({ ...prev, descripcion: e.target.value }))}
                rows={4}
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tipo-edit">Tipo</Label>
                <Select
                  value={nuevoTicket.tipo || 'consulta'}
                  onValueChange={(value) => setNuevoTicket(prev => ({ ...prev, tipo: value }))}
                >
                  <SelectTrigger id="tipo-edit">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIPOS_TICKET.map((tipo) => (
                      <SelectItem key={tipo.id} value={tipo.id}>
                        {tipo.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="estado-edit">Estado</Label>
                <Select
                  value={nuevoTicket.estado || 'abierto'}
                  onValueChange={(value) => setNuevoTicket(prev => ({ ...prev, estado: value }))}
                >
                  <SelectTrigger id="estado-edit">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ESTADOS_TICKET.map((estado) => (
                      <SelectItem key={estado.id} value={estado.id}>
                        {estado.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="prioridad-edit">Prioridad</Label>
                <Select
                  value={nuevoTicket.prioridad || 'media'}
                  onValueChange={(value) => setNuevoTicket(prev => ({ ...prev, prioridad: value }))}
                >
                  <SelectTrigger id="prioridad-edit">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORIDADES.map((prioridad) => (
                      <SelectItem key={prioridad.id} value={prioridad.id}>
                        {prioridad.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Fecha Límite */}
              <div className="space-y-2">
                <Label htmlFor="fecha_limite-edit">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Fecha y Hora Límite
                  </div>
                </Label>
                <Input
                  id="fecha_limite-edit"
                  type="datetime-local"
                  value={nuevoTicket.fecha_limite ? new Date(nuevoTicket.fecha_limite).toISOString().slice(0, 16) : ''}
                  onChange={(e) => {
                    const fechaHora = e.target.value
                    if (fechaHora) {
                      const fechaISO = new Date(fechaHora).toISOString()
                      setNuevoTicket(prev => ({ ...prev, fecha_limite: fechaISO }))
                    } else {
                      setNuevoTicket(prev => ({ ...prev, fecha_limite: '' }))
                    }
                  }}
                  placeholder="Selecciona fecha y hora límite"
                />
                <p className="text-xs text-gray-500">
                  El sistema alertará cuando se alcance esta fecha y hora
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowEditDialog(false)} disabled={updateTicketMutation.isPending}>
                Cancelar
              </Button>
              <Button
                onClick={handleActualizarTicket}
                disabled={!nuevoTicket.titulo || !nuevoTicket.descripcion || updateTicketMutation.isPending}
              >
              {updateTicketMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Actualizando...
                </>
              ) : (
                'Actualizar Ticket'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default TicketsAtencion
