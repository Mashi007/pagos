import { useState } from 'react'
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
  CreditCard
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

// Mock data para notificaciones
const mockNotificaciones = [
  {
    id: 1,
    tipo: 'vencimiento',
    titulo: 'Cuotas próximas a vencer',
    mensaje: '5 cuotas vencen en los próximos 3 días',
    fecha: '2024-01-15T10:30:00',
    leida: false,
    prioridad: 'alta',
    cliente: 'Juan Carlos Pérez González',
    monto: 850.00
  },
  {
    id: 2,
    tipo: 'mora',
    titulo: 'Cliente en mora',
    mensaje: 'Carlos Alberto Martínez Silva tiene 15 días de atraso',
    fecha: '2024-01-14T14:20:00',
    leida: false,
    prioridad: 'alta',
    cliente: 'Carlos Alberto Martínez Silva',
    monto: 950.00
  },
  {
    id: 3,
    tipo: 'pago',
    titulo: 'Pago confirmado',
    mensaje: 'Se confirmó el pago de $1,200 de María Elena Rodríguez',
    fecha: '2024-01-14T09:15:00',
    leida: true,
    prioridad: 'media',
    cliente: 'María Elena Rodríguez López',
    monto: 1200.00
  },
  {
    id: 4,
    tipo: 'sistema',
    titulo: 'Mantenimiento programado',
    mensaje: 'El sistema estará en mantenimiento el domingo de 2:00 AM a 4:00 AM',
    fecha: '2024-01-13T16:45:00',
    leida: true,
    prioridad: 'baja'
  }
]

export function Notificaciones() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterTipo, setFilterTipo] = useState('')
  const [filterPrioridad, setFilterPrioridad] = useState('')
  const [notificaciones, setNotificaciones] = useState(mockNotificaciones)

  const getTipoIcon = (tipo: string) => {
    switch (tipo) {
      case 'vencimiento':
        return <Calendar className="w-4 h-4 text-orange-600" />
      case 'mora':
        return <AlertTriangle className="w-4 h-4 text-red-600" />
      case 'pago':
        return <CreditCard className="w-4 h-4 text-green-600" />
      case 'sistema':
        return <Info className="w-4 h-4 text-blue-600" />
      default:
        return <Bell className="w-4 h-4 text-gray-600" />
    }
  }

  const getPrioridadBadge = (prioridad: string) => {
    switch (prioridad) {
      case 'alta':
        return <Badge className="bg-red-100 text-red-800">Alta</Badge>
      case 'media':
        return <Badge className="bg-yellow-100 text-yellow-800">Media</Badge>
      case 'baja':
        return <Badge className="bg-green-100 text-green-800">Baja</Badge>
      default:
        return <Badge variant="secondary">{prioridad}</Badge>
    }
  }

  const getTipoBadge = (tipo: string) => {
    switch (tipo) {
      case 'vencimiento':
        return <Badge className="bg-orange-100 text-orange-800">Vencimiento</Badge>
      case 'mora':
        return <Badge className="bg-red-100 text-red-800">Mora</Badge>
      case 'pago':
        return <Badge className="bg-green-100 text-green-800">Pago</Badge>
      case 'sistema':
        return <Badge className="bg-blue-100 text-blue-800">Sistema</Badge>
      default:
        return <Badge variant="secondary">{tipo}</Badge>
    }
  }

  const filteredNotificaciones = notificaciones.filter(notif => {
    const matchesSearch = notif.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         notif.mensaje.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (notif.cliente && notif.cliente.toLowerCase().includes(searchTerm.toLowerCase()))
    const matchesTipo = !filterTipo || notif.tipo === filterTipo
    const matchesPrioridad = !filterPrioridad || notif.prioridad === filterPrioridad
    return matchesSearch && matchesTipo && matchesPrioridad
  })

  const notificacionesNoLeidas = notificaciones.filter(n => !n.leida).length
  const notificacionesAltaPrioridad = notificaciones.filter(n => n.prioridad === 'alta' && !n.leida).length

  const marcarComoLeida = (id: number) => {
    setNotificaciones(prev => 
      prev.map(notif => 
        notif.id === id ? { ...notif, leida: true } : notif
      )
    )
  }

  const marcarTodasComoLeidas = () => {
    setNotificaciones(prev => 
      prev.map(notif => ({ ...notif, leida: true }))
    )
  }

  const eliminarNotificacion = (id: number) => {
    setNotificaciones(prev => prev.filter(notif => notif.id !== id))
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
            <h1 className="text-3xl font-bold text-gray-900">Notificaciones</h1>
            <p className="text-gray-600 mt-1">Mantente al día con todas las actividades del sistema</p>
          </div>
          <div className="flex space-x-2">
            <Button variant="outline" onClick={marcarTodasComoLeidas}>
              <Check className="w-4 h-4 mr-2" />
              Marcar todas como leídas
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
