import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CreditCard,
  Filter,
  Plus,
  Calendar,
  AlertCircle,
  Edit,
  Trash2,
  RefreshCw,
  X,
  MoreHorizontal,
  FileSpreadsheet,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  Search,
  Download,
  Loader2,
  Mail,
  Upload,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '../../components/ui/popover'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { formatDate, formatLastSyncDate, cn } from '../../utils'
import { pagoService, type Pago } from '../../services/pagoService'
import { pagoConErrorService, type PagoConError } from '../../services/pagoConErrorService'
import { RegistrarPagoForm } from './RegistrarPagoForm'
import { ExcelUploaderPagosUI } from './ExcelUploaderPagosUI'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../../components/ui/dialog'
import { ConfirmarBorrarDiaDialog } from './ConfirmarBorrarDiaDialog'
import { PagosListResumen } from './PagosListResumen'
import { PagosKPIsNuevo } from './PagosKPIsNuevo'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'
import { useSearchParams, Link } from 'react-router-dom'
import { useGmailPipeline } from '../../hooks/useGmailPipeline'

/** Si false, la opción "Descargar Excel" (Gmail) no se muestra en el submenú Agregar pago. */
const SHOW_DESCARGA_EXCEL_EN_SUBMENU = false

export function PagosList() {
  const [searchParams, setSearchParams] = useSearchParams()
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
    conciliado: 'si', // Por defecto: solo conciliados = SI
    sin_prestamo: '', // si = solo pagos sin crédito asignado
  })
  const [showRegistrarPago, setShowRegistrarPago] = useState(false)
  const [showCargaMasivaPagos, setShowCargaMasivaPagos] = useState(false)
  const [agregarPagoOpen, setAgregarPagoOpen] = useState(false)
  const [pagoEditando, setPagoEditando] = useState<Pago | PagoConError | null>(null)
  const [accionesOpenId, setAccionesOpenId] = useState<number | null>(null)
  const [conciliandoId, setConciliandoId] = useState<number | null>(null)
  const [isExportingRevisar, setIsExportingRevisar] = useState(false)
  const [showConfirmarBorrar, setShowConfirmarBorrar] = useState(false)
  const [lastImportCobrosResult, setLastImportCobrosResult] = useState<{
    registros_procesados: number
    registros_con_error: number
    mensaje: string
  } | null>(null)
  const [isImportingCobros, setIsImportingCobros] = useState(false)
  const [isExportingRevisionPagos, setIsExportingRevisionPagos] = useState(false)
  const [isDescargandoGmailExcel, setIsDescargandoGmailExcel] = useState(false)
  const [showVaciarTablaGmail, setShowVaciarTablaGmail] = useState(false)
  const [isVaciarTablaGmail, setIsVaciarTablaGmail] = useState(false)
  const [showVaciarTrasDescarga, setShowVaciarTrasDescarga] = useState(false)
  const [gmailScanFilter, setGmailScanFilter] = useState<'unread' | 'read' | 'all'>('unread')
  const [submenuGmailOpen, setSubmenuGmailOpen] = useState(false)
  const queryClient = useQueryClient()
  const lastRunForWhichWeShowedDialogRef = useRef<string | null>(null)

  const { loading: loadingGmail, gmailStatus, setGmailStatus, run: runGmail } = useGmailPipeline({
    onStatusUpdate: (s) => {
      setGmailStatus(s)
      if (s?.last_status === 'success' && s?.latest_data_date && s?.last_run) {
        if (lastRunForWhichWeShowedDialogRef.current !== s.last_run) {
          lastRunForWhichWeShowedDialogRef.current = s.last_run
          setShowConfirmarBorrar(true)
        }
      }
    },
    onDone: (s) => {
      if (s?.last_run) lastRunForWhichWeShowedDialogRef.current = s.last_run
      setShowConfirmarBorrar(true)
    },
  })

  // Cargar estado Gmail al montar; si ya hay éxito con datos, mostrar diálogo Sí/No
  useEffect(() => {
    pagoService.getGmailStatus().then((s) => {
      setGmailStatus(s)
      if (s?.last_status === 'success' && s?.latest_data_date && s?.last_run) {
        if (lastRunForWhichWeShowedDialogRef.current !== s.last_run) {
          lastRunForWhichWeShowedDialogRef.current = s.last_run
          setShowConfirmarBorrar(true)
        }
      }
    }).catch(() => setGmailStatus(null))
  }, [])
  useEffect(() => {
    if (!agregarPagoOpen) return
    pagoService.getGmailStatus().then(setGmailStatus).catch(() => setGmailStatus(null))
  }, [agregarPagoOpen])

  const handleGenerarExcelDesdeGmail = () => {
    setAgregarPagoOpen(false)
    runGmail(gmailScanFilter)
  }

  const handleVaciarTablaGmail = async () => {
    setAgregarPagoOpen(false)
    setIsVaciarTablaGmail(true)
    try {
      const result = await pagoService.confirmarDiaGmail(true)
      toast.success(result.mensaje ?? 'Tabla vaciada.')
      setGmailStatus(null)
      await pagoService.getGmailStatus().then(setGmailStatus)
      setShowVaciarTablaGmail(false)
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsVaciarTablaGmail(false)
    }
  }

  const handleImportarDesdeCobros = async () => {
    setAgregarPagoOpen(false)
    setIsImportingCobros(true)
    setLastImportCobrosResult(null)
    try {
      const res = await pagoService.importarDesdeCobros()
      setLastImportCobrosResult({
        registros_procesados: res.registros_procesados,
        registros_con_error: res.registros_con_error,
        mensaje: res.mensaje,
      })
      await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-con-errores'], exact: false })
      toast.success(res.mensaje)
      if (res.registros_con_error > 0) {
        toast('Hay pagos en Revisar Pagos. Use el botón "Descargar Excel en revisión pagos" si desea exportarlos.', { duration: 5000 })
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || e?.message || 'Error al importar desde Cobros')
    } finally {
      setIsImportingCobros(false)
    }
  }

  const handleDescargarExcelRevisionPagos = async () => {
    setIsExportingRevisionPagos(true)
    try {
      const pagos = await pagoConErrorService.getAllForExport({})
      if (pagos.length === 0) {
        toast.info('No hay pagos en revisión para exportar')
        return
      }
      const { createAndDownloadExcel } = await import('../../types/exceljs')
      const datos = pagos.map((p) => ({
        ID: p.id,
        Cédula: p.cedula_cliente,
        'ID Préstamo': p.prestamo_id ?? '',
        'Fecha pago': typeof p.fecha_pago === 'string' ? p.fecha_pago : (p.fecha_pago as Date)?.toISOString?.()?.slice(0, 10) ?? '',
        'Monto pagado': p.monto_pagado,
        'Nº documento': p.numero_documento,
        'Institución bancaria': p.institucion_bancaria ?? '',
        Estado: p.estado,
        Observaciones: (p as PagoConError).observaciones ?? '',
      }))
      const nombre = `Revision_Pagos_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(datos, 'Revisión pagos', nombre)
      const ids = pagos.map((p) => p.id)
      await pagoConErrorService.eliminarPorDescarga(ids)
      await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-con-errores'], exact: false })
      toast.success(`${pagos.length} pagos exportados y eliminados de la lista`)
    } catch (err) {
      if (import.meta.env.DEV) console.error('Error al descargar Excel', err)
      toast.error('Error al descargar Excel')
    } finally {
      setIsExportingRevisionPagos(false)
    }
  }

  // Contar filtros activos (mismo criterio que Préstamos)
  const activeFiltersCount = [
    filters.cedula,
    filters.estado,
    filters.fechaDesde,
    filters.fechaHasta,
    filters.analista,
    filters.conciliado !== 'si' ? filters.conciliado : null,
    filters.sin_prestamo === 'si' ? 'sin_prestamo' : null,
  ].filter(Boolean).length
  const handleClearFilters = () => {
    setFilters({
      cedula: '',
      estado: '',
      fechaDesde: '',
      fechaHasta: '',
      analista: '',
      conciliado: 'si',
      sin_prestamo: '',
    })
    setPage(1)
  }
  const handleRevisarPagos = () => {
    setFilters(prev => ({ ...prev, sin_prestamo: 'si', conciliado: 'all' }))
    setActiveTab('todos')
    setPage(1)
  }

  const handleExportRevisarExcel = async () => {
    if (!filters.sin_prestamo) return
    setIsExportingRevisar(true)
    try {
      const pagos = await pagoConErrorService.getAllForExport({
        cedula: filters.cedula || undefined,
        fechaDesde: filters.fechaDesde || undefined,
        fechaHasta: filters.fechaHasta || undefined,
      })
      if (pagos.length === 0) {
        toast.info('No hay pagos para exportar')
        return
      }
      const { createAndDownloadExcel } = await import('../../types/exceljs')
      const datos = pagos.map((p) => ({
        ID: p.id,
        Cédula: p.cedula_cliente,
        'ID Préstamo': p.prestamo_id ?? '',
        'Fecha pago': typeof p.fecha_pago === 'string' ? p.fecha_pago : (p.fecha_pago as Date)?.toISOString?.()?.slice(0, 10) ?? '',
        'Monto pagado': p.monto_pagado,
        'Nº documento': p.numero_documento,
        'Institución bancaria': p.institucion_bancaria ?? '',
        Estado: p.estado,
        'Fecha registro': p.fecha_registro ? (typeof p.fecha_registro === 'string' ? p.fecha_registro : (p.fecha_registro as Date)?.toISOString?.() ?? '') : '',
        'Fecha conciliación': p.fecha_conciliacion ? (typeof p.fecha_conciliacion === 'string' ? p.fecha_conciliacion : (p.fecha_conciliacion as Date)?.toISOString?.() ?? '') : '',
        Conciliado: p.conciliado ? 'Sí' : 'No',
        'Verificado concordancia': p.verificado_concordancia ?? '',
        'Usuario registro': p.usuario_registro ?? '',
        Notas: p.notas ?? '',
        'Observaciones': (p as PagoConError).observaciones ?? '',
      }))
      const nombre = `Revisar_Pagos_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(datos, 'Revisar Pagos', nombre)
      // Tras guardar el Excel en PC, mover a revisar_pagos para que desaparezcan de la vista
      const ids = pagos.map((p) => p.id)
      await pagoConErrorService.eliminarPorDescarga(ids)
      queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['pagos-con-errores'], exact: false })
      toast.success(`${pagos.length} pagos exportados y eliminados de la lista`)
    } catch (err) {
      if (import.meta.env.DEV) console.error('Error al exportar', err)
      toast.error('Error al exportar. Intenta de nuevo.')
    } finally {
      setIsExportingRevisar(false)
    }
  }

  useEffect(() => {
    if (searchParams.get('revisar') === '1') {
      setFilters(prev => ({ ...prev, sin_prestamo: 'si', conciliado: 'all' }))
      setActiveTab('todos')
      setPage(1)
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const esRevisarPagos = filters.sin_prestamo === 'si'
  const { data, isLoading, error, isError } = useQuery({
    queryKey: esRevisarPagos ? ['pagos-con-errores', page, perPage, filters] : ['pagos', page, perPage, filters],
    queryFn: () =>
      esRevisarPagos
        ? pagoConErrorService.getAll(page, perPage, {
            cedula: filters.cedula || undefined,
            estado: filters.estado || undefined,
            fechaDesde: filters.fechaDesde || undefined,
            fechaHasta: filters.fechaHasta || undefined,
            conciliado: filters.conciliado === 'all' ? undefined : filters.conciliado,
          })
        : pagoService.getAllPagos(page, perPage, filters),
    staleTime: 15_000, // 15 s – evita múltiples refetch por re-renders y cambios de foco durante batch
    refetchOnMount: true,
    refetchOnWindowFocus: false, // Desactivado para no interrumpir batch con GETs innecesarios
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
      await queryClient.invalidateQueries({ queryKey: ['pagos-con-errores'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['pagos-con-errores'], exact: false })
      await queryClient.refetchQueries({ queryKey: ['pagos-kpis'], exact: false })
      toast.success('Datos actualizados correctamente')
    } catch (error: unknown) {
      toast.error('Error al actualizar los datos')
    }
  }
  return (
    <div className="space-y-6">
      <PagosKPIsNuevo />
      <div className="flex flex-wrap justify-end items-center gap-3 rounded-xl border border-gray-200/80 bg-gray-50/50 px-4 py-3 sm:px-5 sm:py-4">
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
          <Button
            variant={filters.sin_prestamo === 'si' ? 'default' : 'outline'}
            size="lg"
            onClick={handleRevisarPagos}
            className="px-6 py-6 text-base font-semibold"
            title="Ver pagos sin número de crédito asignado"
          >
            <Search className="w-5 h-5 mr-2" />
            Revisar Pagos
          </Button>
          {filters.sin_prestamo === 'si' && (
            <Button
              variant="outline"
              size="lg"
              onClick={handleExportRevisarExcel}
              disabled={isExportingRevisar}
              className="px-6 py-6 text-base font-semibold"
              title="Descargar todos los pagos a revisar en Excel"
            >
              {isExportingRevisar ? (
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              ) : (
                <Download className="w-5 h-5 mr-2" />
              )}
              Descargar Excel
            </Button>
          )}
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
            <PopoverContent className="w-72 p-3" align="end">
              {gmailStatus && (
                <p className="text-xs text-gray-600 px-2 py-1.5 mb-2 border-b border-gray-100">
                  {gmailStatus.last_status === 'error' ? (
                    <span className="text-amber-600">Última sync Gmail falló</span>
                  ) : gmailStatus.last_status === 'running' ? (
                    <>Procesando: {gmailStatus.last_emails} correos, {gmailStatus.last_files} archivos</>
                  ) : gmailStatus.last_run ? (
                    <>Última sync: {formatLastSyncDate(gmailStatus.last_run)} – {gmailStatus.last_emails} correos, {gmailStatus.last_files} archivos</>
                  ) : (
                    <span className="text-gray-500">Sin sync Gmail aún</span>
                  )}
                </p>
              )}
              <div className="space-y-2">
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-md hover:bg-blue-50"
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
                  className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-md hover:bg-blue-50"
                  onClick={() => {
                    setAgregarPagoOpen(false)
                    setShowCargaMasivaPagos(true)
                  }}
                >
                  <FileSpreadsheet className="w-5 h-5 text-gray-600" />
                  <span>Pagos desde Excel</span>
                  <span className="text-xs text-gray-500 ml-auto">Revisar y editar</span>
                </button>

                {/* Submenú: Generar Excel desde email */}
                <div className="border-t border-gray-100 pt-2 mt-2">
                  <button
                    type="button"
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left rounded-md hover:bg-gray-50"
                    onClick={() => setSubmenuGmailOpen((v) => !v)}
                  >
                    <Mail className="w-5 h-5 text-gray-600" />
                    <span className="font-medium text-gray-800">Generar Excel desde email</span>
                    <ChevronRight className={cn('w-4 h-4 ml-auto text-gray-400 transition-transform', submenuGmailOpen && 'rotate-90')} />
                  </button>
                  {submenuGmailOpen && (
                    <div className="mt-2 ml-2 pl-3 border-l-2 border-gray-200 space-y-2 bg-gray-50/80 rounded-r-md py-2 pr-2">
                      <div>
                        <label className="text-xs text-gray-600 block mb-1">Correos a escanear (Gmail)</label>
                        <Select value={gmailScanFilter} onValueChange={(v: 'unread' | 'read' | 'all') => setGmailScanFilter(v)}>
                          <SelectTrigger className="h-9 text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="unread">No leídos</SelectItem>
                            <SelectItem value="read">Leídos</SelectItem>
                            <SelectItem value="all">Todos (leídos y no leídos)</SelectItem>
                          </SelectContent>
                        </Select>
                        {gmailScanFilter === 'all' && (
                          <p className="text-xs text-gray-600 mt-1.5">
                            Se descargarán todos los correos (leídos y no leídos) del buzón principal.
                          </p>
                        )}
                      </div>
                      <button
                        type="button"
                        className="w-full flex items-center gap-3 px-3 py-2.5 text-left rounded-md hover:bg-blue-50 disabled:opacity-50 text-sm"
                        onClick={handleGenerarExcelDesdeGmail}
                        disabled={loadingGmail}
                      >
                        <Mail className="w-4 h-4 text-gray-600" />
                        <span>{loadingGmail ? `Procesando... (${gmailStatus?.last_emails ?? 0} correos, ${gmailStatus?.last_files ?? 0} archivos)` : 'Procesar correos'}</span>
                        <span className="text-xs text-gray-500 ml-auto">Gmail</span>
                      </button>
                      <button
                        type="button"
                        className="w-full flex items-center gap-3 px-3 py-2.5 text-left rounded-md hover:bg-blue-50 disabled:opacity-50 text-sm"
                        onClick={async () => {
                          setAgregarPagoOpen(false)
                          setIsDescargandoGmailExcel(true)
                          try {
                            await pagoService.downloadGmailExcelTemporal()
                            toast.success('Excel descargado (todas las filas guardadas).')
                            setShowVaciarTrasDescarga(true)
                            pagoService.getGmailStatus().then(setGmailStatus)
                          } catch (e) {
                            toast.error(getErrorMessage(e))
                          } finally {
                            setIsDescargandoGmailExcel(false)
                          }
                        }}
                        disabled={isDescargandoGmailExcel}
                      >
                        <Download className="w-4 h-4 text-gray-600" />
                        <span>{isDescargandoGmailExcel ? 'Descargando...' : 'Descargar Excel (todas las filas guardadas)'}</span>
                        <span className="text-xs text-gray-500 ml-auto">Gmail</span>
                      </button>
                      <button
                        type="button"
                        className="w-full flex items-center gap-3 px-3 py-2.5 text-left rounded-md hover:bg-red-50 disabled:opacity-50 text-red-700 text-sm"
                        onClick={() => {
                          setAgregarPagoOpen(false)
                          setShowVaciarTablaGmail(true)
                        }}
                        disabled={isVaciarTablaGmail}
                      >
                        <Trash2 className="w-4 h-4 text-red-600" />
                        <span>{isVaciarTablaGmail ? 'Vaciando...' : 'Vaciar tabla (solo cuando tú lo pidas)'}</span>
                        <span className="text-xs text-gray-500 ml-auto">Gmail</span>
                      </button>
                    </div>
                  )}
                </div>

                {SHOW_DESCARGA_EXCEL_EN_SUBMENU && submenuGmailOpen && (
                  <button
                    type="button"
                    className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-md hover:bg-blue-50 disabled:opacity-50 ml-2 pl-5 border-l-2 border-gray-200"
                    onClick={async () => {
                      setAgregarPagoOpen(false)
                      setIsDescargandoGmailExcel(true)
                      try {
                        await pagoService.downloadGmailExcel(gmailStatus?.latest_data_date ?? undefined)
                        toast.success('Excel descargado.')
                        pagoService.getGmailStatus().then(setGmailStatus)
                      } catch (e) {
                        toast.error(getErrorMessage(e))
                      } finally {
                        setIsDescargandoGmailExcel(false)
                      }
                    }}
                    disabled={isDescargandoGmailExcel || !gmailStatus?.latest_data_date}
                  >
                    <Download className="w-5 h-5 text-gray-600" />
                    <span>{isDescargandoGmailExcel ? 'Descargando...' : 'Descargar Excel'}</span>
                    {gmailStatus?.latest_data_date && (
                      <span className="text-xs text-gray-500 ml-auto">disponible: {gmailStatus.latest_data_date}</span>
                    )}
                  </button>
                )}
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-md hover:bg-blue-50 disabled:opacity-50 border-t border-gray-100 mt-2 pt-3"
                  onClick={handleImportarDesdeCobros}
                  disabled={isImportingCobros}
                >
                  <CreditCard className="w-5 h-5 text-gray-600" />
                  <span>{isImportingCobros ? 'Importando...' : 'Importar reportados aprobados (Cobros)'}</span>
                  <span className="text-xs text-gray-500 ml-auto">Cobros</span>
                </button>
              </div>
            </PopoverContent>
          </Popover>

      </div>
      {/* Después de importar desde Cobros: si hay errores, ofrecer descargar Excel en revisión */}
      {lastImportCobrosResult && lastImportCobrosResult.registros_con_error > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="py-3 flex flex-wrap items-center gap-3">
            <span className="text-sm text-amber-800">
              {lastImportCobrosResult.registros_procesados} importados; {lastImportCobrosResult.registros_con_error} en Revisar Pagos (no cumplen reglas de carga masiva).
            </span>
            <Button
              variant="outline"
              size="sm"
              className="border-amber-400 text-amber-800 hover:bg-amber-100"
              onClick={handleDescargarExcelRevisionPagos}
              disabled={isExportingRevisionPagos}
            >
              {isExportingRevisionPagos ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Download className="h-4 w-4 mr-1" />}
              Descargar Excel en revisión pagos
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setLastImportCobrosResult(null)}>Ocultar</Button>
          </CardContent>
        </Card>
      )}
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
          {/* Búsqueda y filtro Conciliación siempre visible */}
          <Card className="mb-4">
            <CardContent className="pt-6">
              <div className="flex flex-col sm:flex-row gap-4 flex-wrap">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">Conciliación</label>
                  <Select value={filters.conciliado || 'si'} onValueChange={value => handleFilterChange('conciliado', value)}>
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="Conciliación" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="si">Sí (conciliados)</SelectItem>
                      <SelectItem value="no">No (pendientes)</SelectItem>
                      <SelectItem value="all">Todos</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1 min-w-[200px]">
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
                {filters.sin_prestamo === 'si' && (
                  <div className="flex items-end">
                    <Badge className="bg-amber-500 text-white px-3 py-1.5">
                      Sin crédito asignado
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFilterChange('sin_prestamo', '')}
                      className="ml-2"
                    >
                      <X className="h-4 w-4 mr-1" />
                      Ver todos
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
                    onClick={() =>
                      queryClient.refetchQueries({
                        queryKey: esRevisarPagos ? ['pagos-con-errores'] : ['pagos'],
                        exact: false,
                      })
                    }
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
                  {(filters.cedula || filters.estado || filters.fechaDesde || filters.fechaHasta || filters.analista || (filters.conciliado && filters.conciliado !== 'si') || filters.sin_prestamo === 'si') && (
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
                          <TableHead>Crédito</TableHead>
                          <TableHead>Estado</TableHead>
                          {esRevisarPagos && <TableHead>Observaciones</TableHead>}
                          <TableHead>Monto</TableHead>
                          <TableHead>Fecha Pago</TableHead>
                          <TableHead>Nº Documento</TableHead>
                          <TableHead>Conciliado</TableHead>
                          <TableHead className="text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.pagos.map((pago: Pago) => (
                          <TableRow key={pago.id}>
                            <TableCell>{pago.id}</TableCell>
                            <TableCell>{pago.cedula_cliente}</TableCell>
                            <TableCell>
                              {pago.prestamo_id ? (
                                <span className="text-sm font-medium">#{pago.prestamo_id}</span>
                              ) : (
                                <span className="text-amber-600 text-sm">Sin asignar</span>
                              )}
                            </TableCell>
                            <TableCell>{getEstadoBadge(pago.estado)}</TableCell>
                            {esRevisarPagos && (
                              <TableCell className="text-xs text-amber-700">{(pago as PagoConError).observaciones ?? '-'}</TableCell>
                            )}
                            <TableCell>
                              ${typeof pago.monto_pagado === 'number' ? pago.monto_pagado.toFixed(2) : parseFloat(String(pago.monto_pagado || 0)).toFixed(2)}
                            </TableCell>
                            <TableCell>{formatDate(pago.fecha_pago)}</TableCell>
                            <TableCell>{pago.numero_documento ?? '—'}</TableCell>
                            <TableCell>
                              {(pago.verificado_concordancia === 'SI' || pago.conciliado) ? (
                                <Badge className="bg-green-500 text-white">SI</Badge>
                              ) : (
                                <Badge className="bg-gray-500 text-white">NO</Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              <Popover open={accionesOpenId === pago.id} onOpenChange={(open) => setAccionesOpenId(open ? pago.id : null)}>
                                <PopoverTrigger asChild>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    title="Acciones"
                                    className="h-8 w-8 p-0"
                                  >
                                    <MoreHorizontal className="w-4 h-4" />
                                  </Button>
                                </PopoverTrigger>
                                <PopoverContent className="w-56 p-2" align="end">
                                  <div className="space-y-0.5">
                                    <button
                                      type="button"
                                      className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-gray-100 transition-colors text-left"
                                      onClick={() => {
                                        setPagoEditando(pago)
                                        setShowRegistrarPago(true)
                                        setAccionesOpenId(null)
                                      }}
                                    >
                                      <Edit className="w-4 h-4 text-gray-600" />
                                      Editar
                                    </button>
                                    <button
                                      type="button"
                                      className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-red-50 transition-colors text-left text-red-600"
                                      onClick={async () => {
                                        setAccionesOpenId(null)
                                        if (window.confirm(`¿Estás seguro de eliminar el pago ID ${pago.id}?`)) {
                                          try {
                                            if (esRevisarPagos) {
                                              await pagoConErrorService.delete(pago.id)
                                            } else {
                                              await pagoService.deletePago(pago.id)
                                            }
                                            toast.success('Pago eliminado exitosamente')
                                            await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['pagos-con-errores'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['cuotas-prestamo'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['prestamos'], exact: false })
                                          } catch (error) {
                                            toast.error('Error al eliminar el pago')
                                            if (import.meta.env.DEV) console.error('Error al eliminar el pago', error)
                                          }
                                        }
                                      }}
                                    >
                                      <Trash2 className="w-4 h-4" />
                                      Eliminar
                                    </button>
                                    {(pago.verificado_concordancia === 'SI' || pago.conciliado) ? (
                                      <button
                                        type="button"
                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-amber-50 transition-colors text-left text-amber-700"
                                        disabled={conciliandoId === pago.id}
                                        onClick={async () => {
                                          setAccionesOpenId(null)
                                          setConciliandoId(pago.id)
                                          try {
                                            await pagoService.updateConciliado(pago.id, false)
                                            toast.success('Pago marcado como NO conciliado')
                                            await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
                                          } catch (error) {
                                            toast.error('Error al actualizar conciliación')
                                            if (import.meta.env.DEV) console.error('Error al actualizar conciliación', error)
                                          } finally {
                                            setConciliandoId(null)
                                          }
                                        }}
                                      >
                                        <XCircle className="w-4 h-4" />
                                        {conciliandoId === pago.id ? 'Actualizando...' : 'Conciliar: No'}
                                      </button>
                                    ) : (
                                      <button
                                        type="button"
                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-green-50 transition-colors text-left text-green-700"
                                        disabled={conciliandoId === pago.id}
                                        onClick={async () => {
                                          setAccionesOpenId(null)
                                          setConciliandoId(pago.id)
                                          try {
                                            await pagoService.updateConciliado(pago.id, true)
                                            if (pago.prestamo_id) {
                                              try {
                                                const res = await pagoService.aplicarPagoACuotas(pago.id)
                                                if (res.cuotas_completadas > 0 || res.cuotas_parciales > 0) {
                                                  toast.success(`Conciliado. ${res.message}`)
                                                } else {
                                                  toast.success('Pago marcado como conciliado')
                                                }
                                              } catch {
                                                toast.success('Pago marcado como conciliado')
                                              }
                                            } else {
                                              toast.success('Pago marcado como conciliado')
                                            }
                                            await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['cuotas-prestamo'], exact: false })
                                            await queryClient.invalidateQueries({ queryKey: ['prestamos'], exact: false })
                                          } catch (error) {
                                            toast.error('Error al actualizar conciliación')
                                            if (import.meta.env.DEV) console.error('Error al actualizar conciliación', error)
                                          } finally {
                                            setConciliandoId(null)
                                          }
                                        }}
                                      >
                                        <CheckCircle className="w-4 h-4" />
                                        {conciliandoId === pago.id ? 'Actualizando...' : 'Conciliar: Sí'}
                                      </button>
                                    )}
                                  </div>
                                </PopoverContent>
                              </Popover>
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
          modoGuardarYProcesar={filters.sin_prestamo === 'si'}
          esPagoConError={esRevisarPagos}
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
            setShowRegistrarPago(false)
            setPagoEditando(null)
            try {
              // Invalidar todas las queries relacionadas con pagos primero
              await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['kpis'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
              // Invalidar también la query de últimos pagos (resumen)
              await queryClient.invalidateQueries({ queryKey: ['pagos-ultimos'], exact: false })
              // Cuotas y préstamos (Guardar y Procesar actualiza cuotas en BD)
              await queryClient.invalidateQueries({ queryKey: ['cuotas-prestamo'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['prestamos'], exact: false })
              await queryClient.invalidateQueries({ queryKey: ['pagos-por-cedula'], exact: false })
              // Refetch inmediato de KPIs para actualización en tiempo real
              await queryClient.refetchQueries({ queryKey: ['pagos-kpis'], exact: false })
              // Refetch de todas las queries relacionadas con pagos (no solo activas)
              // Esto asegura que las queries se actualicen incluso si no están montadas
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
              toast.success('Pago registrado exitosamente. El dashboard se ha actualizado.')
            } catch (error) {
              if (import.meta.env.DEV) console.error('Error actualizando dashboard:', error)
              toast.error('Pago registrado, pero hubo un error al actualizar el dashboard')
            }
          }}
        />
      )}
      {/* Carga masiva de pagos (Excel) desde Agregar pago: Previsualizar y editar */}
      {showCargaMasivaPagos && (
        <ExcelUploaderPagosUI
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
      <ConfirmarBorrarDiaDialog
        open={showConfirmarBorrar}
        onOpenChange={setShowConfirmarBorrar}
        fechaDatos={gmailStatus?.latest_data_date}
        onElegir={async (borrar) => {
          const fecha = gmailStatus?.latest_data_date ?? undefined
          try {
            await pagoService.downloadGmailExcel(fecha)
            toast.success('Excel descargado.')
          } catch (e) {
            toast.error(getErrorMessage(e))
            pagoService.getGmailStatus().then(setGmailStatus)
            return
          }
          const result = await pagoService.confirmarDiaGmail(borrar, fecha)
          if (result.confirmado) {
            toast.success(result.mensaje || 'Información del día borrada.')
          } else {
            toast(result.mensaje || 'Información del día se mantiene en BD.')
          }
          pagoService.getGmailStatus().then(setGmailStatus)
        }}
      />

      <Dialog open={showVaciarTablaGmail} onOpenChange={setShowVaciarTablaGmail}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Vaciar tabla (Generar Excel desde Gmail)</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">
            Se borrarán todos los datos de la tabla usada por «Generar Excel desde Gmail» (pagos_gmail_sync_item).
            Esta acción no se puede deshacer. ¿Continuar?
          </p>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowVaciarTablaGmail(false)}
              disabled={isVaciarTablaGmail}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleVaciarTablaGmail}
              disabled={isVaciarTablaGmail}
            >
              {isVaciarTablaGmail ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Trash2 className="w-4 h-4 mr-2" />}
              Vaciar tabla
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showVaciarTrasDescarga} onOpenChange={setShowVaciarTrasDescarga}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿Quieres vaciar la tabla?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">
            Si eliges <strong>Sí</strong>, se vacía la tabla (se borran los datos descargados).
            Si eliges <strong>No</strong>, los datos se mantienen y las nuevas filas se seguirán guardando a continuación.
          </p>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowVaciarTrasDescarga(false)
                toast.success('Datos mantenidos. Las nuevas filas se guardarán a continuación.')
              }}
            >
              No, seguir guardando
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={isVaciarTablaGmail}
              onClick={async () => {
                setShowVaciarTrasDescarga(false)
                setIsVaciarTablaGmail(true)
                try {
                  const result = await pagoService.confirmarDiaGmail(true)
                  toast.success(result.mensaje ?? 'Tabla vaciada.')
                  pagoService.getGmailStatus().then(setGmailStatus)
                } catch (e) {
                  toast.error(getErrorMessage(e))
                } finally {
                  setIsVaciarTablaGmail(false)
                }
              }}
            >
              {isVaciarTablaGmail ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Sí, vaciar tabla
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

