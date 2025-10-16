import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  FileText,
  Download,
  Calendar,
  Filter,
  BarChart3,
  PieChart,
  TrendingUp,
  Users,
  DollarSign,
  Clock,
  Search,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatCurrency, formatDate } from '@/utils'

// Mock data para reportes
const mockReportes = [
  {
    id: 'REP001',
    nombre: 'Reporte de Cartera por Asesor',
    tipo: 'CARTERA',
    descripcion: 'Análisis detallado de la cartera asignada a cada analista',
    fechaGeneracion: '2024-07-20',
    periodo: 'Julio 2024',
    formato: 'PDF',
    tamaño: '2.4 MB',
    descargas: 15,
    estado: 'DISPONIBLE',
    generadoPor: 'itmaster@rapicreditca.com',
  },
  {
    id: 'REP002',
    nombre: 'Análisis de Morosidad',
    tipo: 'MOROSIDAD',
    descripcion: 'Reporte de clientes en mora por período y analista',
    fechaGeneracion: '2024-07-19',
    periodo: 'Julio 2024',
    formato: 'Excel',
    tamaño: '1.8 MB',
    descargas: 8,
    estado: 'DISPONIBLE',
    generadoPor: 'itmaster@rapicreditca.com',
  },
  {
    id: 'REP003',
    nombre: 'Flujo de Caja Mensual',
    tipo: 'FINANCIERO',
    descripcion: 'Proyección de ingresos y egresos para el próximo mes',
    fechaGeneracion: '2024-07-18',
    periodo: 'Agosto 2024',
    formato: 'PDF',
    tamaño: '3.1 MB',
    descargas: 12,
    estado: 'PROCESANDO',
    generadoPor: 'itmaster@rapicreditca.com',
  },
  {
    id: 'REP004',
    nombre: 'Reporte de Pagos Diarios',
    tipo: 'PAGOS',
    descripcion: 'Registro detallado de todos los pagos recibidos',
    fechaGeneracion: '2024-07-17',
    periodo: 'Julio 2024',
    formato: 'CSV',
    tamaño: '850 KB',
    descargas: 25,
    estado: 'DISPONIBLE',
    generadoPor: 'itmaster@rapicreditca.com',
  },
]

const tiposReporte = [
  { value: 'CARTERA', label: 'Cartera', icon: DollarSign },
  { value: 'MOROSIDAD', label: 'Morosidad', icon: TrendingUp },
  { value: 'PAGOS', label: 'Pagos', icon: Users },
  { value: 'FINANCIERO', label: 'Financiero', icon: BarChart3 },
  { value: 'ASESORES', label: 'Asesores', icon: Users },
  { value: 'PRODUCTOS', label: 'Productos', icon: PieChart },
]

