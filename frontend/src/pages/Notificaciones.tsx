import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Bell, 
  Search, 
  Filter, 
  Check,
  AlertTriangle,
  Info,
  X,
  Calendar,
  User,
  CreditCard,
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
  const [skip, setSkip] = useState(0)
  const limit = 50

  // Cargar notificaciones desde API
  const { data: notificaciones = [], isLoading, error, refetch } = useQuery({
    queryKey: ['notificaciones', filterEstado, skip, limit],
    queryFn: () => notificacionService.listarNotificaciones(skip, limit, filterEstado || undefined),
    refetchInterval: 30000, // Refrescar cada 30 segundos
  })

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
    setSkip(0)
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
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
      >
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">No Leídas</CardTitle>
            <Bell className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {notificacionesNoLeidas}
            </div>
            <p className="text-xs text-gray-600">Pendientes de revisar</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Alta Prioridad</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {notificacionesAltaPrioridad}
            </div>
            <p className="text-xs text-gray-600">Requieren atención inmediata</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total</CardTitle>
            <Info className="h-4 w-4 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">
              {notificaciones.length}
            </div>
            <p className="text-xs text-gray-600">Notificaciones en el sistema</p>
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
                  placeholder="Buscar notificaciones..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <select
                value={filterTipo}
                onChange={(e) => setFilterTipo(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos los tipos</option>
                <option value="vencimiento">Vencimiento</option>
                <option value="mora">Mora</option>
                <option value="pago">Pago</option>
                <option value="sistema">Sistema</option>
              </select>
              <select
                value={filterPrioridad}
                onChange={(e) => setFilterPrioridad(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todas las prioridades</option>
                <option value="alta">Alta</option>
                <option value="media">Media</option>
                <option value="baja">Baja</option>
              </select>
              <Button variant="outline" className="flex items-center">
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
            <CardTitle>Centro de Notificaciones</CardTitle>
            <CardDescription>
              Todas las alertas y notificaciones del sistema
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {filteredNotificaciones.map((notificacion) => (
                <div 
                  key={notificacion.id} 
                  className={`border rounded-lg p-4 hover:bg-gray-50 transition-colors ${
                    !notificacion.leida ? 'bg-blue-50 border-blue-200' : ''
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-start space-x-3">
                        <div className="mt-1">
                          {getTipoIcon(notificacion.tipo)}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <h3 className={`font-semibold ${!notificacion.leida ? 'text-gray-900' : 'text-gray-700'}`}>
                              {notificacion.titulo}
                            </h3>
                            {!notificacion.leida && (
                              <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                            )}
                          </div>
                          <p className="text-gray-600 text-sm mb-2">{notificacion.mensaje}</p>
                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span>{new Date(notificacion.fecha).toLocaleString('es-ES')}</span>
                            {notificacion.cliente && (
                              <span className="flex items-center">
                                <User className="w-3 h-3 mr-1" />
                                {notificacion.cliente}
                              </span>
                            )}
                            {notificacion.monto && (
                              <span className="font-medium text-green-600">
                                ${notificacion.monto.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="flex space-x-2">
                        {getTipoBadge(notificacion.tipo)}
                        {getPrioridadBadge(notificacion.prioridad)}
                      </div>
                      <div className="flex space-x-1">
                        {!notificacion.leida && (
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => marcarComoLeida(notificacion.id)}
                          >
                            <Check className="w-3 h-3" />
                          </Button>
                        )}
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => eliminarNotificacion(notificacion.id)}
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              
              {filteredNotificaciones.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Bell className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p>No se encontraron notificaciones con los filtros aplicados</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
