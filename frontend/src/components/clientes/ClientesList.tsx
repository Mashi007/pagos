import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Filter,
  Plus,
  Edit,
  Trash2,
  Phone,
  Mail,
  Calendar,
  MessageSquare,
  RefreshCw,
  AlertCircle,
  Eye,
  FileSpreadsheet,
  Download,
  Loader2,
  X
} from 'lucide-react'

import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { LoadingSpinner } from '../../components/ui/loading-spinner'
import { AlertWithIcon } from '../../components/ui/alert'
import { CrearClienteForm } from './CrearClienteForm'
import { ClientesKPIs } from './ClientesKPIs'
import { CasosRevisarDialog } from './CasosRevisarDialog'
import { ExcelUploaderUI } from './ExcelUploaderUI'

import { useDebounce } from '../../hooks/useDebounce'
import { useClientesStats } from '../../hooks/useClientesStats'
import { useSimpleAuth } from '../../store/simpleAuthStore'
import { formatDate } from '../../utils'
import { ClienteFilters, PaginatedResponse, Cliente } from '../../types'
import { getErrorDetail } from '../../types/errors'
import { useClientes } from '../../hooks/useClientes'
import { useEstadosCliente } from '../../hooks/useEstadosCliente'
import { useQueryClient } from '@tanstack/react-query'
import { clienteService } from '../../services/clienteService'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

