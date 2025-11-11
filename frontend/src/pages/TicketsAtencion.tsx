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
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatDate } from '@/utils'

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

export function TicketsAtencion() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filtroEstado, setFiltroEstado] = useState<string>('todos')
  const [filtroPrioridad, setFiltroPrioridad] = useState<string>('todos')

  // Mock data para demostración
  const mockTickets = [
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

  const ticketsFiltrados = mockTickets.filter(ticket => {
    const matchSearch =
      ticket.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.cliente.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.descripcion.toLowerCase().includes(searchTerm.toLowerCase())
    const matchEstado = filtroEstado === 'todos' || ticket.estado === filtroEstado
    const matchPrioridad = filtroPrioridad === 'todos' || ticket.prioridad === filtroPrioridad
    return matchSearch && matchEstado && matchPrioridad
  })

  const estadisticas = {
    total: mockTickets.length,
    abiertos: mockTickets.filter(t => t.estado === 'abierto').length,
    enProceso: mockTickets.filter(t => t.estado === 'en_proceso').length,
    resueltos: mockTickets.filter(t => t.estado === 'resuelto').length,
    cerrados: mockTickets.filter(t => t.estado === 'cerrado').length,
  }

  const getEstadoInfo = (estado: string) => {
    return ESTADOS_TICKET.find(e => e.id === estado) || ESTADOS_TICKET[0]
  }

  const getPrioridadInfo = (prioridad: string) => {
    return PRIORIDADES.find(p => p.id === prioridad) || PRIORIDADES[0]
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
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Ticket
        </Button>
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
                        <TableCell>{ticket.cliente}</TableCell>
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

