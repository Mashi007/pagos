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
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Phone,
  DollarSign,
  Building,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { formatCurrency, formatDate } from '@/utils'
import { useClientes, useSearchClientes } from '@/hooks/useClientes'
import { usePrestamos } from '@/hooks/usePrestamos'
import { Cliente } from '@/types'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

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
    id: 'prestamo_activo', 
    label: 'Préstamo Activo', 
    color: 'bg-purple-50 border-purple-200', 
    headerColor: 'bg-purple-100 text-purple-800',
    icon: TrendingUp,
    count: 0
  },
]

// Mapear estado de Cliente a estado del embudo
const mapearEstadoEmbudo = (cliente: Cliente): string => {
  // Si tiene préstamo activo
  if (cliente.estado === 'ACTIVO' && cliente.total_financiamiento && cliente.total_financiamiento > 0) {
    return 'prestamo_activo'
  }
  // Si está en mora, podría estar en evaluación
  if (cliente.estado === 'MORA') {
    return 'evaluacion'
  }
  // Si está finalizado
  if (cliente.estado === 'FINALIZADO') {
    return 'aprobado'
  }
  // Si está inactivo
  if (cliente.estado === 'INACTIVO') {
    return 'rechazado'
  }
  // Por defecto, prospecto
  return 'prospecto'
}

export function EmbudoClientes() {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [searchCliente, setSearchCliente] = useState('')
  const [clientesEnEmbudo, setClientesEnEmbudo] = useState<Map<number, Cliente>>(new Map())

  // Obtener todos los clientes para el embudo
  const { data: clientesData, isLoading: isLoadingClientes } = useClientes(
    undefined,
    1,
    1000 // Obtener muchos clientes para el embudo
  )

  // Obtener préstamos para vincular concesionarios
  const { data: prestamosData } = usePrestamos(undefined, 1, 1000)

  // Búsqueda de clientes para agregar
  const { data: clientesBuscados = [], isLoading: isLoadingSearch } = useSearchClientes(searchCliente)

  // Convertir clientes a formato del embudo
  const clientesEmbudo = useMemo(() => {
    if (!clientesData?.data) return []
    
    const prestamos = prestamosData?.data || []
    
    // Combinar clientes de la API con clientes agregados manualmente
    const todosClientes = [...clientesData.data]
    clientesEnEmbudo.forEach((cliente) => {
      if (!todosClientes.find(c => c.id === cliente.id)) {
        todosClientes.push(cliente)
      }
    })

    return todosClientes.map(cliente => {
      // Buscar préstamo del cliente para obtener concesionario
      const prestamoCliente = prestamos.find(p => p.cliente_id === cliente.id)
      const concesionario = prestamoCliente?.concesionario || 'N/A'
      
      return {
        id: cliente.id,
        nombre: `${cliente.nombres} ${cliente.apellidos}`,
        cedula: cliente.cedula,
        telefono: cliente.telefono || 'N/A',
        estado: mapearEstadoEmbudo(cliente),
        montoSolicitado: prestamoCliente?.total_financiamiento || cliente.total_financiamiento || cliente.monto_financiado || 0,
        fechaIngreso: new Date(cliente.fecha_registro),
        concesionario: concesionario,
        cliente: cliente, // Guardar referencia al cliente completo
      }
    })
  }, [clientesData, clientesEnEmbudo, prestamosData])

  const clientesFiltrados = clientesEmbudo.filter(cliente => {
    const matchSearch =
      cliente.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cliente.cedula.includes(searchTerm) ||
      cliente.telefono.includes(searchTerm) ||
      cliente.concesionario.toLowerCase().includes(searchTerm.toLowerCase())
    return matchSearch
  })

  // Agrupar clientes por estado
  const clientesPorEstado = ESTADOS_EMBUDO.map(estado => ({
    ...estado,
    clientes: clientesFiltrados.filter(c => c.estado === estado.id),
    count: clientesFiltrados.filter(c => c.estado === estado.id).length
  }))

  const estadisticas = {
    total: clientesEmbudo.length,
    prospectos: clientesEmbudo.filter(c => c.estado === 'prospecto').length,
    evaluacion: clientesEmbudo.filter(c => c.estado === 'evaluacion').length,
    aprobados: clientesEmbudo.filter(c => c.estado === 'aprobado').length,
    rechazados: clientesEmbudo.filter(c => c.estado === 'rechazado').length,
    activos: clientesEmbudo.filter(c => c.estado === 'prestamo_activo').length,
  }

  const handleAgregarCliente = (cliente: Cliente) => {
    setClientesEnEmbudo(prev => new Map(prev).set(cliente.id, cliente))
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
            <Target className="h-8 w-8 text-blue-600" />
            Venta Servicios
          </h1>
          <p className="text-gray-600 mt-1">
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
                            <h3 className="font-semibold">{cliente.nombres} {cliente.apellidos}</h3>
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
      </motion.div>

      {/* Estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{estadisticas.total}</div>
            <p className="text-xs text-gray-600 mt-1">Total Clientes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">{estadisticas.prospectos}</div>
            <p className="text-xs text-gray-600 mt-1">Prospectos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{estadisticas.evaluacion}</div>
            <p className="text-xs text-gray-600 mt-1">En Evaluación</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{estadisticas.aprobados}</div>
            <p className="text-xs text-gray-600 mt-1">Aprobados</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-red-600">{estadisticas.rechazados}</div>
            <p className="text-xs text-gray-600 mt-1">Rechazados</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-purple-600">{estadisticas.activos}</div>
            <p className="text-xs text-gray-600 mt-1">Préstamos Activos</p>
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
                      {columna.clientes.length === 0 ? (
                        <div className="text-center py-8 text-gray-400">
                          <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          <p className="text-xs">No hay clientes</p>
                        </div>
                      ) : (
                        columna.clientes.map((cliente) => (
                          <motion.div
                            key={cliente.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            whileHover={{ scale: 1.02 }}
                            onClick={() => navigate(`/clientes/${cliente.id}`)}
                            className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer"
                          >
                            <div className="space-y-3">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <h3 className="font-semibold text-gray-900 text-sm">{cliente.nombre}</h3>
                                  <p className="text-xs text-gray-500 mt-1">Cédula: {cliente.cedula}</p>
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
