import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { getErrorMessage, getErrorDetail } from '../types/errors'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { formatCurrency, formatDate } from '../utils'
import { reporteService } from '../services/reporteService'
import { TablaAmortizacionCompleta } from '../components/reportes/TablaAmortizacionCompleta'
import { toast } from 'sonner'

// Mock data para reportes
const mockReportes = [
  {
    id: 'REP001',
    nombre: 'Reporte de Cartera por Asesor',
    tipo: 'CARTERA',
    descripcion: 'AnÃ¡lisis detallado de la cartera asignada a cada analista',
    fechaGeneracion: '2024-07-20',
    periodo: 'Julio 2024',
    formato: 'PDF',
    tamaÃ±o: '2.4 MB',
    descargas: 15,
    estado: 'DISPONIBLE',
    generadoPor: 'itmaster@rapicreditca.com',
  },
  {
    id: 'REP002',
    nombre: 'AnÃ¡lisis de Morosidad',
    tipo: 'MOROSIDAD',
    descripcion: 'Reporte de clientes en mora por perÃ­odo y analista',
    fechaGeneracion: '2024-07-19',
    periodo: 'Julio 2024',
    formato: 'Excel',
    tamaÃ±o: '1.8 MB',
    descargas: 8,
    estado: 'DISPONIBLE',
    generadoPor: 'itmaster@rapicreditca.com',
  },
  {
    id: 'REP003',
    nombre: 'Flujo de Caja Mensual',
    tipo: 'FINANCIERO',
    descripcion: 'ProyecciÃ³n de ingresos y egresos para el prÃ³ximo mes',
    fechaGeneracion: '2024-07-18',
    periodo: 'Agosto 2024',
    formato: 'PDF',
    tamaÃ±o: '3.1 MB',
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
    tamaÃ±o: '850 KB',
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

// ValidaciÃ³n de cÃ©dula venezolana
const validarCedula = (cedula: string): boolean => {
  if (!cedula || cedula.trim().length === 0) return false
  // Formato: V/E/J/P/G seguido de 6-12 dÃ­gitos
  return /^[VEJPG]\d{6,12}$/i.test(cedula.trim())
}

export function Reportes() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterTipo, setFilterTipo] = useState('Todos')
  const [filterEstado, setFilterEstado] = useState('Todos')
  const [selectedPeriodo, setSelectedPeriodo] = useState('mes')
  const [generandoReporte, setGenerandoReporte] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Obtener resumen del dashboard para KPIs
  const {
    data: resumenData,
    isLoading: loadingResumen,
    isError: errorResumen,
    refetch: refetchResumen
  } = useQuery({
    queryKey: ['reportes-resumen'],
    queryFn: () => reporteService.getResumenDashboard(),
    staleTime: 2 * 60 * 1000, // 2 minutos - datos mÃ¡s frescos
    retry: 2, // Dos reintentos para asegurar conexiÃ³n
    refetchOnWindowFocus: true, // Recargar cuando la ventana recupera el foco
    refetchInterval: 5 * 60 * 1000, // Refrescar cada 5 minutos automÃ¡ticamente
  })

  // Funciones para generar reportes
  const generarReporte = async (tipo: string, formato: 'excel' | 'pdf' = 'excel') => {
    try {
      setGenerandoReporte(tipo)
      toast.loading(`Generando reporte de ${tipo}...`)

      const fechaCorte = new Date().toISOString().split('T')[0]

      if (tipo === 'CARTERA') {
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
        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        queryClient.invalidateQueries({ queryKey: ['kpis'] })
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
        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        queryClient.invalidateQueries({ queryKey: ['kpis'] })
      } else if (tipo === 'MOROSIDAD') {
        const reporte = await reporteService.getReporteMorosidad(fechaCorte)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} obtenido exitosamente`)
        console.log('Reporte de morosidad:', reporte)
      } else if (tipo === 'FINANCIERO') {
        const reporte = await reporteService.getReporteFinanciero(fechaCorte)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} obtenido exitosamente`)
        console.log('Reporte financiero:', reporte)
      } else if (tipo === 'ASESORES') {
        const reporte = await reporteService.getReporteAsesores(fechaCorte)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} obtenido exitosamente`)
        console.log('Reporte de asesores:', reporte)
      } else if (tipo === 'PRODUCTOS') {
        const reporte = await reporteService.getReporteProductos(fechaCorte)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} obtenido exitosamente`)
        console.log('Reporte de productos:', reporte)
      } else {
        toast.dismiss()
        toast.info(`GeneraciÃ³n de reporte ${tipo} prÃ³ximamente disponible`)
      }
    } catch (error: unknown) {
      console.error('Error generando reporte:', error)
      toast.dismiss()
      const errorMessage = getErrorMessage(error)
      const detail = getErrorDetail(error)
      
      // Mensajes de error mÃ¡s amigables
      let mensajeError = detail || errorMessage
      if (errorMessage?.includes('500') || errorMessage?.includes('Error del servidor')) {
        mensajeError = 'Error del servidor. Por favor, intente nuevamente en unos momentos.'
      } else if (errorMessage?.includes('404') || errorMessage?.includes('No se encontraron')) {
        mensajeError = 'No se encontraron datos para los filtros seleccionados.'
      } else if (errorMessage?.includes('timeout') || errorMessage?.includes('Timeout')) {
        mensajeError = 'La operaciÃ³n estÃ¡ tomando demasiado tiempo. Por favor, intente con un rango de fechas mÃ¡s corto.'
      } else if (!mensajeError) {
        mensajeError = `Error al generar reporte de ${tipo}. Por favor, contacte al soporte si el problema persiste.`
      }
      
      toast.error(mensajeError)
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

  // KPIs desde el backend - asegurar que sean nÃºmeros (validaciÃ³n robusta)
  const kpiCartera = Number(resumenData?.cartera_activa ?? 0) || 0
  const kpiPrestamosMora = Number(resumenData?.prestamos_mora ?? 0) || 0
  const kpiTotalPrestamos = Number(resumenData?.total_prestamos ?? 0) || 0
  const kpiPagosMes = Number(resumenData?.pagos_mes ?? 0) || 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
          <p className="text-gray-600">Genera y descarga reportes detallados del sistema.</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            refetchResumen()
            toast.info('Actualizando datos...')
          }}
          disabled={loadingResumen}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${loadingResumen ? 'animate-spin' : ''}`} />
          Actualizar KPIs
        </Button>
      </div>

      {/* Mensaje de error si hay problema cargando datos */}
      {errorResumen && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-md">
          <p className="font-semibold">Error al cargar datos de KPIs</p>
          <p className="text-sm mt-1">
            No se pudieron obtener los datos del servidor. Por favor, intenta actualizar manualmente.
          </p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cartera Activa</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold">{formatCurrency(kpiCartera)}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">Total en cartera</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">PrÃ©stamos en Mora</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold text-red-600">{kpiPrestamosMora.toLocaleString()}</div>
            )}
            <p className="text-xs text-muted-foreground">Requieren atenciÃ³n</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total PrÃ©stamos</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold">{kpiTotalPrestamos.toLocaleString()}</div>
            )}
            <p className="text-xs text-muted-foreground">PrÃ©stamos activos</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pagos del Mes</CardTitle>
            <Download className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold text-green-600">
                {formatCurrency(kpiPagosMes)}
              </div>
            )}
            <p className="text-xs text-muted-foreground">Este mes</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabla de AmortizaciÃ³n Completa */}
      <TablaAmortizacionCompleta />

      {/* Generate Report Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <RefreshCw className="mr-2 h-5 w-5" /> Generar Nuevo Reporte
          </CardTitle>
          <CardDescription>Selecciona el tipo de reporte y configuraciÃ³n para generar.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tiposReporte.map((tipo) => {
              const IconComponent = tipo.icon
              const isGenerando = generandoReporte === tipo.value
              const isDisponible = ['CARTERA', 'PAGOS', 'MOROSIDAD', 'FINANCIERO', 'ASESORES', 'PRODUCTOS'].includes(tipo.value)

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
                      toast.info(`El reporte de ${tipo.label} estarÃ¡ disponible prÃ³ximamente`)
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
                  <SelectItem value="aÃ±o">Este aÃ±o</SelectItem>
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
              placeholder="Buscar por nombre, descripciÃ³n o ID..."
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
                <TableHead>DescripciÃ³n</TableHead>
                <TableHead>PerÃ­odo</TableHead>
                <TableHead>Formato</TableHead>
                <TableHead>TamaÃ±o</TableHead>
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
                    <TableCell>{reporte.tamaÃ±o}</TableCell>
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
                                toast.info('La descarga de este reporte estarÃ¡ disponible prÃ³ximamente')
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
