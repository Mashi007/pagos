import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Clock,
  Play,
  Pause,
  Square,
  Settings,
  Calendar,
  Bell,
  Mail,
  MessageSquare,
  Users,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Plus,
  Edit,
  Trash2,
  Eye,
  FileText,
  Shield,
  Link,
  Search,
  Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDate } from '@/utils'
import { apiClient } from '@/services/api'
import toast from 'react-hot-toast'

// Tipo para las tareas programadas
interface TareaProgramada {
  id: string
  nombre: string
  descripcion: string
  tipo: string
  frecuencia: string
  hora: string
  estado: string
  ultimaEjecucion: string | null
  proximaEjecucion: string | null
  exitos: number
  fallos: number
  canales: string[]
  configuracion: Record<string, any>
}

// Mock data para programador (fallback)
const mockTareas: TareaProgramada[] = [
  {
    id: 'TASK001',
    nombre: 'Recordatorio de Vencimientos',
    descripcion: 'Enviar notificaciones a clientes con cuotas próximas a vencer',
    tipo: 'NOTIFICACION',
    frecuencia: 'DIARIO',
    hora: '08:00',
    estado: 'ACTIVO',
    ultimaEjecucion: '2024-07-20T08:00:00Z',
    proximaEjecucion: '2024-07-21T08:00:00Z',
    exitos: 45,
    fallos: 2,
    canales: ['EMAIL', 'SMS'],
    configuracion: {
      dias_anticipacion: 3,
      template: 'vencimiento_proximo'
    }
  },
  {
    id: 'TASK002',
    nombre: 'Reporte Semanal de Cartera',
    descripcion: 'Generar y enviar reporte de cartera a gerencia',
    tipo: 'REPORTE',
    frecuencia: 'SEMANAL',
    hora: '09:00',
    estado: 'ACTIVO',
    ultimaEjecucion: '2024-07-19T09:00:00Z',
    proximaEjecucion: '2024-07-26T09:00:00Z',
    exitos: 12,
    fallos: 0,
    canales: ['EMAIL'],
    configuracion: {
      destinatarios: ['gerencia@financiamiento.com'],
      formato: 'PDF'
    }
  },
  {
    id: 'TASK003',
    nombre: 'Actualización de Mora',
    descripcion: 'Actualizar estado de mora de clientes diariamente',
    tipo: 'PROCESO',
    frecuencia: 'DIARIO',
    hora: '06:00',
    estado: 'PAUSADO',
    ultimaEjecucion: '2024-07-18T06:00:00Z',
    proximaEjecucion: '2024-07-21T06:00:00Z',
    exitos: 28,
    fallos: 1,
    canales: ['SISTEMA'],
    configuracion: {
      actualizar_estados: true,
      calcular_dias_mora: true
    }
  },
  {
    id: 'TASK004',
    nombre: 'Backup de Base de Datos',
    descripcion: 'Realizar respaldo automático de la base de datos',
    tipo: 'BACKUP',
    frecuencia: 'DIARIO',
    hora: '02:00',
    estado: 'ACTIVO',
    ultimaEjecucion: '2024-07-20T02:00:00Z',
    proximaEjecucion: '2024-07-21T02:00:00Z',
    exitos: 89,
    fallos: 3,
    canales: ['SISTEMA'],
    configuracion: {
      retencion_dias: 30,
      comprimir: true
    }
  },
  {
    id: 'TASK005',
    nombre: 'Notificación de Pagos Recibidos',
    descripcion: 'Notificar a analistaes sobre pagos recibidos de sus clientes',
    tipo: 'NOTIFICACION',
    frecuencia: 'CONTINUO',
    hora: '00:00',
    estado: 'ACTIVO',
    ultimaEjecucion: '2024-07-20T15:30:00Z',
    proximaEjecucion: 'CONTINUO',
    exitos: 156,
    fallos: 5,
    canales: ['EMAIL', 'PUSH'],
    configuracion: {
      delay_minutos: 5,
      incluir_detalles: true
    }
  },
]

const tiposTarea = [
  { value: 'NOTIFICACION', label: 'Notificación', icon: Bell },
  { value: 'REPORTE', label: 'Reporte', icon: FileText },
  { value: 'PROCESO', label: 'Proceso', icon: RefreshCw },
  { value: 'BACKUP', label: 'Backup', icon: Shield },
  { value: 'INTEGRACION', label: 'Integración', icon: Link },
]

const frecuencias = [
  { value: 'CONTINUO', label: 'Continuo' },
  { value: 'DIARIO', label: 'Diario' },
  { value: 'SEMANAL', label: 'Semanal' },
  { value: 'MENSUAL', label: 'Mensual' },
  { value: 'PERSONALIZADO', label: 'Personalizado' },
]

