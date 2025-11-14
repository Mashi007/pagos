import { useState } from 'react'
import { motion } from 'framer-motion'
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
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { formatDate } from '@/utils'
import { useSearchClientes } from '@/hooks/useClientes'
import { Cliente } from '@/types'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useSimpleAuth } from '@/store/simpleAuthStore'

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
  { id: 'alta', label: 'Alta', color: 'bg-orange-100 text-orange-800' },
  { id: 'urgente', label: 'Urgente', color: 'bg-red-100 text-red-800' },
]

// Tipos de ticket
const TIPOS_TICKET = [
  { id: 'consulta', label: 'Consulta' },
  { id: 'incidencia', label: 'Incidencia' },
  { id: 'solicitud', label: 'Solicitud' },
  { id: 'reclamo', label: 'Reclamo' },
]

interface Ticket {
  id: number
  titulo: string
  descripcion: string
  clienteId?: number
  cliente?: string
  clienteData?: Cliente
  estado: string
  prioridad: string
  asignadoA: string
  fechaCreacion: Date
  fechaActualizacion: Date
  tipo: string
}

export function TicketsAtencion() {
  const { user } = useSimpleAuth()
  const [searchTerm, setSearchTerm] = useState('')
  const [filtroEstado, setFiltroEstado] = useState<string>('todos')
  const [filtroPrioridad, setFiltroPrioridad] = useState<string>('todos')
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [searchCliente, setSearchCliente] = useState('')
  const [clienteSeleccionado, setClienteSeleccionado] = useState<Cliente | null>(null)
  const [nuevoTicket, setNuevoTicket] = useState<Partial<Ticket>>({
    titulo: '',
    descripcion: '',
    estado: 'abierto',
    prioridad: 'media',
    tipo: 'consulta',
    asignadoA: user ? `${user.nombre} ${user.apellido}` : '',
  })
  const [tickets, setTickets] = useState<Ticket[]>([])

  // Búsqueda de clientes para agregar al ticket
  // Búsqueda optimizada: se activa con 2 caracteres para capturar datos rápidamente
  const { data: clientesBuscados = [], isLoading: isLoadingSearch } = useSearchClientes(searchCliente)

  const ticketsFiltrados = tickets.filter(ticket => {
    const matchSearch =
      ticket.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ticket.cliente && ticket.cliente.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (ticket.clienteData && (
        ticket.clienteData.cedula.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (ticket.clienteData.telefono && ticket.clienteData.telefono.includes(searchTerm))
      )) ||
      ticket.descripcion.toLowerCase().includes(searchTerm.toLowerCase())
    const matchEstado = filtroEstado === 'todos' || ticket.estado === filtroEstado
    const matchPrioridad = filtroPrioridad === 'todos' || ticket.prioridad === filtroPrioridad
    return matchSearch && matchEstado && matchPrioridad
  })

  const estadisticas = {
    total: tickets.length,
    abiertos: tickets.filter(t => t.estado === 'abierto').length,
    enProceso: tickets.filter(t => t.estado === 'en_proceso').length,
    resueltos: tickets.filter(t => t.estado === 'resuelto').length,
    cerrados: tickets.filter(t => t.estado === 'cerrado').length,
  }

  const getEstadoInfo = (estado: string) => {
    return ESTADOS_TICKET.find(e => e.id === estado) || ESTADOS_TICKET[0]
  }

  const getPrioridadInfo = (prioridad: string) => {
    return PRIORIDADES.find(p => p.id === prioridad) || PRIORIDADES[0]
  }

  const handleSeleccionarCliente = (cliente: Cliente) => {
    // Capturar rápidamente todos los datos del cliente
    const nombreCompleto = [cliente.nombres, cliente.apellidos].filter(Boolean).join(' ').trim() || 'Sin nombre'
    setClienteSeleccionado(cliente)
    setNuevoTicket(prev => ({
      ...prev,
      clienteId: cliente.id,
      cliente: nombreCompleto,
      clienteData: cliente,
      // Pre-llenar descripción con datos del cliente si está vacía para agilizar
      descripcion: prev.descripcion || `Cliente: ${nombreCompleto}\nCédula: ${cliente.cedula}${cliente.telefono ? `\nTeléfono: ${cliente.telefono}` : ''}${cliente.email ? `\nEmail: ${cliente.email}` : ''}\n\n`,
    }))
    setSearchCliente('')
  }

  const handleCrearTicket = () => {
    if (!nuevoTicket.titulo || !nuevoTicket.descripcion) {
      return
    }

    const ticket: Ticket = {
      id: Date.now(),
      ...nuevoTicket,
      cliente: clienteSeleccionado 
        ? [clienteSeleccionado.nombres, clienteSeleccionado.apellidos].filter(Boolean).join(' ').trim() || 'Sin nombre'
        : nuevoTicket.cliente,
      clienteId: clienteSeleccionado?.id,
      clienteData: clienteSeleccionado || undefined,
      fechaCreacion: new Date(),
      fechaActualizacion: new Date(),
    } as Ticket

    setTickets(prev => [ticket, ...prev])
    setShowAddDialog(false)
    setNuevoTicket({
      titulo: '',
      descripcion: '',
      estado: 'abierto',
      prioridad: 'media',
      tipo: 'consulta',
      asignadoA: user ? `${user.nombre} ${user.apellido}` : '',
    })
    setClienteSeleccionado(null)
    setSearchCliente('')
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
            Tickets de Atención
          </h1>
          <p className="text-gray-600 mt-1">
            Gestión de incidencias y actividades que generan seguimiento
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
                  <Card className="p-3 bg-blue-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold">{[clienteSeleccionado.nombres, clienteSeleccionado.apellidos].filter(Boolean).join(' ') || 'Sin nombre'}</p>
                        <p className="text-sm text-gray-600">Cédula: {clienteSeleccionado.cedula}</p>
                        {clienteSeleccionado.telefono && (
                          <p className="text-sm text-gray-600">Tel: {clienteSeleccionado.telefono}</p>
                        )}
                        {clienteSeleccionado.email && (
                          <p className="text-sm text-gray-600">Email: {clienteSeleccionado.email}</p>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setClienteSeleccionado(null)
                          setNuevoTicket(prev => ({ ...prev, clienteId: undefined, cliente: undefined, clienteData: undefined }))
                        }}
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
                      <div className="max-h-48 overflow-y-auto border rounded-lg space-y-1 p-2 bg-white">
                        {clientesBuscados.map((cliente) => (
                          <Card
                            key={cliente.id}
                            className="cursor-pointer hover:bg-blue-50 hover:border-blue-300 transition-all"
                            onClick={() => handleSeleccionarCliente(cliente)}
                          >
                            <CardContent className="p-3">
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <p className="font-medium text-sm text-gray-900">{[cliente.nombres, cliente.apellidos].filter(Boolean).join(' ') || 'Sin nombre'}</p>
                                  <div className="flex gap-3 mt-1">
                                    <p className="text-xs text-gray-600">Cédula: <span className="font-medium">{cliente.cedula}</span></p>
                                    {cliente.telefono && (
                                      <p className="text-xs text-gray-600">Tel: <span className="font-medium">{cliente.telefono}</span></p>
                                    )}
                                    {cliente.email && (
                                      <p className="text-xs text-gray-600">Email: <span className="font-medium">{cliente.email}</span></p>
                                    )}
                                  </div>
                                </div>
                                <Button size="sm" variant="outline" className="ml-2">
                                  Seleccionar
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    ) : searchCliente.length > 0 && searchCliente.length < 2 ? (
                      <div className="text-xs text-gray-400 mt-1 px-1">
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
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddDialog(false)}>
                Cancelar
              </Button>
              <Button onClick={handleCrearTicket} disabled={!nuevoTicket.titulo || !nuevoTicket.descripcion}>
                Crear Ticket
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </motion.div>

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
          <CardTitle>Tickets de Atención</CardTitle>
          <CardDescription>
            Línea de tiempo de incidencias y actividades ordenadas por ID
          </CardDescription>
        </CardHeader>
        <CardContent>
          {ticketsFiltrados.length === 0 ? (
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
                  .sort((a, b) => a.id - b.id) // Ordenar por ID
                  .map((ticket, index) => {
                    const estadoInfo = getEstadoInfo(ticket.estado)
                    const prioridadInfo = getPrioridadInfo(ticket.prioridad)
                    const EstadoIcon = estadoInfo.icon
                    const isLast = index === ticketsFiltrados.length - 1
                    
                    return (
                      <motion.div
                        key={ticket.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="relative flex items-start gap-6"
                      >
                        {/* Punto en la línea de tiempo */}
                        <div className="relative z-10 flex-shrink-0">
                          <div className={`w-16 h-16 rounded-full flex items-center justify-center border-4 border-white shadow-lg ${
                            ticket.estado === 'resuelto' ? 'bg-green-500' :
                            ticket.estado === 'cerrado' ? 'bg-gray-500' :
                            ticket.estado === 'en_proceso' ? 'bg-yellow-500' :
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
                            className="bg-white rounded-lg border-2 border-gray-200 shadow-md hover:shadow-lg transition-all duration-200 p-6"
                          >
                            {/* Header del ticket */}
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex-1 min-w-0">
                                <h3 className="text-lg font-bold text-gray-900 mb-2">
                                  {ticket.titulo}
                                </h3>
                                <p className="text-sm text-gray-600 line-clamp-2">
                                  {ticket.descripcion}
                                </p>
                              </div>
                              <div className="flex gap-2 ml-4">
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <Eye className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <Edit className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MessageSquare className="h-4 w-4" />
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
                                      <p className="font-semibold text-sm text-gray-900">{ticket.cliente}</p>
                                      <div className="mt-1 space-y-0.5">
                                        <p className="text-xs text-gray-600">Cédula: <span className="font-medium">{ticket.clienteData.cedula}</span></p>
                                        {ticket.clienteData.telefono && (
                                          <p className="text-xs text-gray-600">Tel: <span className="font-medium">{ticket.clienteData.telefono}</span></p>
                                        )}
                                        {ticket.clienteData.email && (
                                          <p className="text-xs text-gray-600">Email: <span className="font-medium">{ticket.clienteData.email}</span></p>
                                        )}
                                      </div>
                                      {ticket.clienteId && (
                                        <Button
                                          variant="link"
                                          size="sm"
                                          className="h-auto p-0 text-xs mt-1 text-blue-600 hover:text-blue-700"
                                          onClick={() => window.open(`/clientes/${ticket.clienteId}`, '_blank')}
                                        >
                                          Ver cliente completo →
                                        </Button>
                                      )}
                                    </div>
                                  ) : (
                                    <p className="font-semibold text-sm text-gray-900">{ticket.cliente || 'N/A'}</p>
                                  )}
                                </div>
                              </div>

                              {/* Asignado a */}
                              <div className="flex items-start gap-3">
                                <User className="h-5 w-5 text-gray-400 mt-0.5 flex-shrink-0" />
                                <div className="min-w-0">
                                  <p className="text-xs text-gray-500 mb-1">Asignado a</p>
                                  <p className="font-semibold text-sm text-gray-900">{ticket.asignadoA}</p>
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
                                {ticket.tipo}
                              </Badge>
                              <div className="flex items-center gap-1 text-xs text-gray-500 ml-auto">
                                <Calendar className="h-3 w-3" />
                                <span>{formatDate(ticket.fechaCreacion)}</span>
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
        </CardContent>
      </Card>
    </div>
  )
}
