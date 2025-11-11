import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  Search,
  Plus,
  Eye,
  Edit,
  Building,
  Users,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Car,
  DollarSign,
  Link,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatDate } from '@/utils'
import { useConcesionarios } from '@/hooks/useConcesionarios'
import { usePrestamos } from '@/hooks/usePrestamos'
import { useClientes } from '@/hooks/useClientes'
import { Concesionario } from '@/services/concesionarioService'
import { Prestamo } from '@/types'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useNavigate } from 'react-router-dom'

// Estados del embudo de concesionarios
const ESTADOS_EMBUDO = [
  { 
    id: 'activo', 
    label: 'Activo', 
    color: 'bg-green-50 border-green-200', 
    headerColor: 'bg-green-100 text-green-800',
    icon: CheckCircle,
    count: 0
  },
  { 
    id: 'pendiente', 
    label: 'Pendiente', 
    color: 'bg-yellow-50 border-yellow-200', 
    headerColor: 'bg-yellow-100 text-yellow-800',
    icon: Clock,
    count: 0
  },
  { 
    id: 'inactivo', 
    label: 'Inactivo', 
    color: 'bg-gray-50 border-gray-200', 
    headerColor: 'bg-gray-100 text-gray-800',
    icon: XCircle,
    count: 0
  },
]

// Mapear estado de concesionario
const mapearEstadoConcesionario = (concesionario: Concesionario, prestamos: Prestamo[]): string => {
  if (!concesionario.activo) {
    return 'inactivo'
  }
  
  // Si tiene préstamos aprobados, está activo
  const prestamosAprobados = prestamos.filter(p => 
    p.concesionario === concesionario.nombre && p.estado === 'APROBADO'
  )
  
  if (prestamosAprobados.length > 0) {
    return 'activo'
  }
  
  // Si tiene préstamos en revisión o draft, está pendiente
  const prestamosPendientes = prestamos.filter(p => 
    p.concesionario === concesionario.nombre && 
    (p.estado === 'EN_REVISION' || p.estado === 'DRAFT')
  )
  
  if (prestamosPendientes.length > 0) {
    return 'pendiente'
  }
  
  // Si está activo pero sin préstamos, está pendiente
  return 'pendiente'
}