export function Programador() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterEstado, setFilterEstado] = useState('Todos')
  const [filterTipo, setFilterTipo] = useState('Todos')
  const [selectedTarea, setSelectedTarea] = useState<string | null>(null)

  // Obtener tareas programadas del backend
  const { data: tareasData, isLoading, error, refetch } = useQuery({
    queryKey: ['tareas-programadas'],
    queryFn: async () => {
      const response = await apiClient.get<{ tareas: TareaProgramada[]; total: number; scheduler_activo: boolean }>(
        '/api/v1/scheduler/tareas'
      )
      return response
    },
    staleTime: 30 * 1000, // 30 segundos
    refetchInterval: 60 * 1000, // Refrescar cada minuto
  })

  const tareas = tareasData?.tareas || []
  const schedulerActivo = tareasData?.scheduler_activo || false

  const filteredTareas = tareas.filter((tarea) => {
    const matchesSearch =
      tarea.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tarea.descripcion.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tarea.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesEstado = filterEstado === 'Todos' || tarea.estado === filterEstado
    const matchesTipo = filterTipo === 'Todos' || tarea.tipo === filterTipo
    return matchesSearch && matchesEstado && matchesTipo
  })

  const totalTareas = tareas.length
  const activas = tareas.filter((t) => t.estado === 'ACTIVO').length
  const pausadas = tareas.filter((t) => t.estado === 'PAUSADO').length
  const exitosTotales = tareas.reduce((sum, t) => sum + t.exitos, 0)
  const fallosTotales = tareas.reduce((sum, t) => sum + t.fallos, 0)

  const handleToggleTarea = (id: string) => {
    console.log(`Toggle tarea ${id}`)
    // Lógica para pausar/reanudar tarea (futuro)
    toast('Funcionalidad de pausar/reanudar próximamente')
  }

  const handleEjecutarTarea = async (id: string) => {
    try {
      await apiClient.post('/api/v1/scheduler/ejecutar-manual')
      toast.success('Tarea ejecutada manualmente')
      refetch()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al ejecutar tarea')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Programador de Tareas</h1>
          <p className="text-gray-600">Gestiona las tareas automatizadas y programadas del sistema.</p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm" disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Cargando...
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 h-4 w-4" />
              Actualizar
            </>
          )}
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Error al cargar tareas programadas. Por favor, intente nuevamente.
        </div>
      )}

      {!schedulerActivo && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
          ⚠️ El scheduler no está activo. Las tareas programadas no se ejecutarán automáticamente.
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tareas</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalTareas}</div>
            <p className="text-xs text-muted-foreground">Tareas configuradas</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activas</CardTitle>
            <Play className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{activas}</div>
            <p className="text-xs text-muted-foreground">En ejecución</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pausadas</CardTitle>
            <Pause className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{pausadas}</div>
            <p className="text-xs text-muted-foreground">Temporalmente detenidas</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasa de Éxito</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((exitosTotales / (exitosTotales + fallosTotales)) * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">Ejecuciones exitosas</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Settings className="mr-2 h-5 w-5" /> Filtros y Búsqueda
          </CardTitle>
          <CardDescription>Filtra las tareas programadas por diferentes criterios.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Input
              placeholder="Buscar por nombre, descripción o ID..."
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
                <SelectItem value="ACTIVO">Activo</SelectItem>
                <SelectItem value="PAUSADO">Pausado</SelectItem>
                <SelectItem value="ERROR">Error</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterTipo} onValueChange={setFilterTipo}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todos los tipos</SelectItem>
                {tiposTarea.map((tipo) => (
                  <SelectItem key={tipo.value} value={tipo.value}>{tipo.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Lista de Tareas */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Tareas Programadas
            <div className="flex space-x-2">
              <Button>
                <Plus className="mr-2 h-4 w-4" /> Nueva Tarea
              </Button>
            </div>
          </CardTitle>
          <CardDescription>Lista de todas las tareas automatizadas del sistema.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Frecuencia</TableHead>
                <TableHead>Hora</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Última Ejecución</TableHead>
                <TableHead>Próxima Ejecución</TableHead>
                <TableHead>Éxitos/Fallos</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
              <TableRow>
                <TableCell colSpan={10} className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" />
                  <p className="text-gray-500 mt-2">Cargando tareas programadas...</p>
                </TableCell>
              </TableRow>
            ) : filteredTareas.length > 0 ? (
                filteredTareas.map((tarea) => (
                  <TableRow key={tarea.id}>
                    <TableCell className="font-medium">{tarea.id}</TableCell>
                    <TableCell>
                      <div>
                        <div className="font-semibold">{tarea.nombre}</div>
                        <div className="text-sm text-gray-500 max-w-[200px] truncate">
                          {tarea.descripcion}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{tarea.tipo}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{tarea.frecuencia}</Badge>
                    </TableCell>
                    <TableCell>{tarea.hora}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          tarea.estado === 'ACTIVO'
                            ? 'success'
                            : tarea.estado === 'PAUSADO'
                              ? 'warning'
                              : 'destructive'
                        }
                      >
                        {tarea.estado === 'ACTIVO' && <Play className="h-3 w-3 mr-1" />}
                        {tarea.estado === 'PAUSADO' && <Pause className="h-3 w-3 mr-1" />}
                        {tarea.estado === 'ERROR' && <XCircle className="h-3 w-3 mr-1" />}
                        {tarea.estado}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {formatDate(tarea.ultimaEjecucion)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {tarea.proximaEjecucion === 'CONTINUO' ? 'Continuo' : formatDate(tarea.proximaEjecucion)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <span className="text-green-600 text-sm">{tarea.exitos}</span>
                        <span className="text-gray-400">/</span>
                        <span className="text-red-600 text-sm">{tarea.fallos}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedTarea(tarea.id)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEjecutarTarea(tarea.id)}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleTarea(tarea.id)}
                        >
                          {tarea.estado === 'ACTIVO' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-gray-500">
                    No se encontraron tareas programadas.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detalle de Tarea */}
      {selectedTarea && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Clock className="mr-2 h-5 w-5" /> Detalle de Tarea - {selectedTarea}
            </CardTitle>
            <CardDescription>Configuración y historial de la tarea seleccionada.</CardDescription>
          </CardHeader>
          <CardContent>
            {(() => {
              const tarea = tareas.find(t => t.id === selectedTarea)
              if (!tarea) return null

              return (
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-4">
                    <h3 className="font-semibold">Información General</h3>
                    <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                      <div><strong>ID:</strong> {tarea.id}</div>
                      <div><strong>Nombre:</strong> {tarea.nombre}</div>
                      <div><strong>Descripción:</strong> {tarea.descripcion}</div>
                      <div><strong>Tipo:</strong> {tarea.tipo}</div>
                      <div><strong>Frecuencia:</strong> {tarea.frecuencia}</div>
                      <div><strong>Hora:</strong> {tarea.hora}</div>
                      <div><strong>Estado:</strong> 
                        <Badge
                          variant={
                            tarea.estado === 'ACTIVO'
                              ? 'success'
                              : tarea.estado === 'PAUSADO'
                                ? 'warning'
                                : 'destructive'
                          }
                          className="ml-2"
                        >
                          {tarea.estado}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Estadísticas</h3>
                    <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                      <div><strong>Ejecuciones Exitosas:</strong> {tarea.exitos}</div>
                      <div><strong>Ejecuciones Fallidas:</strong> {tarea.fallos}</div>
                      <div><strong>Tasa de Éxito:</strong> 
                        {((tarea.exitos / (tarea.exitos + tarea.fallos)) * 100).toFixed(1)}%
                      </div>
                      <div><strong>Última Ejecución:</strong> {formatDate(tarea.ultimaEjecucion)}</div>
                      <div><strong>Próxima Ejecución:</strong> 
                        {tarea.proximaEjecucion === 'CONTINUO' ? 'Continuo' : formatDate(tarea.proximaEjecucion)}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Canales de Comunicación</h3>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="flex flex-wrap gap-2">
                        {tarea.canales.map((canal) => (
                          <Badge key={canal} variant="outline">
                            {canal}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Configuración</h3>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                        {JSON.stringify(tarea.configuracion, null, 2)}
                      </pre>
                    </div>
                  </div>

                  <div className="md:col-span-2 flex justify-end space-x-2">
                    <Button variant="outline">
                      <Edit className="mr-2 h-4 w-4" /> Editar
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleToggleTarea(tarea.id)}
                    >
                      {tarea.estado === 'ACTIVO' ? (
                        <>
                          <Pause className="mr-2 h-4 w-4" /> Pausar
                        </>
                      ) : (
                        <>
                          <Play className="mr-2 h-4 w-4" /> Reanudar
                        </>
                      )}
                    </Button>
                    <Button
                      onClick={() => handleEjecutarTarea(tarea.id)}
                    >
                      <Play className="mr-2 h-4 w-4" /> Ejecutar Ahora
                    </Button>
                  </div>
                </div>
              )
            })()}
          </CardContent>
        </Card>
      )}
    </motion.div>
  )
}
