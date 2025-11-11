import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Search,
  Filter,
  Plus,
  Eye,
  Edit,
  GitBranch,
  Users,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatCurrency, formatDate } from '@/utils'

// Estados del embudo
const ESTADOS_EMBUDO = [
  { id: 'prospecto', label: 'Prospecto', color: 'bg-gray-100 text-gray-800', icon: Users },
  { id: 'evaluacion', label: 'En Evaluación', color: 'bg-blue-100 text-blue-800', icon: Clock },
  { id: 'aprobado', label: 'Aprobado', color: 'bg-green-100 text-green-800', icon: CheckCircle },
  { id: 'rechazado', label: 'Rechazado', color: 'bg-red-100 text-red-800', icon: XCircle },
  { id: 'prestamo_activo', label: 'Préstamo Activo', color: 'bg-purple-100 text-purple-800', icon: TrendingUp },
]

export function EmbudoClientes() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filtroEstado, setFiltroEstado] = useState<string>('todos')
  const [clientes] = useState<any[]>([]) // TODO: Conectar con API

  // Mock data para demostración
  const mockClientes = [
    {
      id: 1,
      nombre: 'Juan Pérez',
      cedula: '1234567890',
      telefono: '0991234567',
      estado: 'prospecto',
      montoSolicitado: 15000,
      fechaIngreso: new Date('2025-01-15'),
      concesionario: 'Concesionario A',
    },
    {
      id: 2,
      nombre: 'María González',
      cedula: '0987654321',
      telefono: '0997654321',
      estado: 'evaluacion',
      montoSolicitado: 25000,
      fechaIngreso: new Date('2025-01-14'),
      concesionario: 'Concesionario B',
    },
    {
      id: 3,
      nombre: 'Carlos Rodríguez',
      cedula: '1122334455',
      telefono: '0991122334',
      estado: 'aprobado',
      montoSolicitado: 30000,
      fechaIngreso: new Date('2025-01-13'),
      concesionario: 'Concesionario A',
    },
  ]

  const clientesFiltrados = mockClientes.filter(cliente => {
    const matchSearch =
      cliente.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cliente.cedula.includes(searchTerm) ||
      cliente.telefono.includes(searchTerm)
    const matchEstado = filtroEstado === 'todos' || cliente.estado === filtroEstado
    return matchSearch && matchEstado
  })

  const estadisticas = {
    total: mockClientes.length,
    prospectos: mockClientes.filter(c => c.estado === 'prospecto').length,
    evaluacion: mockClientes.filter(c => c.estado === 'evaluacion').length,
    aprobados: mockClientes.filter(c => c.estado === 'aprobado').length,
    rechazados: mockClientes.filter(c => c.estado === 'rechazado').length,
    activos: mockClientes.filter(c => c.estado === 'prestamo_activo').length,
  }

  const getEstadoInfo = (estado: string) => {
    return ESTADOS_EMBUDO.find(e => e.id === estado) || ESTADOS_EMBUDO[0]
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
            <GitBranch className="h-8 w-8 text-blue-600" />
            Embudo de Clientes
          </h1>
          <p className="text-gray-600 mt-1">
            Seguimiento de personas que requieren préstamos
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Cliente
        </Button>
      </motion.div>

      {/* Estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{estadisticas.total}</div>
            <p className="text-xs text-gray-600 mt-1">Total Clientes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">{estadisticas.prospectos}</div>
            <p className="text-xs text-gray-600 mt-1">Prospectos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{estadisticas.evaluacion}</div>
            <p className="text-xs text-gray-600 mt-1">En Evaluación</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{estadisticas.aprobados}</div>
            <p className="text-xs text-gray-600 mt-1">Aprobados</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-red-600">{estadisticas.rechazados}</div>
            <p className="text-xs text-gray-600 mt-1">Rechazados</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-purple-600">{estadisticas.activos}</div>
            <p className="text-xs text-gray-600 mt-1">Préstamos Activos</p>
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
                  placeholder="Buscar por nombre, cédula o teléfono..."
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

      {/* Tabla de Clientes */}
      <Card>
        <CardHeader>
          <CardTitle>Clientes en el Embudo</CardTitle>
          <CardDescription>
            Lista de clientes que requieren préstamos y su estado actual
          </CardDescription>
        </CardHeader>
        <CardContent>
          {clientesFiltrados.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No se encontraron clientes con los filtros aplicados</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Cédula</TableHead>
                    <TableHead>Teléfono</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Monto Solicitado</TableHead>
                    <TableHead>Concesionario</TableHead>
                    <TableHead>Fecha Ingreso</TableHead>
                    <TableHead>Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clientesFiltrados.map((cliente) => {
                    const estadoInfo = getEstadoInfo(cliente.estado)
                    const EstadoIcon = estadoInfo.icon
                    return (
                      <TableRow key={cliente.id}>
                        <TableCell className="font-medium">{cliente.nombre}</TableCell>
                        <TableCell>{cliente.cedula}</TableCell>
                        <TableCell>{cliente.telefono}</TableCell>
                        <TableCell>
                          <Badge className={estadoInfo.color}>
                            <EstadoIcon className="h-3 w-3 mr-1" />
                            {estadoInfo.label}
                          </Badge>
                        </TableCell>
                        <TableCell>{formatCurrency(cliente.montoSolicitado)}</TableCell>
                        <TableCell>{cliente.concesionario}</TableCell>
                        <TableCell>{formatDate(cliente.fechaIngreso)}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button variant="ghost" size="icon">
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon">
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
    </div>
  )
}

