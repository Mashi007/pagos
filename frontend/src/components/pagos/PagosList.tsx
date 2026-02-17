import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CreditCard,
  Filter,
  Plus,
  Calendar,
  AlertCircle,
  Edit,
  Trash2,
  AlertTriangle,
  RefreshCw,
  X,
  ChevronDown,
  FileSpreadsheet,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '../../components/ui/popover'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { formatDate } from '../../utils'
import { pagoService, type Pago } from '../../services/pagoService'
import { RegistrarPagoForm } from './RegistrarPagoForm'
import { ExcelUploader } from './ExcelUploader'
import { CargaMasivaMenu } from './CargaMasivaMenu'
import { PagosListResumen } from './PagosListResumen'
import { PagosKPIsNuevo } from './PagosKPIsNuevo'
import { toast } from 'sonner'

export function PagosList() {
  const [activeTab, setActiveTab] = useState('todos')
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    cedula: '',
    estado: '',
    fechaDesde: '',
    fechaHasta: '',
    analista: '',
  })
  const [showRegistrarPago, setShowRegistrarPago] = useState(false)
  const [showCargaMasivaPagos, setShowCargaMasivaPagos] = useState(false)
  const [agregarPagoOpen, setAgregarPagoOpen] = useState(false)
  const [pagoEditando, setPagoEditando] = useState<Pago | null>(null)
  const queryClient = useQueryClient()

  // Contar filtros activos (mismo criterio que Préstamos)
  const activeFiltersCount = [
    filters.cedula,
    filters.estado,
    filters.fechaDesde,
    filters.fechaHasta,
    filters.analista,
  ].filter(Boolean).length

  const handleClearFilters = () => {
    setFilters({
      cedula: '',
      estado: '',
      fechaDesde: '',
      fechaHasta: '',
      analista: '',
    })
    setPage(1)
  }

  // Query para obtener pagos
  const { data, isLoading, error, isError } = useQuery({
    queryKey: ['pagos', page, perPage, filters],
    queryFn: () => pagoService.getAllPagos(page, perPage, filters),
    staleTime: 0, // Siempre refetch cuando se invalida (mejor para actualización inmediata)
    refetchOnMount: true, // Refetch cuando el componente se monta
    refetchOnWindowFocus: false, // No refetch en focus (evita requests innecesarios)
  })

  const handleFilterChange = (key: string, value: string) => {
    // Convertir "all" a cadena vacía para que el servicio no incluya el filtro
    const filterValue = value === 'all' ? '' : value
    setFilters(prev => ({ ...prev, [key]: filterValue }))
    setPage(1)
  }

  const getEstadoBadge = (estado: string) => {
    const estados: Record<string, { color: string; label: string }> = {
      PAGADO: { color: 'bg-green-500', label: 'Pagado' },
      PENDIENTE: { color: 'bg-yellow-500', label: 'Pendiente' },
      ATRASADO: { color: 'bg-red-500', label: 'Atrasado' },
      PARCIAL: { color: 'bg-blue-500', label: 'Parcial' },
      ADELANTADO: { color: 'bg-purple-500', label: 'Adelantado' },
    }
    const config = estados[estado] || { color: 'bg-gray-500', label: estado }
    return (
      <Badge className={`${config.color} text-white`}>{config.label}</Badge>
    )
  }

  const handleRefresh = async () => {
    try {
      await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['pagos-kpis'], exact: false })
      toast.success('Datos actualizados correctamente')
    } catch (error: unknown) {
      toast.error('Error al actualizar los datos')
    }
  }

  const handleDescargarPagosConErrores = async () => {
    try {
      toast.loading('Generando informe de pagos con errores...', { id: 'descargar-errores' })
      const { blob, filename } = await pagoService.descargarPagosConErrores()

      // Crear URL temporal y descargar
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename

      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      toast.success('Informe descargado correctamente', { id: 'descargar-errores' })
    } catch (error) {
      console.error('Error descargando informe de errores:', error)
      toast.error('Error al descargar el informe de pagos con errores', { id: 'descargar-errores' })
    }
  }

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <PagosKPIsNuevo />

      {/* Acciones: título ya está en PagosPage */}
      <div className="flex justify-end items-center gap-3 flex-wrap">
          <Button
            variant="outline"
            size="lg"
            onClick={handleRefresh}
            className="px-6 py-6 text-base font-semibold"
            disabled={isLoading}
          >
            <RefreshCw className={`w-5 h-5 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <CargaMasivaMenu
            onSuccess={async () => {
              try {
                // Invalidar todas las queries relacionadas con pagos
                await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
                await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false }) // ✓ Invalidar KPIs específicamente
                await queryClient.invalidateQueries({ queryKey: ['kpis'], exact: false })
                await queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false })
                await queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
                await queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
                await queryClient.invalidateQueries({ queryKey: ['pagos-ultimos'], exact: false })
                // Refetch inmediato de KPIs y pagos
                await queryClient.refetchQueries({ queryKey: ['pagos-kpis'], exact: false })
                await queryClient.refetchQueries({ queryKey: ['pagos'], exact: false })
                toast.success('Datos actualizados correctamente')
              } catch (error) {
                console.error('âŒ Error actualizando dashboard:', error)
              }
            }}
          />
          <Popover open={agregarPagoOpen} onOpenChange={setAgregarPagoOpen}>
            <PopoverTrigger asChild>
              <Button
                size="lg"
                className="px-8 py-6 text-base font-semibold min-w-[200px] bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Plus className="w-5 h-5 mr-2" />
                Agregar pago
                <ChevronDown className="w-4 h-4 ml-2" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64 p-2" align="end">
              <div className="space-y-1">
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors text-left"
                  onClick={() => {
                    setShowRegistrarPago(true)
                    setAgregarPagoOpen(false)
                  }}
                >
                  <Edit className="w-5 h-5 text-gray-600" />
                  <span>Registrar un pago</span>
                  <span className="text-xs text-gray-500 ml-auto">Formulario</span>
                </button>
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors text-left"
                  onClick={() => {
                    setShowCargaMasivaPagos(true)
                    setAgregarPagoOpen(false)
                  }}
                >
                  <FileSpreadsheet className="w-5 h-5 text-gray-600" />
                  <span>Carga masiva</span>
                  <span className="text-xs text-gray-500 ml-auto">Excel</span>
                </button>
              </div>
            </PopoverContent>
          </Popover>
          <Button
            variant="outline"
            size="lg"
            onClick={handleDescargarPagosConErrores}
            className="px-6 py-6 text-base font-semibold border-red-500 text-red-600 hover:bg-red-50"
          >
            <AlertTriangle className="w-5 h-5 mr-2" />
            Pagos con Errores
          </Button>
      </div>

      {/* Pestañas: por defecto Resumen por Cliente (detalles por cliente, más reciente a más antiguo) */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="todos">Todos los Pagos</TabsTrigger>
          <TabsTrigger value="resumen">Detalle por Cliente</TabsTrigger>
        </TabsList>

        {/* Tab: Detalle por Cliente (resumen + ver pagos del cliente, más reciente a más antiguo) */}
        <TabsContent value="resumen">
          <PagosListResumen />
        </TabsContent>

        {/* Tab: Todos los Pagos */}
        <TabsContent value="todos">
          {/* Búsqueda por cédula siempre visible */}
          <Card className="mb-4">
            <CardContent className="pt-6">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-700 mb-1 block">Buscar por cédula</label>
                  <Input
                    placeholder="Escriba cédula para filtrar..."
                    value={filters.cedula}
                    onChange={e => {
                      handleFilterChange('cedula', e.target.value)
                    }}
                    className="max-w-md"
                  />
                </div>
                {filters.cedula && (
                  <div className="flex items-end">
                    <Button variant="ghost" size="sm" onClick={() => handleFilterChange('cedula', '')}>
                      <X className="h-4 w-4 mr-1" />
                      Limpiar búsqueda
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Filtros adicionales (expandibles) */}
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
                {showFilters && (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 pt-4 border-t">
                    <div>
                      <label className="text-sm font-medium text-gray-700 mb-1 block">Cédula de identidad</label>
                      <Input
                        placeholder="Cédula"
                        value={filters.cedula}
                        onChange={e => handleFilterChange('cedula', e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 mb-1 block">Estado</label>
                      <Select value={filters.estado || 'all'} onValueChange={value => handleFilterChange('estado', value)}>
                        <SelectTrigger>
                          <SelectValue placeholder="Estado" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Todos</SelectItem>
                          <SelectItem value="PAGADO">Pagado</SelectItem>
                          <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                          <SelectItem value="ATRASADO">Atrasado</SelectItem>
                          <SelectItem value="PARCIAL">Parcial</SelectItem>
                          <SelectItem value="ADELANTADO">Adelantado</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 mb-1 block">Fecha desde</label>
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                        <Input
                          type="date"
                          value={filters.fechaDesde}
                          onChange={e => handleFilterChange('fechaDesde', e.target.value)}
                          className="pl-10"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 mb-1 block">Fecha hasta</label>
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                        <Input
                          type="date"
                          value={filters.fechaHasta}
                          onChange={e => handleFilterChange('fechaHasta', e.target.value)}
                          className="pl-10"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 mb-1 block">Analista</label>
                      <Input
                        placeholder="Analista"
                        value={filters.analista}
                        onChange={e => handleFilterChange('analista', e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Tabla de Pagos */}
          <Card>
            <CardHeader>
              <CardTitle>Lista de Pagos</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <p className="text-gray-500">Cargando pagos...</p>
                </div>
              ) : isError ? (
                <div className="text-center py-12">
                  <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                  <p className="text-red-600 font-semibold mb-2">Error al cargar los pagos</p>
                  <p className="text-gray-600 text-sm">
                    {error instanceof Error ? error.message : 'Error desconocido'}
                  </p>
                  <Button
                    className="mt-4"
                    onClick={() => queryClient.refetchQueries({ queryKey: ['pagos'] })}
                  >
                    Reintentar
                  </Button>
                </div>
              ) : !data?.pagos || data.pagos.length === 0 ? (
                <div className="text-center py-12">
                  <CreditCard className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 font-semibold mb-2">No se encontraron pagos</p>
                  <p className="text-gray-500 text-sm">
                    {data?.total === 0
                      ? 'No hay pagos registrados en el sistema.'
                      : 'No hay pagos que coincidan con los filtros aplicados.'}
                  </p>
                  {(filters.cedula || filters.estado || filters.fechaDesde || filters.fechaHasta || filters.analista) && (
                    <Button className="mt-4" variant="outline" onClick={handleClearFilters}>
                      Limpiar Filtros
                    </Button>
                  )}
                </div>
              ) : (
                <>
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>Cédula</TableHead>
                          <TableHead>Estado</TableHead>
                          <TableHead className="text-center">Cuotas Atrasadas</TableHead>
                          <TableHead>Monto</TableHead>
                          <TableHead>Fecha Pago</TableHead>
                          <TableHead>Nº Documento</TableHead>
                          <TableHead>Institución</TableHead>
                          <TableHead>Conciliado</TableHead>
                          <TableHead>Notas</TableHead>
                          <TableHead className="text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.pagos.map((pago: Pago) => (
                          <TableRow key={pago.id}>
                            <TableCell>{pago.id}</TableCell>
                            <TableCell>{pago.cedula_cliente}</TableCell>
                            <TableCell>{getEstadoBadge(pago.estado)}</TableCell>
                            <TableCell className="text-center">
                              <span className={pago.cuotas_atrasadas && pago.cuotas_atrasadas > 0 ? 'text-red-600 font-semibold' : ''}>
                                {pago.cuotas_atrasadas ?? 0}
                              </span>
                            </TableCell>
                            <TableCell>
                              ${typeof pago.monto_pagado === 'number' ? pago.monto_pagado.toFixed(2) : parseFloat(String(pago.monto_pagado || 0)).toFixed(2)}
                            </TableCell>
                            <TableCell>{formatDate(pago.fecha_pago)}</TableCell>
                            <TableCell>{pago.numero_documento ?? '—'}</TableCell>
                            <TableCell>{pago.institucion_bancaria ?? '—'}</TableCell>
                            <TableCell>
                              {(pago.verificado_concordancia === 'SI' || pago.conciliado) ? (
                                <Badge className="bg-green-500 text-white">SI</Badge>
                              ) : (
                                <Badge className="bg-gray-500 text-white">NO</Badge>
                              )}
                            </TableCell>
                            <TableCell className="max-w-[180px] truncate" title={pago.notas ?? ''}>
                              {pago.notas ?? '—'}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  title="Editar Pago"
                                  onClick={() => {
                                    setPagoEditando(pago)
                                    setShowRegistrarPago(true)
                                  }}
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  title="Eliminar Pago"
                                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                  onClick={async () => {
                                    if (window.confirm(`¿Estás seguro de eliminar el pago ID ${pago.id}?`)) {
                                      try {
                                        await pagoService.deletePago(pago.id)
                                        toast.success('Pago eliminado exitosamente')
                                        queryClient.invalidateQueries({ queryKey: ['pagos'] })
                                      } catch (error) {
                                        toast.error('Error al eliminar el pago')
                                        console.error(error)
                                      }
                                    }
                                  }}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {/* Paginación (mismo formato que Préstamos) */}
                  {data.total_pages > 1 && (
                    <div className="flex items-center justify-between mt-4">
                      <div className="text-sm text-gray-600">
                        Página {data.page} de {data.total_pages} ({data.total} total)
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={page === 1}
                          onClick={() => setPage(p => Math.max(1, p - 1))}
                        >
                          Anterior
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={page >= data.total_pages}
                          onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
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
        </TabsContent>
      </Tabs>

      {/* Registrar/Editar Pago Modal */}
      {showRegistrarPago && (
        <RegistrarPagoForm
          pagoId={pagoEditando?.id}
          pagoInicial={pagoEditando ? {
            cedula_cliente: pagoEditando.cedula_cliente,
            prestamo_id: pagoEditando.prestamo_id,
            fecha_pago: typeof pagoEditando.fecha_pago === 'string'
              ? pagoEditando.fecha_pago.split('T')[0]
              : new Date(pagoEditando.fecha_pago).toISOString().split('T')[0],
            monto_pagado: pagoEditando.monto_pagado,
            numero_documento: pagoEditando.numero_documento,
            institucion_bancaria: pagoEditando.institucion_bancaria,
            notas: pagoEditando.notas || null,
          } : undefined}
          onClose={() => {
            setShowRegistrarPago(false)
            setPagoEditando(null)
          }}
          onSuccess={async () => {
            console.log('ðŸ”„ onSuccess llamado - Iniciando actualización de dashboard...')
            setShowRegistrarPago(false)
            setPagoEditando(null)

            try {
              // Invalidar todas las queries relacionadas con pagos primero
              console.log('ðŸ”€ Invalidando queries de pagos...')
              await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })

              // Invalidar queries de KPIs y dashboard que puedan depender de pagos
              console.log('ðŸ”€ Invalidando queries de KPIs y dashboard...')
              await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false }) // âœ… Invalidar específicamente pagos-kpis
              await queryClient.invalidateQueries({ queryKey: ['kpis'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })

              // Invalidar también la query de últimos pagos (resumen)
              await queryClient.invalidateQueries({ queryKey: ['pagos-ultimos'], exact: false })

              // Refetch inmediato de KPIs para actualización en tiempo real
              await queryClient.refetchQueries({ queryKey: ['pagos-kpis'], exact: false })

              // Refetch de todas las queries relacionadas con pagos (no solo activas)
              // Esto asegura que las queries se actualicen incluso si no están montadas
              console.log('ðŸ” Ejecutando refetch de queries de pagos...')
              const refetchResult = await queryClient.refetchQueries({
                queryKey: ['pagos'],
                exact: false
              })

              // Refetch también de queries activas para actualización inmediata
              const activeRefetchResult = await queryClient.refetchQueries({
                queryKey: ['pagos'],
                exact: false,
                type: 'active'
              })

              console.log('âœ… Refetch completado:', { refetchResult, activeRefetchResult })

              toast.success('Pago registrado exitosamente. El dashboard se ha actualizado.')
            } catch (error) {
              console.error('âŒ Error actualizando dashboard:', error)
              toast.error('Pago registrado, pero hubo un error al actualizar el dashboard')
            }
          }}
        />
      )}

      {/* Carga masiva de pagos (Excel) desde Agregar pago */}
      {showCargaMasivaPagos && (
        <ExcelUploader
          onClose={() => setShowCargaMasivaPagos(false)}
          onSuccess={async () => {
            setShowCargaMasivaPagos(false)
            await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
            await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
            await queryClient.invalidateQueries({ queryKey: ['pagos-ultimos'], exact: false })
            await queryClient.refetchQueries({ queryKey: ['pagos'], exact: false })
            await queryClient.refetchQueries({ queryKey: ['pagos-kpis'], exact: false })
            toast.success('Datos actualizados correctamente')
          }}
        />
      )}

    </div>
  )
}

