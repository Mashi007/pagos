import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  CreditCard,
  DollarSign,
  Users,
  Calendar,
  Search,
  Filter,
  ArrowDownToLine,
  PlusCircle,
  Eye,
  Edit,
  Trash2,
  CheckCircle,
  Clock,
  AlertTriangle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatCurrency, formatDate } from '@/utils'

// Mock data para préstamos
const mockPrestamos = [
  {
    id: 'PREST001',
    cliente: 'Juan Carlos Pérez González',
    cedula: '12345678',
    vehiculo: 'Toyota Corolla 2022',
    monto: 20000.00,
    cuotaMensual: 450.50,
    plazo: 48,
    tasa: 12.5,
    fechaAprobacion: '2024-06-15',
    estado: 'ACTIVO',
    saldoPendiente: 10812.00,
    proximaCuota: '2024-08-01',
    diasMora: 0,
  },
  {
    id: 'PREST002',
    cliente: 'María Elena Rodríguez López',
    cedula: '87654321',
    vehiculo: 'Hyundai Accent 2023',
    monto: 15000.00,
    cuotaMensual: 416.67,
    plazo: 36,
    tasa: 11.8,
    fechaAprobacion: '2024-07-10',
    estado: 'ACTIVO',
    saldoPendiente: 10000.00,
    proximaCuota: '2024-08-05',
    diasMora: 0,
  },
  {
    id: 'PREST003',
    cliente: 'Carlos Alberto Martínez Silva',
    cedula: '11223344',
    vehiculo: 'Nissan Versa 2021',
    monto: 18000.00,
    cuotaMensual: 428.57,
    plazo: 42,
    tasa: 13.2,
    fechaAprobacion: '2024-05-20',
    estado: 'EN_MORA',
    saldoPendiente: 13714.30,
    proximaCuota: '2024-07-25',
    diasMora: 15,
  },
  {
    id: 'PREST004',
    cliente: 'Ana Sofía Gómez Herrera',
    cedula: '99887766',
    vehiculo: 'Kia Sportage 2024',
    monto: 30000.00,
    cuotaMensual: 625.00,
    plazo: 48,
    tasa: 10.5,
    fechaAprobacion: '2023-12-01',
    estado: 'FINALIZADO',
    saldoPendiente: 0.00,
    proximaCuota: '2024-07-01',
    diasMora: 0,
  },
  {
    id: 'PREST005',
    cliente: 'Luis Fernando Vargas Castro',
    cedula: '55443322',
    vehiculo: 'Mazda CX-5 2023',
    monto: 25000.00,
    cuotaMensual: 520.83,
    plazo: 48,
    tasa: 12.0,
    fechaAprobacion: '2024-06-01',
    estado: 'ACTIVO',
    saldoPendiente: 20833.33,
    proximaCuota: '2024-08-01',
    diasMora: 0,
  },
]

export function Prestamos() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState('Todos')
  const [filterEstado, setFilterEstado] = useState('Todos')

  const filteredPrestamos = mockPrestamos.filter((prestamo) => {
    const matchesSearch =
      prestamo.cliente.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prestamo.cedula.includes(searchTerm) ||
      prestamo.vehiculo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prestamo.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = filterStatus === 'Todos' || prestamo.estado === filterStatus
    return matchesSearch && matchesStatus
  })

  const totalPrestamos = mockPrestamos.length
  const prestamosActivos = mockPrestamos.filter((p) => p.estado === 'ACTIVO').length
  const prestamosEnMora = mockPrestamos.filter((p) => p.estado === 'EN_MORA').length
  const carteraTotal = mockPrestamos.reduce((sum, p) => sum + p.saldoPendiente, 0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <h1 className="text-3xl font-bold text-gray-900">Gestión de Préstamos</h1>
      <p className="text-gray-600">Administra y monitorea todos los préstamos del sistema.</p>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Préstamos</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalPrestamos}</div>
            <p className="text-xs text-muted-foreground">Préstamos registrados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Préstamos Activos</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{prestamosActivos}</div>
            <p className="text-xs text-muted-foreground">En proceso de pago</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">En Mora</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{prestamosEnMora}</div>
            <p className="text-xs text-muted-foreground">Requieren seguimiento</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cartera Total</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(carteraTotal)}</div>
            <p className="text-xs text-muted-foreground">Saldo pendiente</p>
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Lista de Préstamos
            <div className="flex space-x-2">
              <Button>
                <PlusCircle className="mr-2 h-4 w-4" /> Nuevo Préstamo
              </Button>
              <Button variant="outline" size="sm">
                <ArrowDownToLine className="mr-2 h-4 w-4" /> Exportar
              </Button>
            </div>
          </CardTitle>
          <CardDescription>Gestiona todos los préstamos del sistema.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <Input
              placeholder="Buscar por cliente, cédula, vehículo o ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
              leftIcon={<Search className="h-4 w-4 text-gray-400" />}
            />
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px]">
                <Filter className="mr-2 h-4 w-4 text-gray-400" />
                <SelectValue placeholder="Filtrar por estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todos los estados</SelectItem>
                <SelectItem value="ACTIVO">Activo</SelectItem>
                <SelectItem value="EN_MORA">En Mora</SelectItem>
                <SelectItem value="FINALIZADO">Finalizado</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID Préstamo</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead>Cédula</TableHead>
                <TableHead>Vehículo</TableHead>
                <TableHead>Monto</TableHead>
                <TableHead>Cuota Mensual</TableHead>
                <TableHead>Plazo</TableHead>
                <TableHead>Tasa</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Saldo</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPrestamos.length > 0 ? (
                filteredPrestamos.map((prestamo) => (
                  <TableRow key={prestamo.id}>
                    <TableCell className="font-medium">{prestamo.id}</TableCell>
                    <TableCell>{prestamo.cliente}</TableCell>
                    <TableCell>{prestamo.cedula}</TableCell>
                    <TableCell>{prestamo.vehiculo}</TableCell>
                    <TableCell>{formatCurrency(prestamo.monto)}</TableCell>
                    <TableCell>{formatCurrency(prestamo.cuotaMensual)}</TableCell>
                    <TableCell>{prestamo.plazo} meses</TableCell>
                    <TableCell>{prestamo.tasa}%</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          prestamo.estado === 'ACTIVO'
                            ? 'success'
                            : prestamo.estado === 'EN_MORA'
                              ? 'destructive'
                              : 'default'
                        }
                      >
                        {prestamo.estado === 'ACTIVO' && <CheckCircle className="h-3 w-3 mr-1" />}
                        {prestamo.estado === 'EN_MORA' && <AlertTriangle className="h-3 w-3 mr-1" />}
                        {prestamo.estado === 'FINALIZADO' && <CheckCircle className="h-3 w-3 mr-1" />}
                        {prestamo.estado}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatCurrency(prestamo.saldoPendiente)}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="mr-1">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" className="mr-1">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={11} className="text-center text-gray-500">
                    No se encontraron préstamos.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </motion.div>
  )
}
