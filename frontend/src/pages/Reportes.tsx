import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
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
  Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatCurrency, formatDate } from '@/utils'
import { reporteService } from '@/services/reporteService'
import { toast } from 'sonner'

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
  const [generandoReporte, setGenerandoReporte] = useState<string | null>(null)

  // Obtener resumen del dashboard para KPIs
  const { data: resumenData, isLoading: loadingResumen } = useQuery({
    queryKey: ['reportes-resumen'],
    queryFn: () => reporteService.getResumenDashboard(),
    staleTime: 5 * 60 * 1000, // 5 minutos
  })

  // Funciones para generar reportes
  const generarReporte = async (tipo: string, formato: 'excel' | 'pdf' = 'excel') => {
    try {
      setGenerandoReporte(tipo)
      toast.loading(`Generando reporte de ${tipo}...`)

      if (tipo === 'CARTERA') {
        const fechaCorte = new Date().toISOString().split('T')[0]
        const blob = await reporteService.exportarReporteCartera(formato, fechaCorte)
        
        // Crear enlace de descarga
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `reporte_cartera_${fechaCorte}.${formato === 'excel' ? 'xlsx' : 'pdf'}`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        
        toast.dismiss()
        toast.success(`Reporte de ${tipo} generado exitosamente`)
      } else if (tipo === 'PAGOS') {
        // Para pagos, necesitamos fechas de inicio y fin
        const fechaFin = new Date()
        const fechaInicio = new Date()
        fechaInicio.setMonth(fechaInicio.getMonth() - 1)
        
        const reporte = await reporteService.getReportePagos(
          fechaInicio.toISOString().split('T')[0],
          fechaFin.toISOString().split('T')[0]
        )
        
        toast.dismiss()
        toast.success(`Reporte de ${tipo} obtenido exitosamente`)
        console.log('Reporte de pagos:', reporte)
      } else {
        toast.dismiss()
        toast.info(`Generación de reporte ${tipo} próximamente disponible`)
      }
    } catch (error: any) {
      console.error('Error generando reporte:', error)
      toast.dismiss()
      toast.error(error.response?.data?.detail || `Error al generar reporte de ${tipo}`)
    } finally {
      setGenerandoReporte(null)
    }
  }

  // Filtrar reportes mock (por ahora mantenemos los datos mock para la tabla)
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

  // KPIs desde el backend
  const kpiCartera = resumenData?.cartera_activa || 0
  const kpiPrestamosMora = resumenData?.prestamos_mora || 0
  const kpiTotalPrestamos = resumenData?.total_prestamos || 0

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
            <CardTitle className="text-sm font-medium">Cartera Activa</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold">{formatCurrency(kpiCartera)}</div>
            )}
            <p className="text-xs text-muted-foreground">Total en cartera</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Préstamos en Mora</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold text-red-600">{kpiPrestamosMora}</div>
            )}
            <p className="text-xs text-muted-foreground">Requieren atención</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Préstamos</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold">{kpiTotalPrestamos}</div>
            )}
            <p className="text-xs text-muted-foreground">Préstamos activos</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pagos del Mes</CardTitle>
            <Download className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold text-green-600">
                {formatCurrency(resumenData?.pagos_mes || 0)}
              </div>
            )}
            <p className="text-xs text-muted-foreground">Este mes</p>
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
              const isGenerando = generandoReporte === tipo.value
              const isDisponible = tipo.value === 'CARTERA' || tipo.value === 'PAGOS'
              
              return (
                <Card
                  key={tipo.value}
                  className={`cursor-pointer hover:shadow-md transition-shadow ${
                    !isDisponible ? 'opacity-60' : ''
                  }`}
                  onClick={() => {
                    if (isDisponible && !isGenerando) {
                      generarReporte(tipo.value, 'excel')
                    } else if (!isDisponible) {
                      toast.info(`El reporte de ${tipo.label} estará disponible próximamente`)
                    }
                  }}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <IconComponent className="h-8 w-8 text-blue-600" />
                        <div>
                          <h3 className="font-semibold">{tipo.label}</h3>
                          <p className="text-sm text-gray-600">
                            {isGenerando ? 'Generando...' : 'Generar reporte'}
                          </p>
                        </div>
                      </div>
                      {isGenerando && (
                        <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                      )}
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
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={async () => {
                            try {
                              if (reporte.tipo === 'CARTERA') {
                                const fecha = reporte.fechaGeneracion
                                const formato = reporte.formato.toLowerCase() === 'pdf' ? 'pdf' : 'excel'
                                await generarReporte('CARTERA', formato)
                              } else {
                                toast.info('La descarga de este reporte estará disponible próximamente')
                              }
                            } catch (error) {
                              console.error('Error descargando reporte:', error)
                            }
                          }}
                        >
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
