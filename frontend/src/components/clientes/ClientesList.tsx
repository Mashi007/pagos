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
  User,
  Calendar,
  MessageSquare,
  RefreshCw
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
import { useNavigate } from 'react-router-dom'

export function ClientesList() {
  // Forzar nuevo build - versión actualizada
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState<ClienteFilters>({})
  const [currentPage, setCurrentPage] = useState(1)
  const [perPage, setPerPage] = useState(20) // Tamaño de página configurable
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
  const handleVerCliente = (cliente: { id: number; cedula?: string; nombre?: string; [key: string]: unknown }) => {
    setClienteSeleccionado(cliente)
    // Aquí podrías abrir un modal o navegar a una página de detalles
    console.log('Ver cliente:', cliente)
  }

  const handleEditarCliente = async (cliente: { id: number; [key: string]: unknown }) => {
    try {
      // ✅ Obtener cliente completo desde la API para asegurar todos los campos
      console.log('📝 Obteniendo datos completos del cliente ID:', cliente.id)
      const clienteCompleto = await clienteService.getCliente(String(cliente.id))
      console.log('📝 Cliente completo obtenido:', clienteCompleto)

      setClienteSeleccionado(clienteCompleto)
      setShowEditarCliente(true)
    } catch (error) {
      console.error('❌ Error al obtener cliente completo:', error)
      // Si falla, usar el cliente de la lista como fallback
      setClienteSeleccionado(cliente)
      setShowEditarCliente(true)
    }
  }

  const handleEliminarCliente = (cliente: { id: number; nombre?: string; cedula?: string; [key: string]: unknown }) => {
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
    error,
    isError,
    refetch: refetchClientes,
    isRefetching
  } = useClientes(
    { ...filters, search: debouncedSearch },
    currentPage,
    perPage
  )

  // ✅ DEBUG: Log para diagnosticar problemas
  console.log('🔍 [ClientesList] Estado de la query:', {
    isLoading,
    isError,
    error: error ? {
      message: error instanceof Error ? error.message : String(error),
      ...(error as any)?.response?.data
    } : null,
    clientesData,
    hasData: !!clientesData,
    dataLength: clientesData?.data?.length || 0,
    total: clientesData?.total,
    page: clientesData?.page,
    per_page: clientesData?.per_page,
    total_pages: clientesData?.total_pages
  })

  // Estadísticas de clientes
  const {
    data: statsData,
    isLoading: statsLoading,
    refetch: refetchStats
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
      fecha_ultimo_pago: '2024-01-15'
    },
    {
      id: '2',
      nombre: 'María García',
      email: 'maria@example.com',
      telefono: '+1234567891',
      estado: 'MORA',
      saldo_pendiente: 3000,
      fecha_ultimo_pago: '2024-01-10'
    }
  ]

  // ✅ CORRECCIÓN: Usar datos reales si existen, sino usar mock solo si no hay respuesta del servidor
  // Si clientesData existe (incluso si data es un array vacío), usar los datos reales
  const clientes = clientesData?.data !== undefined 
    ? (Array.isArray(clientesData.data) ? clientesData.data : [])
    : mockClientes // Solo usar mock si no hay respuesta del servidor (clientesData es undefined)
  
  const totalPages = clientesData?.total_pages || 1
  const total = clientesData?.total || 0

  // ✅ DEBUG: Log de datos finales
  console.log('✅ [ClientesList] Datos finales para renderizar:', {
    clientesLength: clientes.length,
    usingMock: clientes === mockClientes,
    totalPages,
    total,
    hasClientesData: !!clientesData,
    clientesDataType: typeof clientesData?.data,
    isArray: Array.isArray(clientesData?.data),
    clientesDataKeys: clientesData ? Object.keys(clientesData) : []
  })

  const handleSearch = (value: string) => {
    setSearchTerm(value)
    setCurrentPage(1)
  }

  const handleFilterChange = (key: keyof ClienteFilters, value: string | number | boolean | null | undefined) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setFilters({})
    setSearchTerm('')
    setCurrentPage(1)
  }

  const handlePerPageChange = (newPerPage: number) => {
    setPerPage(newPerPage)
    setCurrentPage(1) // Resetear a página 1 cuando cambia el tamaño
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || isError) {
    const errorMessage = error instanceof Error 
      ? error.message 
      : (error as any)?.response?.data?.detail 
        || (error as any)?.message 
        || 'Error desconocido'
    
    console.error('❌ [ClientesList] Error cargando clientes:', {
      error,
      errorMessage,
      isError,
      errorDetails: error
    })

    return (
      <AlertWithIcon
        variant="destructive"
        title="Error al cargar clientes"
        description={`No se pudieron cargar los clientes: ${errorMessage}. Por favor, intenta nuevamente.`}
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
          <Button
            variant="outline"
            size="lg"
            onClick={async () => {
              // ✅ Actualizar tanto la lista como las estadísticas
              await Promise.all([
                refetchClientes(),
                refetchStats()
              ])
              // Invalidar queries para asegurar actualización completa
              queryClient.invalidateQueries({ queryKey: ['clientes'] })
              queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
            }}
            disabled={isRefetching || isLoading || statsLoading}
            className="px-6 py-6 text-base font-semibold"
            title="Actualizar datos y estadísticas"
          >
            <RefreshCw className={`w-5 h-5 mr-2 ${(isRefetching || statsLoading) ? 'animate-spin' : ''}`} />
            {(isRefetching || statsLoading) ? 'Actualizando...' : 'Actualizar'}
          </Button>
          <Button
            size="lg"
            onClick={() => setShowCrearCliente(true)}
            className="px-8 py-6 text-base font-semibold min-w-[200px]"
          >
            <Plus className="w-5 h-5 mr-2" />
            Nuevo Cliente
          </Button>
        </div>
      </div>

      {/* KPIs de Clientes */}
      <ClientesKPIs
        activos={statsData?.activos || 0}
        inactivos={statsData?.inactivos || 0}
        finalizados={statsData?.finalizados || 0}
        total={statsData?.total || 0}
        isLoading={statsLoading}
      />

      {/* Filtros y búsqueda */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Buscar por cédula o nombres..."
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
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <Filter className="w-4 h-4" />
                  Filtros de Búsqueda
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {/* Cédula de identidad */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Cédula de identidad
                    </label>
                    <Input
                      type="text"
                      placeholder="Cédula de identidad"
                      value={filters.cedula || ''}
                      onChange={(e) => handleFilterChange('cedula', e.target.value || undefined)}
                      className="w-full"
                    />
                  </div>

                  {/* Estado */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Estado
                    </label>
                    <select
                      className="w-full p-2 border border-gray-300 rounded-md bg-white"
                      value={filters.estado || ''}
                      onChange={(e) => handleFilterChange('estado', e.target.value || undefined)}
                    >
                      <option value="">Todos</option>
                      <option value="ACTIVO">Activo</option>
                      <option value="INACTIVO">Inactivo</option>
                      <option value="FINALIZADO">Finalizado</option>
                    </select>
                  </div>

                  {/* Email */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Email
                    </label>
                    <Input
                      type="email"
                      placeholder="Email"
                      value={filters.email || ''}
                      onChange={(e) => handleFilterChange('email', e.target.value || undefined)}
                      className="w-full"
                    />
                  </div>

                  {/* Teléfono */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Teléfono
                    </label>
                    <Input
                      type="text"
                      placeholder="Teléfono"
                      value={filters.telefono || ''}
                      onChange={(e) => handleFilterChange('telefono', e.target.value || undefined)}
                      className="w-full"
                    />
                  </div>

                  {/* Ocupación */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Ocupación
                    </label>
                    <Input
                      type="text"
                      placeholder="Ocupación"
                      value={filters.ocupacion || ''}
                      onChange={(e) => handleFilterChange('ocupacion', e.target.value || undefined)}
                      className="w-full"
                    />
                  </div>

                  {/* Usuario que registró */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Usuario que registró
                    </label>
                    <Input
                      type="text"
                      placeholder="Usuario que registró"
                      value={filters.usuario_registro || ''}
                      onChange={(e) => handleFilterChange('usuario_registro', e.target.value || undefined)}
                      className="w-full"
                    />
                  </div>

                  {/* Fecha Desde */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Fecha desde
                    </label>
                    <div className="relative">
                      <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                      <Input
                        type="date"
                        placeholder="dd / mm / aaaa"
                        value={filters.fecha_desde || ''}
                        onChange={(e) => {
                          const fecha = e.target.value
                          // Convertir de YYYY-MM-DD a formato para backend
                          handleFilterChange('fecha_desde', fecha || undefined)
                        }}
                        className="pl-10 w-full"
                      />
                    </div>
                  </div>

                  {/* Fecha Hasta */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Fecha hasta
                    </label>
                    <div className="relative">
                      <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                      <Input
                        type="date"
                        placeholder="dd / mm / aaaa"
                        value={filters.fecha_hasta || ''}
                        onChange={(e) => {
                          const fecha = e.target.value
                          handleFilterChange('fecha_hasta', fecha || undefined)
                        }}
                        className="pl-10 w-full"
                      />
                    </div>
                  </div>
                </div>

                {/* Botón Limpiar Filtros */}
                <div className="flex justify-end pt-2">
                  <Button variant="outline" onClick={clearFilters}>
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
                  <TableHead>Fecha Actualización</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {clientes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                      {isLoading ? (
                        <div className="flex items-center justify-center">
                          <LoadingSpinner size="sm" />
                          <span className="ml-2">Cargando clientes...</span>
                        </div>
                      ) : clientesData?.total === 0 ? (
                        'No hay clientes que coincidan con los filtros seleccionados'
                      ) : clientesData?.total && clientesData.total > 0 ? (
                        `Se encontraron ${clientesData.total} clientes pero no se pudieron cargar. Verifica la consola para más detalles.`
                      ) : (
                        'No se pudieron cargar los clientes. Verifica la consola para más detalles.'
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  clientes.map((cliente) => (
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
                          {cliente.email && (
                            <a
                              href={`/comunicaciones?cliente_id=${cliente.id}&tipo=email`}
                              className="ml-2 text-green-600 hover:text-green-800"
                              title="Ver comunicaciones de Email"
                            >
                              <MessageSquare className="w-4 h-4" />
                            </a>
                          )}
                        </div>
                        <div className="flex items-center text-sm text-gray-600">
                          <Phone className="w-3 h-3 mr-2" />
                          {cliente.telefono}
                          {cliente.telefono && (
                            <a
                              href={`/comunicaciones?cliente_id=${cliente.id}&tipo=whatsapp`}
                              className="ml-2 text-green-600 hover:text-green-800"
                              title="Ver comunicaciones de WhatsApp"
                            >
                              <MessageSquare className="w-4 h-4" />
                            </a>
                          )}
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
                      <div className="text-sm text-gray-600">
                        {cliente.fecha_actualizacion
                          ? formatDate(cliente.fecha_actualizacion)
                          : cliente.fecha_registro
                            ? formatDate(cliente.fecha_registro)
                            : 'N/A'}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* ✅ BOTÓN VER COMUNICACIONES */}
                        <Button
                          variant="outline"
                          size="sm"
                          title="Ver comunicaciones"
                          className="text-blue-600 border-blue-400 bg-blue-50 hover:text-white hover:bg-blue-600 hover:border-blue-600 font-medium cursor-pointer transition-colors"
                          onClick={() => {
                            navigate(`/comunicaciones?cliente_id=${cliente.id}`)
                          }}
                        >
                          <MessageSquare className="w-4 h-4 mr-1" />
                          Comunicaciones
                        </Button>

                        {/* ✅ BOTÓN EDITAR - ACTIVO Y FUNCIONAL */}
                        <Button
                          variant="outline"
                          size="sm"
                          title="Editar cliente"
                          className="text-green-600 border-green-400 bg-green-50 hover:text-white hover:bg-green-600 hover:border-green-600 font-medium cursor-pointer transition-colors"
                          onClick={() => {
                            console.log('🟢 Botón Editar clickeado para cliente ID:', cliente.id)
                            handleEditarCliente(cliente)
                          }}
                        >
                          <Edit className="w-4 h-4 mr-1" />
                          Editar
                        </Button>

                        {/* ✅ BOTÓN ELIMINAR - ACTIVO Y FUNCIONAL */}
                        <Button
                          variant="outline"
                          size="sm"
                          title="Eliminar cliente"
                          className="text-red-600 border-red-400 bg-red-50 hover:text-white hover:bg-red-600 hover:border-red-600 font-medium cursor-pointer transition-colors"
                          onClick={() => {
                            console.log('🔴 Botón Eliminar clickeado para cliente ID:', cliente.id)
                            handleEliminarCliente(cliente)
                          }}
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          Eliminar
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Paginación */}
      {(totalPages > 1 || clientesData?.total) && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-700">
              Mostrando {((currentPage - 1) * perPage) + 1} - {Math.min(currentPage * perPage, clientesData?.total || 0)} de {clientesData?.total || 0} clientes
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-700 whitespace-nowrap">
                Por página:
              </label>
              <select
                value={perPage}
                onChange={(e) => handlePerPageChange(Number(e.target.value))}
                className="p-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
                <option value={2000}>2000</option>
                <option value={5000}>5000</option>
              </select>
            </div>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <div className="text-sm text-gray-700 mr-2">
                Página {currentPage} de {totalPages}
              </div>
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
          )}
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
            onOpenEditExisting={async (clienteId: number) => {
              try {
                const clienteCompleto = await clienteService.getCliente(String(clienteId))
                setClienteSeleccionado(clienteCompleto)
                setShowEditarCliente(true)
              } catch (e) {
                // Fallback: abrir con ID solamente
                setClienteSeleccionado({ id: clienteId })
                setShowEditarCliente(true)
              }
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