export function EmbudoConcesionarios() {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [concesionarioSeleccionado, setConcesionarioSeleccionado] = useState<number | null>(null)

  // Obtener concesionarios reales
  const { data: concesionariosData, isLoading: isLoadingConcesionarios } = useConcesionarios({ limit: 1000 })

  // Obtener todos los préstamos para calcular estadísticas
  const { data: prestamosData, isLoading: isLoadingPrestamos } = usePrestamos(
    undefined,
    1,
    1000 // Obtener muchos préstamos para análisis
  )

  // Obtener todos los clientes para vincular con préstamos
  const { data: clientesData } = useClientes(undefined, 1, 1000)

  const concesionarios = concesionariosData?.items || []
  const prestamos = prestamosData?.data || []
  const clientes = clientesData?.data || []

  // Calcular estadísticas por concesionario
  const concesionariosConEstadisticas = useMemo(() => {
    return concesionarios.map(concesionario => {
      const prestamosConcesionario = prestamos.filter(p => 
        p.concesionario === concesionario.nombre
      )
      
      const prestamosAprobados = prestamosConcesionario.filter(p => p.estado === 'APROBADO')
      
      // Obtener clientes únicos de los préstamos
      const clientesIds = new Set(prestamosConcesionario.map(p => p.cliente_id))
      const clientesAsignados = clientes.filter(c => clientesIds.has(c.id))
      
      // Calcular monto total de préstamos aprobados
      const montoTotal = prestamosAprobados.reduce((sum, p) => 
        sum + Number(p.total_financiamiento || 0), 0
      )

      return {
        ...concesionario,
        estado: mapearEstadoConcesionario(concesionario, prestamos),
        clientesAsignados: clientesAsignados.length,
        prestamosActivos: prestamosAprobados.length,
        prestamosTotal: prestamosConcesionario.length,
        montoTotal,
        prestamos: prestamosConcesionario,
        clientes: clientesAsignados,
      }
    })
  }, [concesionarios, prestamos, clientes])

  // Filtrar concesionarios
  const concesionariosFiltrados = concesionariosConEstadisticas.filter(concesionario => {
    const matchSearch =
      concesionario.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      searchTerm === ''
    return matchSearch
  })

  // Agrupar concesionarios por estado
  const concesionariosPorEstado = ESTADOS_EMBUDO.map(estado => ({
    ...estado,
    concesionarios: concesionariosFiltrados.filter(c => c.estado === estado.id),
    count: concesionariosFiltrados.filter(c => c.estado === estado.id).length
  }))

  // Estadísticas generales
  const estadisticas = useMemo(() => {
    return {
      total: concesionariosConEstadisticas.length,
      activos: concesionariosConEstadisticas.filter(c => c.estado === 'activo').length,
      pendientes: concesionariosConEstadisticas.filter(c => c.estado === 'pendiente').length,
      inactivos: concesionariosConEstadisticas.filter(c => c.estado === 'inactivo').length,
      totalClientes: new Set(
        concesionariosConEstadisticas.flatMap(c => c.prestamos.map(p => p.cliente_id))
      ).size,
      totalPrestamos: concesionariosConEstadisticas.reduce((sum, c) => sum + c.prestamosActivos, 0),
      montoTotal: concesionariosConEstadisticas.reduce((sum, c) => sum + c.montoTotal, 0),
    }
  }, [concesionariosConEstadisticas])

  // Concesionario seleccionado y sus datos
  const concesionarioDetalle = concesionarioSeleccionado
    ? concesionariosConEstadisticas.find(c => c.id === concesionarioSeleccionado)
    : null

  // Clientes y préstamos del concesionario seleccionado
  const clientesYprestamosDetalle = useMemo(() => {
    if (!concesionarioDetalle) return []
    
    // Agrupar por cliente y mostrar sus préstamos
    const clientesMap = new Map<number, {
      cliente: typeof clientes[0]
      prestamos: Prestamo[]
      montoTotal: number
    }>()

    concesionarioDetalle.prestamos.forEach(prestamo => {
      const cliente = clientes.find(c => c.id === prestamo.cliente_id)
      if (cliente) {
        if (!clientesMap.has(cliente.id)) {
          clientesMap.set(cliente.id, {
            cliente,
            prestamos: [],
            montoTotal: 0
          })
        }
        const entry = clientesMap.get(cliente.id)!
        entry.prestamos.push(prestamo)
        entry.montoTotal += Number(prestamo.total_financiamiento || 0)
      }
    })

    return Array.from(clientesMap.values())
  }, [concesionarioDetalle, clientes])

  if (isLoadingConcesionarios || isLoadingPrestamos) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Building className="h-8 w-8 text-blue-600" />
            Seguimiento Concesionarios
          </h1>
          <p className="text-gray-600 mt-1">
            Seguimiento de concesionarios que gestionan ventas en base a créditos
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/concesionarios')}>
            <Building className="h-4 w-4 mr-2" />
            Gestionar Concesionarios
          </Button>
          <Button onClick={() => navigate('/concesionarios')}>
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Concesionario
          </Button>
        </div>
      </motion.div>

      {/* Estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{estadisticas.total}</div>
            <p className="text-xs text-gray-600 mt-1">Total Concesionarios</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{estadisticas.activos}</div>
            <p className="text-xs text-gray-600 mt-1">Activos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-yellow-600">{estadisticas.pendientes}</div>
            <p className="text-xs text-gray-600 mt-1">Pendientes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">{estadisticas.inactivos}</div>
            <p className="text-xs text-gray-600 mt-1">Inactivos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{estadisticas.totalClientes}</div>
            <p className="text-xs text-gray-600 mt-1">Total Clientes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-purple-600">{estadisticas.totalPrestamos}</div>
            <p className="text-xs text-gray-600 mt-1">Préstamos Activos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{formatCurrency(estadisticas.montoTotal)}</div>
            <p className="text-xs text-gray-600 mt-1">Monto Total</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Buscar por nombre de concesionario..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Kanban Board - Embudo Visual */}
        <div className="lg:col-span-2 overflow-x-auto pb-4">
          <div className="flex gap-4 min-w-max">
            {concesionariosPorEstado.map((columna) => {
              const EstadoIcon = columna.icon
              return (
                <motion.div
                  key={columna.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="flex-shrink-0 w-80"
                >
                  <Card className={`h-full ${columna.color} border-2`}>
                    <CardHeader className={`${columna.headerColor} pb-3`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <EstadoIcon className="h-5 w-5" />
                          <CardTitle className="text-sm font-semibold">{columna.label}</CardTitle>
                        </div>
                        <Badge variant="secondary" className="bg-white/80">
                          {columna.count}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="p-3 space-y-3 max-h-[calc(100vh-400px)] overflow-y-auto">
                      {columna.concesionarios.length === 0 ? (
                        <div className="text-center py-8 text-gray-400">
                          <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          <p className="text-xs">No hay concesionarios</p>
                        </div>
                      ) : (
                        columna.concesionarios.map((concesionario) => (
                          <motion.div
                            key={concesionario.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            whileHover={{ scale: 1.02 }}
                            onClick={() => setConcesionarioSeleccionado(
                              concesionarioSeleccionado === concesionario.id ? null : concesionario.id
                            )}
                            className={`bg-white rounded-lg p-4 shadow-sm border-2 transition-all cursor-pointer ${
                              concesionarioSeleccionado === concesionario.id
                                ? 'border-blue-500 shadow-md'
                                : 'border-gray-200 hover:shadow-md'
                            }`}
                          >
                            <div className="space-y-3">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <h3 className="font-semibold text-gray-900 text-sm">{concesionario.nombre}</h3>
                                  <p className="text-xs text-gray-500 mt-1">
                                    {concesionario.activo ? 'Activo' : 'Inactivo'}
                                  </p>
                                </div>
                                <div className="flex gap-1">
                                  <Button 
                                    variant="ghost" 
                                    size="icon" 
                                    className="h-7 w-7"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setConcesionarioSeleccionado(
                                        concesionarioSeleccionado === concesionario.id ? null : concesionario.id
                                      )
                                    }}
                                  >
                                    <Eye className="h-3.5 w-3.5" />
                                  </Button>
                                  <Button 
                                    variant="ghost" 
                                    size="icon" 
                                    className="h-7 w-7"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      navigate(`/concesionarios`)
                                    }}
                                  >
                                    <Edit className="h-3.5 w-3.5" />
                                  </Button>
                                </div>
                              </div>
                              
                              <div className="space-y-2 pt-2 border-t border-gray-100">
                                <div className="grid grid-cols-2 gap-2 pt-2">
                                  <div className="bg-blue-50 rounded p-2">
                                    <div className="text-xs text-gray-600">Clientes</div>
                                    <div className="text-sm font-bold text-blue-700">{concesionario.clientesAsignados}</div>
                                  </div>
                                  <div className="bg-purple-50 rounded p-2">
                                    <div className="text-xs text-gray-600">Préstamos</div>
                                    <div className="text-sm font-bold text-purple-700">{concesionario.prestamosActivos}</div>
                                  </div>
                                </div>
                                {concesionario.montoTotal > 0 && (
                                  <div className="flex items-center gap-2 text-xs pt-1">
                                    <DollarSign className="h-3.5 w-3.5 text-green-600" />
                                    <span className="font-semibold text-green-700">{formatCurrency(concesionario.montoTotal)}</span>
                                  </div>
                                )}
                                <div className="text-xs text-gray-500 pt-1">
                                  Registro: {formatDate(new Date(concesionario.created_at))}
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        ))
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              )
            })}
          </div>
        </div>

        {/* Panel de Clientes y Préstamos del Concesionario Seleccionado */}
        <div className="lg:col-span-1">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="text-lg">
                {concesionarioDetalle
                  ? `${concesionarioDetalle.nombre}`
                  : 'Seleccione un concesionario'}
              </CardTitle>
              <CardDescription>
                {concesionarioDetalle
                  ? `${concesionarioDetalle.clientesAsignados} clientes, ${concesionarioDetalle.prestamosActivos} préstamos activos`
                  : 'Haga clic en un concesionario para ver sus clientes y préstamos'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 max-h-[calc(100vh-400px)] overflow-y-auto">
              {!concesionarioDetalle ? (
                <div className="text-center py-12 text-gray-500">
                  <Building className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-sm">Seleccione un concesionario para ver sus clientes y préstamos</p>
                </div>
              ) : clientesYprestamosDetalle.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Users className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-sm">Este concesionario no tiene clientes asignados</p>
                </div>
              ) : (
                clientesYprestamosDetalle.map(({ cliente, prestamos: prestamosCliente, montoTotal }) => (
                  <motion.div
                    key={cliente.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-gray-50 rounded-lg p-3 border border-gray-200 hover:border-blue-300 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-medium text-sm text-gray-900">
                          {cliente.nombres} {cliente.apellidos}
                        </h4>
                        <p className="text-xs text-gray-500 mt-1">Cédula: {cliente.cedula}</p>
                        {cliente.telefono && (
                          <p className="text-xs text-gray-500">Tel: {cliente.telefono}</p>
                        )}
                      </div>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="h-7 w-7"
                        onClick={() => window.open(`/clientes/${cliente.id}`, '_blank')}
                      >
                        <Link className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    
                    <div className="space-y-2 mt-2 pt-2 border-t border-gray-200">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-600">Préstamos:</span>
                        <Badge variant="outline" className="text-xs">
                          {prestamosCliente.length}
                        </Badge>
                      </div>
                      
                      {prestamosCliente.map((prestamo) => (
                        <div key={prestamo.id} className="bg-white rounded p-2 border border-gray-100">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-gray-700">
                              Préstamo #{prestamo.id}
                            </span>
                            <Badge 
                              variant="outline" 
                              className={`text-xs ${
                                prestamo.estado === 'APROBADO' ? 'border-green-500 text-green-700' :
                                prestamo.estado === 'EN_REVISION' ? 'border-yellow-500 text-yellow-700' :
                                'border-gray-500 text-gray-700'
                              }`}
                            >
                              {prestamo.estado}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-gray-600">
                            <DollarSign className="h-3 w-3" />
                            <span>{formatCurrency(Number(prestamo.total_financiamiento || 0))}</span>
                          </div>
                          {prestamo.modelo_vehiculo && (
                            <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                              <Car className="h-3 w-3" />
                              <span>{prestamo.modelo_vehiculo}</span>
                            </div>
                          )}
                          <div className="flex gap-1 mt-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 text-xs px-2"
                              onClick={() => window.open(`/prestamos`, '_blank')}
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              Ver
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 text-xs px-2"
                              onClick={() => window.open(`/clientes/${cliente.id}`, '_blank')}
                            >
                              <Users className="h-3 w-3 mr-1" />
                              Cliente
                            </Button>
                          </div>
                        </div>
                      ))}
                      
                      {montoTotal > 0 && (
                        <div className="flex items-center justify-between pt-1 border-t border-gray-200">
                          <span className="text-xs font-semibold text-gray-700">Total:</span>
                          <span className="text-xs font-bold text-green-700">
                            {formatCurrency(montoTotal)}
                          </span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
