import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Search,
  Plus,
  Eye,
  Edit,
  Target,
  Users,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Phone,
  DollarSign,
  Building,
  X,
  Menu,
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog'
import { formatCurrency, formatDate } from '../utils'
import { useClientes, useSearchClientes, useCambiarEstadoCliente } from '../hooks/useClientes'
import { usePrestamos } from '../hooks/usePrestamos'
import { Cliente } from '../types'
import { LoadingSpinner } from '../components/ui/loading-spinner'
import { clienteService } from '../services/clienteService'
import { useQuery } from '@tanstack/react-query'

// Estados del embudo
const ESTADOS_EMBUDO = [
  {
    id: 'prospecto',
    label: 'Prospecto',
    color: 'bg-gray-50 border-gray-200',
    headerColor: 'bg-gray-100 text-gray-800',
    icon: Users,
    count: 0
  },
  {
    id: 'evaluacion',
    label: 'En Evaluación',
    color: 'bg-blue-50 border-blue-200',
    headerColor: 'bg-blue-100 text-blue-800',
    icon: Clock,
    count: 0
  },
  {
    id: 'aprobado',
    label: 'Aprobado',
    color: 'bg-green-50 border-green-200',
    headerColor: 'bg-green-100 text-green-800',
    icon: CheckCircle,
    count: 0
  },
  {
    id: 'rechazado',
    label: 'Rechazado',
    color: 'bg-red-50 border-red-200',
    headerColor: 'bg-red-100 text-red-800',
    icon: XCircle,
    count: 0
  },
  {
    id: 'agregar_otro',
    label: 'Agregar embudo (agregar otro)',
    color: 'bg-purple-50 border-purple-200',
    headerColor: 'bg-purple-100 text-purple-800',
    icon: Plus,
    count: 0
  },
]

// Mapear estado de Cliente a estado del embudo
const mapearEstadoEmbudo = (
  cliente: Cliente,
  tienePrestamos: boolean,
  prestamosAlDia: boolean,
  prestamosCliente: any[] = []
): string => {
  // 1. RECHAZADO: Solo si en módulo préstamos está con ese estado
  const prestamosRechazados = prestamosCliente.filter(p =>
    p.estado === 'RECHAZADO'
  )
  if (prestamosRechazados.length > 0) {
    return 'rechazado'
  }

  // 2. APROBADO: Todos los que tienen estado aprobado en préstamos
  const prestamosAprobados = prestamosCliente.filter(p =>
    p.estado === 'APROBADO'
  )
  if (prestamosAprobados.length > 0) {
    return 'aprobado'
  }

  // 3. EN EVALUACIÓN: Solo si están en el módulo préstamos en evaluación (EN_REVISION o DRAFT)
  const prestamosEnEvaluacion = prestamosCliente.filter(p =>
    p.estado === 'EN_REVISION' || p.estado === 'DRAFT'
  )
  if (prestamosEnEvaluacion.length > 0) {
    return 'evaluacion'
  }

  // 4. PROSPECTO: Debe habilitarse para encontrar cliente de base de datos
  // Cualquier cliente de la base de datos puede ser prospecto (no requiere tener préstamos)
  // Si no tiene préstamos o no está en ningún estado específico, es prospecto
  return 'prospecto'
}

