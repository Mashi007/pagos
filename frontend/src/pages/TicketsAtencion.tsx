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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
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
  const { data: clientesBuscados = [], isLoading: isLoadingSearch } = useSearchClientes(searchCliente)

  // Mock data inicial para demostración
  const mockTickets: Ticket[] = [
    {
      id: 1,
      titulo: 'Consulta sobre estado de préstamo',
      descripcion: 'Cliente solicita información sobre el estado de su préstamo',
      cliente: 'Juan Pérez',
      estado: 'abierto',
      prioridad: 'media',
      asignadoA: 'Ana García',
      fechaCreacion: new Date('2025-01-15'),
      fechaActualizacion: new Date('2025-01-15'),
      tipo: 'Consulta',
    },
    {
      id: 2,
      titulo: 'Problema con pago',
      descripcion: 'Cliente reporta problema al realizar pago',
      cliente: 'María González',
      estado: 'en_proceso',
      prioridad: 'alta',
      asignadoA: 'Carlos López',
      fechaCreacion: new Date('2025-01-14'),
      fechaActualizacion: new Date('2025-01-15'),
      tipo: 'Incidencia',
    },
    {
      id: 3,
      titulo: 'Solicitud de cambio de fecha de pago',
      descripcion: 'Cliente solicita cambiar fecha de pago',
      cliente: 'Carlos Rodríguez',
      estado: 'resuelto',
      prioridad: 'baja',
      asignadoA: 'Ana García',
      fechaCreacion: new Date('2025-01-13'),
      fechaActualizacion: new Date('2025-01-14'),
      tipo: 'Solicitud',
    },
  ]

  const todosTickets = tickets.length > 0 ? tickets : mockTickets

  const ticketsFiltrados = todosTickets.filter(ticket => {
    const matchSearch =
      ticket.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ticket.cliente && ticket.cliente.toLowerCase().includes(searchTerm.toLowerCase())) ||
      ticket.descripcion.toLowerCase().includes(searchTerm.toLowerCase())
    const matchEstado = filtroEstado === 'todos' || ticket.estado === filtroEstado
    const matchPrioridad = filtroPrioridad === 'todos' || ticket.prioridad === filtroPrioridad
    return matchSearch && matchEstado && matchPrioridad
  })

  const estadisticas = {
    total: todosTickets.length,
    abiertos: todosTickets.filter(t => t.estado === 'abierto').length,
    enProceso: todosTickets.filter(t => t.estado === 'en_proceso').length,
    resueltos: todosTickets.filter(t => t.estado === 'resuelto').length,
    cerrados: todosTickets.filter(t => t.estado === 'cerrado').length,
  }

  const getEstadoInfo = (estado: string) => {
    return ESTADOS_TICKET.find(e => e.id === estado) || ESTADOS_TICKET[0]
  }

  const getPrioridadInfo = (prioridad: string) => {
    return PRIORIDADES.find(p => p.id === prioridad) || PRIORIDADES[0]
  }

  const handleSeleccionarCliente = (cliente: Cliente) => {
    setClienteSeleccionado(cliente)
    setNuevoTicket(prev => ({
      ...prev,
      clienteId: cliente.id,
      cliente: `${cliente.nombres} ${cliente.apellidos}`,
      clienteData: cliente,
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
      cliente: clienteSeleccionado ? `${clienteSeleccionado.nombres} ${clienteSeleccionado.apellidos}` : nuevoTicket.cliente,
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
                        <p className="font-semibold">{clienteSeleccionado.nombres} {clienteSeleccionado.apellidos}</p>
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
                        placeholder="Buscar cliente por nombre, cédula o teléfono..."
                        value={searchCliente}
                        onChange={(e) => setSearchCliente(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    {isLoadingSearch ? (
                      <div className="flex justify-center py-4">
                        <LoadingSpinner />
                      </div>
                    ) : searchCliente.length >= 2 && clientesBuscados.length > 0 && (
                      <div className="max-h-48 overflow-y-auto border rounded-lg space-y-1 p-2">
                        {clientesBuscados.map((cliente) => (
                          <Card
                            key={cliente.id}
                            className="cursor-pointer hover:bg-gray-50 transition-colors"
                            onClick={() => handleSeleccionarCliente(cliente)}
                          >
                            <CardContent className="p-3">
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="font-medium text-sm">{cliente.nombres} {cliente.apellidos}</p>
                                  <p className="text-xs text-gray-500">Cédula: {cliente.cedula}</p>
                                  {cliente.telefono && (
                                    <p className="text-xs text-gray-500">Tel: {cliente.telefono}</p>
                                  )}
                                </div>
                                <Button size="sm" variant="outline">
                                  Seleccionar
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    )}
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

      {/* Tabla de Tickets */}
      <Card>
        <CardHeader>
          <CardTitle>Tickets de Atención</CardTitle>
          <CardDescription>
            Lista de incidencias y actividades que requieren seguimiento
          </CardDescription>
        </CardHeader>
        <CardContent>
          {ticketsFiltrados.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No se encontraron tickets con los filtros aplicados</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Título</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Prioridad</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Asignado a</TableHead>
                    <TableHead>Fecha Creación</TableHead>
                    <TableHead>Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ticketsFiltrados.map((ticket) => {
                    const estadoInfo = getEstadoInfo(ticket.estado)
                    const prioridadInfo = getPrioridadInfo(ticket.prioridad)
                    const EstadoIcon = estadoInfo.icon
                    return (
                      <TableRow key={ticket.id}>
                        <TableCell className="font-medium">#{ticket.id}</TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{ticket.titulo}</div>
                            <div className="text-sm text-gray-500 truncate max-w-xs">
                              {ticket.descripcion}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          {ticket.clienteData ? (
                            <div>
                              <div className="font-medium">{ticket.cliente}</div>
                              <div className="text-xs text-gray-500">Cédula: {ticket.clienteData.cedula}</div>
                              {ticket.clienteId && (
                                <Button
                                  variant="link"
                                  size="sm"
                                  className="h-auto p-0 text-xs"
                                  onClick={() => window.open(`/clientes/${ticket.clienteId}`, '_blank')}
                                >
                                  Ver cliente
                                </Button>
                              )}
                            </div>
                          ) : (
                            ticket.cliente
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge className={estadoInfo.color}>
                            <EstadoIcon className="h-3 w-3 mr-1" />
                            {estadoInfo.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={prioridadInfo.color}>
                            {prioridadInfo.label}
                          </Badge>
                        </TableCell>
                        <TableCell>{ticket.tipo}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-gray-400" />
                            {ticket.asignadoA}
                          </div>
                        </TableCell>
                        <TableCell>{formatDate(ticket.fechaCreacion)}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button variant="ghost" size="icon">
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon">
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon">
                              <MessageSquare className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
