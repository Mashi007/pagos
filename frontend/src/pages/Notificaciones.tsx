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
  RefreshCw
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useQuery } from '@tanstack/react-query'
import { notificacionService, type Notificacion, type NotificacionStats } from '@/services/notificacionService'
import { toast } from 'sonner'

export function Notificaciones() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterEstado, setFilterEstado] = useState<string>('')
  const [filterCanal, setFilterCanal] = useState<string>('')
  const [page, setPage] = useState(1)
  const perPage = 20

  // Cargar notificaciones desde API
  const { data: notificacionesData, isLoading, error, refetch } = useQuery({
    queryKey: ['notificaciones', filterEstado, page, perPage],
    queryFn: () => notificacionService.listarNotificaciones(page, perPage, filterEstado || undefined),
    refetchInterval: 30000, // Refrescar cada 30 segundos
  })

  const notificaciones = notificacionesData?.items || []
  const total = notificacionesData?.total || 0
  const totalPages = notificacionesData?.total_pages || 0

  // Cargar estadísticas
  const { data: estadisticas } = useQuery({
    queryKey: ['notificaciones-estadisticas'],
    queryFn: () => notificacionService.obtenerEstadisticas(),
    refetchInterval: 30000,
  })

  // Filtrar notificaciones localmente por búsqueda y canal
  const filteredNotificaciones = notificaciones.filter(notif => {
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
    }
    const tipoInfo = tipos[tipo] || { label: tipo, color: 'bg-gray-100 text-gray-800' }
    return <Badge className={tipoInfo.color}>{tipoInfo.label}</Badge>
  }

  const handleRefresh = () => {
    refetch()
    toast.success('Notificaciones actualizadas')
  }

  const handleLimpiarFiltros = () => {
    setSearchTerm('')
    setFilterEstado('')
    setFilterCanal('')
    setPage(1)
  }

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
            <h1 className="text-3xl font-bold text-gray-900">Historial de Notificaciones</h1>
            <p className="text-gray-600 mt-1">Verifica el estado de todos los envíos de email y notificaciones</p>
          </div>
          <div className="flex space-x-2">
            <Button variant="outline" onClick={handleRefresh} disabled={isLoading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-6"
      >
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total</CardTitle>
            <Bell className="h-4 w-4 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">
              {estadisticas?.total || 0}
            </div>
            <p className="text-xs text-gray-600">Notificaciones en el sistema</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Enviadas</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {estadisticas?.enviadas || 0}
            </div>
            <p className="text-xs text-gray-600">
              {estadisticas?.tasa_exito ? `${estadisticas.tasa_exito.toFixed(1)}% éxito` : 'Envíos exitosos'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pendientes</CardTitle>
            <Clock className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {estadisticas?.pendientes || 0}
            </div>
            <p className="text-xs text-gray-600">En espera de envío</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fallidas</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {estadisticas?.fallidas || 0}
            </div>
            <p className="text-xs text-gray-600">Requieren revisión</p>
          </CardContent>
        </Card>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Filter className="w-5 h-5 mr-2" />
              Filtros y Búsqueda
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Buscar por asunto, mensaje o tipo..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
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
                <option value="CANCELADA">Canceladas</option>
              </select>
              <select
                value={filterCanal}
                onChange={(e) => setFilterCanal(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos los canales</option>
                <option value="EMAIL">Email</option>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="SMS">SMS</option>
              </select>
              <Button variant="outline" onClick={handleLimpiarFiltros} className="flex items-center">
                <Filter className="w-4 h-4 mr-2" />
                Limpiar Filtros
              </Button>
            </div>
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
            <CardTitle>Historial de Envíos</CardTitle>
            <CardDescription>
              Registro completo de todas las notificaciones enviadas desde el sistema
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 mx-auto mb-4 text-gray-400 animate-spin" />
                <p className="text-gray-500">Cargando notificaciones...</p>
              </div>
            ) : error ? (
              <div className="text-center py-8 text-red-500">
                <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
                <p>Error al cargar notificaciones</p>
                <Button variant="outline" onClick={() => refetch()} className="mt-4">
                  Reintentar
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredNotificaciones.map((notificacion) => (
                  <div 
                    key={notificacion.id} 
                    className={`border rounded-lg p-4 hover:bg-gray-50 transition-colors ${
                      notificacion.estado === 'FALLIDA' ? 'bg-red-50 border-red-200' :
                      notificacion.estado === 'PENDIENTE' ? 'bg-yellow-50 border-yellow-200' :
                      notificacion.estado === 'ENVIADA' ? 'bg-green-50 border-green-200' :
                      'bg-white border-gray-200'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-start space-x-3">
                          <div className="mt-1">
                            {notificacion.canal === 'EMAIL' ? (
                              <Mail className="w-5 h-5 text-blue-600" />
                            ) : (
                              <Bell className="w-5 h-5 text-gray-600" />
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-2">
                              <h3 className="font-semibold text-gray-900">
                                {notificacion.asunto || 'Sin asunto'}
                              </h3>
                            </div>
                            <p className="text-gray-600 text-sm mb-2 line-clamp-2">
                              {notificacion.mensaje}
                            </p>
                            <div className="flex items-center space-x-4 text-xs text-gray-500 flex-wrap gap-2">
                              <span className="flex items-center">
                                <Calendar className="w-3 h-3 mr-1" />
                                Creada: {new Date(notificacion.fecha_creacion || notificacion.created_at || Date.now()).toLocaleString('es-ES')}
                              </span>
                              {notificacion.fecha_envio && (
                                <span className="flex items-center">
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  Enviada: {new Date(notificacion.fecha_envio).toLocaleString('es-ES')}
                                </span>
                              )}
                              {notificacion.cliente_id && (
                                <span className="flex items-center">
                                  <User className="w-3 h-3 mr-1" />
                                  Cliente ID: {notificacion.cliente_id}
                                </span>
                              )}
                            </div>
                            {notificacion.estado === 'FALLIDA' && (
                              <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-800">
                                <strong>Error:</strong> {notificacion.error_mensaje || 'Error desconocido'}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <div className="flex flex-col space-y-2">
                          {getEstadoBadge(notificacion.estado)}
                          {getCanalBadge(notificacion.canal || 'EMAIL')}
                          {getTipoBadge(notificacion.tipo)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                
                {filteredNotificaciones.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <Bell className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>No se encontraron notificaciones con los filtros aplicados</p>
                    {notificaciones.length > 0 && (
                      <p className="text-sm mt-2">
                        Mostrando {filteredNotificaciones.length} de {notificaciones.length} notificaciones
                      </p>
                    )}
                  </div>
                )}

                {/* Paginación */}
                {totalPages > 1 && (
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
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
