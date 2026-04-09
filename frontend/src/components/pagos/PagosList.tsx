import { useState, useEffect, useMemo } from 'react'
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
  Check,
  Eye,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../../components/ui/popover'
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '../../components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'
import { formatDate, formatLastSyncDate, cn } from '../../utils'
import { pagoService, type Pago } from '../../services/pagoService'
import { prestamoService } from '../../services/prestamoService'
import type { Prestamo } from '../../types'
import {
  pagoConErrorService,
  type PagoConError,
} from '../../services/pagoConErrorService'
import { RegistrarPagoForm } from './RegistrarPagoForm'
import { ExcelUploaderPagosUI } from './ExcelUploaderPagosUI'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../../components/ui/dialog'
import { PagosListResumen } from './PagosListResumen'
import { toast } from 'sonner'
import { getErrorMessage, isAxiosError } from '../../types/errors'
import { Link, useSearchParams } from 'react-router-dom'
import { SEGMENTO_INFOPAGOS } from '../../constants/rutasIngresoPago'
import { BASE_PATH } from '../../config/env'
import { useGmailPipeline } from '../../hooks/useGmailPipeline'

import { invalidatePagosPrestamosRevisionYCuotas } from '../../constants/queryKeys'
import {
  claveDocumentoPagoListaNormalizada,
  textoDocumentoPagoParaListado,
} from '../../utils/pagoExcelValidation'

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
  const [reemplazarPagosOpen, setReemplazarPagosOpen] = useState(false)
  const [reemplazarStep, setReemplazarStep] = useState<
    'cedula' | 'elegir' | 'confirmar'
  >('cedula')
  const [cedulaReemplazo, setCedulaReemplazo] = useState('')
  const [prestamosReemplazo, setPrestamosReemplazo] = useState<Prestamo[]>([])
  const [prestamoIdReemplazo, setPrestamoIdReemplazo] = useState<number | null>(
    null
  )
  const [loadingReemplazo, setLoadingReemplazo] = useState(false)
  const [agregarPagoOpen, setAgregarPagoOpen] = useState(false)
  const [pagoEditando, setPagoEditando] = useState<Pago | PagoConError | null>(
    null
  )
  const [accionesOpenId, setAccionesOpenId] = useState<number | null>(null)
  const [conciliandoId, setConciliandoId] = useState<number | null>(null)
  const [isExportingRevisar, setIsExportingRevisar] = useState(false)
  const [lastImportCobrosResult, setLastImportCobrosResult] = useState<{
    registros_procesados: number
    registros_con_error: number
    cuotas_aplicadas?: number
    operaciones_cuota_total?: number
    pagos_con_aplicacion_a_cuotas?: number
    pagos_sin_aplicacion_cuotas_total?: number
    pagos_sin_aplicacion_cuotas_truncados?: boolean
    pagos_sin_aplicacion_cuotas?: Array<{
      pago_id: number | null
      cedula_cliente: string
      prestamo_id: number | null
      motivo: string
      detalle: string
    }>
    mensaje: string
  } | null>(null)
  const [isDescargandoExcelCobrosErrores, setIsDescargandoExcelCobrosErrores] =
    useState(false)
  const [isImportingCobros, setIsImportingCobros] = useState(false)
  const [isExportingRevisionPagos, setIsExportingRevisionPagos] =
    useState(false)
  const [isDescargandoGmailExcel, setIsDescargandoGmailExcel] = useState(false)
  const [showVaciarTablaGmail, setShowVaciarTablaGmail] = useState(false)
  const [isVaciarTablaGmail, setIsVaciarTablaGmail] = useState(false)
  const [submenuGmailOpen, setSubmenuGmailOpen] = useState(false)
  const queryClient = useQueryClient()

  const {
    loading: loadingGmail,
    gmailStatus,
    setGmailStatus,
    run: runGmail,
    stopPolling: stopGmailPolling,
  } = useGmailPipeline({
    onStatusUpdate: s => setGmailStatus(s),
  })

  // Cargar estado Gmail al montar
  useEffect(() => {
    pagoService
      .getGmailStatus()
      .then(setGmailStatus)
      .catch(() => setGmailStatus(null))
  }, [])
  useEffect(() => {
    if (!agregarPagoOpen) return
    pagoService
      .getGmailStatus()
      .then(setGmailStatus)
      .catch(() => setGmailStatus(null))
  }, [agregarPagoOpen])

  useEffect(() => {
    return () => {
      stopGmailPolling()
    }
  }, [stopGmailPolling])

  const handleDetenerSeguimientoGmail = () => {
    stopGmailPolling()
    toast.info('Seguimiento detenido')
  }

  const handleGenerarExcelDesdeGmail = () => {
    setAgregarPagoOpen(false)
    runGmail('all')
  }

  const handleVaciarTablaGmail = async () => {
    setAgregarPagoOpen(false)
    setIsVaciarTablaGmail(true)
    try {
      const result = await pagoService.confirmarDiaGmail(true)
      toast.success('Tabla vaciada')
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
        cuotas_aplicadas: res.cuotas_aplicadas,
        operaciones_cuota_total: res.operaciones_cuota_total,
        pagos_con_aplicacion_a_cuotas: res.pagos_con_aplicacion_a_cuotas,
        pagos_sin_aplicacion_cuotas_total:
          res.pagos_sin_aplicacion_cuotas_total,
        pagos_sin_aplicacion_cuotas_truncados:
          res.pagos_sin_aplicacion_cuotas_truncados,
        pagos_sin_aplicacion_cuotas: res.pagos_sin_aplicacion_cuotas,
        mensaje: res.mensaje,
      })
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      const ops =
        typeof res.operaciones_cuota_total === 'number'
          ? res.operaciones_cuota_total
          : res.cuotas_aplicadas
      const pagosArticulados = res.pagos_con_aplicacion_a_cuotas
      const extraOps =
        typeof ops === 'number' &&
        ops > 0 &&
        typeof pagosArticulados === 'number'
          ? ` ${ops} operaciones en cuotas (${pagosArticulados} pago(s) con monto aplicado a cronograma).`
          : ''
      toast.success(`${res.mensaje}${extraOps}`)
      const sinAplicar = res.pagos_sin_aplicacion_cuotas_total ?? 0
      if (sinAplicar > 0) {
        toast(
          `${sinAplicar} pago(s) quedaron en tabla Pagos sin aplicar a cuotas (revisar préstamo o usar «Aplicar a cuotas»).`,
          { duration: 8000 }
        )
      }
      if (res.registros_con_error > 0) {
        toast(
          'Hay registros con error. Use el botón "Descargar Excel (errores de esta importación)" para revisarlos.',
          { duration: 5000 }
        )
      }
    } catch (e: any) {
      toast.error(
        e?.response?.data?.detail ||
          e?.message ||
          'Error al importar desde Cobros'
      )
    } finally {
      setIsImportingCobros(false)
    }
  }

  const handleDescargarExcelErroresCobros = async () => {
    setIsDescargandoExcelCobrosErrores(true)
    try {
      await pagoService.descargarExcelErroresImportacionCobros()
      toast.success(
        'Excel descargado. Los registros con error se han vaciado del servidor.'
      )
      setLastImportCobrosResult(null)
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsDescargandoExcelCobrosErrores(false)
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
      const datos = pagos.map(p => ({
        ID: p.id,
        Cédula: p.cedula_cliente,
        'ID Préstamo': p.prestamo_id ?? '',
        'Fecha pago':
          typeof p.fecha_pago === 'string'
            ? p.fecha_pago
            : ((p.fecha_pago as Date)?.toISOString?.()?.slice(0, 10) ?? ''),
        'Monto pagado': p.monto_pagado,
        'Nº documento': textoDocumentoPagoParaListado(
          p.numero_documento,
          p.codigo_documento
        ),
        'Institución bancaria': p.institucion_bancaria ?? '',
        Estado: p.estado,
        Observaciones: (p as PagoConError).observaciones ?? '',
      }))
      const nombre = `Revision_Pagos_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(datos, 'Revisión pagos', nombre)
      const ids = pagos.map(p => p.id)
      await pagoConErrorService.eliminarPorDescarga(ids)
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
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
      const datos = pagos.map(p => ({
        ID: p.id,
        Cédula: p.cedula_cliente,
        'ID Préstamo': p.prestamo_id ?? '',
        'Fecha pago':
          typeof p.fecha_pago === 'string'
            ? p.fecha_pago
            : ((p.fecha_pago as Date)?.toISOString?.()?.slice(0, 10) ?? ''),
        'Monto pagado': p.monto_pagado,
        'Nº documento': textoDocumentoPagoParaListado(
          p.numero_documento,
          p.codigo_documento
        ),
        'Institución bancaria': p.institucion_bancaria ?? '',
        Estado: p.estado,
        'Fecha registro': p.fecha_registro
          ? typeof p.fecha_registro === 'string'
            ? p.fecha_registro
            : ((p.fecha_registro as Date)?.toISOString?.() ?? '')
          : '',
        'Fecha conciliación': p.fecha_conciliacion
          ? typeof p.fecha_conciliacion === 'string'
            ? p.fecha_conciliacion
            : ((p.fecha_conciliacion as Date)?.toISOString?.() ?? '')
          : '',
        Conciliado: p.conciliado ? 'Sí' : 'No',
        'Verificado concordancia': p.verificado_concordancia ?? '',
        'Usuario registro': p.usuario_registro ?? '',
        Notas: p.notas ?? '',
        Observaciones: (p as PagoConError).observaciones ?? '',
      }))
      const nombre = `Revisar_Pagos_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(datos, 'Revisar Pagos', nombre)
      // Tras guardar el Excel en PC, mover a revisar_pagos para que desaparezcan de la vista
      const ids = pagos.map(p => p.id)
      await pagoConErrorService.eliminarPorDescarga(ids)
      void invalidatePagosPrestamosRevisionYCuotas(queryClient)
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
    queryKey: esRevisarPagos
      ? ['pagos-con-errores', page, perPage, filters]
      : ['pagos', page, perPage, filters],
    queryFn: () =>
      esRevisarPagos
        ? pagoConErrorService.getAll(page, perPage, {
            cedula: filters.cedula || undefined,
            estado: filters.estado || undefined,
            fechaDesde: filters.fechaDesde || undefined,
            fechaHasta: filters.fechaHasta || undefined,
            conciliado:
              filters.conciliado === 'all' ? undefined : filters.conciliado,
          })
        : pagoService.getAllPagos(page, perPage, filters),
    staleTime: 15_000, // 15 s - evita múltiples refetch por re-renders y cambios de foco durante batch
    refetchOnMount: true,
    refetchOnWindowFocus: false, // Desactivado para no interrumpir batch con GETs innecesarios
  })

  /** Solo lista normal + filtro cédula: API devuelve suma de montos de todos los pagos que coinciden. */
  const resumenTotalCedula = useMemo(() => {
    if (esRevisarPagos || !filters.cedula.trim()) return null
    const sum = data?.sum_monto_pagado_cedula
    if (typeof sum !== 'number' || Number.isNaN(sum)) return null
    return {
      sum,
      cantidad: data?.total ?? 0,
      cedula: filters.cedula.trim(),
    }
  }, [
    esRevisarPagos,
    filters.cedula,
    data?.sum_monto_pagado_cedula,
    data?.total,
  ])

  /** Claves comprobante+código (misma lógica que BD) repetidas en la página actual (advertencia visual). */
  const documentosDuplicadosEnPagina = useMemo(() => {
    const pagos = data?.pagos
    if (!pagos?.length) return new Set<string>()
    const counts = new Map<string, number>()
    for (const p of pagos) {
      const key = claveDocumentoPagoListaNormalizada(
        p.numero_documento,
        p.codigo_documento ?? null
      )
      if (!key) continue
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    const dup = new Set<string>()
    for (const [k, n] of counts) {
      if (n > 1) dup.add(k)
    }
    return dup
  }, [data?.pagos])

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
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await queryClient.refetchQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.refetchQueries({
        queryKey: ['pagos-con-errores'],
        exact: false,
      })
      await queryClient.refetchQueries({
        queryKey: ['pagos-kpis'],
        exact: false,
      })
      toast.success('Datos actualizados correctamente')
    } catch (error: unknown) {
      toast.error('Error al actualizar los datos')
    }
  }

  const cerrarReemplazarPagos = () => {
    setReemplazarPagosOpen(false)
    setReemplazarStep('cedula')
    setCedulaReemplazo('')
    setPrestamosReemplazo([])
    setPrestamoIdReemplazo(null)
    setLoadingReemplazo(false)
  }

  const abrirReemplazarPagos = () => {
    setReemplazarStep('cedula')
    setCedulaReemplazo('')
    setPrestamosReemplazo([])
    setPrestamoIdReemplazo(null)
    setLoadingReemplazo(false)
    setReemplazarPagosOpen(true)
  }

  const prestamoReemplazoSeleccionado = prestamosReemplazo.find(
    p => p.id === prestamoIdReemplazo
  )

  const handleBuscarPrestamosReemplazo = async () => {
    const ced = cedulaReemplazo.trim()
    if (!ced) {
      toast.error('Indique la cédula')
      return
    }
    setLoadingReemplazo(true)
    try {
      const lista = await prestamoService.getPrestamosByCedula(ced)
      const aprobados = lista.filter(
        p => (p.estado || '').toUpperCase() === 'APROBADO'
      )
      if (aprobados.length === 0) {
        toast.error('No hay préstamos aprobados para esa cédula')
        setPrestamosReemplazo([])
        setPrestamoIdReemplazo(null)
        return
      }
      setPrestamosReemplazo(aprobados)
      if (aprobados.length === 1) {
        setPrestamoIdReemplazo(aprobados[0].id)
        setReemplazarStep('confirmar')
      } else {
        setPrestamoIdReemplazo(null)
        setReemplazarStep('elegir')
      }
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setLoadingReemplazo(false)
    }
  }

  const handleConfirmarReemplazarPagos = async () => {
    if (prestamoIdReemplazo == null) return
    setLoadingReemplazo(true)
    try {
      const r =
        await pagoService.deleteTodosPagosPorPrestamo(prestamoIdReemplazo)
      toast.success(
        `Se eliminaron ${r.pagos_eliminados} pago(s). Cargue el Excel con los nuevos pagos.`
      )
      cerrarReemplazarPagos()
      setShowCargaMasivaPagos(true)
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await queryClient.refetchQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.refetchQueries({
        queryKey: ['pagos-kpis'],
        exact: false,
      })
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setLoadingReemplazo(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-3 rounded-xl border border-gray-200/80 bg-gray-50/50 px-4 py-3 sm:px-5 sm:py-4">
        <Button
          variant="outline"
          size="lg"
          onClick={handleRefresh}
          className="px-6 py-6 text-base font-semibold"
          disabled={isLoading}
        >
          <RefreshCw
            className={`mr-2 h-5 w-5 ${isLoading ? 'animate-spin' : ''}`}
          />
          Actualizar
        </Button>
        <Button
          variant={filters.sin_prestamo === 'si' ? 'default' : 'outline'}
          size="lg"
          onClick={handleRevisarPagos}
          className="px-6 py-6 text-base font-semibold"
          title="Ver pagos sin número de crédito asignado"
        >
          <Search className="mr-2 h-5 w-5" />
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
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            ) : (
              <Download className="mr-2 h-5 w-5" />
            )}
            Descargar Excel
          </Button>
        )}
        <Popover open={agregarPagoOpen} onOpenChange={setAgregarPagoOpen}>
          <PopoverTrigger asChild>
            <Button
              size="lg"
              className="min-w-[200px] bg-primary px-8 py-6 text-base font-semibold text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="mr-2 h-5 w-5" />
              Agregar pago
              <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-72 p-3" align="end">
            {gmailStatus && (
              <p className="mb-2 border-b border-gray-100 px-2 py-1.5 text-xs text-gray-600">
                {gmailStatus.last_status === 'error' ? (
                  <span className="text-amber-600">
                    Última sync Gmail falló
                  </span>
                ) : gmailStatus.last_status === 'running' ? (
                  <>
                    Procesando: {gmailStatus.last_emails} correos,{' '}
                    {gmailStatus.last_files} archivos
                  </>
                ) : gmailStatus.last_run ? (
                  <>
                    Última sync: {formatLastSyncDate(gmailStatus.last_run)} -{' '}
                    {gmailStatus.last_emails} correos, {gmailStatus.last_files}{' '}
                    archivos
                    {typeof gmailStatus.last_correos_marcados_revision ===
                      'number' &&
                    gmailStatus.last_correos_marcados_revision > 0 ? (
                      <>
                        <br />
                        <span className="text-emerald-800">
                          {gmailStatus.last_correos_marcados_revision} correo(s)
                          leidos con al menos un comprobante (etiqueta IMAGEN 1
                          / 2 / 3 + estrella).
                        </span>
                      </>
                    ) : null}
                  </>
                ) : (
                  <span className="text-gray-500">Sin sync Gmail aún</span>
                )}
              </p>
            )}
            <div className="space-y-2">
              <a
                href={`${BASE_PATH}/${SEGMENTO_INFOPAGOS}`.replace(/\/+/g, '/')}
                target="_blank"
                rel="noreferrer"
                className="flex w-full items-center gap-3 rounded-md px-4 py-3 text-left hover:bg-blue-50"
                onClick={() => setAgregarPagoOpen(false)}
              >
                <Edit className="h-5 w-5 text-gray-600" />
                <span>Registrar un pago</span>
                <span className="ml-auto text-xs text-gray-500">
                  Infopagos (un solo flujo)
                </span>
              </a>
              <button
                type="button"
                className="flex w-full items-center gap-3 rounded-md px-4 py-3 text-left hover:bg-blue-50"
                onClick={() => {
                  setAgregarPagoOpen(false)
                  setShowCargaMasivaPagos(true)
                }}
              >
                <FileSpreadsheet className="h-5 w-5 text-gray-600" />
                <span>Pagos desde Excel</span>
                <span className="ml-auto text-xs text-gray-500">
                  Revisar y editar
                </span>
              </button>

              {/* Submenu: Gmail (unico disparo manual: Procesar correos) */}
              <div className="mt-2 border-t border-gray-100 pt-2">
                <button
                  type="button"
                  className="flex w-full items-center gap-3 rounded-md px-4 py-2.5 text-left hover:bg-gray-50"
                  onClick={() => setSubmenuGmailOpen(v => !v)}
                >
                  <Mail className="h-5 w-5 text-gray-600" />
                  <span className="font-medium text-gray-800">
                    Generar Excel desde email
                  </span>
                  <ChevronRight
                    className={cn(
                      'ml-auto h-4 w-4 text-gray-400 transition-transform',
                      submenuGmailOpen && 'rotate-90'
                    )}
                  />
                </button>
                {submenuGmailOpen && (
                  <div className="ml-2 mt-2 space-y-2 rounded-r-md border-l-2 border-gray-200 bg-gray-50/80 py-2 pl-3 pr-2">
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm hover:bg-blue-50 disabled:opacity-50"
                      onClick={handleGenerarExcelDesdeGmail}
                      disabled={loadingGmail}
                    >
                      <Mail className="h-4 w-4 text-gray-600" />
                      <span>
                        {loadingGmail
                          ? `Procesando... (${gmailStatus?.last_emails ?? 0} correos, ${gmailStatus?.last_files ?? 0} archivos)`
                          : 'Procesar correos'}
                      </span>
                      <span className="ml-auto text-xs text-gray-500">
                        Gmail
                      </span>
                    </button>
                    {loadingGmail && (
                      <button
                        type="button"
                        className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm text-amber-800 hover:bg-amber-50"
                        onClick={handleDetenerSeguimientoGmail}
                      >
                        <X className="h-4 w-4 shrink-0" />
                        <span>Detener seguimiento</span>
                      </button>
                    )}
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm hover:bg-blue-50 disabled:opacity-50"
                      onClick={async () => {
                        setAgregarPagoOpen(false)
                        setIsDescargandoGmailExcel(true)
                        try {
                          await pagoService.downloadGmailExcelTemporal()
                          toast.success('Excel descargado')
                          pagoService.getGmailStatus().then(setGmailStatus)
                        } catch (e) {
                          toast.error(getErrorMessage(e))
                        } finally {
                          setIsDescargandoGmailExcel(false)
                        }
                      }}
                      disabled={isDescargandoGmailExcel}
                    >
                      <Download className="h-4 w-4 text-gray-600" />
                      <span>
                        {isDescargandoGmailExcel
                          ? 'Descargando...'
                          : 'Descargar Excel'}
                      </span>
                      <span className="ml-auto text-xs text-gray-500">
                        Gmail
                      </span>
                    </button>
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
                      onClick={() => {
                        setAgregarPagoOpen(false)
                        setShowVaciarTablaGmail(true)
                      }}
                      disabled={isVaciarTablaGmail}
                    >
                      <Trash2 className="h-4 w-4 text-red-600" />
                      <span>
                        {isVaciarTablaGmail ? 'Vaciando...' : 'Vaciar tabla'}
                      </span>
                      <span className="ml-auto text-xs text-gray-500">
                        Gmail
                      </span>
                    </button>
                  </div>
                )}
              </div>

              {SHOW_DESCARGA_EXCEL_EN_SUBMENU && submenuGmailOpen && (
                <button
                  type="button"
                  className="ml-2 flex w-full items-center gap-3 rounded-md border-l-2 border-gray-200 px-4 py-3 pl-5 text-left hover:bg-blue-50 disabled:opacity-50"
                  onClick={async () => {
                    setAgregarPagoOpen(false)
                    setIsDescargandoGmailExcel(true)
                    try {
                      await pagoService.downloadGmailExcel(
                        gmailStatus?.latest_data_date ?? undefined
                      )
                      toast.success('Excel descargado')
                      pagoService.getGmailStatus().then(setGmailStatus)
                    } catch (e) {
                      toast.error(getErrorMessage(e))
                    } finally {
                      setIsDescargandoGmailExcel(false)
                    }
                  }}
                  disabled={
                    isDescargandoGmailExcel || !gmailStatus?.latest_data_date
                  }
                >
                  <Download className="h-5 w-5 text-gray-600" />
                  <span>
                    {isDescargandoGmailExcel
                      ? 'Descargando...'
                      : 'Descargar Excel'}
                  </span>
                  {gmailStatus?.latest_data_date && (
                    <span className="ml-auto text-xs text-gray-500">
                      disponible: {gmailStatus.latest_data_date}
                    </span>
                  )}
                </button>
              )}
            </div>
          </PopoverContent>
        </Popover>
        <Button
          type="button"
          variant="outline"
          size="lg"
          className="px-6 py-6 text-base font-semibold"
          onClick={abrirReemplazarPagos}
        >
          <span
            className="mr-2 inline-flex h-5 w-5 shrink-0 items-center justify-center text-xl font-semibold leading-none"
            aria-hidden
          >
            -
          </span>
          Reemplazar pagos
        </Button>
      </div>
      <Dialog
        open={reemplazarPagosOpen}
        onOpenChange={open => {
          if (!open) cerrarReemplazarPagos()
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Reemplazar pagos</DialogTitle>
          </DialogHeader>
          {reemplazarStep === 'cedula' && (
            <div className="space-y-4 py-2">
              <p className="text-sm text-gray-600">
                Ingrese la cédula del cliente. Solo se consideran préstamos en
                estado APROBADO.
              </p>
              <Input
                placeholder="Cédula"
                value={cedulaReemplazo}
                onChange={e => setCedulaReemplazo(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void handleBuscarPrestamosReemplazo()
                  }
                }}
                autoFocus
              />
              <DialogFooter className="gap-2 sm:gap-0">
                <Button
                  type="button"
                  variant="outline"
                  onClick={cerrarReemplazarPagos}
                  disabled={loadingReemplazo}
                >
                  Cancelar
                </Button>
                <Button
                  type="button"
                  onClick={() => void handleBuscarPrestamosReemplazo()}
                  disabled={loadingReemplazo}
                >
                  {loadingReemplazo ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Buscando...
                    </>
                  ) : (
                    'Continuar'
                  )}
                </Button>
              </DialogFooter>
            </div>
          )}
          {reemplazarStep === 'elegir' && (
            <div className="space-y-4 py-2">
              <p className="text-sm text-gray-600">
                Hay {prestamosReemplazo.length} préstamos aprobados. Elija el
                crédito cuyos pagos desea borrar y reemplazar.
              </p>
              <Select
                value={
                  prestamoIdReemplazo != null ? String(prestamoIdReemplazo) : ''
                }
                onValueChange={v => setPrestamoIdReemplazo(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccione préstamo" />
                </SelectTrigger>
                <SelectContent>
                  {prestamosReemplazo.map(p => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      #{p.id} {p.modelo_vehiculo || p.producto || 'Préstamo'} -{' '}
                      {p.nombres}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <DialogFooter className="gap-2 sm:gap-0">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setReemplazarStep('cedula')
                    setPrestamoIdReemplazo(null)
                  }}
                  disabled={loadingReemplazo}
                >
                  Atrás
                </Button>
                <Button
                  type="button"
                  onClick={() => {
                    if (prestamoIdReemplazo == null) {
                      toast.error('Seleccione un préstamo')
                      return
                    }
                    setReemplazarStep('confirmar')
                  }}
                  disabled={loadingReemplazo || prestamoIdReemplazo == null}
                >
                  Continuar
                </Button>
              </DialogFooter>
            </div>
          )}
          {reemplazarStep === 'confirmar' &&
            prestamoIdReemplazo != null &&
            prestamoReemplazoSeleccionado && (
              <div className="space-y-4 py-2">
                <p className="text-sm text-gray-700">
                  ¿Desea borrar <strong>todos los pagos</strong> de la cédula{' '}
                  <strong>{prestamoReemplazoSeleccionado.cedula}</strong> en el
                  préstamo <strong>#{prestamoIdReemplazo}</strong>
                  {prestamoReemplazoSeleccionado.modelo_vehiculo
                    ? ` (${prestamoReemplazoSeleccionado.modelo_vehiculo})`
                    : ''}
                  ? Luego podrá cargar los pagos desde Excel con el flujo
                  habitual.
                </p>
                <DialogFooter className="gap-2 sm:gap-0">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      setReemplazarStep(
                        prestamosReemplazo.length > 1 ? 'elegir' : 'cedula'
                      )
                    }
                    disabled={loadingReemplazo}
                  >
                    Atrás
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    onClick={() => void handleConfirmarReemplazarPagos()}
                    disabled={loadingReemplazo}
                  >
                    {loadingReemplazo ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Borrando...
                      </>
                    ) : (
                      'Sí, borrar todos los pagos'
                    )}
                  </Button>
                </DialogFooter>
              </div>
            )}
        </DialogContent>
      </Dialog>
      {/* Después de importar desde Cobros: si hay errores, ofrecer descargar Excel de esta importación (datos_importados_conerrores) */}
      {lastImportCobrosResult &&
        lastImportCobrosResult.registros_con_error > 0 && (
          <Card className="border-amber-200 bg-amber-50">
            <CardContent className="flex flex-wrap items-center gap-3 py-3">
              <span className="text-sm text-amber-800">
                {lastImportCobrosResult.registros_procesados} importados
                {typeof lastImportCobrosResult.cuotas_aplicadas === 'number' &&
                  lastImportCobrosResult.cuotas_aplicadas > 0 && (
                    <>
                      {' '}
                      ({lastImportCobrosResult.cuotas_aplicadas} operaciones en
                      cuotas
                      {typeof lastImportCobrosResult.pagos_con_aplicacion_a_cuotas ===
                      'number'
                        ? `, ${lastImportCobrosResult.pagos_con_aplicacion_a_cuotas} pago(s) con aplicación`
                        : ''}
                      )
                    </>
                  )}
                ; {lastImportCobrosResult.registros_con_error} con error (no
                cumplen reglas de carga masiva). Descargue el Excel para revisar
                y corregir.
              </span>
              <Button
                variant="outline"
                size="sm"
                className="border-amber-400 text-amber-800 hover:bg-amber-100"
                onClick={handleDescargarExcelErroresCobros}
                disabled={isDescargandoExcelCobrosErrores}
              >
                {isDescargandoExcelCobrosErrores ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-1 h-4 w-4" />
                )}
                Descargar Excel (errores de esta importación)
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setLastImportCobrosResult(null)}
              >
                Ocultar
              </Button>
            </CardContent>
          </Card>
        )}
      {lastImportCobrosResult &&
        (lastImportCobrosResult.pagos_sin_aplicacion_cuotas_total ?? 0) > 0 && (
          <Card className="border-orange-200 bg-orange-50">
            <CardContent className="flex flex-col gap-2 py-3">
              <span className="text-sm font-medium text-orange-900">
                {lastImportCobrosResult.pagos_sin_aplicacion_cuotas_total}{' '}
                pago(s) importado(s) sin aplicar a cuotas
                {lastImportCobrosResult.pagos_sin_aplicacion_cuotas_truncados
                  ? ' (lista truncada)'
                  : ''}
              </span>
              <p className="text-xs text-orange-800">
                Revise cuotas del préstamo o use «Aplicar a cuotas» en la fila
                del pago. Detalle:
              </p>
              <ul className="max-h-32 list-disc overflow-y-auto pl-5 text-xs text-orange-900">
                {(lastImportCobrosResult.pagos_sin_aplicacion_cuotas ?? []).map(
                  (row, i) => (
                    <li key={`${row.pago_id ?? i}-${row.cedula_cliente}`}>
                      {row.pago_id != null ? `#${row.pago_id}` : '-'} ·{' '}
                      {row.cedula_cliente || '-'} · préstamo{' '}
                      {row.prestamo_id ?? '-'} · {row.motivo}: {row.detalle}
                    </li>
                  )
                )}
              </ul>
              <Button
                variant="ghost"
                size="sm"
                className="self-start"
                onClick={() => setLastImportCobrosResult(null)}
              >
                Ocultar
              </Button>
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
              <div className="flex flex-col flex-wrap gap-4 sm:flex-row">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Conciliación
                  </label>
                  <Select
                    value={filters.conciliado || 'si'}
                    onValueChange={value =>
                      handleFilterChange('conciliado', value)
                    }
                  >
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
                <div className="min-w-[200px] flex-1">
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Buscar por cédula
                  </label>
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
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFilterChange('cedula', '')}
                    >
                      <X className="mr-1 h-4 w-4" />
                      Limpiar búsqueda
                    </Button>
                  </div>
                )}
                {filters.sin_prestamo === 'si' && (
                  <div className="flex items-end">
                    <Badge className="bg-amber-500 px-3 py-1.5 text-white">
                      Sin crédito asignado
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFilterChange('sin_prestamo', '')}
                      className="ml-2"
                    >
                      <X className="mr-1 h-4 w-4" />
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
                      {activeFiltersCount}{' '}
                      {activeFiltersCount === 1
                        ? 'filtro activo'
                        : 'filtros activos'}
                    </Badge>
                  )}
                </div>
                <div className="flex gap-2">
                  {activeFiltersCount > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleClearFilters}
                    >
                      <X className="mr-1 h-4 w-4" />
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
                  <div className="grid grid-cols-1 gap-4 border-t pt-4 md:grid-cols-2 lg:grid-cols-5">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Cédula de identidad
                      </label>
                      <Input
                        placeholder="Cédula"
                        value={filters.cedula}
                        onChange={e =>
                          handleFilterChange('cedula', e.target.value)
                        }
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Estado
                      </label>
                      <Select
                        value={filters.estado || 'all'}
                        onValueChange={value =>
                          handleFilterChange('estado', value)
                        }
                      >
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
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Fecha desde
                      </label>
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />
                        <Input
                          type="date"
                          value={filters.fechaDesde}
                          onChange={e =>
                            handleFilterChange('fechaDesde', e.target.value)
                          }
                          className="pl-10"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Fecha hasta
                      </label>
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />
                        <Input
                          type="date"
                          value={filters.fechaHasta}
                          onChange={e =>
                            handleFilterChange('fechaHasta', e.target.value)
                          }
                          className="pl-10"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Analista
                      </label>
                      <Input
                        placeholder="Analista"
                        value={filters.analista}
                        onChange={e =>
                          handleFilterChange('analista', e.target.value)
                        }
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
              {!esRevisarPagos && (
                <p className="text-sm text-gray-600">
                  Vista de cartera activa: pagos sin crédito asignado o con
                  préstamo en estado <strong>Aprobado</strong>. No se listan
                  pagos de créditos liquidados u otros estados (use
                  exportación/API con{' '}
                  <code className="rounded bg-gray-100 px-1 text-xs">
                    prestamo_cartera=todos
                  </code>{' '}
                  si necesita el histórico completo).
                </p>
              )}
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="py-12 text-center">
                  <div className="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"></div>
                  <p className="text-gray-500">Cargando pagos...</p>
                </div>
              ) : isError ? (
                <div className="py-12 text-center">
                  <AlertCircle className="mx-auto mb-4 h-12 w-12 text-red-500" />
                  <p className="mb-2 font-semibold text-red-600">
                    Error al cargar los pagos
                  </p>
                  <p className="text-sm text-gray-600">
                    {error instanceof Error
                      ? error.message
                      : 'Error desconocido'}
                  </p>
                  <Button
                    className="mt-4"
                    onClick={() =>
                      queryClient.refetchQueries({
                        queryKey: esRevisarPagos
                          ? ['pagos-con-errores']
                          : ['pagos'],
                        exact: false,
                      })
                    }
                  >
                    Reintentar
                  </Button>
                </div>
              ) : !data?.pagos || data.pagos.length === 0 ? (
                <div className="py-12 text-center">
                  <CreditCard className="mx-auto mb-4 h-12 w-12 text-gray-400" />
                  <p className="mb-2 font-semibold text-gray-600">
                    No se encontraron pagos
                  </p>
                  <p className="text-sm text-gray-500">
                    {data?.total === 0
                      ? 'No hay pagos registrados en el sistema.'
                      : 'No hay pagos que coincidan con los filtros aplicados.'}
                  </p>
                  {(filters.cedula ||
                    filters.estado ||
                    filters.fechaDesde ||
                    filters.fechaHasta ||
                    filters.analista ||
                    (filters.conciliado && filters.conciliado !== 'si') ||
                    filters.sin_prestamo === 'si') && (
                    <Button
                      className="mt-4"
                      variant="outline"
                      onClick={handleClearFilters}
                    >
                      Limpiar Filtros
                    </Button>
                  )}
                  {resumenTotalCedula && (
                    <p className="mt-4 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950">
                      <span className="font-semibold">
                        Total monto (cédula + filtros):
                      </span>{' '}
                      ${resumenTotalCedula.sum.toFixed(2)} -{' '}
                      {resumenTotalCedula.cantidad} pago(s)
                    </p>
                  )}
                </div>
              ) : (
                <>
                  <div className="overflow-hidden rounded-lg border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>Cédula</TableHead>
                          <TableHead>Crédito</TableHead>
                          <TableHead>Estado</TableHead>
                          {esRevisarPagos && (
                            <TableHead>Observaciones</TableHead>
                          )}
                          <TableHead>Monto</TableHead>
                          <TableHead>Fecha Pago</TableHead>
                          <TableHead>Nº Documento</TableHead>
                          <TableHead>Conciliado</TableHead>
                          <TableHead>Recibo cobros</TableHead>
                          <TableHead className="text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.pagos.map((pago: Pago) => {
                          const docKey = claveDocumentoPagoListaNormalizada(
                            pago.numero_documento,
                            pago.codigo_documento ?? null
                          )
                          const documentoDuplicadoEnVista =
                            Boolean(docKey) &&
                            documentosDuplicadosEnPagina.has(docKey)
                          return (
                            <TableRow key={pago.id}>
                              <TableCell>{pago.id}</TableCell>
                              <TableCell>{pago.cedula_cliente}</TableCell>
                              <TableCell>
                                {pago.prestamo_id ? (
                                  <span className="text-sm font-medium">
                                    #{pago.prestamo_id}
                                  </span>
                                ) : (
                                  <span className="text-sm text-amber-600">
                                    Sin asignar
                                  </span>
                                )}
                              </TableCell>
                              <TableCell>
                                {getEstadoBadge(pago.estado)}
                              </TableCell>
                              {esRevisarPagos && (
                                <TableCell className="text-xs text-amber-700">
                                  {(pago as PagoConError).observaciones ?? '-'}
                                </TableCell>
                              )}
                              <TableCell>
                                $
                                {typeof pago.monto_pagado === 'number'
                                  ? pago.monto_pagado.toFixed(2)
                                  : parseFloat(
                                      String(pago.monto_pagado || 0)
                                    ).toFixed(2)}
                              </TableCell>
                              <TableCell>
                                {formatDate(pago.fecha_pago)}
                              </TableCell>
                              <TableCell
                                className={cn(
                                  documentoDuplicadoEnVista &&
                                    'bg-orange-100 text-orange-950 dark:bg-orange-950/35 dark:text-orange-100'
                                )}
                                title={
                                  documentoDuplicadoEnVista
                                    ? 'Advertencia: misma clave comprobante + código aparece más de una vez en esta página.'
                                    : undefined
                                }
                              >
                                {textoDocumentoPagoParaListado(
                                  pago.numero_documento,
                                  pago.codigo_documento
                                )}
                              </TableCell>
                              <TableCell>
                                {pago.verificado_concordancia === 'SI' ||
                                pago.conciliado ? (
                                  <Badge className="bg-green-500 text-white">
                                    SI
                                  </Badge>
                                ) : (
                                  <Badge className="bg-gray-500 text-white">
                                    NO
                                  </Badge>
                                )}
                              </TableCell>
                              <TableCell>
                                {pago.pago_reportado_id != null &&
                                pago.pago_reportado_id > 0 ? (
                                  <Link
                                    to={`/cobros/pagos-reportados/${pago.pago_reportado_id}`}
                                    className="inline-flex items-center gap-1 text-sm font-medium text-violet-700 hover:text-violet-900"
                                  >
                                    Ver recibo
                                  </Link>
                                ) : (
                                  (() => {
                                    const u =
                                      (pago.link_comprobante || '').trim() ||
                                      (pago.documento_ruta || '').trim()
                                    return u ? (
                                      <a
                                        href={u}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 text-sm font-medium text-violet-700 hover:text-violet-900"
                                        title="Comprobante en Drive (import Gmail)"
                                      >
                                        <Eye className="h-4 w-4" />
                                        Ver en Drive
                                      </a>
                                    ) : (
                                      <span className="text-sm text-gray-500">
                                        -
                                      </span>
                                    )
                                  })()
                                )}
                              </TableCell>
                              <TableCell className="text-right">
                                <Popover
                                  open={accionesOpenId === pago.id}
                                  onOpenChange={open =>
                                    setAccionesOpenId(open ? pago.id : null)
                                  }
                                >
                                  <PopoverTrigger asChild>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      title="Acciones"
                                      className="h-8 w-8 p-0"
                                    >
                                      <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                  </PopoverTrigger>
                                  <PopoverContent
                                    className="w-56 p-2"
                                    align="end"
                                  >
                                    <div className="space-y-0.5">
                                      <button
                                        type="button"
                                        className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-gray-100"
                                        onClick={() => {
                                          setPagoEditando(pago)
                                          setShowRegistrarPago(true)
                                          setAccionesOpenId(null)
                                        }}
                                      >
                                        <Edit className="h-4 w-4 text-gray-600" />
                                        Editar
                                      </button>
                                      <button
                                        type="button"
                                        className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50"
                                        onClick={async () => {
                                          setAccionesOpenId(null)
                                          if (
                                            window.confirm(
                                              `¿Estás seguro de eliminar el pago ID ${pago.id}?`
                                            )
                                          ) {
                                            try {
                                              if (esRevisarPagos) {
                                                await pagoConErrorService.delete(
                                                  pago.id
                                                )
                                              } else {
                                                await pagoService.deletePago(
                                                  pago.id
                                                )
                                              }
                                              toast.success(
                                                'Pago eliminado exitosamente'
                                              )
                                              await invalidatePagosPrestamosRevisionYCuotas(
                                                queryClient
                                              )
                                            } catch (error) {
                                              toast.error(
                                                'Error al eliminar el pago'
                                              )
                                              if (import.meta.env.DEV)
                                                console.error(
                                                  'Error al eliminar el pago',
                                                  error
                                                )
                                            }
                                          }
                                        }}
                                      >
                                        <Trash2 className="h-4 w-4" />
                                        Eliminar
                                      </button>
                                      {pago.verificado_concordancia === 'SI' ||
                                      pago.conciliado ? (
                                        <button
                                          type="button"
                                          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-amber-700 transition-colors hover:bg-amber-50"
                                          disabled={conciliandoId === pago.id}
                                          onClick={async () => {
                                            setAccionesOpenId(null)
                                            setConciliandoId(pago.id)
                                            try {
                                              await pagoService.updateConciliado(
                                                pago.id,
                                                false
                                              )
                                              toast.success(
                                                'Pago marcado como NO conciliado'
                                              )
                                              await invalidatePagosPrestamosRevisionYCuotas(
                                                queryClient
                                              )
                                            } catch (error) {
                                              toast.error(
                                                'Error al actualizar conciliación'
                                              )
                                              if (import.meta.env.DEV)
                                                console.error(
                                                  'Error al actualizar conciliación',
                                                  error
                                                )
                                            } finally {
                                              setConciliandoId(null)
                                            }
                                          }}
                                        >
                                          <XCircle className="h-4 w-4" />
                                          {conciliandoId === pago.id
                                            ? 'Actualizando...'
                                            : 'Conciliar: No'}
                                        </button>
                                      ) : (
                                        <button
                                          type="button"
                                          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-green-700 transition-colors hover:bg-green-50"
                                          disabled={conciliandoId === pago.id}
                                          onClick={async () => {
                                            setAccionesOpenId(null)
                                            setConciliandoId(pago.id)
                                            try {
                                              await pagoService.updateConciliado(
                                                pago.id,
                                                true
                                              )
                                              if (pago.prestamo_id) {
                                                try {
                                                  const res =
                                                    await pagoService.aplicarPagoACuotas(
                                                      pago.id
                                                    )
                                                  if (res.ya_aplicado) {
                                                    toast.success(res.message)
                                                  } else if (
                                                    res.cuotas_completadas >
                                                      0 ||
                                                    res.cuotas_parciales > 0
                                                  ) {
                                                    toast.success(
                                                      `Conciliado. ${res.message}`
                                                    )
                                                  } else {
                                                    toast.success(
                                                      'Pago marcado como conciliado'
                                                    )
                                                  }
                                                } catch (applyErr) {
                                                  if (
                                                    isAxiosError(applyErr) &&
                                                    applyErr.response
                                                      ?.status === 409
                                                  ) {
                                                    toast.error(
                                                      getErrorMessage(applyErr)
                                                    )
                                                  } else {
                                                    toast.success(
                                                      'Pago marcado como conciliado'
                                                    )
                                                  }
                                                }
                                              } else {
                                                toast.success(
                                                  'Pago marcado como conciliado'
                                                )
                                              }
                                              await invalidatePagosPrestamosRevisionYCuotas(
                                                queryClient,
                                                { includeDashboardMenu: true }
                                              )
                                            } catch (error) {
                                              toast.error(
                                                'Error al actualizar conciliación'
                                              )
                                              if (import.meta.env.DEV)
                                                console.error(
                                                  'Error al actualizar conciliación',
                                                  error
                                                )
                                            } finally {
                                              setConciliandoId(null)
                                            }
                                          }}
                                        >
                                          <CheckCircle className="h-4 w-4" />
                                          {conciliandoId === pago.id
                                            ? 'Actualizando...'
                                            : 'Conciliar: Sí'}
                                        </button>
                                      )}
                                    </div>
                                  </PopoverContent>
                                </Popover>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                  {resumenTotalCedula && (
                    <div
                      className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950"
                      role="status"
                    >
                      <span>
                        <span className="font-semibold">
                          Total para cédula filtrada:
                        </span>{' '}
                        {resumenTotalCedula.cedula}
                      </span>
                      <span>
                        <span className="font-semibold">Suma de montos:</span> $
                        {resumenTotalCedula.sum.toFixed(2)} -{' '}
                        {resumenTotalCedula.cantidad} pago(s) con los filtros
                        actuales (incluye todas las páginas)
                      </span>
                    </div>
                  )}
                  {/* Paginación (mismo formato que Préstamos) */}
                  {data.total_pages > 1 && (
                    <div className="mt-4 flex items-center justify-between">
                      <div className="text-sm text-gray-600">
                        Página {data.page} de {data.total_pages} ({data.total}{' '}
                        total)
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
                          onClick={() =>
                            setPage(p => Math.min(data.total_pages, p + 1))
                          }
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
          pagoInicial={
            pagoEditando
              ? {
                  cedula_cliente: pagoEditando.cedula_cliente,
                  prestamo_id: pagoEditando.prestamo_id,
                  fecha_pago:
                    typeof pagoEditando.fecha_pago === 'string'
                      ? pagoEditando.fecha_pago.split('T')[0]
                      : new Date(pagoEditando.fecha_pago)
                          .toISOString()
                          .split('T')[0],
                  monto_pagado:
                    pagoEditando.moneda_registro === 'BS' &&
                    pagoEditando.monto_bs_original != null
                      ? Number(pagoEditando.monto_bs_original)
                      : pagoEditando.monto_pagado,
                  monto_bs_original: pagoEditando.monto_bs_original ?? null,
                  moneda_registro:
                    pagoEditando.moneda_registro === 'BS' ? 'BS' : 'USD',
                  numero_documento: pagoEditando.numero_documento,
                  codigo_documento: pagoEditando.codigo_documento ?? null,
                  institucion_bancaria: pagoEditando.institucion_bancaria,
                  notas: pagoEditando.notas || null,
                }
              : undefined
          }
          onClose={() => {
            setShowRegistrarPago(false)
            setPagoEditando(null)
          }}
          onSuccess={async () => {
            setShowRegistrarPago(false)
            setPagoEditando(null)
            try {
              await invalidatePagosPrestamosRevisionYCuotas(queryClient, {
                includeDashboardMenu: true,
              })
              await queryClient.refetchQueries({
                queryKey: ['cuotas-prestamo'],
                exact: false,
              })
              await queryClient.refetchQueries({
                queryKey: ['pagos-kpis'],
                exact: false,
              })
              await queryClient.refetchQueries({
                queryKey: ['pagos'],
                exact: false,
              })
              await queryClient.refetchQueries({
                queryKey: ['pagos'],
                exact: false,
                type: 'active',
              })
              toast.success(
                'Pago registrado exitosamente. El dashboard se ha actualizado.'
              )
            } catch (error) {
              if (import.meta.env.DEV)
                console.error('Error actualizando dashboard:', error)
              toast.error(
                'Pago registrado, pero hubo un error al actualizar el dashboard'
              )
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
            await invalidatePagosPrestamosRevisionYCuotas(queryClient, {
              includeDashboardMenu: true,
            })
            await queryClient.refetchQueries({
              queryKey: ['pagos'],
              exact: false,
            })
            await queryClient.refetchQueries({
              queryKey: ['pagos-kpis'],
              exact: false,
            })
            toast.success('Datos actualizados correctamente')
          }}
        />
      )}
      <Dialog
        open={showVaciarTablaGmail}
        onOpenChange={setShowVaciarTablaGmail}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Vaciar tabla Gmail</DialogTitle>
          </DialogHeader>
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
              {isVaciarTablaGmail ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Vaciar tabla
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
