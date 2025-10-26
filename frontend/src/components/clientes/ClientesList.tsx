import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Search, 
  Filter, 
  Plus, 
  Eye, 
  Edit, 
  Trash2, 
  MoreHorizontal,
  Phone,
  Mail,
  Car,
  User,
  AlertCircle
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { AlertWithIcon } from '@/components/ui/alert'
import { CrearClienteForm } from './CrearClienteForm'
import { ClientesKPIs } from './ClientesKPIs'

import { useDebounce } from '@/hooks/useDebounce'
import { useClientesStats } from '@/hooks/useClientesStats'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency, formatDate } from '@/utils'
import { ClienteFilters } from '@/types'
import { useClientes } from '@/hooks/useClientes'
import { useQueryClient } from '@tanstack/react-query'
import { clienteService } from '@/services/clienteService'

export function ClientesList() {
  // Forzar nuevo build - versión actualizada
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState<ClienteFilters>({})
  const [currentPage, setCurrentPage] = useState(1)
  const [showFilters, setShowFilters] = useState(false)
  const [showCrearCliente, setShowCrearCliente] = useState(false)
  const [clienteSeleccionado, setClienteSeleccionado] = useState<any>(null)
  const [showEditarCliente, setShowEditarCliente] = useState(false)
  const [showEliminarCliente, setShowEliminarCliente] = useState(false)
  const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null)

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 3000) // Auto-hide after 3 seconds
  }

  const debouncedSearch = useDebounce(searchTerm, 300)

  // Funciones para manejar acciones
  const handleVerCliente = (cliente: any) => {
    setClienteSeleccionado(cliente)
    // Aquí podrías abrir un modal o navegar a una página de detalles
    console.log('Ver cliente:', cliente)
  }

  const handleEditarCliente = (cliente: any) => {
    setClienteSeleccionado(cliente)
    setShowEditarCliente(true)
  }

  const handleEliminarCliente = (cliente: any) => {
    setClienteSeleccionado(cliente)
    setShowEliminarCliente(true)
  }

  const confirmarEliminacion = async () => {
    if (!clienteSeleccionado) return
    
    try {
      console.log('🗑️ Eliminando cliente:', clienteSeleccionado.id)
      
      // ✅ ACTIVAR: Llamada real a la API para eliminar
      await clienteService.deleteCliente(clienteSeleccionado.id)
      
      console.log('✅ Cliente eliminado exitosamente')
      
      // Refrescar la lista
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      queryClient.invalidateQueries({ queryKey: ['clientes-stats'] }) // ✅ Actualizar estadísticas
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['kpis'] })
      
      // Cerrar modal
      setShowEliminarCliente(false)
      setClienteSeleccionado(null)
      
      // Mostrar mensaje de éxito - UNA SOLA NOTIFICACIÓN
      showNotification('success', '✅ Cliente eliminado permanentemente de la base de datos')
      
    } catch (error) {
      console.error('❌ Error eliminando cliente:', error)
      showNotification('error', '❌ Error al eliminar el cliente. Intenta nuevamente.')
    }
  }

  const handleSuccess = () => {
    setShowCrearCliente(false)
    setShowEditarCliente(false)
    setClienteSeleccionado(null)
    queryClient.invalidateQueries({ queryKey: ['clientes'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] }) // ✅ Actualizar estadísticas
  }
  const { user } = useSimpleAuth()
  const canViewAllClients = true // Todos pueden ver todos los clientes
  const queryClient = useQueryClient()

  // Queries
  const {
    data: clientesData,
    isLoading,
    error
  } = useClientes(
    { ...filters, search: debouncedSearch },
    currentPage,
    20
  )

  // Estadísticas de clientes
  const {
    data: statsData,
    isLoading: statsLoading
  } = useClientesStats()

  // Datos mockeados para desarrollo
  const mockClientes = [
    {
      id: '1',
      nombre: 'Juan Pérez',
      email: 'juan@example.com',
      telefono: '+1234567890',
      estado: 'ACTIVO',
      saldo_pendiente: 5000,
      fecha_ultimo_pago: '2024-01-15',
       analista_config_id: 1  // Ahora es ID numérico de tabla analistaes
    },
    {
      id: '2',
      nombre: 'María García',
      email: 'maria@example.com',
      telefono: '+1234567891',
      estado: 'MORA',
      saldo_pendiente: 3000,
      fecha_ultimo_pago: '2024-01-10',
       analista_config_id: 2  // Ahora es ID numérico de tabla analistaes
    }
  ]

  const clientes = clientesData?.data || mockClientes
  const totalPages = clientesData?.total_pages || 1

  const handleSearch = (value: string) => {
    setSearchTerm(value)
    setCurrentPage(1)
  }

  const handleFilterChange = (key: keyof ClienteFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setFilters({})
    setSearchTerm('')
    setCurrentPage(1)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <AlertWithIcon
        variant="destructive"
        title="Error al cargar clientes"
        description="No se pudieron cargar los clientes. Por favor, intenta nuevamente."
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-gray-600 mt-1">
            Gestiona tu cartera de clientes
          </p>
        </div>
        
        <div className="flex gap-2">
          <Button size="sm" onClick={() => setShowCrearCliente(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Cliente
          </Button>
        </div>
      </div>

      {/* KPIs de Clientes */}
      {statsData && (
        <ClientesKPIs
          activos={statsData.activos}
          inactivos={statsData.inactivos}
          finalizados={statsData.finalizados}
          total={statsData.total}
          isLoading={statsLoading}
        />
      )}

      {/* Filtros y búsqueda */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Buscar por nombre, email o teléfono..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <Button
              variant="outline"
              onClick={() => setShowFilters(!showFilters)}
              className="sm:w-auto"
            >
              <Filter className="w-4 h-4 mr-2" />
              Filtros
            </Button>
          </div>

          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 pt-4 border-t"
            >
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Estado
                  </label>
                  <select
                    className="w-full p-2 border border-gray-300 rounded-md"
                    value={filters.estado || ''}
                    onChange={(e) => handleFilterChange('estado', e.target.value || undefined)}
                  >
                    <option value="">Todos</option>
                    <option value="ACTIVO">Activo</option>
                    <option value="MORA">Mora</option>
                    <option value="INACTIVO">Inactivo</option>
                  </select>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Asesor
                  </label>
                  <select
                    className="w-full p-2 border border-gray-300 rounded-md"
                     value={filters.analista_config_id || ''}
                     onChange={(e) => handleFilterChange('analista_config_id', e.target.value || undefined)}
                  >
                    <option value="">Todos</option>
                    <option value="analista1">Asesor 1</option>
                    <option value="analista2">Asesor 2</option>
                  </select>
                </div>
                
                <div className="flex items-end">
                  <Button variant="outline" onClick={clearFilters} className="w-full">
                    Limpiar Filtros
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* Tabla de clientes */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Contacto</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Vehículo & Analista</TableHead>
                  <TableHead>Concesionario & Registro</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {clientes.map((cliente: any) => (
                  <TableRow key={cliente.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-gray-900">
                          {cliente.nombres}  {/* ✅ nombres unificados */}
                        </div>
                        <div className="text-sm text-gray-500">
                          Cédula: {cliente.cedula} | ID: {cliente.id}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="flex items-center text-sm text-gray-600">
                          <Mail className="w-3 h-3 mr-2" />
                          {cliente.email}
                        </div>
                        <div className="flex items-center text-sm text-gray-600">
                          <Phone className="w-3 h-3 mr-2" />
                          {cliente.telefono}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant={cliente.estado === 'ACTIVO' ? 'default' : 'destructive'}
                      >
                        {cliente.estado}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="text-sm text-gray-600">
                          <Car className="w-3 h-3 inline mr-1" />
                          {cliente.modelo_vehiculo || 'Sin asignar'}
                        </div>
                        <div className="text-xs text-gray-500">
                          Analista: {cliente.analista || 'Sin asignar'}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="text-sm text-gray-600">
                          {cliente.concesionario || 'Sin asignar'}
                        </div>
                        <div className="text-xs text-gray-500">
                          Registro: {formatDate(cliente.fecha_registro)}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* ✅ BOTÓN EDITAR - ACTIVO */}
                        <Button 
                          variant="outline" 
                          size="sm"
                          title="Editar cliente"
                          className="text-green-600 border-green-300 hover:text-green-700 hover:bg-green-50 hover:border-green-400"
                          onClick={() => handleEditarCliente(cliente)}
                        >
                          <Edit className="w-4 h-4 mr-1" />
                          Editar
                        </Button>
                        
                        {/* ✅ BOTÓN ELIMINAR - ACTIVO */}
                        <Button 
                          variant="outline" 
                          size="sm"
                          title="Eliminar cliente"
                          className="text-red-600 border-red-300 hover:text-red-700 hover:bg-red-50 hover:border-red-400"
                          onClick={() => handleEliminarCliente(cliente)}
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          Eliminar
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Paginación */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Página {currentPage} de {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}

      {/* Modal Crear Cliente */}
      <AnimatePresence>
        {showCrearCliente && (
          <CrearClienteForm 
            onClose={() => setShowCrearCliente(false)}
            onSuccess={() => {
              // ✅ CORRECCIÓN: Invalidar queries para actualizar datos
              queryClient.invalidateQueries({ queryKey: ['clientes'] })
              queryClient.invalidateQueries({ queryKey: ['dashboard'] })
              queryClient.invalidateQueries({ queryKey: ['kpis'] })
            }}
            onClienteCreated={() => {
              // ✅ CORRECCIÓN: Invalidar queries para actualizar datos
              queryClient.invalidateQueries({ queryKey: ['clientes'] })
              queryClient.invalidateQueries({ queryKey: ['dashboard'] })
              queryClient.invalidateQueries({ queryKey: ['kpis'] })
            }}
          />
        )}
      </AnimatePresence>

      {/* Modal Editar Cliente */}
      <AnimatePresence>
        {showEditarCliente && clienteSeleccionado && (
          <CrearClienteForm 
            cliente={clienteSeleccionado}
            onClose={() => {
              setShowEditarCliente(false)
              setClienteSeleccionado(null)
            }}
            onSuccess={handleSuccess}
          />
        )}
      </AnimatePresence>

      {/* Modal Confirmar Eliminación */}
      <AnimatePresence>
        {showEliminarCliente && clienteSeleccionado && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-lg p-6 max-w-md w-full mx-4"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-red-100 rounded-full">
                  <Trash2 className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    Eliminar Cliente
                  </h3>
                  <p className="text-sm text-red-600 font-medium">
                    ⚠️ ELIMINACIÓN PERMANENTE - No se puede deshacer
                  </p>
                </div>
              </div>
              
              <div className="mb-6">
                <p className="text-gray-700">
                  ¿Estás seguro de que quieres <span className="font-semibold text-red-600">ELIMINAR PERMANENTEMENTE</span> al cliente{' '}
                  <span className="font-semibold">
                    {clienteSeleccionado.nombres}
                  </span>?
                </p>
                <p className="text-sm text-red-600 mt-2 font-medium">
                  ⚠️ El cliente será eliminado completamente de la base de datos.
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Cédula: {clienteSeleccionado.cedula}
                </p>
              </div>
              
              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowEliminarCliente(false)
                    setClienteSeleccionado(null)
                  }}
                >
                  Cancelar
                </Button>
                <Button
                  variant="destructive"
                  onClick={confirmarEliminacion}
                >
                  Eliminar
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ✅ NOTIFICACIÓN ÚNICA */}
      {notification && (
        <motion.div
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -50 }}
          className={`fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-md ${
            notification.type === 'success' 
              ? 'bg-green-100 border border-green-300 text-green-800' 
              : 'bg-red-100 border border-red-300 text-red-800'
          }`}
        >
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="font-medium">{notification.message}</span>
            <button
              onClick={() => setNotification(null)}
              className="ml-2 text-gray-500 hover:text-gray-700"
            >
              ×
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}