export function ClientesList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const showRevisarClientes = searchParams.get('revisar') === '1'
  const { opciones: opcionesEstado } = useEstadosCliente()
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState<ClienteFilters>({})
  const [currentPage, setCurrentPage] = useState(1)
  const [perPage, setPerPage] = useState(20) // TamaÒo de p·gina configurable
  const [showFilters, setShowFilters] = useState(false)
  const [showCrearCliente, setShowCrearCliente] = useState(false)
  const [showExcelUpload, setShowExcelUpload] = useState(false)
  const [clienteSeleccionado, setClienteSeleccionado] = useState<any>(null)
  const [showEditarCliente, setShowEditarCliente] = useState(false)
  const [showEliminarCliente, setShowEliminarCliente] = useState(false)
  const [showCasosRevisar, setShowCasosRevisar] = useState(false)
  const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null)
  const [pageRevisar, setPageRevisar] = useState(1)
  const [isExportingRevisar, setIsExportingRevisar] = useState(false)
  const perPageRevisar = 20

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 3000) // Auto-hide after 3 seconds
  }

  const debouncedSearch = useDebounce(searchTerm, 300)

  // Funciones para manejar acciones
  const handleEditarCliente = async (cliente: { id: number; [key: string]: unknown }) => {
    try {
      // ‚úÖ Obtener cliente completo desde la API para asegurar todos los campos
      console.log('üìù Obteniendo datos completos del cliente ID:', cliente.id)
      const clienteCompleto = await clienteService.getCliente(String(cliente.id))
      console.log('üìù Cliente completo obtenido:', clienteCompleto)

      setClienteSeleccionado(clienteCompleto)
      setShowEditarCliente(true)
    } catch (error) {
      console.error('‚ùå Error al obtener cliente completo:', error)
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
      console.log('üóëÔ∏è Eliminando cliente:', clienteSeleccionado.id)

      // ‚úÖ ACTIVAR: Llamada real a la API para eliminar
      await clienteService.deleteCliente(String(clienteSeleccionado.id))

      console.log('‚úÖ Cliente eliminado exitosamente')

      // Refrescar la lista
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      queryClient.invalidateQueries({ queryKey: ['clientes-stats'] }) // ‚úÖ Actualizar estadÌsticas
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['kpis'] })

      // Cerrar modal
      setShowEliminarCliente(false)
      setClienteSeleccionado(null)

      // Mostrar mensaje de Èxito - UNA SOLA NOTIFICACI”N
      showNotification('success', '‚úÖ Cliente eliminado permanentemente de la base de datos')

    } catch (error: unknown) {
      console.error('‚ùå Error eliminando cliente:', error)
      const detail = getErrorDetail(error)
      const mensaje = detail || 'Error al eliminar el cliente. Intenta nuevamente.'
      showNotification('error', mensaje)
    }
  }

  const handleSuccess = () => {
    setShowCrearCliente(false)
    setShowEditarCliente(false)
    setClienteSeleccionado(null)
    queryClient.invalidateQueries({ queryKey: ['clientes'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] }) // ‚úÖ Actualizar estadÌsticas
  }
  useSimpleAuth()
  const queryClient = useQueryClient()

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

  const clientesResponse = clientesData as PaginatedResponse<Cliente> | undefined

  const {
    data: statsData,
    isLoading: statsLoading,
    refetch: refetchStats
  } = useClientesStats()

  const { data: revisarData, isLoading: revisarLoading, refetch: refetchRevisar } = useQuery({
    queryKey: ['clientes-con-errores', pageRevisar, perPageRevisar],
    queryFn: () => clienteService.getClientesConErrores(pageRevisar, perPageRevisar),
    enabled: showRevisarClientes,
  })

  const handleExportRevisarExcel = async () => {
    if (!revisarData?.items?.length) return
    setIsExportingRevisar(true)
    try {
      const total = revisarData.total
      const perPage = 100
      const pages = Math.ceil(total / perPage) || 1
      const allItems: Array<Record<string, unknown>> = []
      for (let p = 1; p <= pages; p++) {
        const res = await clienteService.getClientesConErrores(p, perPage)
        if (res.items?.length) allItems.push(...res.items.map((it: any) => ({
          'Fila origen': it.fila_origen ?? '',
          CÈdula: it.cedula ?? '',
          Nombres: it.nombres ?? '',
          Email: it.email ?? '',
          TelÈfono: it.telefono ?? '',
          Errores: it.errores ?? '',
          Estado: it.estado ?? '',
          'Fecha registro': it.fecha_registro ?? '',
        })))
      }
      const { createAndDownloadExcel } = await import('../../types/exceljs')
      const nombre = `Revisar_Clientes_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(allItems, 'Revisar Clientes', nombre)
      
      // Extraer IDs de items para eliminar de la BD tras descarga
      const idsToDelete = revisarData.items.map((item: any) => item.id).filter((id: any) => id)
      if (idsToDelete.length > 0) {
        try {
          await clienteService.eliminarPorDescarga(idsToDelete)
        } catch (err) {
          console.error('Error eliminando clientes tras descarga:', err)
        }
      }
      
      // Invalidar queries y refrescar vista
      queryClient.invalidateQueries({ queryKey: ['clientesConErrores'] })
      refetchRevisar()
      showNotification('success', `${allItems.length} cliente(s) exportados y eliminados`)
    } catch (err) {
      console.error('Error exportando Revisar Clientes:', err)
      showNotification('error', 'Error al exportar. Intenta de nuevo.')
    } finally {
      setIsExportingRevisar(false)
    }
  }

  const mockClientes = [
    {
      id: '1',
      nombre: 'Juan PÈrez',
      email: 'juan@example.com',
      telefono: '+1234567890',
      estado: 'ACTIVO',
      saldo_pendiente: 5000,
      fecha_ultimo_pago: '2024-01-15'
    },
    {
      id: '2',
      nombre: 'MarÌa GarcÌa',
      email: 'maria@example.com',
      telefono: '+1234567891',
      estado: 'MORA',
      saldo_pendiente: 3000,
      fecha_ultimo_pago: '2024-01-10'
    }
  ]

  // ‚úÖ CORRECCI”N: Usar datos reales si existen, sino usar mock solo si no hay respuesta del servidor
  // Si clientesResponse existe (incluso si data es un array vacÌo), usar los datos reales
  const clientes = clientesResponse?.data !== undefined 
    ? (Array.isArray(clientesResponse.data) ? clientesResponse.data : [])
    : mockClientes // Solo usar mock si no hay respuesta del servidor (clientesResponse es undefined)

  const totalPages = clientesResponse?.total_pages || 1
  const total = clientesResponse?.total || 0

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
    setCurrentPage(1) // Resetear a p·gina 1 cuando cambia el tamaÒo
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || isError) {
    const rawDetail = (error as any)?.response?.data?.detail
    const rawMessage = (error as any)?.message
    const errorMessage =
      error instanceof Error
        ? error.message
        : typeof rawDetail === 'string'
          ? rawDetail
          : Array.isArray(rawDetail)
            ? rawDetail.map((d: any) => d?.msg ?? d?.message ?? JSON.stringify(d)).join('. ')
            : rawDetail && typeof rawDetail === 'object'
              ? JSON.stringify(rawDetail)
              : typeof rawMessage === 'string'
                ? rawMessage
                : 'Error desconocido'

    console.error('[ClientesList] Error cargando clientes:', {
      isError,
      errorMessage,
      errorDetails: error
    })

    return (
      <AlertWithIcon
        variant="destructive"
        title="Error al cargar clientes"
        description={`No se pudieron cargar los clientes: ${String(errorMessage)}. Por favor, intenta nuevamente.`}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* KPIs primero (mismo orden que Pagos: KPIs ? botones) */}
      <ClientesKPIs
        activos={statsData?.activos || 0}
        nuevosEsteMes={statsData?.nuevos_este_mes ?? 0}
        finalizados={statsData?.finalizados || 0}
        total={statsData?.total || 0}
        isLoading={statsLoading}
      />

      {/* TÌtulo y botones */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-gray-600 mt-1">
            Gestiona tu cartera de clientes
          </p>
        </div>

        <div className="flex gap-2 flex-wrap">
          <Button
            variant="outline"
            size="lg"
            onClick={async () => {
              await Promise.all([
                refetchClientes(),
                refetchStats()
              ])
              queryClient.invalidateQueries({ queryKey: ['clientes'] })
              queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
            }}
            disabled={isRefetching || isLoading || statsLoading}
            className="px-6 py-6 text-base font-semibold"
            title="Actualizar datos y estadÌsticas"
          >
            <RefreshCw className={`w-5 h-5 mr-2 ${(isRefetching || statsLoading) ? 'animate-spin' : ''}`} />
            {(isRefetching || statsLoading) ? 'Actualizando...' : 'Actualizar'}
          </Button>
          <Button
            variant={showRevisarClientes ? 'default' : 'outline'}
            size="lg"
            onClick={() => setSearchParams(showRevisarClientes ? {} : { revisar: '1' })}
            className="px-6 py-6 text-base font-semibold"
            title="Ver clientes enviados desde carga masiva para revisiÛn manual (descargar Excel)"
          >
            <Search className="w-5 h-5 mr-2" />
            Revisar clientes
          </Button>
          {showRevisarClientes && (
            <Button
              variant="outline"
              size="lg"
              onClick={handleExportRevisarExcel}
              disabled={isExportingRevisar || !revisarData?.items?.length}
              className="px-6 py-6 text-base font-semibold"
              title="Descargar todos los clientes a revisar en Excel"
            >
              {isExportingRevisar ? (
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              ) : (
                <Download className="w-5 h-5 mr-2" />
              )}
              Descargar Excel
            </Button>
          )}
          <Button
            variant="outline"
            size="lg"
            onClick={() => setShowCasosRevisar(true)}
            className="px-6 py-6 text-base font-semibold border-amber-400 text-amber-700 hover:bg-amber-50"
            title="Cargar clientes con valores placeholder (cÈdula, nombres, telÈfono o email a revisar)"
          >
            <AlertCircle className="w-5 h-5 mr-2" />
            Cargar casos a revisar
          </Button>
          <div className="relative group">
            <Button
              size="lg"
              className="px-8 py-6 text-base font-semibold min-w-[200px] flex items-center justify-between"
            >
              <span className="flex items-center">
                <Plus className="w-5 h-5 mr-2" />
                Nuevo Cliente
              </span>
              <span className="ml-2">?</span>
            </Button>
            {/* Puente invisible para que el hover no se pierda al bajar el cursor al men˙ */}
            <div className="absolute left-0 right-0 top-full h-2 z-40" aria-hidden="true" />
            {/* Dropdown Menu */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="absolute right-0 top-full mt-2 w-56 bg-white rounded-lg shadow-xl border border-gray-200 z-50 hidden group-hover:block"
            >
              <motion.button
                onClick={() => setShowCrearCliente(true)}
                className="w-full text-left px-4 py-3 hover:bg-blue-50 flex items-center gap-2 text-gray-700 hover:text-blue-600 border-b border-gray-100 first:rounded-t-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Crear cliente manual
              </motion.button>
              <motion.button
                onClick={() => setShowExcelUpload(true)}
                className="w-full text-left px-4 py-3 hover:bg-blue-50 flex items-center gap-2 text-gray-700 hover:text-blue-600 last:rounded-b-lg transition-colors"
              >
                <FileSpreadsheet className="w-4 h-4" />
                Cargar desde Excel
              </motion.button>
            </motion.div>
          </div>
        </div>
      </div>

      {/* SecciÛn Revisar clientes (enviados desde carga masiva) */}
      {showRevisarClientes && (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Search className="w-5 h-5 text-amber-600" />
                  Revisar clientes
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Clientes enviados desde la carga masiva para revisiÛn manual. Descarga el Excel para corregir y reimportar.
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
                  title="Descargar todos los clientes a revisar en Excel"
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
              <p className="text-gray-500 text-center py-6">No hay clientes pendientes de revisiÛn.</p>
            ) : (
              <>
                <div className="overflow-x-auto rounded border border-gray-200 bg-white">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">Fila</TableHead>
                        <TableHead>CÈdula</TableHead>
                        <TableHead>Nombres</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>TelÈfono</TableHead>
                        <TableHead>Errores</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {revisarData.items.map((item: { id: number; fila_origen?: number; cedula?: string | null; nombres?: string | null; email?: string | null; telefono?: string | null; errores?: string | null }) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-mono text-xs">{item.fila_origen ?? '-'}</TableCell>
                          <TableCell>{item.cedula ?? '-'}</TableCell>
                          <TableCell>{item.nombres ?? '-'}</TableCell>
                          <TableCell>{item.email ?? '-'}</TableCell>
                          <TableCell>{item.telefono ?? '-'}</TableCell>
                          <TableCell className="max-w-xs truncate text-amber-700" title={item.errores ?? ''}>{item.errores ?? '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                {revisarData.total > perPageRevisar && (
                  <div className="flex items-center justify-between mt-3 text-sm text-gray-600">
                    <span>
                      {((pageRevisar - 1) * perPageRevisar) + 1}ñ{Math.min(pageRevisar * perPageRevisar, revisarData.total)} de {revisarData.total}
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

      {/* Filtros y b˙squeda */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Buscar por cÈdula o nombres..."
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
                  Filtros de B˙squeda
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {/* CÈdula de identidad */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      CÈdula de identidad
                    </label>
                    <Input
                      type="text"
                      placeholder="CÈdula de identidad"
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
                      {(opcionesEstado.length > 0 ? opcionesEstado : [
                        { valor: 'ACTIVO', etiqueta: 'Activo', orden: 1 },
                        { valor: 'INACTIVO', etiqueta: 'Inactivo', orden: 2 },
                        { valor: 'FINALIZADO', etiqueta: 'Finalizado', orden: 3 },
                        { valor: 'LEGACY', etiqueta: 'Legacy', orden: 4 },
                      ]).map((opt) => (
                        <option key={opt.valor} value={opt.valor}>{opt.etiqueta}</option>
                      ))}
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

                  {/* TelÈfono */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      TelÈfono
                    </label>
                    <Input
                      type="text"
                      placeholder="TelÈfono"
                      value={filters.telefono || ''}
                      onChange={(e) => handleFilterChange('telefono', e.target.value || undefined)}
                      className="w-full"
                    />
                  </div>

                  {/* OcupaciÛn */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      OcupaciÛn
                    </label>
                    <Input
                      type="text"
                      placeholder="OcupaciÛn"
                      value={filters.ocupacion || ''}
                      onChange={(e) => handleFilterChange('ocupacion', e.target.value || undefined)}
                      className="w-full"
                    />
                  </div>

                  {/* Usuario que registrÛ */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Usuario que registrÛ
                    </label>
                    <Input
                      type="text"
                      placeholder="Usuario que registrÛ"
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

                {/* BotÛn Limpiar Filtros */}
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
                  <TableHead className="font-semibold">Cliente</TableHead>
                  <TableHead className="font-semibold">Contacto</TableHead>
                  <TableHead className="font-semibold">Estado</TableHead>
                  <TableHead className="font-semibold">Fecha ActualizaciÛn</TableHead>
                  <TableHead className="text-right font-semibold">Acciones</TableHead>
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
                      ) : clientesResponse?.total === 0 ? (
                        'No hay clientes que coincidan con los filtros seleccionados'
                      ) : clientesResponse?.total && clientesResponse.total > 0 ? (
                        `Se encontraron ${clientesResponse.total} clientes pero no se pudieron cargar. Verifica la consola para m·s detalles.`
                      ) : (
                        'No se pudieron cargar los clientes. Verifica la consola para m·s detalles.'
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  clientes.map((cliente, index) => (
                  <TableRow key={cliente?.id != null ? String(cliente.id) : `row-${index}`}>
                    <TableCell>
                      <div>
                        <button
                          type="button"
                          onClick={() => navigate(`/clientes/${cliente.id}`)}
                          className="font-medium text-gray-900 hover:text-blue-600 hover:underline text-left"
                        >
                          {typeof cliente.nombres === 'string' || typeof cliente.nombres === 'number' ? cliente.nombres : (cliente as any).nombre ?? ''}
                        </button>
                        <div className="text-sm text-gray-500">
                          CÈdula: {String(cliente.cedula ?? '')} | ID: {String(cliente.id ?? '')}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="flex items-center text-sm text-gray-600">
                          <Mail className="w-3 h-3 mr-2" />
                          {String(cliente.email ?? '')}
                          {cliente.email && (
                            <Link
                              to={`/comunicaciones?cliente_id=${cliente.id}&tipo=email`}
                              className="ml-2 text-green-600 hover:text-green-800 inline-flex"
                              title="Ver comunicaciones de Email"
                            >
                              <MessageSquare className="w-4 h-4" />
                            </Link>
                          )}
                        </div>
                        <div className="flex items-center text-sm text-gray-600">
                          <Phone className="w-3 h-3 mr-2" />
                          {String(cliente.telefono ?? '')}
                          {cliente.telefono && (
                            <Link
                              to={`/comunicaciones?cliente_id=${cliente.id}&tipo=whatsapp`}
                              className="ml-2 text-green-600 hover:text-green-800 inline-flex"
                              title="Ver comunicaciones de WhatsApp"
                            >
                              <MessageSquare className="w-4 h-4" />
                            </Link>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={cliente.estado === 'ACTIVO' ? 'default' : 'destructive'}
                      >
                        {String(cliente.estado ?? '')}
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
                        <Button
                          variant="outline"
                          size="icon"
                          title="Ver detalle"
                          className="text-slate-600 border-slate-400 hover:bg-slate-100 font-medium cursor-pointer transition-colors h-8 w-8"
                          onClick={() => navigate(`/clientes/${cliente.id}`)}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          title="Ver comunicaciones"
                          className="text-blue-600 border-blue-400 bg-blue-50 hover:text-white hover:bg-blue-600 hover:border-blue-600 font-medium cursor-pointer transition-colors h-8 w-8"
                          onClick={() => {
                            navigate(`/comunicaciones?cliente_id=${cliente.id}`)
                          }}
                        >
                          <MessageSquare className="w-4 h-4" />
                        </Button>

                        {/* ‚úÖ BOT”N EDITAR - ACTIVO Y FUNCIONAL */}
                        <Button
                          variant="outline"
                          size="icon"
                          title="Editar cliente"
                          className="text-green-600 border-green-400 bg-green-50 hover:text-white hover:bg-green-600 hover:border-green-600 font-medium cursor-pointer transition-colors h-8 w-8"
                          onClick={() => handleEditarCliente(cliente)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>

                        {/* ‚úÖ BOT”N ELIMINAR - ACTIVO Y FUNCIONAL */}
                        <Button
                          variant="outline"
                          size="icon"
                          title="Eliminar cliente"
                          className="text-red-600 border-red-400 bg-red-50 hover:text-white hover:bg-red-600 hover:border-red-600 font-medium cursor-pointer transition-colors h-8 w-8"
                          onClick={() => {
                            console.log('üî¥ BotÛn Eliminar clickeado para cliente ID:', cliente.id)
                            handleEliminarCliente(cliente)
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
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

      {/* PaginaciÛn */}
      {(totalPages > 1 || clientesResponse?.total) && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-700">
              Mostrando {((currentPage - 1) * perPage) + 1} - {Math.min(currentPage * perPage, clientesResponse?.total || 0)} de {clientesResponse?.total || 0} clientes
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-700 whitespace-nowrap">
                Por p·gina:
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
                P·gina {currentPage} de {totalPages}
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
              // ‚úÖ CORRECCI”N: Invalidar queries para actualizar datos
              queryClient.invalidateQueries({ queryKey: ['clientes'] })
              queryClient.invalidateQueries({ queryKey: ['dashboard'] })
              queryClient.invalidateQueries({ queryKey: ['kpis'] })
            }}
            onClienteCreated={() => {
              // ‚úÖ CORRECCI”N: Invalidar queries para actualizar datos
              queryClient.invalidateQueries({ queryKey: ['clientes'] })
              queryClient.invalidateQueries({ queryKey: ['dashboard'] })
              queryClient.invalidateQueries({ queryKey: ['kpis'] })
            }}
            onOpenEditExisting={async (clienteId: number) => {
              try {
                const clienteCompleto = await clienteService.getCliente(String(clienteId))
                setClienteSeleccionado(clienteCompleto)
                setShowEditarCliente(true)
              } catch {
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

      {/* Modal Casos a Revisar */}
      <CasosRevisarDialog
        open={showCasosRevisar}
        onClose={() => {
          setShowCasosRevisar(false)
          // ? Invalidar cache al cerrar para asegurar que se actualizÛ
          queryClient.invalidateQueries({ queryKey: ['clientes'] })
          queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
        }}
        onSuccess={() => {
          // ? Invalidar cache cuando se guarda exitosamente
          queryClient.invalidateQueries({ queryKey: ['clientes'] })
          queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
          showNotification('success', 'Cliente(s) actualizado(s) correctamente')
        }}
      />

      {/* Modal Confirmar EliminaciÛn */}
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
                    ‚ö Ô∏è ELIMINACI”N PERMANENTE - No se puede deshacer
                  </p>
                </div>
              </div>

              <div className="mb-6">
                <p className="text-gray-700">
                  øEst·s seguro de que quieres <span className="font-semibold text-red-600">ELIMINAR PERMANENTEMENTE</span> al cliente{' '}
                  <span className="font-semibold">
                    {clienteSeleccionado.nombres}
                  </span>?
                </p>
                <p className="text-sm text-red-600 mt-2 font-medium">
                  ‚ö Ô∏è El cliente ser· eliminado completamente de la base de datos.
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  CÈdula: {clienteSeleccionado.cedula}
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

      {/* Modal Carga Excel */}
      <AnimatePresence>
        {showExcelUpload && (
          <ExcelUploaderUI
            onClose={() => setShowExcelUpload(false)}
            onSuccess={() => {
              setShowExcelUpload(false)
              queryClient.invalidateQueries({ queryKey: ['clientes'] })
              queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
              showNotification('success', 'Cliente(s) cargado(s) exitosamente')
            }}
          />
        )}
      </AnimatePresence>

      {/* ‚úÖ NOTIFICACI”N √öNICA */}
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
              √ó
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}


