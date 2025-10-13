import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  Search, 
  Filter, 
  Plus, 
  Eye, 
  Edit, 
  Trash2, 
  Download,
  Upload,
  MoreHorizontal,
  Phone,
  Mail,
  MapPin,
  Car
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { AlertWithIcon } from '@/components/ui/alert'

import { useClientes, useDeleteCliente, useExportClientes } from '@/hooks/useClientes'
import { useDebounce } from '@/hooks/useDebounce'
import { usePermissions } from '@/store/authStore'
import { formatCurrency, formatDate, getMoraStatus } from '@/utils'
import { ClienteFilters } from '@/types'

export function ClientesList() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState<ClienteFilters>({})
  const [currentPage, setCurrentPage] = useState(1)
  const [showFilters, setShowFilters] = useState(false)

  const debouncedSearch = useDebounce(searchTerm, 300)
  const { canViewAllClients, canManageConfig } = usePermissions()

  // Queries
  const {
    data: clientesData,
    isLoading,
    error,
    refetch
  } = useClientes(
    { ...filters, search: debouncedSearch },
    currentPage,
    20
  )

  const deleteClienteMutation = useDeleteCliente()
  const exportClientesMutation = useExportClientes()

  const handleSearch = (value: string) => {
    setSearchTerm(value)
    setCurrentPage(1) // Reset to first page on search
  }

  const handleFilterChange = (newFilters: Partial<ClienteFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }))
    setCurrentPage(1)
  }

  const handleDelete = async (clienteId: string, clienteNombre: string) => {
    if (window.confirm(`¿Está seguro de eliminar al cliente ${clienteNombre}?`)) {
      await deleteClienteMutation.mutateAsync(clienteId)
    }
  }

  const handleExport = async (format: 'excel' | 'pdf' = 'excel') => {
    await exportClientesMutation.mutateAsync({ filters, format })
  }

  const getEstadoBadge = (estado: string) => {
    const variants = {
      ACTIVO: 'success',
      INACTIVO: 'secondary',
      MORA: 'destructive',
      CANCELADO: 'outline'
    } as const

    return (
      <Badge variant={variants[estado as keyof typeof variants] || 'secondary'}>
        {estado}
      </Badge>
    )
  }

  if (error) {
    return (
      <AlertWithIcon
        variant="destructive"
        title="Error al cargar clientes"
        description="No se pudieron cargar los clientes. Intente nuevamente."
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Clientes</h1>
          <p className="text-gray-600">
            {clientesData?.total || 0} clientes registrados
          </p>
        </div>
        
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => handleExport('excel')} variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Exportar Excel
          </Button>
          
          {canManageConfig() && (
            <Button onClick={() => handleExport('pdf')} variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Exportar PDF
            </Button>
          )}
          
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Cliente
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="Buscar por nombre, cédula, teléfono o placa..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                leftIcon={<Search className="w-4 h-4" />}
              />
            </div>
            
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2"
              >
                <Filter className="w-4 h-4" />
                Filtros
              </Button>
              
              {canManageConfig() && (
                <Button variant="outline" size="icon">
                  <Upload className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>

          {/* Advanced Filters */}
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 pt-4 border-t border-gray-200"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Estado
                  </label>
                  <select
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    value={filters.estado || ''}
                    onChange={(e) => handleFilterChange({ estado: e.target.value as any })}
                  >
                    <option value="">Todos</option>
                    <option value="ACTIVO">Activo</option>
                    <option value="INACTIVO">Inactivo</option>
                    <option value="MORA">En Mora</option>
                    <option value="CANCELADO">Cancelado</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fecha Desde
                  </label>
                  <Input
                    type="date"
                    value={filters.fecha_desde || ''}
                    onChange={(e) => handleFilterChange({ fecha_desde: e.target.value })}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fecha Hasta
                  </label>
                  <Input
                    type="date"
                    value={filters.fecha_hasta || ''}
                    onChange={(e) => handleFilterChange({ fecha_hasta: e.target.value })}
                  />
                </div>

                <div className="flex items-end">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setFilters({})
                      setSearchTerm('')
                    }}
                    className="w-full"
                  >
                    Limpiar Filtros
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* Clients Table/Cards */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" text="Cargando clientes..." />
        </div>
      ) : clientesData?.data.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <Search className="w-16 h-16 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No se encontraron clientes
            </h3>
            <p className="text-gray-600 mb-4">
              {searchTerm || Object.keys(filters).length > 0
                ? 'Intente ajustar los filtros de búsqueda'
                : 'Comience agregando su primer cliente'
              }
            </p>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Agregar Cliente
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden lg:block">
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Contacto</TableHead>
                    <TableHead>Vehículo</TableHead>
                    <TableHead>Financiamiento</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Próxima Cuota</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clientesData?.data.map((cliente) => (
                    <TableRow key={cliente.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium text-gray-900">
                            {cliente.nombre} {cliente.apellido}
                          </div>
                          <div className="text-sm text-gray-500">
                            {cliente.cedula}
                          </div>
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <div className="space-y-1">
                          <div className="flex items-center text-sm text-gray-600">
                            <Phone className="w-3 h-3 mr-1" />
                            {cliente.telefono}
                          </div>
                          {cliente.email && (
                            <div className="flex items-center text-sm text-gray-600">
                              <Mail className="w-3 h-3 mr-1" />
                              {cliente.email}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <div className="flex items-center text-sm">
                          <Car className="w-4 h-4 mr-2 text-gray-400" />
                          <div>
                            <div className="font-medium">
                              {cliente.marca_vehiculo} {cliente.modelo_vehiculo}
                            </div>
                            <div className="text-gray-500">
                              {cliente.año_vehiculo} • {cliente.placa_vehiculo}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <div>
                          <div className="font-medium">
                            {formatCurrency(cliente.total_financiamiento)}
                          </div>
                          <div className="text-sm text-gray-500">
                            {cliente.plazo_meses} meses • {cliente.tasa_interes}%
                          </div>
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        {getEstadoBadge(cliente.estado)}
                      </TableCell>
                      
                      <TableCell>
                        <div className="text-sm">
                          {formatDate(cliente.proxima_cuota)}
                        </div>
                      </TableCell>
                      
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="icon">
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="icon">
                            <Edit className="w-4 h-4" />
                          </Button>
                          {canManageConfig() && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(cliente.id, `${cliente.nombre} ${cliente.apellido}`)}
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          </div>

          {/* Mobile Cards */}
          <div className="lg:hidden space-y-4">
            {clientesData?.data.map((cliente) => (
              <motion.div
                key={cliente.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white rounded-lg border border-gray-200 p-4"
              >
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-medium text-gray-900">
                      {cliente.nombre} {cliente.apellido}
                    </h3>
                    <p className="text-sm text-gray-500">{cliente.cedula}</p>
                  </div>
                  {getEstadoBadge(cliente.estado)}
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center text-gray-600">
                    <Phone className="w-4 h-4 mr-2" />
                    {cliente.telefono}
                  </div>
                  
                  <div className="flex items-center text-gray-600">
                    <Car className="w-4 h-4 mr-2" />
                    {cliente.marca_vehiculo} {cliente.modelo_vehiculo} ({cliente.año_vehiculo})
                  </div>
                  
                  <div className="flex justify-between items-center pt-2 border-t border-gray-100">
                    <span className="font-medium">
                      {formatCurrency(cliente.total_financiamiento)}
                    </span>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon">
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Pagination */}
          {clientesData && clientesData.total_pages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-6">
              <Button
                variant="outline"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(currentPage - 1)}
              >
                Anterior
              </Button>
              
              <span className="text-sm text-gray-600">
                Página {currentPage} de {clientesData.total_pages}
              </span>
              
              <Button
                variant="outline"
                disabled={currentPage === clientesData.total_pages}
                onClick={() => setCurrentPage(currentPage + 1)}
              >
                Siguiente
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
