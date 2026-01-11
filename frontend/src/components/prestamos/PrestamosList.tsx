import { useState, useEffect } from 'react'
import { Plus, Search, Filter, Edit, Eye, Trash2, DollarSign, Calendar, Lock, Calculator, CheckCircle2, X } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { usePrestamos, useDeletePrestamo, prestamoKeys, type PrestamoFilters } from '@/hooks/usePrestamos'
import { useQueryClient } from '@tanstack/react-query'
import { usePermissions } from '@/hooks/usePermissions'
import { useConcesionariosActivos } from '@/hooks/useConcesionarios'
import { useAnalistasActivos } from '@/hooks/useAnalistas'
import { useModelosVehiculosActivos } from '@/hooks/useModelosVehiculos'
import { CrearPrestamoForm } from './CrearPrestamoForm'
import { PrestamosKPIs } from './PrestamosKPIs'
import { EvaluacionRiesgoForm } from './EvaluacionRiesgoForm'
import { PrestamoDetalleModal } from './PrestamoDetalleModal'
import { FormularioAprobacionCondiciones } from './FormularioAprobacionCondiciones'
import { formatDate } from '@/utils'
import { prestamoService } from '@/services/prestamoService'
import { toast } from 'sonner'

export function PrestamosList() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<PrestamoFilters>({
    search: '',
    estado: undefined,
    cedula: '',
    analista: undefined,
    concesionario: undefined,
    modelo: undefined,
    fecha_inicio: undefined,
    fecha_fin: undefined,
  })
  const [showFilters, setShowFilters] = useState(false)
  const [showCrearPrestamo, setShowCrearPrestamo] = useState(false)
  const [showEvaluacion, setShowEvaluacion] = useState(false)
  const [showDetalle, setShowDetalle] = useState(false)
  const [showAprobacionCondiciones, setShowAprobacionCondiciones] = useState(false)
  const [editingPrestamo, setEditingPrestamo] = useState<any>(null)
  const [evaluacionPrestamo, setEvaluacionPrestamo] = useState<any>(null)
  const [aprobacionPrestamo, setAprobacionPrestamo] = useState<any>(null)
  const [viewingPrestamo, setViewingPrestamo] = useState<any>(null)
  const [deletePrestamoId, setDeletePrestamoId] = useState<number | null>(null)

  const queryClient = useQueryClient()
  const { data, isLoading, error } = usePrestamos(filters, page)
  const deletePrestamo = useDeletePrestamo()
  const { canEditPrestamo, canDeletePrestamo, canApprovePrestamo, canViewEvaluacionRiesgo } = usePermissions()

  // Obtener opciones para los selects
  const { data: concesionarios = [] } = useConcesionariosActivos()
  const { data: analistas = [] } = useAnalistasActivos()
  const { data: modelosVehiculos = [] } = useModelosVehiculosActivos()

  // Función para limpiar filtros
  const handleClearFilters = () => {
    setFilters({
      search: '',
      estado: undefined,
      cedula: '',
      analista: undefined,
      concesionario: undefined,
      modelo: undefined,
      fecha_inicio: undefined,
      fecha_fin: undefined,
    })
    setPage(1)
  }

  // Contar filtros activos
  const activeFiltersCount = [
    filters.search,
    filters.estado,
    filters.cedula,
    filters.analista,
    filters.concesionario,
    filters.modelo,
    filters.fecha_inicio,
    filters.fecha_fin,
  ].filter(Boolean).length

  // Efecto para resetear página cuando cambien los filtros
  useEffect(() => {
    setPage(1)
  }, [
    filters.search,
    filters.estado,
    filters.cedula,
    filters.analista,
    filters.concesionario,
    filters.modelo,
    filters.fecha_inicio,
    filters.fecha_fin,
  ])

  const getEstadoBadge = (estado: string) => {
    const badges = {
      DRAFT: 'bg-gray-100 text-gray-800 border-gray-300',
      EN_REVISION: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      EVALUADO: 'bg-blue-100 text-blue-800 border-blue-300',
      APROBADO: 'bg-green-100 text-green-800 border-green-300',
      RECHAZADO: 'bg-red-100 text-red-800 border-red-300',
    }
    return badges[estado as keyof typeof badges] || badges.DRAFT
  }

  const getEstadoLabel = (estado: string) => {
    const labels: Record<string, string> = {
      DRAFT: 'Borrador',
      EN_REVISION: 'En Revisión',
      EVALUADO: 'Evaluado',
      APROBADO: 'Aprobado',
      RECHAZADO: 'Rechazado',
    }
    return labels[estado] || estado
  }

  const handleEdit = (prestamo: any) => {
    setEditingPrestamo(prestamo)
    setShowCrearPrestamo(true)
  }

  const handleEvaluarRiesgo = (prestamo: any) => {
    setEvaluacionPrestamo(prestamo)
    setShowEvaluacion(true)
  }

  const handleAprobarCredito = (prestamo: any) => {
    setAprobacionPrestamo(prestamo)
    setShowAprobacionCondiciones(true)
  }

  const handleView = (prestamo: any) => {
    setViewingPrestamo(prestamo)
    setShowDetalle(true)
  }

  const handleDelete = async (id: number) => {
    if (window.confirm('¿Está seguro de eliminar este préstamo?')) {
      await deletePrestamo.mutateAsync(id)
    }
  }

  const handleMarcarRevision = async (prestamoId: number, requiereRevision: boolean) => {
    try {
      await prestamoService.marcarRevision(prestamoId, requiereRevision)
      queryClient.invalidateQueries({ queryKey: prestamoKeys.list(filters, page) })
      toast.success(
        requiereRevision
          ? 'Préstamo marcado para revisión. Aparecerá en el reporte de diferencias.'
          : 'Préstamo desmarcado de revisión.'
      )
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al actualizar estado de revisión')
    }
  }

  if (showCrearPrestamo) {
    return (
      <CrearPrestamoForm
        prestamo={editingPrestamo}
        onClose={() => {
          setShowCrearPrestamo(false)
          setEditingPrestamo(null)
        }}
        onSuccess={() => {
          setShowCrearPrestamo(false)
          setEditingPrestamo(null)
        }}
      />
    )
  }

  if (showEvaluacion) {
    return (
      <EvaluacionRiesgoForm
        prestamo={evaluacionPrestamo}
        onClose={() => {
          setShowEvaluacion(false)
          setEvaluacionPrestamo(null)
        }}
        onSuccess={async () => {
          setShowEvaluacion(false)
          setEvaluacionPrestamo(null)
          // Remover cache stale para forzar refetch completo
          queryClient.removeQueries({ queryKey: prestamoKeys.lists() })
          queryClient.removeQueries({ queryKey: prestamoKeys.all })
          // Invalidar todas las queries
          queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
          queryClient.invalidateQueries({ queryKey: prestamoKeys.lists() })
          // Forzar refetch inmediato ignorando staleTime
          await queryClient.refetchQueries({
            queryKey: prestamoKeys.all,
            exact: false,
            type: 'active'
          })
        }}
      />
    )
  }

  if (showAprobacionCondiciones) {
    return (
      <FormularioAprobacionCondiciones
        prestamo={aprobacionPrestamo}
        onClose={() => {
          setShowAprobacionCondiciones(false)
          setAprobacionPrestamo(null)
        }}
        onSuccess={async () => {
          setShowAprobacionCondiciones(false)
          setAprobacionPrestamo(null)
          // Remover cache stale para forzar refetch completo
          queryClient.removeQueries({ queryKey: prestamoKeys.lists() })
          queryClient.removeQueries({ queryKey: prestamoKeys.all })
          // Invalidar todas las queries
          queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
          queryClient.invalidateQueries({ queryKey: prestamoKeys.lists() })
          // Forzar refetch inmediato ignorando staleTime
          await queryClient.refetchQueries({
            queryKey: prestamoKeys.all,
            exact: false,
            type: 'active'
          })
        }}
      />
    )
  }

  if (showDetalle && viewingPrestamo) {
    return (
      <PrestamoDetalleModal
        prestamo={viewingPrestamo}
        onClose={() => {
          setShowDetalle(false)
          setViewingPrestamo(null)
        }}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <PrestamosKPIs />

      {/* Encabezado */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Préstamos</h1>
          <p className="text-gray-600 mt-1">Gestión de préstamos y financiamiento</p>
        </div>
        <Button
          size="lg"
          onClick={() => setShowCrearPrestamo(true)}
          className="px-8 py-6 text-base font-semibold min-w-[200px]"
        >
          <Plus className="w-5 h-5 mr-2" />
          Nuevo Préstamo
        </Button>
      </div>

      {/* Filtros y búsqueda */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-gray-600" />
              <CardTitle>Filtros de Búsqueda</CardTitle>
              {activeFiltersCount > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {activeFiltersCount} {activeFiltersCount === 1 ? 'filtro activo' : 'filtros activos'}
                </Badge>
              )}
            </div>
            <div className="flex gap-2">
              {activeFiltersCount > 0 && (
                <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                  <X className="h-4 w-4 mr-1" />
                  Limpiar
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
              >
                {showFilters ? 'Ocultar' : 'Mostrar'} filtros
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="space-y-4">
            {/* Fila 1: Búsqueda general */}
            <div className="flex gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                  <Input
                    placeholder="Buscar por nombre..."
                    value={filters.search || ''}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    className="pl-10"
                  />
                </div>
              </div>
            </div>

            {/* Filtros expandibles */}
            {showFilters && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 pt-4 border-t">
                {/* Cédula */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Cédula de identidad
                  </label>
                  <Input
                    placeholder="Cédula de identidad"
                    value={filters.cedula || ''}
                    onChange={(e) => setFilters({ ...filters, cedula: e.target.value })}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        setPage(1)
                      }
                    }}
                  />
                </div>

                {/* Estado */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Estado
                  </label>
                  <Select
                    value={filters.estado || 'ALL'}
                    onValueChange={(value) =>
                      setFilters({ ...filters, estado: value === 'ALL' ? undefined : value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Estado" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">Todos los estados</SelectItem>
                      <SelectItem value="DRAFT">🔵 Borrador</SelectItem>
                      <SelectItem value="EN_REVISION">🟡 En Revisión</SelectItem>
                      <SelectItem value="EVALUADO">🔷 Evaluado</SelectItem>
                      <SelectItem value="APROBADO">🟢 Aprobado</SelectItem>
                      <SelectItem value="RECHAZADO">🔴 Rechazado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Fecha Inicio */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Fecha Inicio
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                    <Input
                      type="date"
                      placeholder="dd / mm / aaaa"
                      value={filters.fecha_inicio || ''}
                      onChange={(e) =>
                        setFilters({ ...filters, fecha_inicio: e.target.value || undefined })
                      }
                      className="pl-10"
                    />
                  </div>
                </div>

                {/* Fecha Fin */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Fecha Fin
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                    <Input
                      type="date"
                      placeholder="dd / mm / aaaa"
                      value={filters.fecha_fin || ''}
                      onChange={(e) =>
                        setFilters({ ...filters, fecha_fin: e.target.value || undefined })
                      }
                      className="pl-10"
                    />
                  </div>
                </div>

                {/* Analista */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Analista
                  </label>
                  <Select
                    value={filters.analista || 'ALL'}
                    onValueChange={(value) =>
                      setFilters({ ...filters, analista: value === 'ALL' ? undefined : value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Analista" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">Todos los analistas</SelectItem>
                      {analistas.map((analista) => (
                        <SelectItem key={analista.id} value={analista.nombre}>
                          {analista.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Concesionario */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Concesionario
                  </label>
                  <Select
                    value={filters.concesionario || 'ALL'}
                    onValueChange={(value) =>
                      setFilters({
                        ...filters,
                        concesionario: value === 'ALL' ? undefined : value,
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Concesionario" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">Todos los concesionarios</SelectItem>
                      {concesionarios.map((concesionario) => (
                        <SelectItem key={concesionario.id} value={concesionario.nombre}>
                          {concesionario.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Modelo de Vehículo */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Modelo de Vehículo
                  </label>
                  <Select
                    value={filters.modelo || 'ALL'}
                    onValueChange={(value) =>
                      setFilters({ ...filters, modelo: value === 'ALL' ? undefined : value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Modelo" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">Todos los modelos</SelectItem>
                      {modelosVehiculos.map((modelo) => (
                        <SelectItem key={modelo.id} value={modelo.nombre}>
                          {modelo.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tabla de préstamos */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Préstamos</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <div className="text-center py-8">Cargando...</div>}

          {error && (
            <div className="text-center py-8 text-red-600">
              Error al cargar préstamos
            </div>
          )}

          {!isLoading && !error && data && (
            <>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cliente</TableHead>
                      <TableHead>Cédula</TableHead>
                      <TableHead>Monto</TableHead>
                      <TableHead>Modalidad</TableHead>
                      <TableHead>Cuotas</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead className="text-center">REVISAR</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.data.map((prestamo: any) => (
                      <TableRow key={prestamo.id}>
                        <TableCell>
                          <div className="font-medium">{prestamo.nombres}</div>
                        </TableCell>
                        <TableCell>{prestamo.cedula}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <DollarSign className="h-4 w-4 text-green-600" />
                            <span className="font-semibold">
                              {typeof prestamo.total_financiamiento === 'number'
                                ? prestamo.total_financiamiento.toFixed(2)
                                : '0.00'}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {prestamo.modalidad_pago === 'MENSUAL' ? 'Mensual' :
                           prestamo.modalidad_pago === 'QUINCENAL' ? 'Quincenal' :
                           prestamo.modalidad_pago === 'SEMANAL' ? 'Semanal' :
                           prestamo.modalidad_pago}
                        </TableCell>
                        <TableCell>{prestamo.numero_cuotas}</TableCell>
                        <TableCell>
                          <Badge className={getEstadoBadge(prestamo.estado)}>
                            {getEstadoLabel(prestamo.estado)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm text-gray-600">
                            <Calendar className="h-4 w-4" />
                            {formatDate(prestamo.fecha_registro)}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <input
                            type="checkbox"
                            checked={prestamo.requiere_revision || false}
                            onChange={(e) => handleMarcarRevision(prestamo.id, e.target.checked)}
                            className="h-4 w-4 cursor-pointer"
                            title="Marcar para revisar diferencias de abonos"
                          />
                        </TableCell>
                                    <TableCell className="text-right">
                                      <div className="flex justify-end gap-2">
                                        {/* Botón Ver Detalles */}
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={() => handleView(prestamo)}
                                          title="Ver detalles"
                                        >
                                          <Eye className="h-4 w-4" />
                                        </Button>

                                        {/* Botón Evaluar Riesgo - Solo Admin (DRAFT o EN_REVISION) */}
                                        {canViewEvaluacionRiesgo() && (prestamo.estado === 'DRAFT' || prestamo.estado === 'EN_REVISION') && (
                                          <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleEvaluarRiesgo(prestamo)}
                                            title="Evaluar riesgo del préstamo"
                                            className="hover:bg-blue-50"
                                          >
                                            <Calculator className="h-4 w-4 text-blue-600" />
                                          </Button>
                                        )}

                                        {/* Botón Aprobar Crédito - Solo Admin (EVALUADO) */}
                                        {canViewEvaluacionRiesgo() && prestamo.estado === 'EVALUADO' && (
                                          <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleAprobarCredito(prestamo)}
                                            title="Aprobar crédito con condiciones (genera tabla de amortización)"
                                            className="hover:bg-green-50"
                                          >
                                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                                          </Button>
                                        )}

                            {/* Editar removido por política: no editable */}

                            {/* Botón Eliminar - Solo Admin */}
                            {canDeletePrestamo() ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDelete(prestamo.id)}
                                title="Eliminar préstamo"
                              >
                                <Trash2 className="h-4 w-4 text-red-600" />
                              </Button>
                            ) : null}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Paginación */}
              {data.total_pages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-gray-600">
                    Página {data.page} de {data.total_pages} ({data.total} total)
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                    >
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.min(data.total_pages, page + 1))}
                      disabled={page === data.total_pages}
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
