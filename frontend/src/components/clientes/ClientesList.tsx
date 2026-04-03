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
  Eye,
  FileSpreadsheet,
  Download,
  Loader2,
  X,
  Users,
} from 'lucide-react'

import { Button } from '../../components/ui/button'

import { ModulePageHeader } from '../../components/ui/ModulePageHeader'

import { Input } from '../../components/ui/input'

import { Card, CardContent } from '../../components/ui/card'

import { Badge } from '../../components/ui/badge'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'

import { LoadingSpinner } from '../../components/ui/loading-spinner'

import { AlertWithIcon } from '../../components/ui/alert'

import { CrearClienteForm } from './CrearClienteForm'

import { ClientesKPIs } from './ClientesKPIs'

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

  const [perPage, setPerPage] = useState(20) // Tamao de pgina configurable

  const [showFilters, setShowFilters] = useState(false)

  const [showCrearCliente, setShowCrearCliente] = useState(false)

  const [showExcelUpload, setShowExcelUpload] = useState(false)

  const [clienteSeleccionado, setClienteSeleccionado] = useState<any>(null)

  const [showEditarCliente, setShowEditarCliente] = useState(false)

  const [showEliminarCliente, setShowEliminarCliente] = useState(false)

  const [notification, setNotification] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  const [pageRevisar, setPageRevisar] = useState(1)

  const [isExportingRevisar, setIsExportingRevisar] = useState(false)

  const perPageRevisar = 20

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message })

    setTimeout(() => setNotification(null), 3000) // Auto-hide after 3 seconds
  }

  const debouncedSearch = useDebounce(searchTerm, 300)

  // Funciones para manejar acciones

  const handleEditarCliente = async (cliente: {
    id: number
    [key: string]: unknown
  }) => {
    try {
      // ? Obtener cliente completo desde la API para asegurar todos los campos

      console.log('? Obteniendo datos completos del cliente ID:', cliente.id)

      const clienteCompleto = await clienteService.getCliente(
        String(cliente.id)
      )

      console.log('? Cliente completo obtenido:', clienteCompleto)

      setClienteSeleccionado(clienteCompleto)

      setShowEditarCliente(true)
    } catch (error) {
      console.error('? Error al obtener cliente completo:', error)

      // Si falla, usar el cliente de la lista como fallback

      setClienteSeleccionado(cliente)

      setShowEditarCliente(true)
    }
  }

  const handleEliminarCliente = (cliente: {
    id: number
    nombre?: string
    cedula?: string
    [key: string]: unknown
  }) => {
    setClienteSeleccionado(cliente)

    setShowEliminarCliente(true)
  }

  const confirmarEliminacion = async () => {
    if (!clienteSeleccionado) return

    try {
      console.log('? Eliminando cliente:', clienteSeleccionado.id)

      // ? ACTIVAR: Llamada real a la API para eliminar

      await clienteService.deleteCliente(String(clienteSeleccionado.id))

      console.log('? Cliente eliminado exitosamente')

      queryClient.invalidateQueries({ queryKey: ['clientes'] })

      queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

      queryClient.invalidateQueries({ queryKey: ['dashboard'] })

      queryClient.invalidateQueries({ queryKey: ['kpis'] })

      if (typeof refetchStats === 'function') await refetchStats()

      setShowEliminarCliente(false)

      setClienteSeleccionado(null)

      // Mostrar mensaje de xito - UNA SOLA NOTIFICACIN

      showNotification(
        'success',
        '? Cliente eliminado permanentemente de la base de datos'
      )
    } catch (error: unknown) {
      console.error('? Error eliminando cliente:', error)

      const detail = getErrorDetail(error)

      const mensaje =
        detail || 'Error al eliminar el cliente. Intenta nuevamente.'

      showNotification('error', mensaje)
    }
  }

  useSimpleAuth()

  const queryClient = useQueryClient()

  const {
    data: clientesData,

    isLoading,

    error,

    isError,

    refetch: refetchClientes,

    isRefetching,
  } = useClientes(
    { ...filters, search: debouncedSearch },

    currentPage,

    perPage
  )

  const clientesResponse = clientesData as
    | PaginatedResponse<Cliente>
    | undefined

  const {
    data: statsData,

    isLoading: statsLoading,

    refetch: refetchStats,
  } = useClientesStats()

  const handleSuccess = async () => {
    setShowCrearCliente(false)

    setShowEditarCliente(false)

    setClienteSeleccionado(null)

    queryClient.invalidateQueries({ queryKey: ['clientes'] })

    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

    await refetchStats()
  }

  const {
    data: revisarData,
    isLoading: revisarLoading,
    refetch: refetchRevisar,
  } = useQuery({
    queryKey: ['clientes-con-errores', pageRevisar, perPageRevisar],

    queryFn: () =>
      clienteService.getClientesConErrores(pageRevisar, perPageRevisar),

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

      const idsToDelete: number[] = []

      for (let p = 1; p <= pages; p++) {
        const res = await clienteService.getClientesConErrores(p, perPage)

        if (res.items?.length) {
          res.items.forEach((it: any) => {
            if (it.id) idsToDelete.push(it.id)
          })

          allItems.push(
            ...res.items.map((it: any) => ({
              'Fila origen': it.fila_origen ?? '',

              Cédula: it.cedula ?? '',

              Nombres: it.nombres ?? '',

              Email: it.email ?? '',

              Teléfono: it.telefono ?? '',

              Errores: it.errores ?? '',

              Estado: it.estado ?? '',

              'Fecha registro': it.fecha_registro ?? '',
            }))
          )
        }
      }

      const { createAndDownloadExcel } = await import('../../types/exceljs')

      const nombre = `Revisar_Clientes_${new Date().toISOString().slice(0, 10)}.xlsx`

      await createAndDownloadExcel(allItems, 'Revisar Clientes', nombre)

      // Eliminar en BD todos los registros descargados

      if (idsToDelete.length > 0) {
        try {
          await clienteService.eliminarPorDescarga(idsToDelete)
        } catch (err) {
          console.error('Error eliminando clientes tras descarga:', err)
        }
      }

      // Invalidar queries y refrescar vista

      queryClient.invalidateQueries({ queryKey: ['clientes-con-errores'] })

      refetchRevisar()

      showNotification(
        'success',
        `${allItems.length} cliente(s) exportados y eliminados`
      )
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

      nombre: 'Juan Prez',

      email: 'juan@example.com',

      telefono: '+1234567890',

      estado: 'ACTIVO',

      saldo_pendiente: 5000,

      fecha_ultimo_pago: '2024-01-15',
    },

    {
      id: '2',

      nombre: 'Mar\u00EDa Garca',

      email: 'maria@example.com',

      telefono: '+1234567891',

      estado: 'MORA',

      saldo_pendiente: 3000,

      fecha_ultimo_pago: '2024-01-10',
    },
  ]

  // ? CORRECCIN: Usar datos reales si existen, sino usar mock solo si no hay respuesta del servidor

  // Si clientesResponse existe (incluso si data es un array vaco), usar los datos reales

  const clientes =
    clientesResponse?.data !== undefined
      ? Array.isArray(clientesResponse.data)
        ? clientesResponse.data
        : []
      : mockClientes // Solo usar mock si no hay respuesta del servidor (clientesResponse es undefined)

  const totalPages = clientesResponse?.total_pages || 1

  const total = clientesResponse?.total || 0

  const handleSearch = (value: string) => {
    setSearchTerm(value)

    setCurrentPage(1)
  }

  const handleFilterChange = (
    key: keyof ClienteFilters,
    value: string | number | boolean | null | undefined
  ) => {
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

    setCurrentPage(1) // Resetear a pgina 1 cuando cambia el tamao
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
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
            ? rawDetail
                .map((d: any) => d?.msg ?? d?.message ?? JSON.stringify(d))
                .join('. ')
            : rawDetail && typeof rawDetail === 'object'
              ? JSON.stringify(rawDetail)
              : typeof rawMessage === 'string'
                ? rawMessage
                : 'Error desconocido'

    console.error('[ClientesList] Error cargando clientes:', {
      isError,

      errorMessage,

      errorDetails: error,
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
      {/* Titulo primero, luego KPIs */}

      <ModulePageHeader
        icon={Users}
        title="Clientes"
        description="Gestiona tu cartera de clientes"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="lg"
              onClick={async () => {
                await Promise.all([refetchClientes(), refetchStats()])

                queryClient.invalidateQueries({ queryKey: ['clientes'] })

                queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
              }}
              disabled={isRefetching || isLoading || statsLoading}
              className="px-6 py-6 text-base font-semibold"
              title="Actualizar datos y estadísticas"
            >
              <RefreshCw
                className={`mr-2 h-5 w-5 ${isRefetching || statsLoading ? 'animate-spin' : ''}`}
              />

              {isRefetching || statsLoading ? 'Actualizando...' : 'Actualizar'}
            </Button>

            <Button
              variant={showRevisarClientes ? 'default' : 'outline'}
              size="lg"
              onClick={() =>
                setSearchParams(showRevisarClientes ? {} : { revisar: '1' })
              }
              className="px-6 py-6 text-base font-semibold"
              title="Ver clientes enviados desde carga másiva para revisión manual (descargar Excel)"
            >
              <Search className="mr-2 h-5 w-5" />
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
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <Download className="mr-2 h-5 w-5" />
                )}
                Descargar Excel
              </Button>
            )}

            <div className="group relative">
              <Button
                size="lg"
                className="flex min-w-[200px] items-center justify-between px-8 py-6 text-base font-semibold"
              >
                <span className="flex items-center">
                  <Plus className="mr-2 h-5 w-5" />
                  Nuevo Cliente
                </span>
              </Button>

              {/* Puente invisible para que el hover no se pierda al bajar el cursor al men */}

              <div
                className="absolute left-0 right-0 top-full z-40 h-2"
                aria-hidden="true"
              />

              {/* Dropdown Menu */}

              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="absolute right-0 top-full z-50 mt-2 hidden w-56 rounded-lg border border-gray-200 bg-white shadow-xl group-hover:block"
              >
                <motion.button
                  onClick={() => setShowCrearCliente(true)}
                  className="flex w-full items-center gap-2 border-b border-gray-100 px-4 py-3 text-left text-gray-700 transition-colors first:rounded-t-lg hover:bg-blue-50 hover:text-blue-600"
                >
                  <Plus className="h-4 w-4" />
                  Crear cliente manual
                </motion.button>

                <motion.button
                  onClick={() => setShowExcelUpload(true)}
                  className="flex w-full items-center gap-2 px-4 py-3 text-left text-gray-700 transition-colors last:rounded-b-lg hover:bg-blue-50 hover:text-blue-600"
                >
                  <FileSpreadsheet className="h-4 w-4" />
                  Cargar desde Excel
                </motion.button>
              </motion.div>
            </div>
          </div>
        }
      />

      <ClientesKPIs
        activos={statsData?.activos || 0}
        nuevosEsteMes={statsData?.nuevos_este_mes ?? 0}
        finalizados={statsData?.finalizados || 0}
        total={statsData?.total || 0}
        ultimaActualizacion={statsData?.ultima_actualizacion ?? null}
        isLoading={statsLoading}
      />

      {/* Seccin Revisar clientes (enviados desde carga másiva) */}

      {showRevisarClientes && (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
                  <Search className="h-5 w-5 text-amber-600" />
                  Revisar clientes
                </h2>

                <p className="mt-1 text-sm text-gray-600">
                  Clientes enviados desde la carga másiva para revisión manual.
                  Descarga el Excel para corregir y reimportar.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSearchParams({})}
                  title="Cerrar y volver al listado normal"
                >
                  <X className="mr-1 h-4 w-4" />
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
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="mr-1 h-4 w-4" />
                  )}
                  Descargar Excel
                </Button>
              </div>
            </div>

            {revisarLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-amber-600" />
              </div>
            ) : !revisarData?.items?.length ? (
              <p className="py-6 text-center text-gray-500">
                No hay clientes pendientes de revisión.
              </p>
            ) : (
              <>
                <div className="overflow-x-auto rounded border border-gray-200 bg-white">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">Fila</TableHead>

                        <TableHead>Cédula</TableHead>

                        <TableHead>Nombres</TableHead>

                        <TableHead>Email</TableHead>

                        <TableHead>Teléfono</TableHead>

                        <TableHead>Errores</TableHead>
                      </TableRow>
                    </TableHeader>

                    <TableBody>
                      {revisarData.items.map(
                        (item: {
                          id: number
                          fila_origen?: number
                          cedula?: string | null
                          nombres?: string | null
                          email?: string | null
                          telefono?: string | null
                          errores?: string | null
                        }) => (
                          <TableRow key={item.id}>
                            <TableCell className="font-mono text-xs">
                              {item.fila_origen ?? '-'}
                            </TableCell>

                            <TableCell>{item.cedula ?? '-'}</TableCell>

                            <TableCell>{item.nombres ?? '-'}</TableCell>

                            <TableCell>{item.email ?? '-'}</TableCell>

                            <TableCell>{item.telefono ?? '-'}</TableCell>

                            <TableCell
                              className="max-w-xs truncate text-amber-700"
                              title={item.errores ?? ''}
                            >
                              {item.errores ?? '-'}
                            </TableCell>
                          </TableRow>
                        )
                      )}
                    </TableBody>
                  </Table>
                </div>

                {revisarData.total > perPageRevisar && (
                  <div className="mt-3 flex items-center justify-between text-sm text-gray-600">
                    <span>
                      {(pageRevisar - 1) * perPageRevisar + 1}
                      {Math.min(
                        pageRevisar * perPageRevisar,
                        revisarData.total
                      )}{' '}
                      de {revisarData.total}
                    </span>

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={pageRevisar <= 1}
                        onClick={() => setPageRevisar(p => Math.max(1, p - 1))}
                      >
                        Anterior
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        disabled={
                          pageRevisar * perPageRevisar >= revisarData.total
                        }
                        onClick={() => setPageRevisar(p => p + 1)}
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

      {/* Filtros y Búsqueda */}

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                <Input
                  placeholder="Buscar por Cédula o Nombres..."
                  value={searchTerm}
                  onChange={e => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <Button
              variant="outline"
              onClick={() => setShowFilters(!showFilters)}
              className="sm:w-auto"
            >
              <Filter className="mr-2 h-4 w-4" />
              Filtros
            </Button>
          </div>

          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 border-t pt-4"
            >
              <div className="space-y-4">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
                  <Filter className="h-4 w-4" />
                  Filtros de Búsqueda
                </h3>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                  {/* Cédula de identidad */}

                  <div>
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Cédula de identidad
                    </label>

                    <Input
                      type="text"
                      placeholder="Cédula de identidad"
                      value={filters.cedula || ''}
                      onChange={e =>
                        handleFilterChange(
                          'cedula',
                          e.target.value || undefined
                        )
                      }
                      className="w-full"
                    />
                  </div>

                  {/* Estado */}

                  <div>
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Estado
                    </label>

                    <select
                      className="w-full rounded-md border border-gray-300 bg-white p-2"
                      value={filters.estado || ''}
                      onChange={e =>
                        handleFilterChange(
                          'estado',
                          e.target.value || undefined
                        )
                      }
                    >
                      <option value="">Todos</option>

                      {(opcionesEstado.length > 0
                        ? opcionesEstado
                        : [
                            { valor: 'ACTIVO', etiqueta: 'Activo', orden: 1 },

                            {
                              valor: 'INACTIVO',
                              etiqueta: 'Inactivo',
                              orden: 2,
                            },

                            {
                              valor: 'FINALIZADO',
                              etiqueta: 'Finalizado',
                              orden: 3,
                            },

                            { valor: 'LEGACY', etiqueta: 'Legacy', orden: 4 },
                          ]
                      ).map(opt => (
                        <option key={opt.valor} value={opt.valor}>
                          {opt.etiqueta}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Email */}

                  <div>
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Email
                    </label>

                    <Input
                      type="email"
                      placeholder="Email"
                      value={filters.email || ''}
                      onChange={e =>
                        handleFilterChange('email', e.target.value || undefined)
                      }
                      className="w-full"
                    />
                  </div>

                  {/* Teléfono */}

                  <div>
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Teléfono
                    </label>

                    <Input
                      type="text"
                      placeholder="Teléfono"
                      value={filters.telefono || ''}
                      onChange={e =>
                        handleFilterChange(
                          'telefono',
                          e.target.value || undefined
                        )
                      }
                      className="w-full"
                    />
                  </div>

                  {/* Ocupación */}

                  <div>
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Ocupación
                    </label>

                    <Input
                      type="text"
                      placeholder="Ocupación"
                      value={filters.ocupacion || ''}
                      onChange={e =>
                        handleFilterChange(
                          'ocupacion',
                          e.target.value || undefined
                        )
                      }
                      className="w-full"
                    />
                  </div>

                  {/* Usuario que registró */}

                  <div>
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Usuario que registró
                    </label>

                    <Input
                      type="text"
                      placeholder="Usuario que registró"
                      value={filters.usuario_registro || ''}
                      onChange={e =>
                        handleFilterChange(
                          'usuario_registro',
                          e.target.value || undefined
                        )
                      }
                      className="w-full"
                    />
                  </div>

                  {/* Fecha Desde */}

                  <div>
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Fecha desde
                    </label>

                    <div className="relative">
                      <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                      <Input
                        type="date"
                        placeholder="dd / mm / aaaa"
                        value={filters.fecha_desde || ''}
                        onChange={e => {
                          const fecha = e.target.value

                          // Convertir de YYYY-MM-DD a formato para backend

                          handleFilterChange('fecha_desde', fecha || undefined)
                        }}
                        className="w-full pl-10"
                      />
                    </div>
                  </div>

                  {/* Fecha Hasta */}

                  <div>
                    <label className="mb-2 block text-sm font-medium text-gray-700">
                      Fecha hasta
                    </label>

                    <div className="relative">
                      <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                      <Input
                        type="date"
                        placeholder="dd / mm / aaaa"
                        value={filters.fecha_hasta || ''}
                        onChange={e => {
                          const fecha = e.target.value

                          handleFilterChange('fecha_hasta', fecha || undefined)
                        }}
                        className="w-full pl-10"
                      />
                    </div>
                  </div>
                </div>

                {/* Botn Limpiar Filtros */}

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

                  <TableHead className="font-semibold">
                    Fecha registro
                  </TableHead>

                  <TableHead className="font-semibold">
                    Últ. actualización
                  </TableHead>

                  <TableHead className="text-right font-semibold">
                    Acciones
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {clientes.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="py-8 text-center text-gray-500"
                    >
                      {isLoading ? (
                        <div className="flex items-center justify-center">
                          <LoadingSpinner size="sm" />

                          <span className="ml-2">Cargando clientes...</span>
                        </div>
                      ) : clientesResponse?.total === 0 ? (
                        'No hay clientes que coincidan con los filtros seleccionados'
                      ) : clientesResponse?.total &&
                        clientesResponse.total > 0 ? (
                        `Se encontraron ${clientesResponse.total} clientes pero no se pudieron cargar. Verifica la consola para ms detalles.`
                      ) : (
                        'No se pudieron cargar los clientes. Verifica la consola para ms detalles.'
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  clientes.map((cliente, index) => (
                    <TableRow
                      key={
                        cliente?.id != null
                          ? String(cliente.id)
                          : `row-${index}`
                      }
                    >
                      <TableCell>
                        <div>
                          <button
                            type="button"
                            onClick={() => navigate(`/clientes/${cliente.id}`)}
                            className="text-left font-medium text-gray-900 hover:text-blue-600 hover:underline"
                          >
                            {(cliente as any).nombres ||
                              (cliente as any).Nombres ||
                              (cliente as any).nombre ||
                              ''}
                          </button>

                          <div className="text-sm text-gray-500">
                            Cédula: {String(cliente.cedula ?? '')} | ID:{' '}
                            {String(cliente.id ?? '')}
                          </div>
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="space-y-1">
                          <div className="flex items-center text-sm text-gray-600">
                            <Mail className="mr-2 h-3 w-3" />

                            {String(cliente.email ?? '')}

                            {cliente.email && (
                              <Link
                                to={`/comunicaciones?cliente_id=${cliente.id}&tipo=email`}
                                className="ml-2 inline-flex text-green-600 hover:text-green-800"
                                title="Ver comunicaciones de Email"
                              >
                                <MessageSquare className="h-4 w-4" />
                              </Link>
                            )}
                          </div>

                          <div className="flex items-center text-sm text-gray-600">
                            <Phone className="mr-2 h-3 w-3" />

                            {String(cliente.telefono ?? '')}

                            {cliente.telefono && (
                              <Link
                                to={`/comunicaciones?cliente_id=${cliente.id}&tipo=whatsapp`}
                                className="ml-2 inline-flex text-green-600 hover:text-green-800"
                                title="Ver comunicaciones de WhatsApp"
                              >
                                <MessageSquare className="h-4 w-4" />
                              </Link>
                            )}
                          </div>
                        </div>
                      </TableCell>

                      <TableCell>
                        <Badge
                          variant={
                            cliente.estado === 'ACTIVO'
                              ? 'default'
                              : 'destructive'
                          }
                        >
                          {String(cliente.estado ?? '')}
                        </Badge>
                      </TableCell>

                      <TableCell>
                        <div className="text-sm text-gray-600">
                          {cliente.fecha_registro
                            ? formatDate(cliente.fecha_registro)
                            : '-'}
                        </div>
                      </TableCell>

                      <TableCell>
                        <div className="text-sm text-gray-600">
                          {cliente.fecha_actualizacion
                            ? formatDate(cliente.fecha_actualizacion)
                            : '-'}
                        </div>
                      </TableCell>

                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="outline"
                            size="icon"
                            title="Ver detalle"
                            className="h-8 w-8 cursor-pointer border-slate-400 font-medium text-slate-600 transition-colors hover:bg-slate-100"
                            onClick={() => navigate(`/clientes/${cliente.id}`)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>

                          <Button
                            variant="outline"
                            size="icon"
                            title="Ver comunicaciones"
                            className="h-8 w-8 cursor-pointer border-blue-400 bg-blue-50 font-medium text-blue-600 transition-colors hover:border-blue-600 hover:bg-blue-600 hover:text-white"
                            onClick={() => {
                              navigate(
                                `/comunicaciones?cliente_id=${cliente.id}`
                              )
                            }}
                          >
                            <MessageSquare className="h-4 w-4" />
                          </Button>

                          {/* ? BOTN EDITAR - ACTIVO Y FUNCIONAL */}

                          <Button
                            variant="outline"
                            size="icon"
                            title="Editar cliente"
                            className="h-8 w-8 cursor-pointer border-green-400 bg-green-50 font-medium text-green-600 transition-colors hover:border-green-600 hover:bg-green-600 hover:text-white"
                            onClick={() => handleEditarCliente(cliente)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>

                          {/* ? BOTN ELIMINAR - ACTIVO Y FUNCIONAL */}

                          <Button
                            variant="outline"
                            size="icon"
                            title="Eliminar cliente"
                            className="h-8 w-8 cursor-pointer border-red-400 bg-red-50 font-medium text-red-600 transition-colors hover:border-red-600 hover:bg-red-600 hover:text-white"
                            onClick={() => {
                              console.log(
                                '? Botn Eliminar clickeado para cliente ID:',
                                cliente.id
                              )

                              handleEliminarCliente(cliente)
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
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

      {/* Paginacin */}

      {(totalPages > 1 || clientesResponse?.total) && (
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-700">
              Mostrando {(currentPage - 1) * perPage + 1} -{' '}
              {Math.min(currentPage * perPage, clientesResponse?.total || 0)} de{' '}
              {clientesResponse?.total || 0} clientes
            </div>

            <div className="flex items-center gap-2">
              <label className="whitespace-nowrap text-sm text-gray-700">
                Por pgina:
              </label>

              <select
                value={perPage}
                onChange={e => handlePerPageChange(Number(e.target.value))}
                className="rounded-md border border-gray-300 p-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
              <div className="mr-2 text-sm text-gray-700">
                Pgina {currentPage} de {totalPages}
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
                onClick={() =>
                  setCurrentPage(prev => Math.min(totalPages, prev + 1))
                }
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
            onSuccess={async () => {
              queryClient.invalidateQueries({ queryKey: ['clientes'] })

              queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

              queryClient.invalidateQueries({ queryKey: ['dashboard'] })

              queryClient.invalidateQueries({ queryKey: ['kpis'] })

              await refetchStats()
            }}
            onClienteCreated={async () => {
              queryClient.invalidateQueries({ queryKey: ['clientes'] })

              queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

              queryClient.invalidateQueries({ queryKey: ['dashboard'] })

              queryClient.invalidateQueries({ queryKey: ['kpis'] })

              await refetchStats()
            }}
            onOpenEditExisting={async (clienteId: number) => {
              try {
                const clienteCompleto = await clienteService.getCliente(
                  String(clienteId)
                )

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

      {/* Modal Confirmar Eliminacin */}

      <AnimatePresence>
        {showEliminarCliente && clienteSeleccionado && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="mx-4 w-full max-w-md rounded-lg bg-white p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="rounded-full bg-red-100 p-2">
                  <Trash2 className="h-6 w-6 text-red-600" />
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    Eliminar Cliente
                  </h3>

                  <p className="text-sm font-medium text-red-600">
                    ? ELIMINACIN PERMANENTE - No se puede deshacer
                  </p>
                </div>
              </div>

              <div className="mb-6">
                <p className="text-gray-700">
                  Ests seguro de que quieres{' '}
                  <span className="font-semibold text-red-600">
                    ELIMINAR PERMANENTEMENTE
                  </span>{' '}
                  al cliente{' '}
                  <span className="font-semibold">
                    {(clienteSeleccionado as any)?.nombres ??
                      clienteSeleccionado?.Nombres ??
                      ''}
                  </span>
                  ?
                </p>

                <p className="mt-2 text-sm font-medium text-red-600">
                  ? El cliente ser eliminado completamente de la base de datos.
                </p>

                <p className="mt-1 text-sm text-gray-500">
                  Cédula: {clienteSeleccionado.cedula}
                </p>
              </div>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowEliminarCliente(false)

                    setClienteSeleccionado(null)
                  }}
                >
                  Cancelar
                </Button>

                <Button variant="destructive" onClick={confirmarEliminacion}>
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
            onSuccess={async () => {
              setShowExcelUpload(false)

              queryClient.invalidateQueries({ queryKey: ['clientes'] })

              queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

              await refetchStats()

              showNotification('success', 'Cliente(s) cargado(s) exitosamente')
            }}
          />
        )}
      </AnimatePresence>

      {/* Notificación toast única (éxito / error) */}

      {notification && (
        <motion.div
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -50 }}
          className={`fixed right-4 top-4 z-50 max-w-md rounded-lg p-4 shadow-lg ${
            notification.type === 'success'
              ? 'border border-green-300 bg-green-100 text-green-800'
              : 'border border-red-300 bg-red-100 text-red-800'
          }`}
        >
          <div className="flex items-center gap-2">
            <div
              className={`h-2 w-2 rounded-full ${
                notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
              }`}
            />

            <span className="font-medium">{notification.message}</span>

            <button
              type="button"
              onClick={() => setNotification(null)}
              className="ml-2 rounded p-1 text-gray-500 hover:bg-black/5 hover:text-gray-700"
              aria-label="Cerrar notificación"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