export function EmbudoClientes() {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [searchCliente, setSearchCliente] = useState('')
  const [clientesEnEmbudo, setClientesEnEmbudo] = useState<Map<number, Cliente>>(new Map())
  const [estadosManuales, setEstadosManuales] = useState<Map<number, string>>(new Map()) // Guardar estados manuales del embudo
  const [clienteArrastrando, setClienteArrastrando] = useState<number | null>(null)
  const [columnaDestino, setColumnaDestino] = useState<string | null>(null)

  // Hook para actualizar estado del cliente en la BD
  const cambiarEstadoMutation = useCambiarEstadoCliente()

  // Obtener todos los clientes para el embudo
  const { data: clientesData, isLoading: isLoadingClientes } = useClientes(
    undefined,
    1,
    1000 // Obtener muchos clientes para el embudo
  )

  // Obtener préstamos para vincular concesionarios
  const { data: prestamosData } = usePrestamos(undefined, 1, 1000)

  // Obtener estadísticas del embudo desde la API
  const { data: estadisticasEmbudo, isLoading: isLoadingEstadisticas } = useQuery({
    queryKey: ['estadisticas-embudo'],
    queryFn: () => clienteService.getEstadisticasEmbudo(),
    staleTime: 30 * 1000, // Cache de 30 segundos
    refetchInterval: 60 * 1000, // Refrescar cada minuto
  })

  // Búsqueda de clientes para agregar (incluir todos los estados para el embudo)
  const { data: clientesBuscados = [], isLoading: isLoadingSearch } = useSearchClientes(searchCliente, true)

  // Convertir clientes a formato del embudo
  const clientesEmbudo = useMemo(() => {
    if (!clientesData?.data) return []

    const prestamos = prestamosData?.data || []

    // Combinar clientes de la API con clientes agregados manualmente
    // Si un cliente está en clientesEnEmbudo, usar esa versión (tiene estado actualizado)
    const todosClientes = clientesData.data.map(cliente => {
      const clienteActualizado = clientesEnEmbudo.get(cliente.id)
      return clienteActualizado || cliente
    })

    // Agregar clientes que no están en la API pero sí en clientesEnEmbudo
    clientesEnEmbudo.forEach((cliente) => {
      if (!todosClientes.find(c => c.id === cliente.id)) {
        todosClientes.push(cliente)
      }
    })

    return todosClientes.map(cliente => {
      // Buscar préstamos del cliente
      const prestamosCliente = prestamos.filter(p => p.cliente_id === cliente.id)
      const tienePrestamos = prestamosCliente.length > 0

      // Verificar si los préstamos están al día:
      // - El cliente debe estar ACTIVO
      // - No debe tener días de mora (dias_mora === 0)
      // - Los préstamos deben estar APROBADOS (no en revisión o rechazados)
      const prestamosAlDia = tienePrestamos &&
        cliente.estado === 'ACTIVO' &&
        cliente.dias_mora === 0 &&
        prestamosCliente.every(p => p.estado === 'APROBADO')

      const prestamoCliente = prestamosCliente[0] || null
      const concesionario = prestamoCliente?.concesionario || 'N/A'

      // Priorizar estado manual si existe, sino usar el estado calculado
      const estadoCalculado = mapearEstadoEmbudo(cliente, tienePrestamos, prestamosAlDia, prestamosCliente)
      const estadoFinal = estadosManuales.has(cliente.id)
        ? estadosManuales.get(cliente.id)!
        : estadoCalculado

      return {
        id: cliente.id,
        nombre: cliente.nombres?.trim() || 'Sin nombre',
        cedula: cliente.cedula,
        telefono: cliente.telefono || 'N/A',
        estado: estadoFinal,
        montoSolicitado: prestamoCliente?.total_financiamiento || cliente.total_financiamiento || cliente.monto_financiado || 0,
        fechaIngreso: new Date(cliente.fecha_registro),
        concesionario: concesionario,
        cliente: cliente, // Guardar referencia al cliente completo
      }
    })
  }, [clientesData, clientesEnEmbudo, prestamosData, estadosManuales])

  const clientesFiltrados = clientesEmbudo.filter(cliente => {
    const matchSearch =
      cliente.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cliente.cedula.includes(searchTerm) ||
      cliente.telefono.includes(searchTerm) ||
      cliente.concesionario.toLowerCase().includes(searchTerm.toLowerCase())
    return matchSearch
  })

  // Agrupar clientes por estado (debe coincidir con los embudos)
  const clientesPorEstado = useMemo(() => {
    return ESTADOS_EMBUDO.map(estado => ({
      ...estado,
      clientes: clientesFiltrados.filter(c => c.estado === estado.id),
      count: clientesFiltrados.filter(c => c.estado === estado.id).length
    }))
  }, [clientesFiltrados])

  // Estadísticas basadas en los embudos (deben coincidir exactamente)
  const estadisticas = useMemo(() => {
    // Usar los mismos datos que clientesPorEstado para garantizar coincidencia
    const prospectos = clientesPorEstado.find(e => e.id === 'prospecto')?.count || 0
    const evaluacion = clientesPorEstado.find(e => e.id === 'evaluacion')?.count || 0
    const aprobados = clientesPorEstado.find(e => e.id === 'aprobado')?.count || 0
    const rechazados = clientesPorEstado.find(e => e.id === 'rechazado')?.count || 0
    const agregarOtro = clientesPorEstado.find(e => e.id === 'agregar_otro')?.count || 0

    return {
      total: clientesFiltrados.length,
      prospectos,
      evaluacion,
      aprobados,
      rechazados,
      agregarOtro,
    }
  }, [clientesFiltrados, clientesPorEstado])

  const handleAgregarCliente = (cliente: Cliente) => {
    setClientesEnEmbudo(prev => new Map(prev).set(cliente.id, cliente))
    // Asignar automáticamente al embudo "agregar_otro"
    setEstadosManuales(prev => {
      const nuevo = new Map(prev)
      nuevo.set(cliente.id, 'agregar_otro')
      return nuevo
    })
    setSearchCliente('')
    setShowAddDialog(false)
  }

  const handleEliminarCliente = (clienteId: number) => {
    setClientesEnEmbudo(prev => {
      const nuevo = new Map(prev)
      nuevo.delete(clienteId)
      return nuevo
    })
  }

  // Funciones para drag and drop
  const handleDragStart = (clienteId: number) => {
    setClienteArrastrando(clienteId)
  }

  const handleDragOver = (e: React.DragEvent, estadoId: string) => {
    e.preventDefault()
    setColumnaDestino(estadoId)
  }

  const handleDragLeave = () => {
    setColumnaDestino(null)
  }

  // Función auxiliar para mapear estado del embudo al estado del cliente en BD
  // Retorna el nuevo estado o null si no debe cambiar
  const mapearEstadoEmbudoACliente = (
    estadoEmbudo: string,
    cliente: Cliente,
    prestamosCliente: any[] = []
  ): Cliente['estado'] | null => {
    switch (estadoEmbudo) {
      case 'prospecto':
        return 'ACTIVO'
      case 'evaluacion':
        // Si el cliente tiene préstamos en aprobación de riesgo, mantener ACTIVO
        // Solo cambiar a MORA si realmente está en mora
        const tienePrestamosEnRiesgo = prestamosCliente.some(p =>
          p.estado === 'EN_REVISION' || p.estado === 'DRAFT'
        )
        if (tienePrestamosEnRiesgo) {
          // Mantener ACTIVO si está en aprobación de riesgo
          return cliente.estado === 'ACTIVO' ? null : 'ACTIVO'
        }
        // Si no está en aprobación de riesgo, puede ser MORA
        return 'MORA'
      case 'aprobado':
        return 'FINALIZADO'
      case 'rechazado':
        return 'INACTIVO'
      case 'agregar_otro':
        // No cambiar el estado para "agregar otro"
        return null
      default:
        return null
    }
  }

  const handleDrop = async (e: React.DragEvent, estadoDestino: string) => {
    e.preventDefault()
    if (clienteArrastrando && estadoDestino) {
      // Buscar el cliente en la lista de clientes del embudo
      const cliente = clientesEmbudo.find(c => c.id === clienteArrastrando)
      if (cliente && cliente.cliente) {
        // Obtener préstamos del cliente para la lógica de mapeo
        const prestamos = prestamosData?.data || []
        const prestamosCliente = prestamos.filter(p => p.cliente_id === cliente.id)

        // Guardar el estado manual del embudo (esto tiene prioridad sobre el cálculo automático)
        setEstadosManuales(prev => {
          const nuevo = new Map(prev)
          nuevo.set(cliente.id, estadoDestino)
          return nuevo
        })

        // Mapear el estado del embudo al estado del cliente en BD
        const nuevoEstadoCliente = mapearEstadoEmbudoACliente(
          estadoDestino,
          cliente.cliente,
          prestamosCliente
        )

        // Si hay un nuevo estado válido y es diferente al actual, actualizar en BD
        if (nuevoEstadoCliente && nuevoEstadoCliente !== cliente.cliente.estado) {
          try {
            // Actualizar estado en la base de datos
            await cambiarEstadoMutation.mutateAsync({
              id: String(cliente.id),
              estado: nuevoEstadoCliente
            })

            // Actualizar el estado del cliente en el objeto Cliente local
            const clienteActualizado: Cliente = {
              ...cliente.cliente,
              estado: nuevoEstadoCliente,
            }

            // Actualizar en el Map de clientesEnEmbudo
            setClientesEnEmbudo(prev => {
              const nuevo = new Map(prev)
              nuevo.set(cliente.id, clienteActualizado)
              return nuevo
            })
          } catch (error) {
            // Si hay error, revertir el cambio en estadosManuales
            setEstadosManuales(prev => {
              const nuevo = new Map(prev)
              nuevo.delete(cliente.id)
              return nuevo
            })
            console.error('Error al actualizar estado del cliente:', error)
          }
        } else {
          // Si no hay cambio de estado o es null, solo actualizar el estado manual del embudo
          // (ya se hizo arriba con setEstadosManuales)
          // Actualizar también en clientesEnEmbudo para mantener consistencia
          setClientesEnEmbudo(prev => {
            const nuevo = new Map(prev)
            nuevo.set(cliente.id, cliente.cliente)
            return nuevo
          })
        }
      }
    }
    setClienteArrastrando(null)
    setColumnaDestino(null)
  }

  const handleDragEnd = () => {
    setClienteArrastrando(null)
    setColumnaDestino(null)
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
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Target className="h-6 w-6 text-blue-600" />
            Venta Servicios
          </h2>
          <p className="text-gray-600 mt-1 text-sm">
            Gestión de ventas y servicios
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/clientes')}>
            <Users className="h-4 w-4 mr-2" />
            Ver Todos los Clientes
          </Button>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Agregar Cliente
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Buscar y Agregar Cliente</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Buscar por nombre, cédula o teléfono..."
                  value={searchCliente}
                  onChange={(e) => setSearchCliente(e.target.value)}
                  className="pl-10"
                />
              </div>
              {isLoadingSearch ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : clientesBuscados.length === 0 && searchCliente.length >= 2 ? (
                <div className="text-center py-8 text-gray-500">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                  <p>No se encontraron clientes</p>
                </div>
              ) : (
                <div className="max-h-96 overflow-y-auto space-y-2">
                  {clientesBuscados
                    .filter(c => !clientesEnEmbudo.has(c.id))
                    .map((cliente) => (
                    <Card
                      key={cliente.id}
                      className="cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => handleAgregarCliente(cliente)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold">{cliente.nombres || 'Sin nombre'}</h3>
                            <p className="text-sm text-gray-500">Cédula: {cliente.cedula}</p>
                            {cliente.telefono && (
                              <p className="text-sm text-gray-500">Tel: {cliente.telefono}</p>
                            )}
                          </div>
                          <Button size="sm">
                            <Plus className="h-4 w-4 mr-1" />
                            Agregar
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
        </div>
      </motion.div>

      {/* Estadísticas - Deben coincidir exactamente con los embudos */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{estadisticas.total}</div>
            <p className="text-xs text-gray-600 mt-1">Total Clientes</p>
          </CardContent>
        </Card>
        {clientesPorEstado.filter(e => e.id !== 'agregar_otro').map((estado) => {
          const EstadoIcon = estado.icon
          const colorMap: Record<string, string> = {
            'prospecto': 'text-gray-600',
            'evaluacion': 'text-blue-600',
            'aprobado': 'text-green-600',
            'rechazado': 'text-red-600'
          }
          const color = colorMap[estado.id] || 'text-gray-600'

          return (
            <Card key={estado.id}>
              <CardContent className="pt-6">
                <div className={`text-2xl font-bold ${color}`}>{estado.count}</div>
                <p className="text-xs text-gray-600 mt-1">{estado.label}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Buscar por nombre, cédula, teléfono o concesionario..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoadingClientes ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner />
        </div>
      ) : (
        /* Kanban Board - Embudo Visual */
        <div className="overflow-x-auto pb-4">
          <div className="flex gap-4 min-w-max">
            {clientesPorEstado.map((columna) => {
              const EstadoIcon = columna.icon
              return (
                <motion.div
                  key={columna.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="flex-shrink-0 w-80"
                  onDragOver={(e) => handleDragOver(e, columna.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, columna.id)}
                >
                  <Card className={`h-full ${columna.color} border-2 ${
                    columnaDestino === columna.id ? 'ring-2 ring-blue-500 ring-offset-2' : ''
                  } transition-all`}>
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
                      {columna.id === 'agregar_otro' ? (
                        <div className="text-center py-8">
                          <Button
                            variant="outline"
                            className="w-full border-2 border-dashed border-purple-300 hover:border-purple-400 hover:bg-purple-50"
                            onClick={() => setShowAddDialog(true)}
                          >
                            <Plus className="h-4 w-4 mr-2" />
                            Agregar Cliente
                          </Button>
                          {columna.clientes.length > 0 && (
                            <div className="mt-3 space-y-3">
                              {columna.clientes.map((cliente) => (
                                <motion.div
                                  key={cliente.id}
                                  initial={{ opacity: 0, scale: 0.95 }}
                                  animate={{
                                    opacity: clienteArrastrando === cliente.id ? 0.5 : 1,
                                    scale: clienteArrastrando === cliente.id ? 0.95 : 1
                                  }}
                                  whileHover={{ scale: clienteArrastrando === cliente.id ? 0.95 : 1.02 }}
                                  draggable
                                  onDragStart={() => handleDragStart(cliente.id)}
                                  onDragEnd={handleDragEnd}
                                  onClick={() => navigate(`/clientes/${cliente.id}`)}
                                  className={`bg-white rounded-lg p-4 shadow-sm border-2 border-gray-200 hover:border-purple-300 hover:shadow-md transition-all cursor-move ${
                                    clienteArrastrando === cliente.id ? 'opacity-50 cursor-grabbing scale-95' : 'cursor-grab'
                                  }`}
                                >
                                  <div className="space-y-3">
                                    <div className="flex items-start justify-between">
                                      <div className="flex items-start gap-2 flex-1">
                                        <Menu className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                        <div className="flex-1 min-w-0">
                                          <h3 className="font-semibold text-gray-900 text-sm">{cliente.nombre}</h3>
                                          <p className="text-xs text-gray-500 mt-1">Cédula: {cliente.cedula}</p>
                                        </div>
                                      </div>
                                      <div className="flex gap-1">
                                        <Button
                                          variant="ghost"
                                          size="icon"
                                          className="h-7 w-7"
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            navigate(`/clientes/${cliente.id}`)
                                          }}
                                          title="Ver detalles del cliente"
                                        >
                                          <Eye className="h-3.5 w-3.5" />
                                        </Button>
                                        <Button
                                          variant="ghost"
                                          size="icon"
                                          className="h-7 w-7"
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            navigate(`/clientes/${cliente.id}?edit=true`)
                                          }}
                                          title="Editar cliente"
                                        >
                                          <Edit className="h-3.5 w-3.5" />
                                        </Button>
                                        {clientesEnEmbudo.has(cliente.id) && (
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-red-600 hover:text-red-700"
                                            onClick={(e) => {
                                              e.stopPropagation()
                                              handleEliminarCliente(cliente.id)
                                            }}
                                            title="Remover del embudo"
                                          >
                                            <X className="h-3.5 w-3.5" />
                                          </Button>
                                        )}
                                      </div>
                                    </div>

                                    <div className="space-y-2 pt-2 border-t border-gray-100">
                                      <div className="flex items-center gap-2 text-xs text-gray-600">
                                        <Phone className="h-3.5 w-3.5" />
                                        <span>{cliente.telefono}</span>
                                      </div>
                                      {cliente.montoSolicitado > 0 && (
                                        <div className="flex items-center gap-2 text-xs text-gray-600">
                                          <DollarSign className="h-3.5 w-3.5" />
                                          <span className="font-medium">{formatCurrency(cliente.montoSolicitado)}</span>
                                        </div>
                                      )}
                                      <div className="flex items-center gap-2 text-xs text-gray-600">
                                        <Building className="h-3.5 w-3.5" />
                                        <span className="truncate">{cliente.concesionario}</span>
                                      </div>
                                      <div className="text-xs text-gray-500 pt-1">
                                        Ingreso: {formatDate(cliente.fechaIngreso)}
                                      </div>
                                    </div>
                                  </div>
                                </motion.div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : columna.clientes.length === 0 ? (
                        <div className={`text-center py-8 text-gray-400 border-2 border-dashed rounded-lg ${
                          columnaDestino === columna.id ? 'border-blue-400 bg-blue-50/50' : 'border-gray-300'
                        } transition-all`}>
                          <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          <p className="text-xs">Suelta aquí para mover</p>
                        </div>
                      ) : (
                        columna.clientes.map((cliente) => (
                          <motion.div
                            key={cliente.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{
                              opacity: clienteArrastrando === cliente.id ? 0.5 : 1,
                              scale: clienteArrastrando === cliente.id ? 0.95 : 1
                            }}
                            whileHover={{ scale: clienteArrastrando === cliente.id ? 0.95 : 1.02 }}
                            draggable
                            onDragStart={() => handleDragStart(cliente.id)}
                            onDragEnd={handleDragEnd}
                            onClick={() => navigate(`/clientes/${cliente.id}`)}
                            className={`bg-white rounded-lg p-4 shadow-sm border-2 border-gray-200 hover:border-blue-300 hover:shadow-md transition-all cursor-move ${
                              clienteArrastrando === cliente.id ? 'opacity-50 cursor-grabbing scale-95' : 'cursor-grab'
                            }`}
                          >
                            <div className="space-y-3">
                              <div className="flex items-start justify-between">
                                <div className="flex items-start gap-2 flex-1">
                                  <Menu className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                  <div className="flex-1 min-w-0">
                                    <h3 className="font-semibold text-gray-900 text-sm">{cliente.nombre}</h3>
                                    <p className="text-xs text-gray-500 mt-1">Cédula: {cliente.cedula}</p>
                                  </div>
                                </div>
                                <div className="flex gap-1">
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      navigate(`/clientes/${cliente.id}`)
                                    }}
                                    title="Ver detalles del cliente"
                                  >
                                    <Eye className="h-3.5 w-3.5" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      navigate(`/clientes/${cliente.id}?edit=true`)
                                    }}
                                    title="Editar cliente"
                                  >
                                    <Edit className="h-3.5 w-3.5" />
                                  </Button>
                                  {clientesEnEmbudo.has(cliente.id) && (
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      className="h-7 w-7 text-red-600 hover:text-red-700"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        handleEliminarCliente(cliente.id)
                                      }}
                                      title="Remover del embudo"
                                    >
                                      <X className="h-3.5 w-3.5" />
                                    </Button>
                                  )}
                                </div>
                              </div>

                              <div className="space-y-2 pt-2 border-t border-gray-100">
                                <div className="flex items-center gap-2 text-xs text-gray-600">
                                  <Phone className="h-3.5 w-3.5" />
                                  <span>{cliente.telefono}</span>
                                </div>
                                {cliente.montoSolicitado > 0 && (
                                  <div className="flex items-center gap-2 text-xs text-gray-600">
                                    <DollarSign className="h-3.5 w-3.5" />
                                    <span className="font-medium">{formatCurrency(cliente.montoSolicitado)}</span>
                                  </div>
                                )}
                                <div className="flex items-center gap-2 text-xs text-gray-600">
                                  <Building className="h-3.5 w-3.5" />
                                  <span className="truncate">{cliente.concesionario}</span>
                                </div>
                                <div className="text-xs text-gray-500 pt-1">
                                  Ingreso: {formatDate(cliente.fechaIngreso)}
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
      )}
    </div>
  )
}
