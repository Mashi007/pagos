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
  X,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { formatCurrency, formatDate } from '@/utils'
import { useConcesionarios, useCreateConcesionario } from '@/hooks/useConcesionarios'
import { usePrestamos } from '@/hooks/usePrestamos'
import { useClientes } from '@/hooks/useClientes'
import { Concesionario, ConcesionarioCreate } from '@/services/concesionarioService'
import { Prestamo } from '@/types'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useNavigate } from 'react-router-dom'
import { Label } from '@/components/ui/label'

// Estados del embudo de concesionarios
const ESTADOS_EMBUDO = [
  { 
    id: 'activo', 
    label: 'Venta asignada', 
    color: 'bg-green-50 border-green-200', 
    headerColor: 'bg-green-100 text-green-800',
    icon: CheckCircle,
    count: 0
  },
  { 
    id: 'pendiente', 
    label: 'Pendiente requisitos', 
    color: 'bg-yellow-50 border-yellow-200', 
    headerColor: 'bg-yellow-100 text-yellow-800',
    icon: Clock,
    count: 0
  },
  { 
    id: 'inactivo', 
    label: 'Agregar embudo (agregar otro)', 
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
  const [concesionarioSeleccionadoId, setConcesionarioSeleccionadoId] = useState<string>('')
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [searchConcesionario, setSearchConcesionario] = useState('')
  const [concesionariosEnEmbudo, setConcesionariosEnEmbudo] = useState<Map<number, Concesionario>>(new Map())
  const [estadosManuales, setEstadosManuales] = useState<Map<number, string>>(new Map())
  const [nuevoConcesionario, setNuevoConcesionario] = useState<ConcesionarioCreate>({
    nombre: '',
    activo: true
  })
  
  const createConcesionarioMutation = useCreateConcesionario()

  // Obtener concesionarios reales desde configuración/concesionarios
  const { 
    data: concesionariosData, 
    isLoading: isLoadingConcesionarios,
    error: errorConcesionarios,
    refetch: refetchConcesionarios
  } = useConcesionarios({ limit: 1000 })

  // Obtener todos los préstamos para calcular estadísticas
  const { 
    data: prestamosData, 
    isLoading: isLoadingPrestamos,
    error: errorPrestamos
  } = usePrestamos(
    undefined,
    1,
    1000 // Obtener muchos préstamos para análisis
  )

  // Obtener todos los clientes para vincular con préstamos
  const { 
    data: clientesData,
    error: errorClientes
  } = useClientes(undefined, 1, 1000)

  // Extraer concesionarios de la respuesta
  const concesionarios = useMemo(() => {
    if (!concesionariosData) return []
    // El servicio puede devolver items directamente o dentro de una propiedad items
    if (Array.isArray(concesionariosData)) {
      return concesionariosData
    }
    return concesionariosData.items || []
  }, [concesionariosData])

  const prestamos = prestamosData?.data || []
  const clientes = clientesData?.data || []

  // Combinar concesionarios de la API con concesionarios agregados manualmente
  const todosConcesionarios = useMemo(() => {
    const concesionariosAPI = concesionarios.map(concesionario => {
      const concesionarioActualizado = concesionariosEnEmbudo.get(concesionario.id)
      return concesionarioActualizado || concesionario
    })
    
    // Agregar concesionarios que no están en la API pero sí en concesionariosEnEmbudo
    concesionariosEnEmbudo.forEach((concesionario) => {
      if (!concesionariosAPI.find(c => c.id === concesionario.id)) {
        concesionariosAPI.push(concesionario)
      }
    })
    
    return concesionariosAPI
  }, [concesionarios, concesionariosEnEmbudo])

  // Calcular estadísticas por concesionario
  const concesionariosConEstadisticas = useMemo(() => {
    return todosConcesionarios.map(concesionario => {
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
    }).map(concesionario => {
      // Priorizar estado manual si existe
      const estadoManual = estadosManuales.get(concesionario.id)
      if (estadoManual) {
        return { ...concesionario, estado: estadoManual }
      }
      return concesionario
    })
  }, [todosConcesionarios, prestamos, clientes, estadosManuales])

  // Concesionario seleccionado y sus datos
  const concesionarioSeleccionado = concesionarioSeleccionadoId 
    ? Number(concesionarioSeleccionadoId) 
    : null
  const concesionarioDetalle = concesionarioSeleccionado
    ? concesionariosConEstadisticas.find(c => c.id === concesionarioSeleccionado)
    : null

  // Filtrar concesionarios para mostrar solo el seleccionado si hay uno
  const concesionariosParaMostrar = concesionarioSeleccionado
    ? concesionariosConEstadisticas.filter(c => c.id === concesionarioSeleccionado)
    : concesionariosConEstadisticas

  // Filtrar concesionarios (aplicar búsqueda si no hay concesionario seleccionado)
  const concesionariosFiltrados = concesionariosParaMostrar.filter(concesionario => {
    if (concesionarioSeleccionado) {
      // Si hay un concesionario seleccionado, mostrar solo ese
      return true
    }
    const matchSearch =
      concesionario.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      searchTerm === ''
    return matchSearch
  })

  // Búsqueda de concesionarios para agregar
  const concesionariosBuscados = useMemo(() => {
    if (!searchConcesionario || searchConcesionario.length < 2) return []
    return concesionarios.filter(c => 
      c.nombre.toLowerCase().includes(searchConcesionario.toLowerCase()) &&
      !concesionariosEnEmbudo.has(c.id)
    )
  }, [searchConcesionario, concesionarios, concesionariosEnEmbudo])

  const handleAgregarConcesionario = (concesionario: Concesionario) => {
    setConcesionariosEnEmbudo(prev => new Map(prev).set(concesionario.id, concesionario))
    // Asignar automáticamente al embudo "inactivo" (agregar otro)
    setEstadosManuales(prev => {
      const nuevo = new Map(prev)
      nuevo.set(concesionario.id, 'inactivo')
      return nuevo
    })
    setSearchConcesionario('')
    setShowAddDialog(false)
  }

  const handleEliminarConcesionario = (concesionarioId: number) => {
    setConcesionariosEnEmbudo(prev => {
      const nuevo = new Map(prev)
      nuevo.delete(concesionarioId)
      return nuevo
    })
    setEstadosManuales(prev => {
      const nuevo = new Map(prev)
      nuevo.delete(concesionarioId)
      return nuevo
    })
  }

  const handleCrearConcesionario = async () => {
    if (!nuevoConcesionario.nombre.trim()) {
      return
    }
    
    try {
      const creado = await createConcesionarioMutation.mutateAsync(nuevoConcesionario)
      // Agregar el nuevo concesionario al embudo
      setConcesionariosEnEmbudo(prev => new Map(prev).set(creado.id, creado))
      setEstadosManuales(prev => {
        const nuevo = new Map(prev)
        nuevo.set(creado.id, 'inactivo')
        return nuevo
      })
      setNuevoConcesionario({ nombre: '', activo: true })
      setShowCreateDialog(false)
      refetchConcesionarios()
    } catch (error) {
      console.error('Error al crear concesionario:', error)
    }
  }

  // Agrupar concesionarios por estado
  const concesionariosPorEstado = ESTADOS_EMBUDO.map(estado => ({
    ...estado,
    concesionarios: concesionariosFiltrados.filter(c => c.estado === estado.id),
    count: concesionariosFiltrados.filter(c => c.estado === estado.id).length
  }))

  // Estadísticas (generales o del concesionario seleccionado)
  const estadisticas = useMemo(() => {
    const concesionariosParaEstadisticas = concesionarioSeleccionado
      ? concesionariosConEstadisticas.filter(c => c.id === concesionarioSeleccionado)
      : concesionariosConEstadisticas
    
    return {
      total: concesionariosParaEstadisticas.length,
      activos: concesionariosParaEstadisticas.filter(c => c.estado === 'activo').length,
      pendientes: concesionariosParaEstadisticas.filter(c => c.estado === 'pendiente').length,
      inactivos: concesionariosParaEstadisticas.filter(c => c.estado === 'inactivo').length,
      totalClientes: new Set(
        concesionariosParaEstadisticas.flatMap(c => c.prestamos.map(p => p.cliente_id))
      ).size,
      totalPrestamos: concesionariosParaEstadisticas.reduce((sum, c) => sum + c.prestamosActivos, 0),
      montoTotal: concesionariosParaEstadisticas.reduce((sum, c) => sum + c.montoTotal, 0),
    }
  }, [concesionariosConEstadisticas, concesionarioSeleccionado])

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

  // Mostrar errores si existen
  if (errorConcesionarios) {
    return (
      <div className="flex flex-col justify-center items-center min-h-[400px] space-y-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Error al cargar concesionarios</h3>
          <p className="text-sm text-gray-600 mb-4">
            {errorConcesionarios instanceof Error ? errorConcesionarios.message : 'Error desconocido'}
          </p>
          <Button onClick={() => refetchConcesionarios()}>
            Reintentar
          </Button>
        </div>
      </div>
    )
  }

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
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Agregar Existente
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Buscar y Agregar Concesionario</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    placeholder="Buscar por nombre de concesionario..."
                    value={searchConcesionario}
                    onChange={(e) => setSearchConcesionario(e.target.value)}
                    className="pl-10"
                  />
                </div>
                {searchConcesionario.length >= 2 && concesionariosBuscados.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <AlertCircle className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                    <p>No se encontraron concesionarios</p>
                  </div>
                ) : searchConcesionario.length >= 2 && concesionariosBuscados.length > 0 ? (
                  <div className="max-h-96 overflow-y-auto space-y-2">
                    {concesionariosBuscados.map((concesionario) => (
                      <Card
                        key={concesionario.id}
                        className="cursor-pointer hover:bg-gray-50 transition-colors"
                        onClick={() => handleAgregarConcesionario(concesionario)}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <h3 className="font-semibold">{concesionario.nombre}</h3>
                              <p className="text-sm text-gray-500">
                                {concesionario.activo ? 'Activo' : 'Inactivo'}
                              </p>
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
                ) : searchConcesionario.length > 0 && searchConcesionario.length < 2 ? (
                  <div className="text-xs text-gray-400 mt-1 px-1">
                    Escribe al menos 2 caracteres para buscar
                  </div>
                ) : null}
              </div>
            </DialogContent>
          </Dialog>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Crear Nuevo
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Crear Nuevo Concesionario</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="nombre">Nombre del Concesionario *</Label>
                  <Input
                    id="nombre"
                    placeholder="Ej: Concesionario ABC"
                    value={nuevoConcesionario.nombre}
                    onChange={(e) => setNuevoConcesionario({ ...nuevoConcesionario, nombre: e.target.value })}
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="activo"
                    checked={nuevoConcesionario.activo}
                    onChange={(e) => setNuevoConcesionario({ ...nuevoConcesionario, activo: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <Label htmlFor="activo" className="cursor-pointer">
                    Concesionario activo
                  </Label>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => {
                    setShowCreateDialog(false)
                    setNuevoConcesionario({ nombre: '', activo: true })
                  }}>
                    Cancelar
                  </Button>
                  <Button 
                    onClick={handleCrearConcesionario}
                    disabled={!nuevoConcesionario.nombre.trim() || createConcesionarioMutation.isPending}
                  >
                    {createConcesionarioMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Creando...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        Crear
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
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
            <p className="text-xs text-gray-600 mt-1">Venta asignada</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-yellow-600">{estadisticas.pendientes}</div>
            <p className="text-xs text-gray-600 mt-1">Pendiente requisitos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">{estadisticas.inactivos}</div>
            <p className="text-xs text-gray-600 mt-1">Agregar embudo</p>
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

      {/* Filtros y Selector de Concesionario */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="w-full md:w-[300px]">
              <Select
                value={concesionarioSeleccionadoId || 'todos'}
                onValueChange={(value) => {
                  setConcesionarioSeleccionadoId(value === 'todos' ? '' : value)
                  setSearchTerm('') // Limpiar búsqueda al seleccionar
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seleccione un concesionario" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  <SelectItem value="todos">Todos los concesionarios</SelectItem>
                  {concesionarios.map((concesionario) => (
                    <SelectItem key={concesionario.id} value={String(concesionario.id)}>
                      {concesionario.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {!concesionarioSeleccionado && (
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
            )}
          </div>
        </CardContent>
      </Card>

      {/* Mensaje si no hay concesionarios */}
      {concesionarios.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Building className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No hay concesionarios</h3>
              <p className="text-sm text-gray-600 mb-4">
                No se encontraron concesionarios en el sistema. Puedes crear uno nuevo desde la configuración.
              </p>
              <Button onClick={() => navigate('/concesionarios')}>
                <Plus className="h-4 w-4 mr-2" />
                Crear Concesionario
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : !concesionarioSeleccionado ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Building className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Seleccione un concesionario</h3>
              <p className="text-sm text-gray-600 mb-2">
                Haga clic en un concesionario para ver sus clientes y préstamos
              </p>
              <p className="text-xs text-gray-500">
                Seleccione un concesionario para ver sus clientes y préstamos
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
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
                      {columna.id === 'inactivo' ? (
                        <div className="text-center py-8 space-y-3">
                          <Button
                            variant="outline"
                            className="w-full border-2 border-dashed border-gray-300 hover:border-gray-400 hover:bg-gray-50"
                            onClick={() => setShowAddDialog(true)}
                          >
                            <Plus className="h-4 w-4 mr-2" />
                            Agregar Existente
                          </Button>
                          <Button
                            variant="outline"
                            className="w-full border-2 border-dashed border-blue-300 hover:border-blue-400 hover:bg-blue-50"
                            onClick={() => setShowCreateDialog(true)}
                          >
                            <Plus className="h-4 w-4 mr-2" />
                            Crear Nuevo Concesionario
                          </Button>
                          {columna.concesionarios.length > 0 && (
                            <div className="mt-3 space-y-3">
                              {columna.concesionarios.map((concesionario) => (
                                <motion.div
                                  key={concesionario.id}
                                  initial={{ opacity: 0, scale: 0.95 }}
                                  animate={{ opacity: 1, scale: 1 }}
                                  whileHover={{ scale: 1.02 }}
                                  onClick={() => setConcesionarioSeleccionadoId(
                                    concesionarioSeleccionadoId === String(concesionario.id) ? '' : String(concesionario.id)
                                  )}
                                  className={`bg-white rounded-lg p-4 shadow-sm border-2 border-gray-200 hover:border-gray-300 hover:shadow-md transition-all cursor-pointer`}
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
                                            setConcesionarioSeleccionadoId(
                                              concesionarioSeleccionadoId === String(concesionario.id) ? '' : String(concesionario.id)
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
                                        {concesionariosEnEmbudo.has(concesionario.id) && (
                                          <Button 
                                            variant="ghost" 
                                            size="icon" 
                                            className="h-7 w-7 text-red-600 hover:text-red-700"
                                            onClick={(e) => {
                                              e.stopPropagation()
                                              handleEliminarConcesionario(concesionario.id)
                                            }}
                                            title="Remover del embudo"
                                          >
                                            <X className="h-3.5 w-3.5" />
                                          </Button>
                                        )}
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
                              ))}
                            </div>
                          )}
                        </div>
                      ) : columna.concesionarios.length === 0 ? (
                        <div className="text-center py-8 text-gray-400">
                          <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          <p className="text-xs">No hay concesionarios en este estado</p>
                        </div>
                      ) : (
                        columna.concesionarios.map((concesionario) => (
                          <motion.div
                            key={concesionario.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            whileHover={{ scale: 1.02 }}
                            onClick={() => setConcesionarioSeleccionadoId(
                              concesionarioSeleccionadoId === String(concesionario.id) ? '' : String(concesionario.id)
                            )}
                            className={`bg-white rounded-lg p-4 shadow-sm border-2 transition-all cursor-pointer ${
                              concesionarioSeleccionadoId === String(concesionario.id)
                                ? 'border-blue-500 shadow-md'
                                : 'border-gray-200 hover:shadow-md'
                            }`}
                          >
                            <div className="space-y-3">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <h3 className="font-semibold text-gray-900 text-sm">{concesionario.nombre}</h3>
                                  <p className="text-xs text-gray-500 mt-1">
                                    {concesionario.activo ? 'Venta asignada' : 'Inactivo'}
                                  </p>
                                </div>
                                <div className="flex gap-1">
                                  <Button 
                                    variant="ghost" 
                                    size="icon" 
                                    className="h-7 w-7"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setConcesionarioSeleccionadoId(
                                        concesionarioSeleccionadoId === String(concesionario.id) ? '' : String(concesionario.id)
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
                          {[cliente.nombres, cliente.apellidos].filter(Boolean).join(' ') || 'Sin nombre'}
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
      )}
    </div>
  )
}
