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
  Eye,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
// ExcelJS se importa dinámicamente cuando se necesita
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useQuery } from '@tanstack/react-query'
import { notificacionService, type Notificacion, type NotificacionStats } from '@/services/notificacionService'
import { toast } from 'sonner'
import { ConfiguracionNotificaciones } from '@/components/notificaciones/ConfiguracionNotificaciones'

type TabType = 'previa' | 'dia-pago' | 'retrasado' | 'prejudicial' | 'configuracion'

export function Notificaciones() {
  const [activeTab, setActiveTab] = useState<TabType>('previa')
  const [searchTerm, setSearchTerm] = useState('')
  const [filterEstado, setFilterEstado] = useState<string>('')
  const [filterCanal, setFilterCanal] = useState<string>('')
  const [page, setPage] = useState(1)
  const perPage = 20
  
  // Estado para controlar qué grupos de días están expandidos
  const [gruposExpandidos, setGruposExpandidos] = useState<Record<string, boolean>>({
    '5': false,  // Por defecto, todos contraídos
    '3': false,
    '1': false
  })
  
  const toggleGrupo = (dias: string) => {
    setGruposExpandidos(prev => ({
      ...prev,
      [dias]: !prev[dias]
    }))
  }

  // Cargar notificaciones previas si estamos en la pestaña "previa"
  const { data: notificacionesPreviasData, isLoading: isLoadingPrevias, error: errorPrevias, refetch: refetchPrevias } = useQuery({
    queryKey: ['notificaciones-previas', filterEstado],
    queryFn: () => notificacionService.listarNotificacionesPrevias(filterEstado || undefined),
    enabled: activeTab === 'previa', // Solo cargar cuando esté en la pestaña previa
    staleTime: 30 * 1000, // Cache de 30 segundos
    refetchInterval: 2 * 60 * 1000, // Refrescar cada 2 minutos (optimizado de 30s)
    refetchOnWindowFocus: true, // Refrescar al enfocar ventana
    retry: 2, // Reintentar 2 veces en caso de error
    retryDelay: 1000, // Esperar 1 segundo entre reintentos
  })

  // Cargar notificaciones del día de pago si estamos en la pestaña "dia-pago"
  const { data: notificacionesDiaPagoData, isLoading: isLoadingDiaPago, error: errorDiaPago, refetch: refetchDiaPago } = useQuery({
    queryKey: ['notificaciones-dia-pago', filterEstado],
    queryFn: () => notificacionService.listarNotificacionesDiaPago(filterEstado || undefined),
    enabled: activeTab === 'dia-pago', // Solo cargar cuando esté en la pestaña dia-pago
    staleTime: 30 * 1000, // Cache de 30 segundos
    refetchInterval: 2 * 60 * 1000, // Refrescar cada 2 minutos (optimizado de 30s)
    refetchOnWindowFocus: true, // Refrescar al enfocar ventana
    retry: 2, // Reintentar 2 veces en caso de error
    retryDelay: 1000, // Esperar 1 segundo entre reintentos
  })

  // Cargar notificaciones retrasadas si estamos en la pestaña "retrasado"
  const { data: notificacionesRetrasadasData, isLoading: isLoadingRetrasadas, error: errorRetrasadas, refetch: refetchRetrasadas } = useQuery({
    queryKey: ['notificaciones-retrasadas', filterEstado],
    queryFn: () => notificacionService.listarNotificacionesRetrasadas(filterEstado || undefined),
    enabled: activeTab === 'retrasado', // Solo cargar cuando esté en la pestaña retrasado
    staleTime: 30 * 1000, // Cache de 30 segundos
    refetchInterval: 2 * 60 * 1000, // Refrescar cada 2 minutos (optimizado de 30s)
    refetchOnWindowFocus: true, // Refrescar al enfocar ventana
    retry: 2, // Reintentar 2 veces en caso de error
    retryDelay: 1000, // Esperar 1 segundo entre reintentos
  })

  // Cargar notificaciones prejudiciales si estamos en la pestaña "prejudicial"
  const { data: notificacionesPrejudicialesData, isLoading: isLoadingPrejudiciales, error: errorPrejudiciales, refetch: refetchPrejudiciales } = useQuery({
    queryKey: ['notificaciones-prejudicial', filterEstado],
    queryFn: async () => {
      try {
        const result = await notificacionService.listarNotificacionesPrejudiciales(filterEstado || undefined)
        console.log('📊 [NotificacionesPrejudicial] Datos recibidos:', result)
        return result
      } catch (error) {
        console.error('❌ [NotificacionesPrejudicial] Error en query:', error)
        throw error
      }
    },
    enabled: activeTab === 'prejudicial', // Solo cargar cuando esté en la pestaña prejudicial
    staleTime: 30 * 1000, // Cache de 30 segundos
    refetchInterval: 2 * 60 * 1000, // Refrescar cada 2 minutos (optimizado de 30s)
    refetchOnWindowFocus: true, // Refrescar al enfocar ventana
    retry: 2, // Reintentar 2 veces en caso de error
    retryDelay: 1000, // Esperar 1 segundo entre reintentos
  })

  // Cargar notificaciones normales para otras pestañas
  const { data: notificacionesData, isLoading, error, refetch } = useQuery({
    queryKey: ['notificaciones', filterEstado, page, perPage],
    queryFn: () => notificacionService.listarNotificaciones(page, perPage, filterEstado || undefined),
    enabled: activeTab !== 'previa' && activeTab !== 'dia-pago' && activeTab !== 'retrasado' && activeTab !== 'prejudicial', // Solo cargar cuando NO esté en previa, dia-pago, retrasado o prejudicial
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
  
  // Datos de notificaciones del día de pago
  const notificacionesDiaPago = notificacionesDiaPagoData?.items || []
  const totalDiaPago = notificacionesDiaPagoData?.total || 0
  
  // Datos de notificaciones retrasadas
  const notificacionesRetrasadas = notificacionesRetrasadasData?.items || []
  const totalRetrasadas = notificacionesRetrasadasData?.total || 0
  
  // Datos de notificaciones prejudiciales
  const notificacionesPrejudiciales = notificacionesPrejudicialesData?.items || []
  const totalPrejudiciales = notificacionesPrejudicialesData?.total || 0

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
    previa: ['PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES'],
    'dia-pago': ['PAGO_DIA_0'],
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
    } else if (activeTab === 'dia-pago') {
      refetchDiaPago()
    } else if (activeTab === 'retrasado') {
      refetchRetrasadas()
    } else if (activeTab === 'prejudicial') {
      refetchPrejudiciales()
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

      // Importar exceljs dinámicamente
      const { createAndDownloadExcel } = await import('@/types/exceljs')

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

      // Generar el nombre del archivo
      const fecha = new Date().toISOString().split('T')[0]
      const nombreArchivo = `Notificaciones_${estado === 'PENDIENTE' ? 'Pendientes' : 'Fallidas'}_${fecha}.xlsx`

      // Descargar el archivo usando exceljs
      await createAndDownloadExcel(
        datosExcel,
        estado === 'PENDIENTE' ? 'Pendientes' : 'Fallidas',
        nombreArchivo
      )
      
      toast.success(`Archivo Excel descargado: ${nombreArchivo}`)
    } catch (error) {
      console.error('Error al descargar Excel:', error)
      toast.error('Error al generar el archivo Excel')
    }
  }

  const tabs = [
    { id: 'previa' as TabType, label: 'Notificación Previa', icon: Bell },
    { id: 'dia-pago' as TabType, label: 'Día de Pago', icon: Calendar },
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
              <Button variant="outline" onClick={handleRefresh} disabled={
                activeTab === 'previa' ? isLoadingPrevias 
                : activeTab === 'dia-pago' ? isLoadingDiaPago
                : activeTab === 'retrasado' ? isLoadingRetrasadas
                : activeTab === 'prejudicial' ? isLoadingPrejudiciales
                : isLoading
              }>
                <RefreshCw className={`w-4 h-4 mr-2 ${
                  (activeTab === 'previa' ? isLoadingPrevias 
                  : activeTab === 'dia-pago' ? isLoadingDiaPago
                  : activeTab === 'retrasado' ? isLoadingRetrasadas
                  : activeTab === 'prejudicial' ? isLoadingPrejudiciales
                  : isLoading) ? 'animate-spin' : ''
                }`} />
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
                {(activeTab !== 'previa' && activeTab !== 'dia-pago') && (
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
                  {activeTab === 'previa' ? totalPrevias 
                    : activeTab === 'dia-pago' ? totalDiaPago
                    : activeTab === 'retrasado' ? totalRetrasadas
                    : activeTab === 'prejudicial' ? totalPrejudiciales
                    : filteredNotificaciones.length}
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
                    : activeTab === 'dia-pago'
                    ? notificacionesDiaPago.filter(n => n.estado === 'ENVIADA').length
                    : activeTab === 'retrasado'
                    ? notificacionesRetrasadas.filter(n => n.estado === 'ENVIADA').length
                    : activeTab === 'prejudicial'
                    ? notificacionesPrejudiciales.filter(n => n.estado === 'ENVIADA').length
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
                    : activeTab === 'dia-pago'
                    ? notificacionesDiaPago.filter(n => n.estado === 'PENDIENTE').length
                    : activeTab === 'retrasado'
                    ? notificacionesRetrasadas.filter(n => n.estado === 'PENDIENTE').length
                    : activeTab === 'prejudicial'
                    ? notificacionesPrejudiciales.filter(n => n.estado === 'PENDIENTE').length
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
                    : activeTab === 'dia-pago'
                    ? notificacionesDiaPago.filter(n => n.estado === 'FALLIDA').length
                    : activeTab === 'retrasado'
                    ? notificacionesRetrasadas.filter(n => n.estado === 'FALLIDA').length
                    : activeTab === 'prejudicial'
                    ? notificacionesPrejudiciales.filter(n => n.estado === 'FALLIDA').length
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
            {((activeTab === 'previa' ? isLoadingPrevias : activeTab === 'dia-pago' ? isLoadingDiaPago : activeTab === 'retrasado' ? isLoadingRetrasadas : activeTab === 'prejudicial' ? isLoadingPrejudiciales : isLoading)) ? (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 mx-auto mb-4 text-gray-400 animate-spin" />
                <p className="text-gray-500">Cargando notificaciones...</p>
              </div>
            ) : ((activeTab === 'previa' ? errorPrevias : activeTab === 'dia-pago' ? errorDiaPago : activeTab === 'retrasado' ? errorRetrasadas : activeTab === 'prejudicial' ? errorPrejudiciales : error)) ? (
              <div className="text-center py-8 text-red-500">
                <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
                <p>Error al cargar notificaciones</p>
                {activeTab === 'prejudicial' && errorPrejudiciales && (
                  <p className="text-sm text-red-400 mt-2">
                    {errorPrejudiciales instanceof Error ? errorPrejudiciales.message : 'Error desconocido'}
                  </p>
                )}
                <Button variant="outline" onClick={() => {
                  if (activeTab === 'previa') refetchPrevias()
                  else if (activeTab === 'dia-pago') refetchDiaPago()
                  else if (activeTab === 'retrasado') refetchRetrasadas()
                  else if (activeTab === 'prejudicial') refetchPrejudiciales()
                  else refetch()
                }} className="mt-4">
                  Reintentar
                </Button>
              </div>
            ) : (
              <>
                {((activeTab === 'previa' ? notificacionesPrevias.length === 0 : activeTab === 'dia-pago' ? notificacionesDiaPago.length === 0 : activeTab === 'retrasado' ? notificacionesRetrasadas.length === 0 : activeTab === 'prejudicial' ? notificacionesPrejudiciales.length === 0 : filteredNotificaciones.length === 0)) ? (
                  <div className="text-center py-12 text-gray-500">
                    <Bell className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg font-medium">No se encontraron notificaciones</p>
                    {activeTab === 'prejudicial' && (
                      <p className="text-sm text-gray-400 mt-2">
                        No hay clientes con 3 o más cuotas atrasadas en este momento.
                      </p>
                    )}
                    {(activeTab !== 'previa' && activeTab !== 'dia-pago' && activeTab !== 'retrasado' && activeTab !== 'prejudicial') && notificaciones.length > 0 && (
                      <p className="text-sm text-gray-400 mt-2">
                        Intenta ajustar los filtros para ver más resultados
                      </p>
                    )}
                  </div>
                ) : (
                  (activeTab === 'previa' || activeTab === 'retrasado') ? (
                    // Agrupar notificaciones previas o retrasadas por días
                    (() => {
                      const datos = activeTab === 'previa' ? notificacionesPrevias : notificacionesRetrasadas
                      const campoDias = activeTab === 'previa' ? 'dias_antes_vencimiento' : 'dias_atrasado'
                      
                      const grupos = {
                        '5': datos.filter(n => n[campoDias] === 5),
                        '3': datos.filter(n => n[campoDias] === 3),
                        '1': datos.filter(n => n[campoDias] === 1)
                      }
                      
                      // Orden de visualización: 5, 3, 1
                      const ordenGrupos = ['5', '3', '1']
                      const textoDias = activeTab === 'previa' ? 'días antes del vencimiento' : 'días atrasado'
                      
                      return (
                        <div className="space-y-4">
                          {ordenGrupos.map((dias) => {
                            const notificacionesGrupo = grupos[dias as keyof typeof grupos]
                            if (notificacionesGrupo.length === 0) return null
                            
                            const estaExpandido = gruposExpandidos[dias]
                            
                            return (
                              <div key={dias} className="border rounded-lg overflow-hidden bg-white shadow-sm">
                                {/* Encabezado del grupo (clickeable) */}
                                <button
                                  onClick={() => toggleGrupo(dias)}
                                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                                >
                                  <div className="flex items-center gap-3">
                                    {estaExpandido ? (
                                      <ChevronUp className="w-5 h-5 text-gray-500" />
                                    ) : (
                                      <ChevronDown className="w-5 h-5 text-gray-500" />
                                    )}
                                    <Badge className="bg-blue-100 text-blue-800 border-blue-300 text-lg px-4 py-1">
                                      {dias} {textoDias}
                                    </Badge>
                                    <span className="text-sm text-gray-500">
                                      ({notificacionesGrupo.length} {notificacionesGrupo.length === 1 ? 'notificación' : 'notificaciones'})
                                    </span>
                                  </div>
                                </button>
                                
                                {/* Tarjetas del grupo (colapsable) */}
                                {estaExpandido && (
                                  <div className="px-4 pb-4 space-y-4 border-t border-gray-100">
                                    {notificacionesGrupo.map((notificacion) => (
                                    <Card 
                                      key={`${notificacion.prestamo_id}-${notificacion[campoDias]}`}
                                      className="bg-yellow-50 border-yellow-200 hover:shadow-md transition-shadow"
                                    >
                                      <CardContent className="p-4">
                                        <div className="flex items-start justify-between">
                                          <div className="flex items-start gap-4 flex-1">
                                            {/* Icono de campana */}
                                            <div className="mt-1">
                                              <Bell className="w-5 h-5 text-blue-600" />
                                            </div>
                                            
                                            {/* Contenido principal */}
                                            <div className="flex-1 space-y-2">
                                              {/* Nombre y cédula */}
                                              <div className="font-bold text-gray-900">
                                                {notificacion.nombre || 'N/A'} - {notificacion.cedula || 'N/A'}
                                              </div>
                                              
                                              {/* Detalles */}
                                              <div className="grid grid-cols-1 md:grid-cols-2 gap-1 text-sm">
                                                <div className="text-gray-700">
                                                  <span className="font-medium">Modelo:</span> {notificacion.modelo_vehiculo || 'N/A'}
                                                </div>
                                                <div className="text-gray-700">
                                                  <span className="font-medium">Correo:</span> {notificacion.correo || 'N/A'}
                                                </div>
                                                <div className="text-gray-700">
                                                  <span className="font-medium">Teléfono:</span> {notificacion.telefono || 'N/A'}
                                                </div>
                                                <div className="text-gray-700">
                                                  <span className="font-medium">Fecha vencimiento:</span> {
                                                    notificacion.fecha_vencimiento 
                                                      ? new Date(notificacion.fecha_vencimiento).toLocaleDateString('es-ES')
                                                      : 'N/A'
                                                  }
                                                </div>
                                                <div className="text-gray-700">
                                                  <span className="font-medium">Cuota #:</span> {notificacion.numero_cuota || 'N/A'} - <span className="font-medium">Monto:</span> <span className="text-green-600 font-semibold">${notificacion.monto_cuota ? notificacion.monto_cuota.toFixed(2) : '0.00'}</span>
                                                </div>
                                                {notificacion.prestamo_id && (
                                                  <div className="text-gray-700">
                                                    <span className="font-medium">Préstamo ID:</span> {notificacion.prestamo_id}
                                                  </div>
                                                )}
                                              </div>
                                            </div>
                                          </div>
                                          
                                          {/* Badges a la derecha */}
                                          <div className="flex flex-col items-end gap-2 ml-4">
                                            {getEstadoBadge(notificacion.estado)}
                                            <Badge className="bg-blue-100 text-blue-800 border-blue-300">
                                              {notificacion[campoDias]} {activeTab === 'previa' ? 'días antes' : 'días atrasado'}
                                            </Badge>
                                          </div>
                                        </div>
                                      </CardContent>
                                    </Card>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )
                    })()
                  ) : activeTab === 'dia-pago' ? (
                    // Notificaciones del día de pago (sin agrupar, ordenadas alfabéticamente)
                    <div className="space-y-4">
                      {notificacionesDiaPago.map((notificacion) => (
                        <Card 
                          key={`${notificacion.prestamo_id}-${notificacion.numero_cuota}`}
                          className="bg-yellow-50 border-yellow-200 hover:shadow-md transition-shadow"
                        >
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-4 flex-1">
                                {/* Icono de campana */}
                                <div className="mt-1">
                                  <Bell className="w-5 h-5 text-blue-600" />
                                </div>
                                
                                {/* Contenido principal */}
                                <div className="flex-1 space-y-2">
                                  {/* Nombre y cédula */}
                                  <div className="font-bold text-gray-900">
                                    {notificacion.nombre || 'N/A'} - {notificacion.cedula || 'N/A'}
                                  </div>
                                  
                                  {/* Detalles */}
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-1 text-sm">
                                    <div className="text-gray-700">
                                      <span className="font-medium">Modelo:</span> {notificacion.modelo_vehiculo || 'N/A'}
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Correo:</span> {notificacion.correo || 'N/A'}
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Teléfono:</span> {notificacion.telefono || 'N/A'}
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Fecha vencimiento:</span> {
                                        notificacion.fecha_vencimiento 
                                          ? new Date(notificacion.fecha_vencimiento).toLocaleDateString('es-ES')
                                          : 'N/A'
                                      }
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Cuota #:</span> {notificacion.numero_cuota || 'N/A'} - <span className="font-medium">Monto:</span> <span className="text-green-600 font-semibold">${notificacion.monto_cuota ? notificacion.monto_cuota.toFixed(2) : '0.00'}</span>
                                    </div>
                                    {notificacion.prestamo_id && (
                                      <div className="text-gray-700">
                                        <span className="font-medium">Préstamo ID:</span> {notificacion.prestamo_id}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              {/* Badges a la derecha */}
                              <div className="flex flex-col items-end gap-2 ml-4">
                                {getEstadoBadge(notificacion.estado)}
                                <Badge className="bg-orange-100 text-orange-800 border-orange-300">
                                  Vence Hoy
                                </Badge>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : activeTab === 'prejudicial' ? (
                    // Notificaciones prejudiciales (sin agrupar, ordenadas por fecha más antigua)
                    <div className="space-y-4">
                      {notificacionesPrejudiciales.map((notificacion) => (
                        <Card 
                          key={`${notificacion.prestamo_id}-${notificacion.numero_cuota}`}
                          className="bg-yellow-50 border-yellow-200 hover:shadow-md transition-shadow"
                        >
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-4 flex-1">
                                {/* Icono de campana */}
                                <div className="mt-1">
                                  <Bell className="w-5 h-5 text-blue-600" />
                                </div>
                                
                                {/* Contenido principal */}
                                <div className="flex-1 space-y-2">
                                  {/* Nombre y cédula */}
                                  <div className="font-bold text-gray-900">
                                    {notificacion.nombre || 'N/A'} - {notificacion.cedula || 'N/A'}
                                  </div>
                                  
                                  {/* Detalles */}
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-1 text-sm">
                                    <div className="text-gray-700">
                                      <span className="font-medium">Modelo:</span> {notificacion.modelo_vehiculo || 'N/A'}
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Correo:</span> {notificacion.correo || 'N/A'}
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Teléfono:</span> {notificacion.telefono || 'N/A'}
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Fecha vencimiento:</span> {
                                        notificacion.fecha_vencimiento 
                                          ? new Date(notificacion.fecha_vencimiento).toLocaleDateString('es-ES')
                                          : 'N/A'
                                      }
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Cuota #:</span> {notificacion.numero_cuota || 'N/A'} - <span className="font-medium">Monto:</span> <span className="text-green-600 font-semibold">${notificacion.monto_cuota ? notificacion.monto_cuota.toFixed(2) : '0.00'}</span>
                                    </div>
                                    {notificacion.prestamo_id && (
                                      <div className="text-gray-700">
                                        <span className="font-medium">Préstamo ID:</span> {notificacion.prestamo_id}
                                      </div>
                                    )}
                                    {notificacion.total_cuotas_atrasadas && (
                                      <div className="text-gray-700">
                                        <span className="font-medium">Total cuotas atrasadas:</span> <span className="text-red-600 font-semibold">{notificacion.total_cuotas_atrasadas}</span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              {/* Badges a la derecha */}
                              <div className="flex flex-col items-end gap-2 ml-4">
                                {getEstadoBadge(notificacion.estado)}
                                <Badge className="bg-red-100 text-red-800 border-red-300">
                                  Prejudicial
                                </Badge>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    // Notificaciones normales (sin agrupar)
                    <div className="space-y-4">
                      {filteredNotificaciones.map((notificacion) => (
                        <Card 
                          key={notificacion.id}
                          className="bg-yellow-50 border-yellow-200 hover:shadow-md transition-shadow"
                        >
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-4 flex-1">
                                {/* Icono de campana */}
                                <div className="mt-1">
                                  <Bell className="w-5 h-5 text-blue-600" />
                                </div>
                                
                                {/* Contenido principal */}
                                <div className="flex-1 space-y-2">
                                  {/* Asunto */}
                                  <div className="font-bold text-gray-900">
                                    {notificacion.asunto || 'Sin asunto'}
                                  </div>
                                  
                                  {/* Mensaje */}
                                  <div className="text-gray-700 text-sm">
                                    {notificacion.mensaje || 'Sin mensaje'}
                                  </div>
                                  
                                  {/* Detalles adicionales */}
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-1 text-sm">
                                    <div className="text-gray-700">
                                      <span className="font-medium">Tipo:</span> {notificacion.tipo || 'N/A'}
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Canal:</span> {notificacion.canal || 'EMAIL'}
                                    </div>
                                    <div className="text-gray-700">
                                      <span className="font-medium">Fecha:</span> {
                                        notificacion.fecha_creacion || notificacion.created_at
                                          ? new Date(notificacion.fecha_creacion || notificacion.created_at || Date.now()).toLocaleDateString('es-ES')
                                          : 'N/A'
                                      }
                                    </div>
                                    {notificacion.cliente_id && (
                                      <div className="text-gray-700">
                                        <span className="font-medium">Cliente ID:</span> {notificacion.cliente_id}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              {/* Badges a la derecha */}
                              <div className="flex flex-col items-end gap-2 ml-4">
                                {getEstadoBadge(notificacion.estado)}
                                <div className="flex items-center gap-2 mt-2">
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
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )
                )}

                {/* Paginación */}
                {(activeTab !== 'previa' && activeTab !== 'dia-pago' && activeTab !== 'retrasado' && activeTab !== 'prejudicial') && totalPages > 1 && (
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
