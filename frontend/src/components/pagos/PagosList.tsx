import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CreditCard,
  Filter,
  Search,
  Plus,
  Calendar,
  DollarSign,
  AlertCircle,
  Download,
  Upload,
  Edit,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { pagoService, type Pago } from '@/services/pagoService'
import { RegistrarPagoForm } from './RegistrarPagoForm'
import { ExcelUploader } from './ExcelUploader'
import { PagosListResumen } from './PagosListResumen'
import { PagosKPIsNuevo } from './PagosKPIsNuevo'
import { toast } from 'sonner'

export function PagosList() {
  const [activeTab, setActiveTab] = useState('todos')
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [filters, setFilters] = useState({
    cedula: '',
    estado: '',
    fechaDesde: '',
    fechaHasta: '',
    analista: '',
  })
  const [showRegistrarPago, setShowRegistrarPago] = useState(false)
  const [showExcelUploader, setShowExcelUploader] = useState(false)
  const queryClient = useQueryClient()

  // Query para obtener pagos
  const { data, isLoading, error, isError } = useQuery({
    queryKey: ['pagos', page, perPage, filters],
    queryFn: () => pagoService.getAllPagos(page, perPage, filters),
    staleTime: 0, // Siempre refetch cuando se invalida (mejor para actualización inmediata)
    refetchOnMount: true, // Refetch cuando el componente se monta
    refetchOnWindowFocus: false, // No refetch en focus (evita requests innecesarios)
  })

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Módulo de Pagos</h1>
          <p className="text-gray-500 mt-1">Gestión de pagos de clientes</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => setShowExcelUploader(true)}>
            <Upload className="w-5 h-5 mr-2" />
            Cargar Excel
          </Button>
          <Button onClick={() => setShowRegistrarPago(true)}>
            <Plus className="w-5 h-5 mr-2" />
            Registrar Pago
          </Button>
        </div>
      </div>

      {/* KPIs de Pagos */}
      <PagosKPIsNuevo />

      {/* Pestañas */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="todos">Todos los Pagos</TabsTrigger>
          <TabsTrigger value="resumen">Resumen por Cliente</TabsTrigger>
        </TabsList>

        {/* Tab: Todos los Pagos */}
        <TabsContent value="todos">
          {/* Filtros */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Filter className="w-5 h-5" />
                Filtros de Búsqueda
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <Input
                  placeholder="Cédula de identidad"
                  value={filters.cedula}
                  onChange={e => handleFilterChange('cedula', e.target.value)}
                />
                <Select value={filters.estado || undefined} onValueChange={value => handleFilterChange('estado', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Estado" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PAGADO">Pagado</SelectItem>
                    <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                    <SelectItem value="ATRASADO">Atrasado</SelectItem>
                    <SelectItem value="PARCIAL">Parcial</SelectItem>
                    <SelectItem value="ADELANTADO">Adelantado</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  type="date"
                  placeholder="Fecha desde"
                  value={filters.fechaDesde}
                  onChange={e => handleFilterChange('fechaDesde', e.target.value)}
                />
                <Input
                  type="date"
                  placeholder="Fecha hasta"
                  value={filters.fechaHasta}
                  onChange={e => handleFilterChange('fechaHasta', e.target.value)}
                />
                <Input
                  placeholder="Analista"
                  value={filters.analista}
                  onChange={e => handleFilterChange('analista', e.target.value)}
                />
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
                    <Button 
                      className="mt-4" 
                      variant="outline"
                      onClick={() => setFilters({
                        cedula: '',
                        estado: '',
                        fechaDesde: '',
                        fechaHasta: '',
                        analista: '',
                      })}
                    >
                      Limpiar Filtros
                    </Button>
                  )}
                </div>
              ) : (
                <>
                  <div className="mb-4 text-sm text-gray-600">
                    Mostrando {data.pagos.length} de {data.total} pagos (Página {data.page} de {data.total_pages})
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b">
                          <th className="px-4 py-3 text-left">ID</th>
                          <th className="px-4 py-3 text-left">Cédula</th>
                          <th className="px-4 py-3 text-left">ID Crédito</th>
                          <th className="px-4 py-3 text-left">Estado</th>
                          <th className="px-4 py-3 text-left">Cuotas Atrasadas</th>
                          <th className="px-4 py-3 text-left">Monto</th>
                          <th className="px-4 py-3 text-left">Fecha Pago</th>
                          <th className="px-4 py-3 text-left">Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.pagos.map((pago: Pago) => (
                          <tr key={pago.id} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3">{pago.id}</td>
                            <td className="px-4 py-3">{pago.cedula_cliente}</td>
                            <td className="px-4 py-3">{pago.prestamo_id || 'N/A'}</td>
                            <td className="px-4 py-3">{getEstadoBadge(pago.estado)}</td>
                            <td className="px-4 py-3">
                              <span className={pago.cuotas_atrasadas && pago.cuotas_atrasadas > 0 ? 'text-red-600 font-semibold' : ''}>
                                {pago.cuotas_atrasadas ?? 0}
                              </span>
                            </td>
                            <td className="px-4 py-3">${typeof pago.monto_pagado === 'number' ? pago.monto_pagado.toFixed(2) : parseFloat(String(pago.monto_pagado || 0)).toFixed(2)}</td>
                            <td className="px-4 py-3">{new Date(pago.fecha_pago).toLocaleDateString()}</td>
                            <td className="px-4 py-3">
                              <div className="flex gap-2">
                                <Button size="sm" variant="outline" title="Registrar Pago">
                                  <DollarSign className="w-4 h-4" />
                                </Button>
                                <Button size="sm" variant="outline" title="Editar">
                                  <Edit className="w-4 h-4" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {/* Paginación */}
                  {data.total_pages > 1 && (
                    <div className="flex justify-between items-center mt-4">
                      <Button
                        variant="outline"
                        disabled={page === 1}
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                      >
                        Anterior
                      </Button>
                      <span className="text-sm text-gray-600">
                        Página {data.page} de {data.total_pages}
                      </span>
                      <Button
                        variant="outline"
                        disabled={page >= data.total_pages}
                        onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                      >
                        Siguiente
                      </Button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Resumen por Cliente */}
        <TabsContent value="resumen">
          <PagosListResumen />
        </TabsContent>
      </Tabs>

      {/* Registrar Pago Modal */}
      {showRegistrarPago && (
        <RegistrarPagoForm
          onClose={() => setShowRegistrarPago(false)}
          onSuccess={async () => {
            console.log('🔄 onSuccess llamado - Iniciando actualización de dashboard...')
            setShowRegistrarPago(false)
            
            try {
              // Invalidar todas las queries relacionadas con pagos primero
              console.log('🔀 Invalidando queries de pagos...')
              await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
              
              // Invalidar queries de KPIs y dashboard que puedan depender de pagos
              console.log('🔀 Invalidando queries de KPIs y dashboard...')
              await queryClient.invalidateQueries({ queryKey: ['kpis'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false })
              
              // Invalidar también la query de últimos pagos (resumen)
              await queryClient.invalidateQueries({ queryKey: ['pagos-ultimos'], exact: false })
              
              // Refetch de todas las queries relacionadas con pagos (no solo activas)
              // Esto asegura que las queries se actualicen incluso si no están montadas
              console.log('🔁 Ejecutando refetch de queries de pagos...')
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
              
              console.log('✅ Refetch completado:', { refetchResult, activeRefetchResult })
              
              toast.success('Pago registrado exitosamente. El dashboard se ha actualizado.')
            } catch (error) {
              console.error('❌ Error actualizando dashboard:', error)
              toast.error('Pago registrado, pero hubo un error al actualizar el dashboard')
            }
          }}
        />
      )}

      {/* Excel Uploader Modal */}
      {showExcelUploader && (
        <ExcelUploader
          onClose={() => setShowExcelUploader(false)}
          onSuccess={async () => {
            setShowExcelUploader(false)
            try {
              // Invalidar todas las queries relacionadas con pagos
              await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
              // Invalidar queries de KPIs y dashboard
              await queryClient.invalidateQueries({ queryKey: ['kpis'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false })
              
              // Invalidar también la query de últimos pagos (resumen)
              await queryClient.invalidateQueries({ queryKey: ['pagos-ultimos'], exact: false })
              // Refetch de todas las queries relacionadas con pagos
              await queryClient.refetchQueries({ 
                queryKey: ['pagos'],
                exact: false
              })
              // Refetch de queries activas para actualización inmediata
              await queryClient.refetchQueries({ 
                queryKey: ['pagos'],
                exact: false,
                type: 'active'
              })
              toast.success('Pagos cargados exitosamente. El dashboard se ha actualizado.')
            } catch (error) {
              console.error('❌ Error actualizando dashboard después de carga Excel:', error)
              toast.error('Pagos cargados, pero hubo un error al actualizar el dashboard')
            }
          }}
        />
      )}
    </div>
  )
}