export function Reportes() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterTipo, setFilterTipo] = useState('Todos')
  const [filterEstado, setFilterEstado] = useState('Todos')
  const [selectedPeriodo, setSelectedPeriodo] = useState('mes')

  const filteredReportes = mockReportes.filter((reporte) => {
    const matchesSearch =
      reporte.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      reporte.descripcion.toLowerCase().includes(searchTerm.toLowerCase()) ||
      reporte.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesTipo = filterTipo === 'Todos' || reporte.tipo === filterTipo
    const matchesEstado = filterEstado === 'Todos' || reporte.estado === filterEstado
    return matchesSearch && matchesTipo && matchesEstado
  })

  const totalReportes = mockReportes.length
  const reportesDisponibles = mockReportes.filter((r) => r.estado === 'DISPONIBLE').length
  const reportesProcesando = mockReportes.filter((r) => r.estado === 'PROCESANDO').length
  const totalDescargas = mockReportes.reduce((sum, r) => sum + r.descargas, 0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
      <p className="text-gray-600">Genera y descarga reportes detallados del sistema.</p>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Reportes</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalReportes}</div>
            <p className="text-xs text-muted-foreground">Reportes generados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Disponibles</CardTitle>
            <Download className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{reportesDisponibles}</div>
            <p className="text-xs text-muted-foreground">Listos para descargar</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Procesando</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{reportesProcesando}</div>
            <p className="text-xs text-muted-foreground">En generación</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Descargas</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalDescargas}</div>
            <p className="text-xs text-muted-foreground">Total descargados</p>
          </CardContent>
        </Card>
      </div>

      {/* Generate Report Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <RefreshCw className="mr-2 h-5 w-5" /> Generar Nuevo Reporte
          </CardTitle>
          <CardDescription>Selecciona el tipo de reporte y configuración para generar.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tiposReporte.map((tipo) => {
              const IconComponent = tipo.icon
              return (
                <Card key={tipo.value} className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <IconComponent className="h-8 w-8 text-blue-600" />
                      <div>
                        <h3 className="font-semibold">{tipo.label}</h3>
                        <p className="text-sm text-gray-600">Generar reporte</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Reports List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Reportes Generados
            <div className="flex space-x-2">
              <Select value={selectedPeriodo} onValueChange={setSelectedPeriodo}>
                <SelectTrigger className="w-[140px]">
                  <Calendar className="mr-2 h-4 w-4" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dia">Hoy</SelectItem>
                  <SelectItem value="semana">Esta semana</SelectItem>
                  <SelectItem value="mes">Este mes</SelectItem>
                  <SelectItem value="año">Este año</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm">
                <RefreshCw className="mr-2 h-4 w-4" /> Actualizar
              </Button>
            </div>
          </CardTitle>
          <CardDescription>Lista de todos los reportes generados en el sistema.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <Input
              placeholder="Buscar por nombre, descripción o ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
              leftIcon={<Search className="h-4 w-4 text-gray-400" />}
            />
            <Select value={filterTipo} onValueChange={setFilterTipo}>
              <SelectTrigger className="w-[160px]">
                <Filter className="mr-2 h-4 w-4 text-gray-400" />
                <SelectValue placeholder="Filtrar por tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todos los tipos</SelectItem>
                {tiposReporte.map((tipo) => (
                  <SelectItem key={tipo.value} value={tipo.value}>
                    {tipo.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterEstado} onValueChange={setFilterEstado}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Filtrar por estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todos los estados</SelectItem>
                <SelectItem value="DISPONIBLE">Disponible</SelectItem>
                <SelectItem value="PROCESANDO">Procesando</SelectItem>
                <SelectItem value="ERROR">Error</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Descripción</TableHead>
                <TableHead>Período</TableHead>
                <TableHead>Formato</TableHead>
                <TableHead>Tamaño</TableHead>
                <TableHead>Descargas</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredReportes.length > 0 ? (
                filteredReportes.map((reporte) => (
                  <TableRow key={reporte.id}>
                    <TableCell className="font-medium">{reporte.id}</TableCell>
                    <TableCell className="font-semibold">{reporte.nombre}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{reporte.tipo}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate">{reporte.descripcion}</TableCell>
                    <TableCell>{reporte.periodo}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{reporte.formato}</Badge>
                    </TableCell>
                    <TableCell>{reporte.tamaño}</TableCell>
                    <TableCell>{reporte.descargas}</TableCell>
                    <TableCell>{formatDate(reporte.fechaGeneracion)}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          reporte.estado === 'DISPONIBLE'
                            ? 'success'
                            : reporte.estado === 'PROCESANDO'
                              ? 'warning'
                              : 'destructive'
                        }
                      >
                        {reporte.estado}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {reporte.estado === 'DISPONIBLE' && (
                        <Button variant="outline" size="sm">
                          <Download className="mr-2 h-4 w-4" /> Descargar
                        </Button>
                      )}
                      {reporte.estado === 'PROCESANDO' && (
                        <Button variant="outline" size="sm" disabled>
                          <Clock className="mr-2 h-4 w-4" /> Procesando...
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={11} className="text-center text-gray-500">
                    No se encontraron reportes.
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
