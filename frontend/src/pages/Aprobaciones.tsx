import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  CheckCircle,
  XCircle,
  Clock,
  User,
  DollarSign,
  Calendar,
  Search,
  Filter,
  Eye,
  Check,
  X,
  AlertTriangle,
  FileText,
  CreditCard,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatCurrency, formatDate } from '@/utils'

// Mock data para aprobaciones
const mockAprobaciones = [
  {
    id: 'APR001',
    tipo: 'PRESTAMO',
    cliente: 'Roberto Carlos Silva Pérez',
    cedula: 'V12345678',
    monto: 25000.00,
    fechaSolicitud: '2024-07-20',
    fechaLimite: '2024-07-25',
    estado: 'PENDIENTE',
    prioridad: 'ALTA',
    asesor: 'Carlos Mendoza',
    observaciones: 'Cliente con historial crediticio positivo',
    documentos: ['Cédula', 'Comprobante ingresos', 'Referencias'],
    score: 85,
  },
  {
    id: 'APR002',
    tipo: 'PRESTAMO',
    cliente: 'María Elena González López',
    cedula: 'V87654321',
    monto: 18000.00,
    fechaSolicitud: '2024-07-19',
    fechaLimite: '2024-07-24',
    estado: 'APROBADA',
    prioridad: 'MEDIA',
    asesor: 'María González',
    observaciones: 'Documentación completa, ingresos verificados',
    documentos: ['Cédula', 'Comprobante ingresos', 'Referencias', 'Garantías'],
    score: 92,
  },
  {
    id: 'APR003',
    tipo: 'PRESTAMO',
    cliente: 'Luis Alberto Martínez Torres',
    cedula: 'V11223344',
    monto: 35000.00,
    fechaSolicitud: '2024-07-18',
    fechaLimite: '2024-07-23',
    estado: 'RECHAZADA',
    prioridad: 'ALTA',
    asesor: 'Luis Rodríguez',
    observaciones: 'Score crediticio bajo, ingresos insuficientes',
    documentos: ['Cédula', 'Comprobante ingresos'],
    score: 45,
  },
  {
    id: 'APR004',
    tipo: 'REFINANCIAMIENTO',
    cliente: 'Ana Sofía Herrera Castro',
    cedula: 'V99887766',
    monto: 15000.00,
    fechaSolicitud: '2024-07-17',
    fechaLimite: '2024-07-22',
    estado: 'PENDIENTE',
    prioridad: 'BAJA',
    asesor: 'Ana Pérez',
    observaciones: 'Cliente actual, solicita refinanciamiento',
    documentos: ['Cédula', 'Estado cuenta actual'],
    score: 78,
  },
  {
    id: 'APR005',
    tipo: 'PRESTAMO',
    cliente: 'José Fernando Vargas Ruiz',
    cedula: 'V55443322',
    monto: 22000.00,
    fechaSolicitud: '2024-07-16',
    fechaLimite: '2024-07-21',
    estado: 'PENDIENTE',
    prioridad: 'MEDIA',
    asesor: 'José Silva',
    observaciones: 'Documentación en revisión',
    documentos: ['Cédula', 'Comprobante ingresos', 'Referencias'],
    score: 72,
  },
]

const tiposAprobacion = [
  { value: 'PRESTAMO', label: 'Préstamo', icon: CreditCard },
  { value: 'REFINANCIAMIENTO', label: 'Refinanciamiento', icon: RefreshCw },
  { value: 'AMPLIACION', label: 'Ampliación', icon: TrendingUp },
  { value: 'RENOVACION', label: 'Renovación', icon: RotateCcw },
]

