import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Search,
  Filter,
  Plus,
  Eye,
  Edit,
  Building,
  Users,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Car,
  DollarSign,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatCurrency, formatDate } from '@/utils'

// Estados del embudo de concesionarios
const ESTADOS_EMBUDO = [
  { id: 'activo', label: 'Activo', color: 'bg-green-100 text-green-800', icon: CheckCircle },
  { id: 'pendiente', label: 'Pendiente', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  { id: 'inactivo', label: 'Inactivo', color: 'bg-gray-100 text-gray-800', icon: XCircle },
]

export function EmbudoConcesionarios() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filtroEstado, setFiltroEstado] = useState<string>('todos')
  const [concesionarioSeleccionado, setConcesionarioSeleccionado] = useState<number | null>(null)

  // Mock data para demostración
  const mockConcesionarios = [
    {
      id: 1,
      nombre: 'Concesionario A',
      contacto: 'Juan Martínez',
      telefono: '0991234567',
      email: 'contacto@concesionarioa.com',
      estado: 'activo',
      clientesAsignados: 15,
      prestamosActivos: 12,
      montoTotal: 450000,
      fechaRegistro: new Date('2024-01-15'),
    },
    {
      id: 2,
      nombre: 'Concesionario B',
      contacto: 'María López',
      telefono: '0997654321',
      email: 'contacto@concesionariob.com',
      estado: 'activo',
      clientesAsignados: 8,
      prestamosActivos: 6,
      montoTotal: 180000,
      fechaRegistro: new Date('2024-02-20'),
    },
    {
      id: 3,
      nombre: 'Concesionario C',
      contacto: 'Carlos Sánchez',
      telefono: '0991122334',
      email: 'contacto@concesionarioc.com',
      estado: 'pendiente',
      clientesAsignados: 3,
      prestamosActivos: 0,
      montoTotal: 0,
      fechaRegistro: new Date('2025-01-10'),
    },
  ]

  const mockClientesPorConcesionario: Record<number, any[]> = {
    1: [
      { id: 1, nombre: 'Juan Pérez', estado: 'prestamo_activo', monto: 30000, fechaAsignacion: new Date('2024-12-01') },
      { id: 2, nombre: 'María González', estado: 'prestamo_activo', monto: 25000, fechaAsignacion: new Date('2024-12-15') },
      { id: 3, nombre: 'Carlos Rodríguez', estado: 'evaluacion', monto: 0, fechaAsignacion: new Date('2025-01-10') },
    ],
    2: [
      { id: 4, nombre: 'Ana Martínez', estado: 'prestamo_activo', monto: 20000, fechaAsignacion: new Date('2024-11-20') },
      { id: 5, nombre: 'Luis Fernández', estado: 'aprobado', monto: 35000, fechaAsignacion: new Date('2025-01-05') },
    ],
    3: [
      { id: 6, nombre: 'Pedro Gómez', estado: 'prospecto', monto: 0, fechaAsignacion: new Date('2025-01-12') },
    ],
  }

  const concesionariosFiltrados = mockConcesionarios.filter(concesionario => {
    const matchSearch =
      concesionario.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      concesionario.contacto.toLowerCase().includes(searchTerm.toLowerCase()) ||
      concesionario.telefono.includes(searchTerm) ||
      concesionario.email.toLowerCase().includes(searchTerm.toLowerCase())
    const matchEstado = filtroEstado === 'todos' || concesionario.estado === filtroEstado
    return matchSearch && matchEstado
  })

  const estadisticas = {
    total: mockConcesionarios.length,
    activos: mockConcesionarios.filter(c => c.estado === 'activo').length,
    pendientes: mockConcesionarios.filter(c => c.estado === 'pendiente').length,
    inactivos: mockConcesionarios.filter(c => c.estado === 'inactivo').length,
    totalClientes: mockConcesionarios.reduce((sum, c) => sum + c.clientesAsignados, 0),
    totalPrestamos: mockConcesionarios.reduce((sum, c) => sum + c.prestamosActivos, 0),
    montoTotal: mockConcesionarios.reduce((sum, c) => sum + c.montoTotal, 0),
  }

  const getEstadoInfo = (estado: string) => {
    return ESTADOS_EMBUDO.find(e => e.id === estado) || ESTADOS_EMBUDO[0]
  }

  const concesionarioDetalle = concesionarioSeleccionado
    ? mockConcesionarios.find(c => c.id === concesionarioSeleccionado)
    : null

  const clientesDetalle = concesionarioSeleccionado
    ? mockClientesPorConcesionario[concesionarioSeleccionado] || []
    : []

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
            <Building className="h-8 w-8 text-blue-600" />
            Embudo de Concesionarios
          </h1>
          <p className="text-gray-600 mt-1">
            Seguimiento de concesionarios y sus clientes asignados
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Concesionario
        </Button>
      </motion.div>

      {/* Estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{estadisticas.total}</div>
            <p className="text-xs text-gray-600 mt-1">Total Concesionarios</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{estadisticas.activos}</div>
            <p className="text-xs text-gray-600 mt-1">Activos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-yellow-600">{estadisticas.pendientes}</div>
            <p className="text-xs text-gray-600 mt-1">Pendientes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">{estadisticas.inactivos}</div>
            <p className="text-xs text-gray-600 mt-1">Inactivos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{estadisticas.totalClientes}</div>
            <p className="text-xs text-gray-600 mt-1">Total Clientes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-purple-600">{estadisticas.totalPrestamos}</div>
            <p className="text-xs text-gray-600 mt-1">Préstamos Activos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{formatCurrency(estadisticas.montoTotal)}</div>
            <p className="text-xs text-gray-600 mt-1">Monto Total</p>
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
                  placeholder="Buscar por nombre, contacto, teléfono o email..."
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
                {ESTADOS_EMBUDO.map((estado) => (
                  <SelectItem key={estado.id} value={estado.id}>
                    {estado.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tabla de Concesionarios */}
        <Card>
          <CardHeader>
            <CardTitle>Concesionarios</CardTitle>
            <CardDescription>
              Lista de concesionarios y su estado
            </CardDescription>
          </CardHeader>
          <CardContent>
            {concesionariosFiltrados.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p>No se encontraron concesionarios con los filtros aplicados</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Concesionario</TableHead>
                      <TableHead>Contacto</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Clientes</TableHead>
                      <TableHead>Préstamos</TableHead>
                      <TableHead>Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {concesionariosFiltrados.map((concesionario) => {
                      const estadoInfo = getEstadoInfo(concesionario.estado)
                      const EstadoIcon = estadoInfo.icon
                      return (
                        <TableRow
                          key={concesionario.id}
                          className={concesionarioSeleccionado === concesionario.id ? 'bg-blue-50' : ''}
                          onClick={() => setConcesionarioSeleccionado(
                            concesionarioSeleccionado === concesionario.id ? null : concesionario.id
                          )}
                        >
                          <TableCell className="font-medium">{concesionario.nombre}</TableCell>
                          <TableCell>
                            <div>
                              <div>{concesionario.contacto}</div>
                              <div className="text-xs text-gray-500">{concesionario.telefono}</div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge className={estadoInfo.color}>
                              <EstadoIcon className="h-3 w-3 mr-1" />
                              {estadoInfo.label}
                            </Badge>
                          </TableCell>
                          <TableCell>{concesionario.clientesAsignados}</TableCell>
                          <TableCell>{concesionario.prestamosActivos}</TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setConcesionarioSeleccionado(
                                    concesionarioSeleccionado === concesionario.id ? null : concesionario.id
                                  )
                                }}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon" onClick={(e) => e.stopPropagation()}>
                                <Edit className="h-4 w-4" />
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

        {/* Detalle de Clientes del Concesionario Seleccionado */}
        <Card>
          <CardHeader>
            <CardTitle>
              {concesionarioDetalle
                ? `Clientes de ${concesionarioDetalle.nombre}`
                : 'Seleccione un concesionario'}
            </CardTitle>
            <CardDescription>
              {concesionarioDetalle
                ? `Seguimiento de clientes asignados a este concesionario`
                : 'Haga clic en un concesionario para ver sus clientes'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!concesionarioDetalle ? (
              <div className="text-center py-12 text-gray-500">
                <Building className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p>Seleccione un concesionario para ver sus clientes asignados</p>
              </div>
            ) : clientesDetalle.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Users className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p>Este concesionario no tiene clientes asignados</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cliente</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Monto</TableHead>
                      <TableHead>Fecha Asignación</TableHead>
                      <TableHead>Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {clientesDetalle.map((cliente) => (
                      <TableRow key={cliente.id}>
                        <TableCell className="font-medium">{cliente.nombre}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{cliente.estado}</Badge>
                        </TableCell>
                        <TableCell>{formatCurrency(cliente.monto)}</TableCell>
                        <TableCell>{formatDate(cliente.fechaAsignacion)}</TableCell>
                        <TableCell>
                          <Button variant="ghost" size="icon">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

