import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  Bell, 
  Search, 
  Filter, 
  AlertTriangle,
  Calendar,
  User,
  Mail,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Settings,
  Shield,
  Download,
  Eye
} from 'lucide-react'
// XLSX se importa dinámicamente cuando se necesita
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useQuery } from '@tanstack/react-query'
import { notificacionService, type Notificacion, type NotificacionStats } from '@/services/notificacionService'
import { toast } from 'sonner'
import { ConfiguracionNotificaciones } from '@/components/notificaciones/ConfiguracionNotificaciones'

type TabType = 'previa' | 'retrasado' | 'prejudicial' | 'configuracion'

export function Notificaciones() {
  const [activeTab, setActiveTab] = useState<TabType>('previa')
  const [searchTerm, setSearchTerm] = useState('')
  const [filterEstado, setFilterEstado] = useState<string>('')
  const [filterCanal, setFilterCanal] = useState<string>('')
  const [page, setPage] = useState(1)
  const perPage = 20

  // Cargar notificaciones previas si estamos en la pestaña "previa"
  const { data: notificacionesPreviasData, isLoading: isLoadingPrevias, error: errorPrevias, refetch: refetchPrevias } = useQuery({
    queryKey: ['notificaciones-previas', filterEstado],
    queryFn: () => notificacionService.listarNotificacionesPrevias(filterEstado || undefined),
    enabled: activeTab === 'previa', // Solo cargar cuando esté en la pestaña previa
    staleTime: 30 * 1000, // Cache de 30 segundos
    refetchInterval: 2 * 60 * 1000, // Refrescar cada 2 minutos
    refetchOnWindowFocus: true, // Refrescar al enfocar ventana
    retry: 2, // Reintentar 2 veces en caso de error
    retryDelay: 1000, // Esperar 1 segundo entre reintentos
  })

  // Cargar notificaciones normales para otras pestañas
  const { data: notificacionesData, isLoading, error, refetch } = useQuery({
    queryKey: ['notificaciones', filterEstado, page, perPage],
    queryFn: () => notificacionService.listarNotificaciones(page, perPage, filterEstado || undefined),
    enabled: activeTab !== 'previa', // Solo cargar cuando NO esté en la pestaña previa
    staleTime: 30 * 1000, // Cache de 30 segundos
    refetchInterval: 2 * 60 * 1000, // Refrescar cada 2 minutos (reducido de 30s)
    refetchOnWindowFocus: true, // Refrescar al enfocar ventana
  })

  const notificaciones = notificacionesData?.items || []
  const total = notificacionesData?.total || 0
  const totalPages = notificacionesData?.total_pages || 0
  
  // Datos de notificaciones previas
  const notificacionesPrevias = notificacionesPreviasData?.items || []
  const totalPrevias = notificacionesPreviasData?.total || 0

  // Cargar estadísticas
  const { data: estadisticas } = useQuery({
    queryKey: ['notificaciones-estadisticas'],
    queryFn: () => notificacionService.obtenerEstadisticas(),
    staleTime: 30 * 1000, // Cache de 30 segundos
    refetchInterval: 2 * 60 * 1000, // Refrescar cada 2 minutos (reducido de 30s)
    refetchOnWindowFocus: true, // Refrescar al enfocar ventana
  })

  // Tipos de notificación por pestaña
  const tiposPorPestaña: Record<TabType, string[]> = {
    previa: ['PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES', 'PAGO_DIA_0'],
    retrasado: ['PAGO_1_DIA_ATRASADO', 'PAGO_3_DIAS_ATRASADO', 'PAGO_5_DIAS_ATRASADO'],
    prejudicial: ['PREJUDICIAL', 'PREJUDICIAL_1', 'PREJUDICIAL_2'], // Tipos para notificaciones prejudiciales
    configuracion: [] // No se muestran notificaciones en esta pestaña
  }

  // Filtrar notificaciones localmente por pestaña, búsqueda y canal
  const filteredNotificaciones = notificaciones.filter(notif => {
    // Filtrar por pestaña activa (excepto configuración)
    if (activeTab !== 'configuracion') {
      const tiposPermitidos = tiposPorPestaña[activeTab]
      if (!tiposPermitidos.includes(notif.tipo)) {
        return false
      }
    } else {
      // En configuración no mostramos notificaciones
      return false
    }

    const matchesSearch = 
      (notif.asunto || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (notif.mensaje || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      notif.tipo.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCanal = !filterCanal || notif.canal === filterCanal
    return matchesSearch && matchesCanal
  })

  const getEstadoBadge = (estado: string) => {
    switch (estado) {
      case 'ENVIADA':
        return <Badge className="bg-green-100 text-green-800 flex items-center gap-1">
          <CheckCircle className="w-3 h-3" />
          Enviada
        </Badge>
      case 'FALLIDA':
        return <Badge className="bg-red-100 text-red-800 flex items-center gap-1">
          <XCircle className="w-3 h-3" />
          Fallida
        </Badge>
      case 'PENDIENTE':
        return <Badge className="bg-yellow-100 text-yellow-800 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          Pendiente
        </Badge>
      case 'CANCELADA':
        return <Badge className="bg-gray-100 text-gray-800">Cancelada</Badge>
      default:
        return <Badge variant="secondary">{estado}</Badge>
    }
  }

  const getCanalBadge = (canal: string) => {
    switch (canal) {
      case 'EMAIL':
        return <Badge className="bg-blue-100 text-blue-800 flex items-center gap-1">
          <Mail className="w-3 h-3" />
          Email
        </Badge>
      case 'WHATSAPP':
        return <Badge className="bg-green-100 text-green-800">WhatsApp</Badge>
      case 'SMS':
        return <Badge className="bg-purple-100 text-purple-800">SMS</Badge>
      default:
        return <Badge variant="secondary">{canal}</Badge>
    }
  }

  const getTipoBadge = (tipo: string) => {
    const tipos: Record<string, { label: string; color: string }> = {
      'PAGO_5_DIAS_ANTES': { label: 'Recordatorio 5 días', color: 'bg-blue-100 text-blue-800' },
      'PAGO_3_DIAS_ANTES': { label: 'Recordatorio 3 días', color: 'bg-cyan-100 text-cyan-800' },
      'PAGO_1_DIA_ANTES': { label: 'Recordatorio 1 día', color: 'bg-yellow-100 text-yellow-800' },
      'PAGO_DIA_0': { label: 'Vencimiento hoy', color: 'bg-orange-100 text-orange-800' },
      'PAGO_1_DIA_ATRASADO': { label: '1 día atrasado', color: 'bg-red-100 text-red-800' },
      'PAGO_3_DIAS_ATRASADO': { label: '3 días atrasado', color: 'bg-red-100 text-red-800' },
      'PAGO_5_DIAS_ATRASADO': { label: '5 días atrasado', color: 'bg-red-100 text-red-800' },
      'PREJUDICIAL': { label: 'Prejudicial', color: 'bg-purple-100 text-purple-800' },
      'PREJUDICIAL_1': { label: 'Prejudicial - Primera', color: 'bg-purple-100 text-purple-800' },
      'PREJUDICIAL_2': { label: 'Prejudicial - Segunda', color: 'bg-purple-100 text-purple-800' },
    }
    const tipoInfo = tipos[tipo] || { label: tipo, color: 'bg-gray-100 text-gray-800' }
    return <Badge className={tipoInfo.color}>{tipoInfo.label}</Badge>
  }

  const handleRefresh = () => {
    if (activeTab === 'previa') {
      refetchPrevias()
    } else {
      refetch()
    }
    toast.success('Notificaciones actualizadas')
  }

  const handleLimpiarFiltros = () => {
    setSearchTerm('')
    setFilterEstado('')
    setFilterCanal('')
    setPage(1)
  }

  const descargarExcel = async (estado: 'PENDIENTE' | 'FALLIDA') => {
    try {
      // Obtener las notificaciones según el estado
      const notificacionesFiltradas = activeTab === 'previa'
        ? notificacionesPrevias.filter(n => n.estado === estado)
        : filteredNotificaciones.filter(n => n.estado === estado)

      if (notificacionesFiltradas.length === 0) {
        toast.warning(`No hay notificaciones ${estado === 'PENDIENTE' ? 'pendientes' : 'fallidas'} para descargar`)
        return
      }

      // Importar XLSX dinámicamente
      const { importXLSX } = await import('@/types/xlsx')
      const XLSX = await importXLSX()

      // Preparar los datos para Excel
      const datosExcel = notificacionesFiltradas.map(notif => {
        if (activeTab === 'previa') {
          // Para notificaciones previas
          return {
            'Nombre': notif.nombre || '',
            'Cédula': notif.cedula || '',
            'Modelo de Vehículo': notif.modelo_vehiculo || '',
            'Correo': notif.correo || '',
            'Teléfono': notif.telefono || '',
            'Días antes de vencimiento': notif.dias_antes_vencimiento || '',
            'Fecha vencimiento': notif.fecha_vencimiento 
              ? new Date(notif.fecha_vencimiento).toLocaleDateString('es-ES')
              : '',
            'Cuota #': notif.numero_cuota || '',
            'Monto': notif.monto_cuota ? `$${notif.monto_cuota.toFixed(2)}` : '',
            'Préstamo ID': notif.prestamo_id || '',
            'Estado': notif.estado || ''
          }
        } else {
          // Para notificaciones normales
          return {
            'Asunto': notif.asunto || '',
            'Mensaje': notif.mensaje || '',
            'Tipo': notif.tipo || '',
            'Canal': notif.canal || '',
            'Estado': notif.estado || '',
            'Cliente ID': notif.cliente_id || '',
            'Fecha Creación': notif.fecha_creacion 
              ? new Date(notif.fecha_creacion).toLocaleString('es-ES')
              : '',
            'Fecha Envío': notif.fecha_envio 
              ? new Date(notif.fecha_envio).toLocaleString('es-ES')
              : '',
            'Error': notif.error_mensaje || ''
          }
        }
      })

      // Crear el workbook y worksheet
      const wb = XLSX.utils.book_new()
      const ws = XLSX.utils.json_to_sheet(datosExcel) as any

      // Ajustar el ancho de las columnas
      const colWidths = activeTab === 'previa'
        ? [
            { wch: 30 }, // Nombre
            { wch: 15 }, // Cédula
            { wch: 20 }, // Modelo
            { wch: 30 }, // Correo
            { wch: 15 }, // Teléfono
            { wch: 10 }, // Días
            { wch: 15 }, // Fecha vencimiento
            { wch: 8 },  // Cuota #
            { wch: 12 }, // Monto
            { wch: 12 }, // Préstamo ID
            { wch: 12 }  // Estado
          ]
        : [
            { wch: 30 }, // Asunto
            { wch: 50 }, // Mensaje
            { wch: 20 }, // Tipo
            { wch: 12 }, // Canal
            { wch: 12 }, // Estado
            { wch: 12 }, // Cliente ID
            { wch: 20 }, // Fecha Creación
            { wch: 20 }, // Fecha Envío
            { wch: 50 }  // Error
          ]
      ws['!cols'] = colWidths

      // Agregar el worksheet al workbook
      XLSX.utils.book_append_sheet(wb, ws, estado === 'PENDIENTE' ? 'Pendientes' : 'Fallidas')

      // Generar el nombre del archivo
      const fecha = new Date().toISOString().split('T')[0]
      const nombreArchivo = `Notificaciones_${estado === 'PENDIENTE' ? 'Pendientes' : 'Fallidas'}_${fecha}.xlsx`

      // Descargar el archivo
      XLSX.writeFile(wb, nombreArchivo)
      
      toast.success(`Archivo Excel descargado: ${nombreArchivo}`)
    } catch (error) {
      console.error('Error al descargar Excel:', error)
      toast.error('Error al generar el archivo Excel')
    }
  }

  const tabs = [
    { id: 'previa' as TabType, label: 'Notificación Previa', icon: Bell },
    { id: 'retrasado' as TabType, label: 'Notificación Pago Retrasado', icon: AlertTriangle },
    { id: 'prejudicial' as TabType, label: 'Notificación Prejudicial', icon: Shield },
    { id: 'configuracion' as TabType, label: 'Configuración', icon: Settings },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Notificaciones</h1>
            <p className="text-gray-600 mt-1">Gestiona y configura las notificaciones del sistema</p>
          </div>
          {activeTab !== 'configuracion' && (
            <div className="flex space-x-2">
              <Button variant="outline" onClick={handleRefresh} disabled={activeTab === 'previa' ? isLoadingPrevias : isLoading}>
                <RefreshCw className={`w-4 h-4 mr-2 ${(activeTab === 'previa' ? isLoadingPrevias : isLoading) ? 'animate-spin' : ''}`} />
                Actualizar
              </Button>
            </div>
          )}
        </div>
      </motion.div>

      {/* Filters - Movido antes de las pestañas */}
      {activeTab !== 'configuracion' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Filter className="w-5 h-5 mr-2" />
                Filtros y Búsqueda
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`grid grid-cols-1 gap-4 ${activeTab === 'previa' ? 'md:grid-cols-2' : 'md:grid-cols-4'}`}>
                {activeTab !== 'previa' && (
                  <div className="relative">
                    <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      placeholder="Buscar por asunto, mensaje o tipo..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                )}
                <select
                  value={filterEstado}
                  onChange={(e) => {
                    setFilterEstado(e.target.value)
                    setPage(1)
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Todos los estados</option>
                  <option value="ENVIADA">Enviadas</option>
                  <option value="PENDIENTE">Pendientes</option>
                  <option value="FALLIDA">Fallidas</option>
                </select>
                {activeTab !== 'previa' && (
                  <select
                    value={filterCanal}
                    onChange={(e) => setFilterCanal(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Todos los canales</option>
                    <option value="EMAIL">Email</option>
                    <option value="WHATSAPP">WhatsApp</option>
                  </select>
                )}
                <Button variant="outline" onClick={handleLimpiarFiltros} className="flex items-center">
                  <Filter className="w-4 h-4 mr-2" />
                  Limpiar Filtros
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Tabs - Movido después de los filtros */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id)
                    setPage(1)
                    setSearchTerm('')
                    setFilterEstado('')
                    setFilterCanal('')
                  }}
                  className={`
                    flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  {tab.label}
                </button>
              )
            })}
          </nav>
        </div>
      </motion.div>

      {/* Contenido según pestaña activa */}
      {activeTab === 'configuracion' ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <ConfiguracionNotificaciones />
        </motion.div>
      ) : (
        <>
          {/* Stats Cards */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="grid grid-cols-1 md:grid-cols-4 gap-6"
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total</CardTitle>
                <Bell className="h-4 w-4 text-gray-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-600">
                  {activeTab === 'previa' ? totalPrevias : filteredNotificaciones.length}
                </div>
                <p className="text-xs text-gray-600">Notificaciones en esta pestaña</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Enviadas</CardTitle>
                <CheckCircle className="h-4 w-4 text-green-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {activeTab === 'previa' 
                    ? notificacionesPrevias.filter(n => n.estado === 'ENVIADA').length
                    : filteredNotificaciones.filter(n => n.estado === 'ENVIADA').length}
                </div>
                <p className="text-xs text-gray-600">Envíos exitosos</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pendientes</CardTitle>
                <Clock className="h-4 w-4 text-yellow-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">
                  {activeTab === 'previa'
                    ? notificacionesPrevias.filter(n => n.estado === 'PENDIENTE').length
                    : filteredNotificaciones.filter(n => n.estado === 'PENDIENTE').length}
                </div>
                <p className="text-xs text-gray-600 mb-2">En espera de envío</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => descargarExcel('PENDIENTE')}
                >
                  <Download className="w-3 h-3 mr-1" />
                  Descargar Excel
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Fallidas</CardTitle>
                <XCircle className="h-4 w-4 text-red-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">
                  {activeTab === 'previa'
                    ? notificacionesPrevias.filter(n => n.estado === 'FALLIDA').length
                    : filteredNotificaciones.filter(n => n.estado === 'FALLIDA').length}
                </div>
                <p className="text-xs text-gray-600 mb-2">Requieren revisión</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => descargarExcel('FALLIDA')}
                >
                  <Download className="w-3 h-3 mr-1" />
                  Descargar Excel
                </Button>
              </CardContent>
            </Card>
      </motion.div>

      {/* Notificaciones List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Notificaciones en Proceso</CardTitle>
            <CardDescription>
              Registro completo de todas las notificaciones enviadas desde el sistema
            </CardDescription>
          </CardHeader>
          <CardContent>
            {(activeTab === 'previa' ? isLoadingPrevias : isLoading) ? (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 mx-auto mb-4 text-gray-400 animate-spin" />
                <p className="text-gray-500">Cargando notificaciones...</p>
              </div>
            ) : (activeTab === 'previa' ? errorPrevias : error) ? (
              <div className="text-center py-8 text-red-500">
                <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
                <p>Error al cargar notificaciones</p>
                <Button variant="outline" onClick={() => activeTab === 'previa' ? refetchPrevias() : refetch()} className="mt-4">
                  Reintentar
                </Button>
              </div>
            ) : (
              <>
                {(activeTab === 'previa' ? notificacionesPrevias.length === 0 : filteredNotificaciones.length === 0) ? (
                  <div className="text-center py-12 text-gray-500">
                    <Bell className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg font-medium">No se encontraron notificaciones</p>
                    {activeTab !== 'previa' && notificaciones.length > 0 && (
                      <p className="text-sm text-gray-400 mt-2">
                        Intenta ajustar los filtros para ver más resultados
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-gray-50">
                          {activeTab === 'previa' ? (
                            <>
                              <TableHead>Cliente</TableHead>
                              <TableHead>Cédula</TableHead>
                              <TableHead>Modelo</TableHead>
                              <TableHead>Correo</TableHead>
                              <TableHead>Teléfono</TableHead>
                              <TableHead className="text-center">Días antes</TableHead>
                              <TableHead>Fecha Vencimiento</TableHead>
                              <TableHead className="text-center">Cuota #</TableHead>
                              <TableHead className="text-center">Monto</TableHead>
                              <TableHead>Estado</TableHead>
                            </>
                          ) : (
                            <>
                              <TableHead>Asunto</TableHead>
                              <TableHead>Mensaje</TableHead>
                              <TableHead>Tipo</TableHead>
                              <TableHead>Canal</TableHead>
                              <TableHead>Estado</TableHead>
                              <TableHead>Fecha</TableHead>
                              <TableHead className="text-right">Acciones</TableHead>
                            </>
                          )}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(activeTab === 'previa' ? notificacionesPrevias : filteredNotificaciones).map((notificacion) => (
                          <TableRow 
                            key={activeTab === 'previa' ? `${notificacion.prestamo_id}-${notificacion.dias_antes_vencimiento}` : notificacion.id}
                            className="hover:bg-gray-50"
                          >
                            {activeTab === 'previa' ? (
                              <>
                                <TableCell>
                                  <div className="font-medium text-gray-900">
                                    {notificacion.nombre || 'N/A'}
                                  </div>
                                </TableCell>
                                <TableCell className="text-gray-600">
                                  {notificacion.cedula || 'N/A'}
                                </TableCell>
                                <TableCell className="text-gray-600">
                                  {notificacion.modelo_vehiculo || 'N/A'}
                                </TableCell>
                                <TableCell className="text-gray-600">
                                  {notificacion.correo || 'N/A'}
                                </TableCell>
                                <TableCell className="text-gray-600">
                                  {notificacion.telefono || 'N/A'}
                                </TableCell>
                                <TableCell className="text-center">
                                  <Badge className="bg-blue-100 text-blue-800 border-blue-300">
                                    {notificacion.dias_antes_vencimiento} días
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center text-gray-600">
                                    <Calendar className="w-4 h-4 mr-1 text-gray-400" />
                                    {notificacion.fecha_vencimiento 
                                      ? new Date(notificacion.fecha_vencimiento).toLocaleDateString('es-ES')
                                      : 'N/A'}
                                  </div>
                                </TableCell>
                                <TableCell className="text-center text-gray-600">
                                  {notificacion.numero_cuota || 'N/A'}
                                </TableCell>
                                <TableCell className="text-center">
                                  <span className="text-green-600 font-semibold">
                                    ${notificacion.monto_cuota ? notificacion.monto_cuota.toFixed(2) : '0.00'}
                                  </span>
                                </TableCell>
                                <TableCell>
                                  {getEstadoBadge(notificacion.estado)}
                                </TableCell>
                              </>
                            ) : (
                              <>
                                <TableCell>
                                  <div className="font-medium text-gray-900">
                                    {notificacion.asunto || 'Sin asunto'}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <p className="text-gray-600 text-sm line-clamp-2 max-w-md">
                                    {notificacion.mensaje || 'Sin mensaje'}
                                  </p>
                                </TableCell>
                                <TableCell>
                                  {getTipoBadge(notificacion.tipo)}
                                </TableCell>
                                <TableCell>
                                  {getCanalBadge(notificacion.canal || 'EMAIL')}
                                </TableCell>
                                <TableCell>
                                  {getEstadoBadge(notificacion.estado)}
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center text-gray-600">
                                    <Calendar className="w-4 h-4 mr-1 text-gray-400" />
                                    {notificacion.fecha_creacion || notificacion.created_at
                                      ? new Date(notificacion.fecha_creacion || notificacion.created_at || Date.now()).toLocaleDateString('es-ES')
                                      : 'N/A'}
                                  </div>
                                </TableCell>
                                <TableCell className="text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      className="h-8 w-8"
                                      onClick={() => {
                                        // Acción de ver detalles
                                      }}
                                    >
                                      <Eye className="h-4 w-4 text-gray-600" />
                                    </Button>
                                    {notificacion.estado === 'FALLIDA' && (
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8"
                                        onClick={() => {
                                          // Acción de reintentar
                                        }}
                                      >
                                        <RefreshCw className="h-4 w-4 text-red-600" />
                                      </Button>
                                    )}
                                  </div>
                                </TableCell>
                              </>
                            )}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}

                {/* Paginación */}
                {activeTab !== 'previa' && totalPages > 1 && (
                  <div className="flex justify-center items-center space-x-2 pt-4">
                    <Button 
                      variant="outline" 
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                    >
                      Anterior
                    </Button>
                    <span className="text-sm text-gray-600">
                      Página {page} de {totalPages} ({total} total)
                    </span>
                    <Button 
                      variant="outline" 
                      onClick={() => setPage(Math.min(totalPages, page + 1))}
                      disabled={page >= totalPages}
                    >
                      Siguiente
                    </Button>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </motion.div>
        </>
      )}
    </div>
  )
}