export function Aprobaciones() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterEstado, setFilterEstado] = useState('Todos')
  const [filterTipo, setFilterTipo] = useState('Todos')
  const [filterPrioridad, setFilterPrioridad] = useState('Todos')
  const [selectedAprobacion, setSelectedAprobacion] = useState<string | null>(null)

  const filteredAprobaciones = mockAprobaciones.filter((aprobacion) => {
    const matchesSearch =
      aprobacion.cliente.toLowerCase().includes(searchTerm.toLowerCase()) ||
      aprobacion.cedula.includes(searchTerm) ||
      aprobacion.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      aprobacion.asesor.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesEstado = filterEstado === 'Todos' || aprobacion.estado === filterEstado
    const matchesTipo = filterTipo === 'Todos' || aprobacion.tipo === filterTipo
    const matchesPrioridad = filterPrioridad === 'Todos' || aprobacion.prioridad === filterPrioridad
    return matchesSearch && matchesEstado && matchesTipo && matchesPrioridad
  })

  const totalAprobaciones = mockAprobaciones.length
  const pendientes = mockAprobaciones.filter((a) => a.estado === 'PENDIENTE').length
  const aprobadas = mockAprobaciones.filter((a) => a.estado === 'APROBADA').length
  const rechazadas = mockAprobaciones.filter((a) => a.estado === 'RECHAZADA').length

  const handleAprobar = (id: string) => {
    console.log(`Aprobar solicitud ${id}`)
    // Lógica para aprobar
  }

  const handleRechazar = (id: string) => {
    console.log(`Rechazar solicitud ${id}`)
    // Lógica para rechazar
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <h1 className="text-3xl font-bold text-gray-900">Centro de Aprobaciones</h1>
      <p className="text-gray-600">Gestiona las solicitudes de préstamos y refinanciamientos.</p>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Solicitudes</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalAprobaciones}</div>
            <p className="text-xs text-muted-foreground">Solicitudes procesadas</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pendientes</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{pendientes}</div>
            <p className="text-xs text-muted-foreground">Requieren revisión</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Aprobadas</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{aprobadas}</div>
            <p className="text-xs text-muted-foreground">Solicitudes aprobadas</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rechazadas</CardTitle>
            <XCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{rechazadas}</div>
            <p className="text-xs text-muted-foreground">Solicitudes rechazadas</p>
          </CardContent>
        </Card>
      </div>

      {/* Aprobaciones List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Solicitudes de Aprobación
            <div className="flex space-x-2">
              <Button variant="outline" size="sm">
                <Filter className="mr-2 h-4 w-4" /> Filtros Avanzados
              </Button>
            </div>
          </CardTitle>
          <CardDescription>Lista de todas las solicitudes pendientes de aprobación.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <Input
              placeholder="Buscar por cliente, cédula, asesor o ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
              leftIcon={<Search className="h-4 w-4 text-gray-400" />}
            />
            <Select value={filterEstado} onValueChange={setFilterEstado}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todos</SelectItem>
                <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                <SelectItem value="APROBADA">Aprobada</SelectItem>
                <SelectItem value="RECHAZADA">Rechazada</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterTipo} onValueChange={setFilterTipo}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todos</SelectItem>
                <SelectItem value="PRESTAMO">Préstamo</SelectItem>
                <SelectItem value="REFINANCIAMIENTO">Refinanciamiento</SelectItem>
                <SelectItem value="AMPLIACION">Ampliación</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterPrioridad} onValueChange={setFilterPrioridad}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Prioridad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todas</SelectItem>
                <SelectItem value="ALTA">Alta</SelectItem>
                <SelectItem value="MEDIA">Media</SelectItem>
                <SelectItem value="BAJA">Baja</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead>Cédula</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Monto</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Prioridad</TableHead>
                <TableHead>Asesor</TableHead>
                <TableHead>Fecha Límite</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAprobaciones.length > 0 ? (
                filteredAprobaciones.map((aprobacion) => (
                  <TableRow key={aprobacion.id}>
                    <TableCell className="font-medium">{aprobacion.id}</TableCell>
                    <TableCell>{aprobacion.cliente}</TableCell>
                    <TableCell>{aprobacion.cedula}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{aprobacion.tipo}</Badge>
                    </TableCell>
                    <TableCell>{formatCurrency(aprobacion.monto)}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          aprobacion.score >= 80 ? 'success' :
                          aprobacion.score >= 60 ? 'warning' : 'destructive'
                        }
                      >
                        {aprobacion.score}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          aprobacion.prioridad === 'ALTA' ? 'destructive' :
                          aprobacion.prioridad === 'MEDIA' ? 'warning' : 'secondary'
                        }
                      >
                        {aprobacion.prioridad}
                      </Badge>
                    </TableCell>
                    <TableCell>{aprobacion.asesor}</TableCell>
                    <TableCell>
                      {(() => {
                        const fechaLimite = new Date(aprobacion.fechaLimite)
                        const hoy = new Date()
                        const diasRestantes = Math.ceil((fechaLimite.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24))
                        
                        return (
                          <div className={`text-sm ${diasRestantes < 0 ? 'text-red-600' : diasRestantes <= 1 ? 'text-yellow-600' : 'text-gray-600'}`}>
                            {formatDate(aprobacion.fechaLimite)}
                            {diasRestantes < 0 && <div className="text-xs">Vencida</div>}
                            {diasRestantes >= 0 && diasRestantes <= 1 && <div className="text-xs">Vence hoy</div>}
                          </div>
                        )
                      })()}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          aprobacion.estado === 'APROBADA'
                            ? 'success'
                            : aprobacion.estado === 'RECHAZADA'
                              ? 'destructive'
                              : 'warning'
                        }
                      >
                        {aprobacion.estado === 'PENDIENTE' && <Clock className="h-3 w-3 mr-1" />}
                        {aprobacion.estado === 'APROBADA' && <CheckCircle className="h-3 w-3 mr-1" />}
                        {aprobacion.estado === 'RECHAZADA' && <XCircle className="h-3 w-3 mr-1" />}
                        {aprobacion.estado}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedAprobacion(aprobacion.id)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {aprobacion.estado === 'PENDIENTE' && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-green-600 hover:text-green-700"
                              onClick={() => handleAprobar(aprobacion.id)}
                            >
                              <Check className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-600 hover:text-red-700"
                              onClick={() => handleRechazar(aprobacion.id)}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={11} className="text-center text-gray-500">
                    No se encontraron solicitudes.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detalle de Aprobación */}
      {selectedAprobacion && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <FileText className="mr-2 h-5 w-5" /> Detalle de Solicitud - {selectedAprobacion}
            </CardTitle>
            <CardDescription>Información completa de la solicitud seleccionada.</CardDescription>
          </CardHeader>
          <CardContent>
            {(() => {
              const aprobacion = mockAprobaciones.find(a => a.id === selectedAprobacion)
              if (!aprobacion) return null

              return (
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-4">
                    <h3 className="font-semibold">Información del Cliente</h3>
                    <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                      <div><strong>Cliente:</strong> {aprobacion.cliente}</div>
                      <div><strong>Cédula:</strong> {aprobacion.cedula}</div>
                      <div><strong>Tipo de Solicitud:</strong> {aprobacion.tipo}</div>
                      <div><strong>Monto Solicitado:</strong> {formatCurrency(aprobacion.monto)}</div>
                      <div><strong>Score Crediticio:</strong> {aprobacion.score}/100</div>
                      <div><strong>Asesor:</strong> {aprobacion.asesor}</div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Documentación</h3>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <ul className="space-y-1">
                        {aprobacion.documentos.map((doc, index) => (
                          <li key={index} className="flex items-center">
                            <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                            {doc}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="md:col-span-2 space-y-4">
                    <h3 className="font-semibold">Observaciones</h3>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <p>{aprobacion.observaciones}</p>
                    </div>
                  </div>

                  {aprobacion.estado === 'PENDIENTE' && (
                    <div className="md:col-span-2 flex justify-end space-x-2">
                      <Button
                        variant="outline"
                        className="text-red-600 border-red-600 hover:bg-red-50"
                        onClick={() => handleRechazar(aprobacion.id)}
                      >
                        <X className="mr-2 h-4 w-4" /> Rechazar
                      </Button>
                      <Button
                        className="text-green-600 bg-green-600 hover:bg-green-700"
                        onClick={() => handleAprobar(aprobacion.id)}
                      >
                        <Check className="mr-2 h-4 w-4" /> Aprobar
                      </Button>
                    </div>
                  )}
                </div>
              )
            })()}
          </CardContent>
        </Card>
      )}
    </motion.div>
  )
}
