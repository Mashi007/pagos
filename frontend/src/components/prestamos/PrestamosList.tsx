import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Plus, Search, Filter, Edit, Eye, Trash2, DollarSign, Calendar, Lock, CheckCircle2, X, RefreshCw, AlertTriangle, Info, FileSpreadsheet, Download, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { usePrestamos, useDeletePrestamo, prestamoKeys, type PrestamoFilters } from '../../hooks/usePrestamos'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { usePermissions } from '../../hooks/usePermissions'
import { useConcesionariosActivos } from '../../hooks/useConcesionarios'
import { useAnalistasActivos } from '../../hooks/useAnalistas'
import { useModelosVehiculosActivos } from '../../hooks/useModelosVehiculos'
import { CrearPrestamoForm } from './CrearPrestamoForm'
import { ExcelUploaderPrestamos } from './ExcelUploaderPrestamos'
import { PrestamosKPIs } from './PrestamosKPIs'
import { PrestamoDetalleModal } from './PrestamoDetalleModal'
import { AprobarPrestamoManualModal } from './AprobarPrestamoManualModal'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog'
import { formatCurrency, formatDate } from '../../utils'
import { prestamoService } from '../../services/prestamoService'
import { toast } from 'sonner'

export function PrestamosList() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  
  // Vista "Revisar préstamos" (enviados desde carga masiva), misma lógica que Clientes/Pagos
  const showRevisarPrestamos = searchParams.get('revisar') === '1'
  // Leer requiere_revision y cliente_id de los parámetros de URL
  const requiereRevisionParam = searchParams.get('requiere_revision')
  const requiereRevision = requiereRevisionParam === 'true' ? true : undefined
  const clienteIdParam = searchParams.get('cliente_id')
  const clienteIdFromUrl = clienteIdParam ? parseInt(clienteIdParam, 10) : undefined
  const clienteIdValid = clienteIdFromUrl && !Number.isNaN(clienteIdFromUrl) ? clienteIdFromUrl : undefined
  const estadoFromUrl = searchParams.get('estado')
  const estadoValidInit = estadoFromUrl && ['DRAFT', 'EN_REVISION', 'EVALUADO', 'APROBADO', 'DESEMBOLSADO', 'RECHAZADO'].includes(estadoFromUrl) ? estadoFromUrl : undefined

  const [filters, setFilters] = useState<PrestamoFilters>({
    search: '',
    estado: estadoValidInit,
    cedula: '',
    cliente_id: clienteIdValid,
    analista: undefined,
    concesionario: undefined,
    modelo: undefined,
    fecha_inicio: undefined,
    fecha_fin: undefined,
    requiere_revision: requiereRevision,
  })

  // Efecto para actualizar filtros cuando cambien los parámetros de URL
  useEffect(() => {
    const reqRev = searchParams.get('requiere_revision') === 'true' ? true : undefined
    const cid = searchParams.get('cliente_id')
    const cidNum = cid ? parseInt(cid, 10) : undefined
    const cidValid = cidNum && !Number.isNaN(cidNum) ? cidNum : undefined
    const estadoParam = searchParams.get('estado')
    const estadoValid = estadoParam && ['DRAFT', 'EN_REVISION', 'EVALUADO', 'APROBADO', 'DESEMBOLSADO', 'RECHAZADO'].includes(estadoParam) ? estadoParam : undefined
    setFilters(prev => ({
      ...prev,
      requiere_revision: reqRev,
      cliente_id: cidValid,
      estado: estadoValid,
    }))
  }, [searchParams])
  const [showFilters, setShowFilters] = useState(false)
  const [showCrearPrestamo, setShowCrearPrestamo] = useState(false)
  const [showExcelUpload, setShowExcelUpload] = useState(false)
  const [showDetalle, setShowDetalle] = useState(false)
  const [showAprobarManual, setShowAprobarManual] = useState(false)
  const [aprobacionManualPrestamo, setAprobacionManualPrestamo] = useState<any>(null)
  const [editingPrestamo, setEditingPrestamo] = useState<any>(null)
  const [viewingPrestamo, setViewingPrestamo] = useState<any>(null)
  const [deletePrestamoId, setDeletePrestamoId] = useState<number | null>(null)
  const [pageRevisar, setPageRevisar] = useState(1)
  const [isExportingRevisar, setIsExportingRevisar] = useState(false)
  const perPageRevisar = 20

  const queryClient = useQueryClient()
  const { data, isLoading, error } = usePrestamos(filters, page, perPage)
  const deletePrestamo = useDeletePrestamo()
  const { canEditPrestamo, canDeletePrestamo, canApprovePrestamo, canViewEvaluacionRiesgo } = usePermissions()

  const { data: concesionarios = [] } = useConcesionariosActivos()
  const { data: analistas = [] } = useAnalistasActivos()
  const { data: modelosVehiculos = [] } = useModelosVehiculosActivos()

  const { data: revisarData, isLoading: revisarLoading, refetch: refetchRevisar } = useQuery({
    queryKey: ['prestamos-con-errores', pageRevisar, perPageRevisar],
    queryFn: () => prestamoService.getPrestamosConErrores(pageRevisar, perPageRevisar),
    enabled: showRevisarPrestamos,
  })

  const handleExportRevisarExcel = async () => {
    if (!revisarData?.items?.length) return
    setIsExportingRevisar(true)
    try {
      const total = revisarData.total
      const perPage = 100
      const pages = Math.ceil(total / perPage) || 1
      const allItems: Array<Record<string, unknown>> = []
      const allIds: number[] = []
      for (let p = 1; p <= pages; p++) {
        const res = await prestamoService.getPrestamosConErrores(p, perPage)
        if (res.items?.length) {
          for (const it of res.items) {
            allIds.push(it.id)
            allItems.push({
              'Fila origen': it.fila_origen ?? '',
              'Cédula cliente': it.cedula_cliente ?? '',
              'Total financiamiento': it.total_financiamiento ?? '',
              'Modalidad pago': it.modalidad_pago ?? '',
              'Nº cuotas': it.numero_cuotas ?? '',
              Producto: it.producto ?? '',
              Analista: it.analista ?? '',
              Concesionario: it.concesionario ?? '',
              Errores: it.errores ?? '',
              Estado: it.estado ?? '',
              'Fecha registro': it.fecha_registro ?? '',
            })
          }
        }
      }
      const { createAndDownloadExcel } = await import('../../types/exceljs')
      const nombre = `Revisar_Prestamos_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(allItems, 'Revisar Préstamos', nombre)
      if (allIds.length > 0) {
        await prestamoService.eliminarPorDescarga(allIds)
        queryClient.invalidateQueries({ queryKey: ['prestamos-con-errores'] })
        refetchRevisar()
      }
      toast.success(`${allItems.length} préstamo(s) exportados y eliminados de la lista`)
    } catch (err) {
      console.error('Error exportando Revisar Préstamos:', err)
      toast.error('Error al exportar. Intenta de nuevo.')
    } finally {
      setIsExportingRevisar(false)
    }
  }

  const handleResolverPrestamoError = async (errorId: number) => {
    try {
      await prestamoService.resolverPrestamoError(errorId)
      queryClient.invalidateQueries({ queryKey: ['prestamos-con-errores'] })
      refetchRevisar()
      toast.success('Marcado como resuelto')
    } catch (e) {
      console.error(e)
      toast.error('Error al marcar como resuelto')
    }
  }

  // Función para limpiar filtros
  const handleClearFilters = () => {
    setFilters({
      search: '',
      estado: undefined,
      cedula: '',
      cliente_id: undefined,
      analista: undefined,
      concesionario: undefined,
      modelo: undefined,
      fecha_inicio: undefined,
      fecha_fin: undefined,
      requiere_revision: undefined,
    })
    // Limpiar también el parámetro de URL
    setSearchParams({})
    setPage(1)
  }

  // Contar filtros activos
  const activeFiltersCount = [
    filters.search,
    filters.estado,
    filters.cedula,
    filters.cliente_id,
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
    filters.cliente_id,
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
      DESEMBOLSADO: 'bg-blue-100 text-blue-800 border-blue-300',
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
      DESEMBOLSADO: 'Desembolsado',
      RECHAZADO: 'Rechazado',
    }
    return labels[estado] || estado
  }

  const handleEdit = (prestamo: any) => {
    setEditingPrestamo(prestamo)
    setShowCrearPrestamo(true)
  }

  const handleAprobarPrestamo = (prestamo: any) => {
    setAprobacionManualPrestamo(prestamo)
    setShowAprobarManual(true)
  }

  const handleView = (prestamo: any) => {
    setViewingPrestamo(prestamo)
    setShowDetalle(true)
  }

  const handleDeleteClick = (id: number) => setDeletePrestamoId(id)
  const handleDeleteConfirm = async () => {
    if (deletePrestamoId == null) return
    await deletePrestamo.mutateAsync(deletePrestamoId)
    setDeletePrestamoId(null)
  }


  // Función para actualizar los datos manualmente
  const handleRefresh = async () => {
    try {
      // Invalidar todas las queries relacionadas con préstamos
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      queryClient.invalidateQueries({ queryKey: prestamoKeys.lists() })
      
      // Forzar refetch inmediato ignorando staleTime
      await queryClient.refetchQueries({
        queryKey: prestamoKeys.all,
        exact: false,
        type: 'active'
      })
      
      toast.success('Datos actualizados correctamente')
    } catch (error: any) {
      toast.error('Error al actualizar los datos')
    }
  }

  if (showExcelUpload) {
    return (
      <ExcelUploaderPrestamos
        onClose={() => {
          setShowExcelUpload(false)
          queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
          queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
        }}
        onSuccess={() => {
          setShowExcelUpload(false)
          queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
          queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
        }}
      />
    )
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
        onAprobarManual={(p) => {
          setShowCrearPrestamo(false)
          setEditingPrestamo(null)
          setAprobacionManualPrestamo(p)
          setShowAprobarManual(true)
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
      <Dialog open={deletePrestamoId !== null} onOpenChange={(open) => !open && setDeletePrestamoId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar préstamo</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">¿Está seguro de eliminar este préstamo? Esta acción no se puede deshacer.</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletePrestamoId(null)}>Cancelar</Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={deletePrestamo.isPending}>
              {deletePrestamo.isPending ? 'Eliminando...' : 'Eliminar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {showAprobarManual && aprobacionManualPrestamo && (
        <AprobarPrestamoManualModal
          prestamo={aprobacionManualPrestamo}
          onClose={() => {
            setShowAprobarManual(false)
            setAprobacionManualPrestamo(null)
          }}
          onSuccess={async () => {
            const prestamoId = aprobacionManualPrestamo?.id
            setShowAprobarManual(false)
            setAprobacionManualPrestamo(null)
            queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
            queryClient.invalidateQueries({ queryKey: prestamoKeys.lists() })
            if (prestamoId != null) {
              queryClient.invalidateQueries({ queryKey: ['cuotas-prestamo', prestamoId] })
            }
            await queryClient.refetchQueries({
              queryKey: prestamoKeys.all,
              exact: false,
              type: 'active'
            })
          }}
        />
      )}

      {/* KPIs primero (mismo orden que Pagos: KPIs → botones) */}
      <PrestamosKPIs
        analista={filters.analista}
        concesionario={filters.concesionario}
        modelo={filters.modelo}
        fecha_inicio={filters.fecha_inicio}
        fecha_fin={filters.fecha_fin}
      />

      {/* Título y botones */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Préstamos</h1>
          <p className="text-gray-600 mt-1">Gestión de préstamos y financiamiento</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            variant="outline"
            size="lg"
            onClick={() => navigate('/revision-manual')}
            className="px-6 py-6 text-base font-semibold bg-green-50 border-green-200 text-green-700 hover:bg-green-100 hover:border-green-300"
          >
            <CheckCircle2 className="w-5 h-5 mr-2" />
            Revisión Manual
          </Button>
          <Button
            variant={showRevisarPrestamos ? 'default' : 'outline'}
            size="lg"
            onClick={() => setSearchParams(showRevisarPrestamos ? {} : { revisar: '1' })}
            className="px-6 py-6 text-base font-semibold"
          >
            <Search className="w-5 h-5 mr-2" />
            Revisar préstamos
          </Button>
          {showRevisarPrestamos && (
            <Button
              variant="outline"
              size="lg"
              onClick={handleExportRevisarExcel}
              disabled={isExportingRevisar || !revisarData?.items?.length}
              className="px-6 py-6 text-base font-semibold"
            >
              {isExportingRevisar ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : <Download className="w-5 h-5 mr-2" />}
              Descargar Excel
            </Button>
          )}
          <div className="relative group">
            <Button
              size="lg"
              className="px-8 py-6 text-base font-semibold min-w-[200px] flex items-center justify-between"
            >
              <span className="flex items-center">
                <Plus className="w-5 h-5 mr-2" />
                Nuevo Préstamo
              </span>
              <span className="ml-2">▼</span>
            </Button>
            {/* Puente invisible para que el hover no se pierda al bajar el cursor al menú */}
            <div className="absolute left-0 right-0 top-full h-2 z-40" aria-hidden="true" />
            {/* Dropdown Menu */}
            <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-lg shadow-xl border border-gray-200 z-50 hidden group-hover:block">
              <button
                onClick={() => setShowCrearPrestamo(true)}
                className="w-full text-left px-4 py-3 hover:bg-blue-50 flex items-center gap-2 text-gray-700 hover:text-blue-600 border-b border-gray-100 first:rounded-t-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Crear préstamo manual
              </button>
              <button
                onClick={() => setShowExcelUpload(true)}
                className="w-full text-left px-4 py-3 hover:bg-blue-50 flex items-center gap-2 text-gray-700 hover:text-blue-600 last:rounded-b-lg transition-colors"
              >
                <FileSpreadsheet className="w-4 h-4" />
                Cargar desde Excel
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Sección Revisar préstamos (enviados desde carga masiva) */}
      {showRevisarPrestamos && (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Search className="w-5 h-5 text-amber-600" />
                  Revisar préstamos
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Préstamos enviados desde la carga masiva para revisión manual. Descarga el Excel para corregir y reimportar.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSearchParams({})}
                  title="Cerrar y volver al listado normal"
                >
                  <X className="w-4 h-4 mr-1" />
                  Cerrar
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportRevisarExcel}
                  disabled={isExportingRevisar || !revisarData?.items?.length}
                  title="Descargar todos los préstamos a revisar en Excel"
                >
                  {isExportingRevisar ? (
                    <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 mr-1" />
                  )}
                  Descargar Excel
                </Button>
              </div>
            </div>
            {revisarLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-amber-600" />
              </div>
            ) : !revisarData?.items?.length ? (
              <p className="text-gray-500 text-center py-6">No hay préstamos pendientes de revisión.</p>
            ) : (
              <>
                <div className="overflow-x-auto rounded border border-gray-200 bg-white">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">Fila</TableHead>
                        <TableHead>Cédula</TableHead>
                        <TableHead>Total</TableHead>
                        <TableHead>Modalidad</TableHead>
                        <TableHead className="w-16">Cuotas</TableHead>
                        <TableHead>Producto</TableHead>
                        <TableHead>Analista</TableHead>
                        <TableHead>Concesionario</TableHead>
                        <TableHead className="max-w-[200px]">Errores</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Fecha</TableHead>
                        <TableHead className="w-28">Acción</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {revisarData.items.map((item: {
                        id: number
                        fila_origen?: number | null
                        cedula_cliente?: string | null
                        total_financiamiento?: string | null
                        modalidad_pago?: string | null
                        numero_cuotas?: number | null
                        producto?: string | null
                        analista?: string | null
                        concesionario?: string | null
                        errores?: string | null
                        estado?: string | null
                        fecha_registro?: string | null
                      }) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-mono text-xs">{item.fila_origen ?? '-'}</TableCell>
                          <TableCell>{item.cedula_cliente ?? '-'}</TableCell>
                          <TableCell>{item.total_financiamiento ?? '-'}</TableCell>
                          <TableCell>{item.modalidad_pago ?? '-'}</TableCell>
                          <TableCell>{item.numero_cuotas ?? '-'}</TableCell>
                          <TableCell>{item.producto ?? '-'}</TableCell>
                          <TableCell>{item.analista ?? '-'}</TableCell>
                          <TableCell>{item.concesionario ?? '-'}</TableCell>
                          <TableCell className="max-w-[200px] truncate text-amber-700" title={item.errores ?? ''}>{item.errores ?? '-'}</TableCell>
                          <TableCell>{item.estado ?? '-'}</TableCell>
                          <TableCell>{item.fecha_registro ? formatDate(item.fecha_registro) : '-'}</TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-green-600 hover:text-green-700"
                              onClick={() => handleResolverPrestamoError(item.id)}
                            >
                              Marcar resuelto
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                {revisarData.total > perPageRevisar && (
                  <div className="flex items-center justify-between mt-3 text-sm text-gray-600">
                    <span>
                      {((pageRevisar - 1) * perPageRevisar) + 1}–{Math.min(pageRevisar * perPageRevisar, revisarData.total)} de {revisarData.total}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={pageRevisar <= 1}
                        onClick={() => setPageRevisar((p) => Math.max(1, p - 1))}
                      >
                        Anterior
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={pageRevisar * perPageRevisar >= revisarData.total}
                        onClick={() => setPageRevisar((p) => p + 1)}
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
      )}

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
          {filters.cliente_id != null && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
              <span className="text-sm text-blue-800">
                Mostrando préstamos del cliente #{filters.cliente_id}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setFilters(prev => ({ ...prev, cliente_id: undefined }))
                  const params = new URLSearchParams(searchParams)
                  params.delete('cliente_id')
                  setSearchParams(params)
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}
          <div className="space-y-4">
            {/* Fila 1: Búsqueda general */}
            <div className="flex gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                  <Input
                    placeholder="Buscar por cédula..."
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
                      <SelectItem value="DRAFT">Borrador</SelectItem>
                      <SelectItem value="EN_REVISION">En Revisión</SelectItem>
                      <SelectItem value="EVALUADO">Evaluado</SelectItem>
                      <SelectItem value="APROBADO">Aprobado</SelectItem>
                      <SelectItem value="DESEMBOLSADO">Desembolsado</SelectItem>
                      <SelectItem value="RECHAZADO">Rechazado</SelectItem>
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
                        <SelectItem key={modelo.id} value={modelo.modelo}>
                          {modelo.modelo}
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
              Error al cargar préstamos: {error instanceof Error ? error.message : 'Error desconocido'}
            </div>
          )}

          {!isLoading && !error && data && (
            <>
              {/* Debug info - remover en producción */}
              {process.env.NODE_ENV === 'development' && (
                <div className="mb-4 p-2 bg-gray-100 text-xs rounded">
                  <strong>Debug:</strong> data existe: {data ? 'Sí' : 'No'}, 
                  data.data existe: {data?.data ? 'Sí' : 'No'}, 
                  es array: {Array.isArray(data?.data) ? 'Sí' : 'No'}, 
                  longitud: {Array.isArray(data?.data) ? data.data.length : 'N/A'},
                  total: {data?.total || 0}
                </div>
              )}
              
              {(!data.data || !Array.isArray(data.data) || data.data.length === 0) ? (
                <div className="text-center py-8 text-gray-500">
                  <div className="mb-4">
                    {data.total > 0 ? (
                      <>
                        <p className="text-lg font-semibold text-red-600 mb-2">
                          Problema detectado: El sistema reporta {data.total} préstamos, pero no se pudieron mostrar.
                        </p>
                        <p className="text-sm mb-4">
                          Esto puede deberse a un problema en la respuesta del servidor o en el formato de los datos.
                        </p>
                        <Button
                          variant="outline"
                          onClick={handleRefresh}
                          className="mt-2"
                        >
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Intentar actualizar nuevamente
                        </Button>
                      </>
                    ) : (
                      <p>No se encontraron préstamos con los filtros seleccionados.</p>
                    )}
                  </div>
                  {process.env.NODE_ENV === 'development' && (
                    <details className="mt-4 text-left max-w-2xl mx-auto">
                      <summary className="cursor-pointer text-sm font-semibold">Detalles técnicos (solo desarrollo)</summary>
                      <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto">
                        {JSON.stringify({ data, isLoading, error: error ? error.message : null }, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ) : (
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
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.data.map((prestamo: any) => (
                      <TableRow key={prestamo.id}>
                        <TableCell>
                          <div className="font-medium">{prestamo.nombres ?? prestamo.nombre_cliente ?? `Cliente #${prestamo.cliente_id ?? '-'}`}</div>
                        </TableCell>
                        <TableCell>{prestamo.cedula ?? prestamo.cedula_cliente ?? '-'}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <DollarSign className="h-4 w-4 text-green-600 shrink-0" />
                            <span className="font-semibold text-green-700">
                              {formatCurrency(Number(prestamo.total_financiamiento ?? 0))}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {prestamo.modalidad_pago === 'MENSUAL' ? 'Mensual' :
                           prestamo.modalidad_pago === 'QUINCENAL' ? 'Quincenal' :
                           prestamo.modalidad_pago === 'SEMANAL' ? 'Semanal' :
                           prestamo.modalidad_pago ?? '—'}
                        </TableCell>
                        <TableCell>{prestamo.numero_cuotas != null ? prestamo.numero_cuotas : '—'}</TableCell>
                        <TableCell>
                          <Badge className={getEstadoBadge(prestamo.estado)}>
                            {getEstadoLabel(prestamo.estado)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm text-gray-600">
                            <Calendar className="h-4 w-4" />
                            {formatDate(prestamo.fecha_registro ?? prestamo.fecha_creacion)}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            {/* ICONO REVISIÓN MANUAL: ⚠ no revisado | ? en revisión | ausencia = ya revisado */}
                            {(prestamo.estado === 'APROBADO' || prestamo.estado === 'DESEMBOLSADO' || prestamo.fecha_aprobacion) &&
                             prestamo.revision_manual_estado !== 'revisado' && (
                              prestamo.revision_manual_estado === 'revisando' ? (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => navigate(`/revision-manual/editar/${prestamo.id}`)}
                                  title="Está siendo revisado - Click para continuar"
                                  className="hover:bg-yellow-50 text-yellow-600"
                                >
                                  <Info className="h-4 w-4" />
                                </Button>
                              ) : (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => navigate(prestamo.revision_manual_estado === 'pendiente' ? '/revision-manual' : `/revision-manual/editar/${prestamo.id}`)}
                                  title="No ha sido revisado - Click para revisar"
                                  className="hover:bg-orange-50 text-orange-600"
                                >
                                  <AlertTriangle className="h-4 w-4" />
                                </Button>
                              )
                            )}

                            {/* Botón Ver Detalles - Visible cuando APROBADO, DESEMBOLSADO o tiene fecha_aprobacion */}
                            {(prestamo.estado === 'APROBADO' || prestamo.estado === 'DESEMBOLSADO' || prestamo.fecha_aprobacion) && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleView(prestamo)}
                                title="Ver detalles"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                            )}

                            {/* Botón Editar - Solo si tiene permisos Y está DESEMBOLSADO o tiene fecha_aprobacion */}
                            {canEditPrestamo(prestamo.estado) && (prestamo.estado === 'DESEMBOLSADO' || prestamo.fecha_aprobacion) && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(prestamo)}
                                title="Editar préstamo"
                                className="hover:bg-blue-50"
                              >
                                <Edit className="h-4 w-4 text-blue-600" />
                              </Button>
                            )}

                            {/* Aprobar préstamo (riesgo manual) - Reemplaza Evaluar riesgo + Aprobar crédito + Asignar fecha */}
                            {canViewEvaluacionRiesgo() && (prestamo.estado === 'DRAFT' || prestamo.estado === 'EN_REVISION') && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleAprobarPrestamo(prestamo)}
                                title="Aprobar préstamo (fecha, datos editables y declaración)"
                                className="hover:bg-green-50"
                              >
                                <CheckCircle2 className="h-4 w-4 text-green-600" />
                              </Button>
                            )}

                            {/* Botón Eliminar - Solo Admin */}
                            {canDeletePrestamo() ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteClick(prestamo.id)}
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
              )}

              {/* Paginación - siempre visible cuando hay datos */}
              {data && data.total > 0 && (
                <div className="flex flex-col gap-4 mt-6 pt-4 border-t">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="text-sm text-gray-600">
                      Mostrando <span className="font-semibold">{(page - 1) * perPage + 1}</span> - <span className="font-semibold">{Math.min(page * perPage, data.total)}</span> de <span className="font-semibold">{data.total}</span> préstamos
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-600">Filas por página:</span>
                      <Select value={String(perPage)} onValueChange={(v) => { setPerPage(Number(v)); setPage(1) }}>
                        <SelectTrigger className="w-[80px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="10">10</SelectItem>
                          <SelectItem value="20">20</SelectItem>
                          <SelectItem value="50">50</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-center gap-1 flex-wrap">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                      className="px-3"
                    >
                      ← Anterior
                    </Button>
                    
                    <div className="flex gap-1">
                      {Array.from({ length: Math.min(5, data.total_pages) }, (_, i) => {
                        const pageNum = data.total_pages <= 5 
                          ? i + 1 
                          : page <= 3 
                            ? i + 1 
                            : page >= data.total_pages - 2 
                              ? data.total_pages - 4 + i 
                              : page - 2 + i
                        
                        return pageNum <= 0 || pageNum > data.total_pages ? null : (
                          <Button
                            key={pageNum}
                            variant={pageNum === page ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setPage(pageNum)}
                            className={`min-w-[40px] px-3 ${pageNum === page ? 'bg-blue-600 text-white' : ''}`}
                          >
                            {pageNum}
                          </Button>
                        )
                      })}
                    </div>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.min(data.total_pages, page + 1))}
                      disabled={page === data.total_pages}
                      className="px-3"
                    >
                      Siguiente →
                    </Button>
                  </div>

                  {data.total_pages > 5 && (
                    <div className="text-center text-xs text-gray-500">
                      Página {page} de {data.total_pages}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
