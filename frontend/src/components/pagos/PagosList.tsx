import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
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
  FileText,
  RotateCcw,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { ListPaginationBar } from '../../components/ui/ListPaginationBar'
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
import { fechaPagoParaInputDate } from '../../utils/fechaZona'
import { pagoService, type Pago } from '../../services/pagoService'
import { prestamoService } from '../../services/prestamoService'
import type { Prestamo } from '../../types'
import {
  pagoConErrorService,
  type PagoConError,
} from '../../services/pagoConErrorService'
import {
  deleteInfopagosBorradorEscaneer,
  listInfopagosBorradoresEscaneer,
  type InfopagosBorradorListItem,
} from '../../services/cobrosService'
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
import { eliminarPagoRevisionOConError } from '../../utils/eliminarPagoRevision'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { SEGMENTO_INFOPAGOS } from '../../constants/rutasIngresoPago'
import { BASE_PATH } from '../../config/env'
import { REVISION_MANUAL_MODULE_ENABLED } from '../../config/revisionManualModule'
import { useSimpleAuth } from '../../store/simpleAuthStore'
import { isAdminRole, isManagerRole, isOperatorRole } from '../../utils/rol'
import {
  gmailRunSummaryHeadline,
  gmailRunSummaryLines,
  gmailRunningProgressLabel,
  useGmailPipeline,
  type GmailRunSummary,
} from '../../hooks/useGmailPipeline'

import { invalidatePagosPrestamosRevisionYCuotas } from '../../constants/queryKeys'
import {
  claveDocumentoPagoListaNormalizada,
  textoDocumentoPagoParaListado,
} from '../../utils/pagoExcelValidation'
import {
  abrirStaffComprobanteDesdeHref,
  esUrlComprobanteImagenConAuth,
  fetchStaffComprobanteBlobWithDisplayMime,
} from '../../utils/comprobanteImagenAuth'
import {
  GMAIL_METRICS_SNAPSHOT_KEY,
  OBSERVACION_COL_PAGO_DUPLICADO,
  observacionesConMarcaDuplicadoCartera,
  pagoElegibleConciliarAplicar,
  pagoEstaCerradoSoloConsulta,
} from './pagosList/pagosListUtils'
import { ReemplazarPagosDialog } from './pagosList/ReemplazarPagosDialog'
import { StaffComprobanteDock } from './pagosList/StaffComprobanteDock'
import { PagosRevisionTab } from './pagosList/PagosRevisionTab'
import { useStaffComprobantePreview } from './pagosList/useStaffComprobantePreview'

export function PagosList() {
  const { user } = useSimpleAuth()
  const puedeVerRevisionManualPagos =
    isAdminRole(user?.rol) || isManagerRole(user?.rol)
  const accesoDetallePorCliente =
    puedeVerRevisionManualPagos || isOperatorRole(user?.rol)

  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('resumen')
  const [page, setPage] = useState(1)
  const [perPage] = useState(10)
  const [showFilters, setShowFilters] = useState(false)
  const [deepLinkIdentidad, setDeepLinkIdentidad] = useState<{
    cedula: string
    pagoId: string
    prestamoId: string
  }>({ cedula: '', pagoId: '', prestamoId: '' })
  const [filters, setFilters] = useState({
    cedula: '',
    estado: '',
    fechaDesde: '',
    fechaHasta: '',
    analista: '',
    conciliado: 'si', // Por defecto: solo conciliados = SI
    sin_prestamo: '', // si = solo pagos sin crédito asignado
    prestamo_id: '',
    prestamo_cartera: '',
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
  const [showVaciarTablaGmail, setShowVaciarTablaGmail] = useState(false)
  const [isVaciarTablaGmail, setIsVaciarTablaGmail] = useState(false)
  const [submenuGmailOpen, setSubmenuGmailOpen] = useState(false)
  const [gmailMetricsSnapshot, setGmailMetricsSnapshot] = useState<{
    lastRun: string | null
    summary: GmailRunSummary | null
  }>(() => {
    try {
      const raw = window.localStorage.getItem(GMAIL_METRICS_SNAPSHOT_KEY)
      if (!raw) return { lastRun: null, summary: null }
      const parsed = JSON.parse(raw) as {
        lastRun?: string | null
        summary?: GmailRunSummary | null
      }
      return {
        lastRun: typeof parsed.lastRun === 'string' ? parsed.lastRun : null,
        summary: parsed.summary ?? null,
      }
    } catch {
      return { lastRun: null, summary: null }
    }
  })
  const [includeRevisionExportados, setIncludeRevisionExportados] =
    useState(false)
  const [revisionGlobalPage, setRevisionGlobalPage] = useState(1)
  const [revisionGlobalCedulaInput, setRevisionGlobalCedulaInput] = useState('')
  const [revisionGlobalCedulaFiltro, setRevisionGlobalCedulaFiltro] =
    useState('')
  const [
    revisionGlobalNumeroDocumentoInput,
    setRevisionGlobalNumeroDocumentoInput,
  ] = useState('')
  const [
    revisionGlobalNumeroDocumentoFiltro,
    setRevisionGlobalNumeroDocumentoFiltro,
  ] = useState('')
  const [revisionGlobalFechaPagoInput, setRevisionGlobalFechaPagoInput] =
    useState('')
  const [revisionGlobalFechaPagoFiltro, setRevisionGlobalFechaPagoFiltro] =
    useState('')
  const [revisionGlobalMotivoFiltro, setRevisionGlobalMotivoFiltro] = useState<
    | ''
    | 'sin_credito'
    | 'duplicado'
    | 'irreal'
    | 'sin_aplicacion'
    | 'con_notas'
    | 'rebasa_total'
  >('')
  const [revisionGlobalEstadoFiltro, setRevisionGlobalEstadoFiltro] = useState<
    '' | 'PENDIENTE'
  >('PENDIENTE')
  const [editingGlobalId, setEditingGlobalId] = useState<number | null>(null)
  const [globalNotaDraft, setGlobalNotaDraft] = useState('')
  const [savingGlobalId, setSavingGlobalId] = useState<number | null>(null)
  const [deletingGlobalId, setDeletingGlobalId] = useState<number | null>(null)
  const [selectedGlobalIds, setSelectedGlobalIds] = useState<Set<number>>(
    new Set()
  )
  const [isBulkScanningGlobal, setIsBulkScanningGlobal] = useState(false)
  const [bulkGlobalNota, setBulkGlobalNota] = useState('')
  const [isBulkSavingGlobal, setIsBulkSavingGlobal] = useState(false)
  const [isBulkDeletingGlobal, setIsBulkDeletingGlobal] = useState(false)
  const syncingRevisionRef = useRef(false)
  const queryClient = useQueryClient()

  const {
    staffComprobantePreview,
    setStaffComprobantePreview,
    closeStaffComprobanteListPreview,
    openStaffComprobanteForList,
    dockStaffComprobante,
  } = useStaffComprobantePreview()

  const sincronizarPendientesRevision = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (syncingRevisionRef.current) return
      syncingRevisionRef.current = true
      try {
        const mig = await pagoService.migrarPendientesGmailAConErrores()
        if ((mig.migrados ?? 0) > 0 && !opts?.silent) {
          toast.success(
            `${mig.migrados} pago(s) no válido(s) enviados a Pendientes de revisión`
          )
        }
        await queryClient.invalidateQueries({
          queryKey: ['pagos-con-errores'],
          exact: false,
        })
        await queryClient.invalidateQueries({
          queryKey: ['pagos-con-errores-tab'],
          exact: false,
        })
      } catch {
        if (!opts?.silent) {
          toast.error(
            'No se pudo sincronizar pendientes de Gmail. Reintente en unos segundos.'
          )
        }
      } finally {
        syncingRevisionRef.current = false
      }
    },
    [queryClient]
  )

  const {
    loading: loadingGmail,
    pollGaveUp: gmailPollGaveUp,
    gmailStatus,
    setGmailStatus,
    run: runGmail,
    startPolling: startGmailPolling,
    stopPolling: stopGmailPolling,
  } = useGmailPipeline({
    onStatusUpdate: s => setGmailStatus(s),
    onDone: async s => {
      try {
        const invalidos =
          typeof s?.last_run_summary?.pagos_invalidos_pendientes_revision ===
          'number'
            ? s.last_run_summary.pagos_invalidos_pendientes_revision
            : 0
        if (invalidos > 0) {
          await sincronizarPendientesRevision()
        }
      } catch (e) {
        toast.error(
          'La corrida Gmail terminó, pero falló el envío de pendientes a revisión.'
        )
      } finally {
        void invalidatePagosPrestamosRevisionYCuotas(queryClient)
      }
    },
  })

  // Cargar estado Gmail una vez al montar; reanudar polling solo si quedó running.
  // No depender de startGmailPolling: al terminar el tope de espera (30 min) loading
  // vuelve a false, cambia la referencia del callback y este efecto reiniciaba el polling en bucle.
  useEffect(() => {
    let cancelled = false
    pagoService
      .getGmailStatus()
      .then(s => {
        if (cancelled) return
        setGmailStatus(s)
        if (s.last_status === 'running') {
          startGmailPolling('all')
        }
      })
      .catch(() => {
        if (!cancelled) setGmailStatus(null)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al montar PagosList
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

  useEffect(() => {
    const summary = gmailStatus?.last_run_summary ?? null
    if (!summary) return
    const next = {
      lastRun: gmailStatus?.last_run ?? null,
      summary,
    }
    setGmailMetricsSnapshot(next)
    try {
      window.localStorage.setItem(
        GMAIL_METRICS_SNAPSHOT_KEY,
        JSON.stringify(next)
      )
    } catch {
      // storage puede estar restringido; el fallback en memoria igual mantiene sesión actual
    }
  }, [gmailStatus?.last_run, gmailStatus?.last_run_summary])

  const bannerSummary =
    gmailStatus?.last_run_summary ?? gmailMetricsSnapshot.summary
  const bannerLastRun = gmailStatus?.last_run ?? gmailMetricsSnapshot.lastRun

  useEffect(() => {
    if (activeTab !== 'revision') return
    void sincronizarPendientesRevision({ silent: true })
  }, [activeTab, sincronizarPendientesRevision])

  const handleDetenerSeguimientoGmail = () => {
    stopGmailPolling()
    toast.info('Seguimiento detenido')
  }

  const textoProximoEscaneoGmailServidor = (iso: string | null | undefined) => {
    if (!iso) return ''
    const d = new Date(iso)
    return Number.isNaN(d.getTime())
      ? iso
      : d.toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })
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
      if (result.pipeline_running) {
        toast(
          'Sigue un proceso Gmail en curso en el servidor. Espere a que termine antes de generar de nuevo o recibirá "sincronización en curso" (409).',
          { duration: 10000 }
        )
      }
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
        Observaciones: observacionesConMarcaDuplicadoCartera(p as PagoConError),
      }))
      const nombre = `Revision_Pagos_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(datos, 'Revisión pagos', nombre)
      const ids = pagos.map(p => p.id)
      await pagoConErrorService.archivarPorDescarga(ids)
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      toast.success(
        `${pagos.length} pagos exportados y archivados para trazabilidad`
      )
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
    filters.prestamo_id,
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
      prestamo_id: '',
      prestamo_cartera: '',
    })
    setPage(1)
  }
  const handleRevisarPagos = () => {
    setActiveTab('revision')
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
        Observaciones: observacionesConMarcaDuplicadoCartera(p as PagoConError),
      }))
      const nombre = `Revisar_Pagos_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(datos, 'Revisar Pagos', nombre)
      // Tras guardar el Excel en PC, mover a revisar_pagos para que desaparezcan de la vista
      const ids = pagos.map(p => p.id)
      await pagoConErrorService.archivarPorDescarga(ids)
      void invalidatePagosPrestamosRevisionYCuotas(queryClient)
      toast.success(
        `${pagos.length} pagos exportados y archivados para trazabilidad`
      )
    } catch (err) {
      if (import.meta.env.DEV) console.error('Error al exportar', err)
      toast.error('Error al exportar. Intenta de nuevo.')
    } finally {
      setIsExportingRevisar(false)
    }
  }

  useEffect(() => {
    const pidRaw = (searchParams.get('prestamo_id') || '').trim()
    const pagoRaw = (searchParams.get('pago_id') || '').trim()
    const cedRaw = (searchParams.get('cedula') || '').trim()
    const pidNum = Number(pidRaw)
    const pagoNum = Number(pagoRaw)
    const tienePrestamo =
      pidRaw && Number.isFinite(pidNum) && pidNum >= 1
    const tienePago = pagoRaw && Number.isFinite(pagoNum) && pagoNum >= 1
    if (tienePrestamo || tienePago || cedRaw) {
      setDeepLinkIdentidad({
        cedula: cedRaw,
        pagoId: tienePago ? String(Math.trunc(pagoNum)) : '',
        prestamoId: tienePrestamo ? String(Math.trunc(pidNum)) : '',
      })
      if (tienePrestamo) {
        setFilters(prev => ({
          ...prev,
          prestamo_id: String(Math.trunc(pidNum)),
          prestamo_cartera: 'todos',
        }))
      }
      setActiveTab('resumen')
      setPage(1)
    }
    if (searchParams.get('revisar') === '1') {
      setActiveTab('revision')
      setPage(1)
      setSearchParams({}, { replace: true })
      return
    }
    const pestana = (searchParams.get('pestana') || '').trim().toLowerCase()
    if (
      puedeVerRevisionManualPagos &&
      (pestana === 'revision' || pestana === 'revision-global')
    ) {
      setActiveTab('revision')
    } else if (pestana === 'todos' || pestana === 'lista') {
      setActiveTab('resumen')
    } else if (pestana === 'resumen' || pestana === 'detalle') {
      setActiveTab('resumen')
    }
  }, [searchParams, setSearchParams, puedeVerRevisionManualPagos])

  useEffect(() => {
    if (activeTab === 'revision-global') {
      setActiveTab('revision')
    }
  }, [activeTab])

  useEffect(() => {
    if (
      !puedeVerRevisionManualPagos &&
      (activeTab === 'revision' || activeTab === 'revision-global')
    ) {
      setActiveTab('resumen')
    }
  }, [activeTab, puedeVerRevisionManualPagos])

  const {
    data: revisionGlobalData,
    isLoading: isLoadingRevisionGlobal,
    isError: isRevisionGlobalError,
  } = useQuery({
    queryKey: [
      'pagos-revision-global-tab',
      revisionGlobalPage,
      perPage,
      revisionGlobalCedulaFiltro,
      revisionGlobalNumeroDocumentoFiltro,
      revisionGlobalFechaPagoFiltro,
      revisionGlobalEstadoFiltro,
      revisionGlobalMotivoFiltro,
    ],
    queryFn: () =>
      pagoService.getAllPagos(revisionGlobalPage, perPage, {
        cedula: revisionGlobalCedulaFiltro || undefined,
        estado: revisionGlobalEstadoFiltro || undefined,
        tipoRevision:
          revisionGlobalMotivoFiltro === 'rebasa_total'
            ? 'rebasa_total'
            : undefined,
        fechaDesde: revisionGlobalFechaPagoFiltro || undefined,
        fechaHasta: revisionGlobalFechaPagoFiltro || undefined,
        conciliado: 'all',
        prestamo_cartera: 'todos',
      }),
    enabled: activeTab === 'revision-global',
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  })
  const revisionGlobalRowsAnalizadas = useMemo(() => {
    const rows = revisionGlobalData?.pagos ?? []
    const dupMap = new Map<string, number>()
    for (const p of rows) {
      const f =
        typeof p.fecha_pago === 'string'
          ? p.fecha_pago.slice(0, 10)
          : new Date(p.fecha_pago).toISOString().slice(0, 10)
      const docKey = claveDocumentoPagoListaNormalizada(
        p.numero_documento,
        p.codigo_documento ?? null
      )
      if (!docKey) continue
      const key = `${f}::${docKey}`
      dupMap.set(key, (dupMap.get(key) ?? 0) + 1)
    }
    const filtroDoc = revisionGlobalNumeroDocumentoFiltro.trim().toUpperCase()
    return rows
      .filter(p => {
        if (!filtroDoc) return true
        const txt = textoDocumentoPagoParaListado(
          p.numero_documento,
          p.codigo_documento
        ).toUpperCase()
        return txt.includes(filtroDoc)
      })
      .map(p => {
        const motivos: string[] = []
        const monto = Number(p.monto_pagado ?? 0)
        const fechaPagoDate = new Date(p.fecha_pago as string)
        const hoy = new Date()
        hoy.setHours(0, 0, 0, 0)
        const docKey = claveDocumentoPagoListaNormalizada(
          p.numero_documento,
          p.codigo_documento ?? null
        )
        const fechaKey = Number.isNaN(fechaPagoDate.getTime())
          ? ''
          : fechaPagoDate.toISOString().slice(0, 10)
        const dupKey = docKey && fechaKey ? `${fechaKey}::${docKey}` : ''
        const esDuplicadoFechaNumero = dupKey
          ? (dupMap.get(dupKey) ?? 0) > 1
          : false
        if (monto <= 0) motivos.push('Monto no válido')
        if (!Number.isNaN(fechaPagoDate.getTime()) && fechaPagoDate > hoy) {
          motivos.push('Fecha futura')
        }
        if (esDuplicadoFechaNumero) motivos.push('Duplicado fecha + número')
        if (!p.prestamo_id) motivos.push('Sin crédito asociado')
        if (p.tiene_aplicacion_cuotas === false)
          motivos.push('Sin aplicación a cuotas')
        if ((p.notas ?? '').trim()) motivos.push('Con notas')
        if (Number(p.exceso_sobre_total_usd ?? 0) > 0) {
          motivos.push('Rebasa total del préstamo')
        }
        if (revisionGlobalMotivoFiltro === 'rebasa_total') {
          motivos.push('Rebasa total del préstamo')
        }
        return {
          pago: p,
          motivos,
          score: motivos.length,
          esDuplicadoFechaNumero,
        }
      })
      .sort((a, b) => b.score - a.score || b.pago.id - a.pago.id)
  }, [
    revisionGlobalData?.pagos,
    revisionGlobalNumeroDocumentoFiltro,
    revisionGlobalMotivoFiltro,
  ])
  const revisionGlobalRowsFiltradas = useMemo(() => {
    if (!revisionGlobalMotivoFiltro) return revisionGlobalRowsAnalizadas
    return revisionGlobalRowsAnalizadas.filter(row => {
      if (revisionGlobalMotivoFiltro === 'sin_credito') {
        return row.motivos.includes('Sin crédito asociado')
      }
      if (revisionGlobalMotivoFiltro === 'duplicado') {
        return row.motivos.includes('Duplicado fecha + número')
      }
      if (revisionGlobalMotivoFiltro === 'irreal') {
        return (
          row.motivos.includes('Monto no válido') ||
          row.motivos.includes('Fecha futura')
        )
      }
      if (revisionGlobalMotivoFiltro === 'sin_aplicacion') {
        return row.motivos.includes('Sin aplicación a cuotas')
      }
      if (revisionGlobalMotivoFiltro === 'con_notas') {
        return row.motivos.includes('Con notas')
      }
      if (revisionGlobalMotivoFiltro === 'rebasa_total') {
        return row.motivos.includes('Rebasa total del préstamo')
      }
      return true
    })
  }, [revisionGlobalRowsAnalizadas, revisionGlobalMotivoFiltro])
  useEffect(() => {
    const idsVisibles = new Set(revisionGlobalRowsFiltradas.map(r => r.pago.id))
    setSelectedGlobalIds(prev => {
      const next = new Set<number>()
      prev.forEach(id => {
        if (idsVisibles.has(id)) next.add(id)
      })
      return next
    })
  }, [revisionGlobalRowsFiltradas])
  const resumenRevisionGlobal = useMemo(() => {
    const resumen = {
      duplicados: 0,
      irreales: 0,
      sinCredito: 0,
      sinAplicacion: 0,
      conNotas: 0,
      rebasaTotal: 0,
    }
    for (const row of revisionGlobalRowsAnalizadas) {
      if (row.esDuplicadoFechaNumero) resumen.duplicados += 1
      if (
        row.motivos.includes('Monto no válido') ||
        row.motivos.includes('Fecha futura')
      ) {
        resumen.irreales += 1
      }
      if (row.motivos.includes('Sin crédito asociado')) resumen.sinCredito += 1
      if (row.motivos.includes('Sin aplicación a cuotas'))
        resumen.sinAplicacion += 1
      if (row.motivos.includes('Con notas')) resumen.conNotas += 1
      if (row.motivos.includes('Rebasa total del préstamo')) {
        resumen.rebasaTotal += 1
      }
    }
    return resumen
  }, [revisionGlobalRowsAnalizadas])

  const refetchDiagnosticoRevision = async () => {
    await queryClient.refetchQueries({
      queryKey: ['pagos-con-errores-tab'],
      exact: false,
    })
    await queryClient.refetchQueries({
      queryKey: ['pagos-revision-global-tab'],
      exact: false,
    })
  }

  const handleFilterChange = (key: string, value: string) => {
    // Convertir "all" a cadena vacía para que el servicio no incluya el filtro
    const filterValue = value === 'all' ? '' : value
    setFilters(prev => ({ ...prev, [key]: filterValue }))
    setPage(1)
  }
  const abrirEscanerLoteConIds = useCallback((idsRaw: number[]) => {
    if (idsRaw.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return false
    }
    const ids = idsRaw.slice(0, 10)
    if (idsRaw.length > 10) {
      toast.info('Solo se escanean 10 seleccionados por lote.')
    }
    const qs = new URLSearchParams({
      from: 'pagos',
      ids: ids.join(','),
    })
    const href = `${BASE_PATH}/escaner-lote?${qs.toString()}`.replace(
      /\/+/g,
      '/'
    )
    window.location.assign(href)
    return true
  }, [])
  const handleBuscarRevisionGlobal = () => {
    setRevisionGlobalCedulaFiltro(revisionGlobalCedulaInput.trim())
    setRevisionGlobalNumeroDocumentoFiltro(
      revisionGlobalNumeroDocumentoInput.trim()
    )
    setRevisionGlobalFechaPagoFiltro(revisionGlobalFechaPagoInput)
    setRevisionGlobalPage(1)
  }
  const handleLimpiarRevisionGlobal = () => {
    setRevisionGlobalCedulaInput('')
    setRevisionGlobalCedulaFiltro('')
    setRevisionGlobalNumeroDocumentoInput('')
    setRevisionGlobalNumeroDocumentoFiltro('')
    setRevisionGlobalFechaPagoInput('')
    setRevisionGlobalFechaPagoFiltro('')
    setRevisionGlobalMotivoFiltro('')
    setRevisionGlobalEstadoFiltro('PENDIENTE')
    setRevisionGlobalPage(1)
  }
  const handleGuardarNotaGlobal = async (id: number) => {
    if (editingGlobalId !== id) return
    setSavingGlobalId(id)
    try {
      await pagoService.updatePago(id, {
        notas: globalNotaDraft.trim() || null,
      })
      toast.success('Nota guardada')
      setEditingGlobalId(null)
      setGlobalNotaDraft('')
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setSavingGlobalId(null)
    }
  }
  const handleEliminarRevisionGlobal = async (id: number) => {
    if (!window.confirm(`¿Eliminar el pago ID ${id}?`)) return
    setDeletingGlobalId(id)
    try {
      await pagoService.deletePago(id)
      toast.success('Pago eliminado')
      if (
        (revisionGlobalRowsFiltradas.length ?? 0) <= 1 &&
        revisionGlobalPage > 1
      ) {
        setRevisionGlobalPage(prev => Math.max(1, prev - 1))
      }
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setDeletingGlobalId(null)
    }
  }
  const handleSiguienteAnomaliaGlobal = () => {
    const candidatos = revisionGlobalRowsFiltradas.filter(r => r.score > 0)
    if (candidatos.length === 0) {
      toast.info('No hay anomalías en esta página.')
      return
    }
    const idxActual = candidatos.findIndex(r => r.pago.id === editingGlobalId)
    const siguiente =
      candidatos[(idxActual + 1 + candidatos.length) % candidatos.length]
    setEditingGlobalId(siguiente.pago.id)
    setGlobalNotaDraft((siguiente.pago.notas ?? '').trim())
    setPagoEditando(siguiente.pago)
    setShowRegistrarPago(true)
    toast.success(
      `Abriendo anomalía ${idxActual >= 0 ? idxActual + 2 : 1}/${candidatos.length} (ID ${siguiente.pago.id})`
    )
  }
  const toggleGlobalSeleccion = (id: number) => {
    setSelectedGlobalIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  const toggleGlobalSeleccionTodas = () => {
    const visibles = revisionGlobalRowsFiltradas.map(r => r.pago.id)
    const todosSeleccionados =
      visibles.length > 0 && visibles.every(id => selectedGlobalIds.has(id))
    setSelectedGlobalIds(todosSeleccionados ? new Set() : new Set(visibles))
  }
  const handleGuardarGlobalMasivo = async () => {
    const ids = [...selectedGlobalIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }
    setIsBulkSavingGlobal(true)
    try {
      await Promise.all(
        ids.map(id =>
          pagoService.updatePago(id, {
            notas: bulkGlobalNota.trim() || null,
          })
        )
      )
      toast.success(`Nota guardada en ${ids.length} pago(s).`)
      setSelectedGlobalIds(new Set())
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsBulkSavingGlobal(false)
    }
  }
  const handleEliminarGlobalMasivo = async () => {
    const ids = [...selectedGlobalIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }
    if (!window.confirm(`¿Eliminar ${ids.length} pago(s) seleccionados?`))
      return
    setIsBulkDeletingGlobal(true)
    try {
      await Promise.all(ids.map(id => pagoService.deletePago(id)))
      toast.success(`Se eliminaron ${ids.length} pago(s).`)
      setSelectedGlobalIds(new Set())
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsBulkDeletingGlobal(false)
    }
  }
  const handleEscanearGlobalMasivo = async () => {
    const ids = [...selectedGlobalIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }

    setIsBulkScanningGlobal(true)
    try {
      // Obtener pagos seleccionados
      const pagosSeleccionados = revisionGlobalRowsFiltradas
        .filter(r => ids.includes(r.pago.id))
        .map(r => r.pago)

      // Filtrar solo los que tienen cédula definida
      const pagosConCedula = pagosSeleccionados.filter(
        p => p.cedula_cliente && p.cedula_cliente.trim()
      )

      if (pagosConCedula.length === 0) {
        toast.warning(
          'Ninguno de los pagos seleccionados tiene cédula definida.'
        )
        return
      }

      const resultados = {
        exitosos: 0,
        fallidos: 0,
        conError: [] as number[],
      }

      // Procesar cada pago
      for (const pago of pagosConCedula) {
        try {
          // Validaciones básicas (deben cumplirse según regla de cascada del backend)
          if (!pago.prestamo_id) {
            resultados.conError.push(pago.id)
            resultados.fallidos++
            continue
          }

          if (!pago.monto_pagado || pago.monto_pagado <= 0) {
            resultados.conError.push(pago.id)
            resultados.fallidos++
            continue
          }

          // Marcar como conciliado
          await pagoService.updateConciliado(pago.id, true)

          // Aplicar a cuotas en cascada (sin diálogo)
          try {
            await pagoService.aplicarPagoACuotas(pago.id)
          } catch (applyErr) {
            // Si falla aplicar cuotas pero se concilió, registrar como error
            // pero considerarlo procesado
            if (isAxiosError(applyErr) && applyErr.response?.status === 409) {
              // Conflicto (duplicado, etc) - marcar como error pero conciliado
              resultados.conError.push(pago.id)
              resultados.fallidos++
              continue
            }
            // Otros errores de aplicación, se considera como error
            throw applyErr
          }

          resultados.exitosos++
        } catch (err) {
          resultados.conError.push(pago.id)
          resultados.fallidos++
        }
      }

      // Mostrar resumen
      toast.success(
        `Procesados: ${resultados.exitosos} exitosos, ${resultados.fallidos} con error.`
      )

      // Eliminar pagos exitosos de la tabla (limpiar checkboxes y filas)
      const idsExitosos = pagosConCedula
        .filter(p => !resultados.conError.includes(p.id))
        .map(p => p.id)

      if (idsExitosos.length > 0) {
        setSelectedGlobalIds(
          new Set(
            [...selectedGlobalIds].filter(id => !idsExitosos.includes(id))
          )
        )
      }

      // Actualizar datos
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsBulkScanningGlobal(false)
    }
  }

  /**
   * Handler para el botón "Visto" (✓) en las acciones individuales de la tabla.
   * Valida, autoconcilia y aplica a cuotas de forma individual.
   * Si tiene éxito: elimina la fila.
   * Si falla validación: muestra error y deja la fila visible.
   */
  const handleVistoIndividual = async (pago: Pago | PagoConError) => {
    try {
      // Validaciones básicas
      if (!pago.cedula_cliente || !pago.cedula_cliente.trim()) {
        toast.error('Pago sin cédula definida.')
        return
      }

      if (!pago.prestamo_id) {
        toast.error('Pago sin crédito asignado.')
        return
      }

      if (!pago.monto_pagado || pago.monto_pagado <= 0) {
        toast.error('Monto debe ser mayor a 0.')
        return
      }

      // Autoconciliar
      await pagoService.updateConciliado(pago.id, true)

      // Aplicar a cuotas (si aquí falla, devuelve error al usuario)
      try {
        await pagoService.aplicarPagoACuotas(pago.id)
      } catch (applyErr) {
        if (import.meta.env.DEV)
          console.warn('Error aplicando a cuotas', applyErr)
        const errMsg = getErrorMessage(applyErr)
        toast.error(`Error aplicando a cuotas: ${errMsg}`)
        return
      }

      // Éxito: eliminar fila
      toast.success(
        'Pago validado, conciliado, aplicado y eliminado de la lista.'
      )

      // Invalidar queries y refrescar
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
    } catch (err) {
      if (import.meta.env.DEV)
        console.error('Error en handleVistoIndividual:', err)
      toast.error(getErrorMessage(err))
    }
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
        queryKey: ['pagos-con-errores-tab'],
        exact: false,
      })
      await queryClient.refetchQueries({
        queryKey: ['pagos-revision-global-tab'],
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
        `Se eliminaron ${r.pagos_eliminados} pago(s)${
          r.pagos_con_errores_eliminados
            ? ` y ${r.pagos_con_errores_eliminados} pendiente(s) en revisión`
            : ''
        }. Cargue el Excel con los nuevos pagos.`
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
    <div
      className={cn(
        !dockStaffComprobante && 'space-y-6',
        dockStaffComprobante &&
          '-mx-6 flex w-[calc(100%+3rem)] max-w-none flex-col gap-0 border-y border-slate-200/70 bg-white lg:grid lg:h-[calc(100dvh-7.5rem)] lg:max-h-[calc(100dvh-7.5rem)] lg:grid-cols-2 lg:items-stretch lg:divide-x lg:divide-slate-200/70 lg:overflow-hidden'
      )}
    >
      {dockStaffComprobante ? (
        <StaffComprobanteDock
          preview={staffComprobantePreview}
          onClose={closeStaffComprobanteListPreview}
          onRotate={delta =>
            setStaffComprobantePreview(prev => ({
              ...prev,
              rotDeg: (prev.rotDeg + delta + 360) % 360,
            }))
          }
        />
      ) : null}

      <div
        className={cn(
          dockStaffComprobante &&
            'min-h-0 min-w-0 space-y-6 overflow-y-auto overscroll-y-contain px-3 py-4 sm:px-4 lg:py-4 lg:pl-5 lg:pr-0',
          !dockStaffComprobante && 'contents'
        )}
      >
        <div className="flex flex-wrap items-center justify-end gap-3 rounded-xl border border-gray-200/80 bg-gray-50/50 px-4 py-3 sm:px-5 sm:py-4">
          <Button
            variant="outline"
            size="lg"
            onClick={handleRefresh}
            className="px-6 py-6 text-base font-semibold"
          >
            <RefreshCw className="mr-2 h-5 w-5" />
            Actualizar
          </Button>
          {puedeVerRevisionManualPagos ? (
            <>
          <Button
            variant={activeTab === 'revision' ? 'default' : 'outline'}
            size="lg"
            onClick={handleRevisarPagos}
            className="px-6 py-6 text-base font-semibold"
            title="Ver pagos sin número de crédito asignado"
          >
            <Search className="mr-2 h-5 w-5" />
            Revisar Pagos
          </Button>
          {activeTab === 'revision' && (
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
          <Button
            variant="outline"
            size="lg"
            type="button"
            onClick={() => void runGmail('all')}
            disabled={loadingGmail}
            className="max-w-[min(100%,22rem)] px-6 py-6 text-base font-semibold"
            title={
              loadingGmail && gmailStatus?.last_status === 'running'
                ? gmailRunningProgressLabel(gmailStatus)
                : 'Procesar correos Gmail'
            }
          >
            {loadingGmail ? (
              <Loader2 className="mr-2 h-5 w-5 shrink-0 animate-spin" />
            ) : (
              <Mail className="mr-2 h-5 w-5 shrink-0" />
            )}
            <span className="truncate">
              {loadingGmail
                ? gmailRunningProgressLabel(gmailStatus)
                : 'Procesar manualmente'}
            </span>
          </Button>
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
            <PopoverContent className="w-80 max-w-[90vw] p-3" align="end">
              {gmailStatus && (
                <p className="mb-2 border-b border-gray-100 px-2 py-1.5 text-xs text-gray-600">
                  {gmailStatus.last_status === 'error' ? (
                    <span className="block text-amber-600">
                      <span className="font-medium text-amber-700">
                        Última sync Gmail falló
                      </span>
                      {gmailStatus.last_error ? (
                        <span className="mt-1 block max-h-28 overflow-y-auto whitespace-pre-wrap break-words font-normal text-amber-900/85 dark:text-amber-200/90">
                          {gmailStatus.last_error.length > 400
                            ? `${gmailStatus.last_error.slice(0, 400)}…`
                            : gmailStatus.last_error}
                        </span>
                      ) : null}
                      <span className="mt-1.5 block font-normal text-gray-600 dark:text-gray-400">
                        Reintente con &quot;Procesar correos&quot; o revise
                        OAuth en Configuración → Informe de pagos.
                      </span>
                      {gmailStatus.next_run_approx ? (
                        <span className="mt-1.5 block border-t border-amber-100 pt-1.5 text-[11px] leading-snug text-gray-600 dark:text-gray-400">
                          Próximo escaneo en servidor:{' '}
                          {textoProximoEscaneoGmailServidor(
                            gmailStatus.next_run_approx
                          )}
                        </span>
                      ) : null}
                    </span>
                  ) : gmailStatus.last_status === 'running' ? (
                    <>
                      Procesando: {gmailStatus.last_emails} correos,{' '}
                      {gmailStatus.last_files} archivos
                      {typeof gmailStatus.last_run_summary
                        ?.gmail_messages_listed === 'number' &&
                      gmailStatus.last_run_summary.gmail_messages_listed > 0 &&
                      (gmailStatus.last_emails ?? 0) === 0 ? (
                        <span className="mt-1 block text-gray-600">
                          En cola:{' '}
                          {gmailStatus.last_run_summary.gmail_messages_listed}{' '}
                          correo(s).
                        </span>
                      ) : null}
                      {gmailStatus.running_looks_stale ? (
                        <span className="mt-1 block text-amber-700">
                          Sin actividad. Reintente «Procesar manualmente».
                        </span>
                      ) : null}
                    </>
                  ) : gmailStatus.last_run ? (
                    <>
                      Última sync: {formatLastSyncDate(gmailStatus.last_run)} -{' '}
                      {gmailStatus.last_emails} correos,{' '}
                      {gmailStatus.last_files} archivos
                      {typeof gmailStatus.last_correos_marcados_revision ===
                        'number' &&
                      gmailStatus.last_correos_marcados_revision > 0 ? (
                        <>
                          <br />
                          <span className="text-emerald-800">
                            {gmailStatus.last_correos_marcados_revision}{' '}
                            correo(s) leidos con al menos un comprobante
                            (etiqueta IMAGEN 1 / 2 / 3 + estrella).
                          </span>
                        </>
                      ) : null}
                      {gmailStatus.next_run_approx ? (
                        <span className="mt-1 block border-t border-gray-100 pt-1 text-[11px] leading-snug text-gray-500">
                          Próximo escaneo en servidor:{' '}
                          {textoProximoEscaneoGmailServidor(
                            gmailStatus.next_run_approx
                          )}
                        </span>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <span className="text-gray-500">Sin sync Gmail aún</span>
                      {gmailStatus.next_run_approx ? (
                        <span className="mt-1 block border-t border-gray-100 pt-1 text-[11px] leading-snug text-gray-500">
                          Próximo escaneo en servidor:{' '}
                          {textoProximoEscaneoGmailServidor(
                            gmailStatus.next_run_approx
                          )}
                        </span>
                      ) : null}
                    </>
                  )}
                </p>
              )}
              {gmailStatus?.last_run_summary ? (
                <details className="mb-2 rounded-md border border-gray-100 bg-gray-50/60 px-2 py-2 text-xs text-gray-700">
                  <summary className="cursor-pointer select-none font-medium text-gray-800">
                    Métricas detalladas (última corrida)
                  </summary>
                  <ul className="mt-2 space-y-1 pl-1">
                    {gmailRunSummaryLines(gmailStatus.last_run_summary).map(
                      (line, idx) => (
                        <li
                          key={`${idx}-${line}`}
                          className="break-words leading-snug"
                        >
                          {line}
                        </li>
                      )
                    )}
                  </ul>
                </details>
              ) : null}
              <div className="space-y-2">
                <a
                  href={`${BASE_PATH}/${SEGMENTO_INFOPAGOS}`.replace(
                    /\/+/g,
                    '/'
                  )}
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
                      Correos Gmail
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
                      {gmailPollGaveUp &&
                      gmailStatus?.last_status === 'running' ? (
                        <p className="px-3 text-xs text-amber-800">
                          El servidor no respondió a tiempo varias veces; el
                          proceso puede continuar en segundo plano.
                        </p>
                      ) : null}
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
              </div>
            </PopoverContent>
          </Popover>
          <Button
            type="button"
            variant="outline"
            size="lg"
            className="px-6 py-6 text-base font-semibold"
            title="Reemplazar pagos de un préstamo"
            onClick={abrirReemplazarPagos}
          >
            <Trash2 className="mr-2 h-5 w-5 shrink-0" aria-hidden />
            Reemplazar pagos
          </Button>
            </>
          ) : null}
        </div>
        {puedeVerRevisionManualPagos ? (
        <div className="sticky top-2 z-20 rounded-lg border border-gray-200/80 bg-white px-4 py-3 text-sm text-gray-700 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Última corrida Gmail (métricas)
              </div>
              {gmailPollGaveUp && gmailStatus?.last_status === 'running' ? (
                <p className="mt-1 text-xs text-amber-800">
                  Seguimiento pausado (timeout). Recargue en unos minutos.
                </p>
              ) : null}
              <div className="mt-1 break-words">
                {gmailStatus?.last_status === 'running' ? (
                  <>
                    <span className="font-medium text-blue-800">
                      {gmailRunningProgressLabel(gmailStatus)}
                    </span>
                    {typeof gmailStatus.last_run_summary
                      ?.gmail_messages_listed === 'number' &&
                    gmailStatus.last_run_summary.gmail_messages_listed > 0 &&
                    (gmailStatus.last_emails ?? 0) <
                      gmailStatus.last_run_summary.gmail_messages_listed ? (
                      <span className="mt-1 block text-xs text-gray-600">
                        Procesando hilos…
                      </span>
                    ) : null}
                  </>
                ) : bannerSummary ? (
                  gmailRunSummaryHeadline(bannerSummary)
                ) : (
                  'Sin corrida manual reciente.'
                )}
              </div>
              {bannerLastRun ? (
                <div className="mt-1 text-xs text-gray-500">
                  Sincronización: {formatLastSyncDate(bannerLastRun)}
                </div>
              ) : null}
            </div>
          </div>
        </div>
        ) : null}
        <ReemplazarPagosDialog
          open={reemplazarPagosOpen}
          step={reemplazarStep}
          cedula={cedulaReemplazo}
          prestamos={prestamosReemplazo}
          prestamoId={prestamoIdReemplazo}
          prestamoSeleccionado={prestamoReemplazoSeleccionado}
          loading={loadingReemplazo}
          onOpenChange={open => {
            if (!open) cerrarReemplazarPagos()
          }}
          onCedulaChange={setCedulaReemplazo}
          onPrestamoIdChange={setPrestamoIdReemplazo}
          onStepChange={setReemplazarStep}
          onBuscarPrestamos={handleBuscarPrestamosReemplazo}
          onConfirmar={handleConfirmarReemplazarPagos}
        />
        {/* Después de importar desde Cobros: si hay errores, ofrecer descargar Excel de esta importación (datos_importados_conerrores) */}
        {lastImportCobrosResult &&
          lastImportCobrosResult.registros_con_error > 0 && (
            <Card className="border-amber-200 bg-amber-50">
              <CardContent className="flex flex-wrap items-center gap-3 py-3">
                <span className="text-sm text-amber-800">
                  {lastImportCobrosResult.registros_procesados} importados
                  {typeof lastImportCobrosResult.cuotas_aplicadas ===
                    'number' &&
                    lastImportCobrosResult.cuotas_aplicadas > 0 && (
                      <>
                        {' '}
                        ({lastImportCobrosResult.cuotas_aplicadas} operaciones
                        en cuotas
                        {typeof lastImportCobrosResult.pagos_con_aplicacion_a_cuotas ===
                        'number'
                          ? `, ${lastImportCobrosResult.pagos_con_aplicacion_a_cuotas} pago(s) con aplicación`
                          : ''}
                        )
                      </>
                    )}
                  ; {lastImportCobrosResult.registros_con_error} con error (no
                  cumplen reglas de carga masiva). Descargue el Excel para
                  revisar y corregir.
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
          (lastImportCobrosResult.pagos_sin_aplicacion_cuotas_total ?? 0) >
            0 && (
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
                  {(
                    lastImportCobrosResult.pagos_sin_aplicacion_cuotas ?? []
                  ).map((row, i) => (
                    <li key={`${row.pago_id ?? i}-${row.cedula_cliente}`}>
                      {row.pago_id != null ? `#${row.pago_id}` : '-'} ·{' '}
                      {row.cedula_cliente || '-'} · préstamo{' '}
                      {row.prestamo_id ?? '-'} · {row.motivo}: {row.detalle}
                    </li>
                  ))}
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
        {/* Pestañas: Detalle por Cliente es el acceso principal (cédula / pago / préstamo). */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-4">
            {accesoDetallePorCliente ? (
              <TabsTrigger value="resumen">Detalle por Cliente</TabsTrigger>
            ) : null}
            {puedeVerRevisionManualPagos ? (
            <TabsTrigger
              value="revision"
              title="Edita, elimina o escanea pagos con errores"
            >
              Revisión Manual
            </TabsTrigger>
            ) : null}
          </TabsList>
          {/* Tab: Detalle por Cliente (resumen + ver pagos del cliente, más reciente a más antiguo) */}
          {accesoDetallePorCliente ? (
          <TabsContent value="resumen" forceMount>
            <PagosListResumen
              fetchEnabled={activeTab === 'resumen'}
              initialCedula={deepLinkIdentidad.cedula}
              initialPagoId={deepLinkIdentidad.pagoId}
              initialPrestamoId={deepLinkIdentidad.prestamoId}
            />
          </TabsContent>
          ) : null}
          {puedeVerRevisionManualPagos ? (
          <>
          <TabsContent value="revision" forceMount>
            <PagosRevisionTab
              active={activeTab === 'revision'}
              perPage={perPage}
              includeExportados={includeRevisionExportados}
              onIncludeExportadosChange={setIncludeRevisionExportados}
              onOpenPagoEditor={pago => {
                setPagoEditando(pago)
                setShowRegistrarPago(true)
              }}
              openStaffComprobanteForList={openStaffComprobanteForList}
            />
          </TabsContent>
          <TabsContent value="revision-global" forceMount>
            <Card>
              <CardHeader>
                <CardTitle>Revision global de pagos</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
                  <div className="flex-1">
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Filtrar por cédula
                    </label>
                    <Input
                      placeholder="Ej: V12345678"
                      value={revisionGlobalCedulaInput}
                      onChange={e =>
                        setRevisionGlobalCedulaInput(e.target.value)
                      }
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleBuscarRevisionGlobal()
                        }
                      }}
                      className="max-w-md"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Filtrar por N° documento
                    </label>
                    <Input
                      placeholder="Ej: 00012345"
                      value={revisionGlobalNumeroDocumentoInput}
                      onChange={e =>
                        setRevisionGlobalNumeroDocumentoInput(e.target.value)
                      }
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleBuscarRevisionGlobal()
                        }
                      }}
                      className="max-w-md"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Fecha pago
                    </label>
                    <Input
                      type="date"
                      value={revisionGlobalFechaPagoInput}
                      onChange={e =>
                        setRevisionGlobalFechaPagoInput(e.target.value)
                      }
                      className="w-[180px]"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Motivo
                    </label>
                    <Select
                      value={revisionGlobalMotivoFiltro || 'all'}
                      onValueChange={value => {
                        setRevisionGlobalMotivoFiltro(
                          value === 'all'
                            ? ''
                            : (value as
                                | 'sin_credito'
                                | 'duplicado'
                                | 'irreal'
                                | 'sin_aplicacion'
                                | 'con_notas'
                                | 'rebasa_total')
                        )
                        setRevisionGlobalPage(1)
                      }}
                    >
                      <SelectTrigger className="w-[220px]">
                        <SelectValue placeholder="Motivo de anomalía" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        <SelectItem value="sin_credito">Sin crédito</SelectItem>
                        <SelectItem value="duplicado">
                          Duplicado fecha + número
                        </SelectItem>
                        <SelectItem value="irreal">Irreal</SelectItem>
                        <SelectItem value="sin_aplicacion">
                          Sin aplicación a cuotas
                        </SelectItem>
                        <SelectItem value="con_notas">Con notas</SelectItem>
                        <SelectItem value="rebasa_total">
                          Rebasa total del préstamo
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={handleBuscarRevisionGlobal}
                    >
                      Buscar
                    </Button>
                    <Button onClick={handleSiguienteAnomaliaGlobal}>
                      Siguiente anomalía
                    </Button>
                    {(revisionGlobalCedulaFiltro ||
                      revisionGlobalNumeroDocumentoFiltro ||
                      revisionGlobalFechaPagoFiltro ||
                      revisionGlobalEstadoFiltro ||
                      revisionGlobalMotivoFiltro) && (
                      <Button
                        variant="ghost"
                        onClick={handleLimpiarRevisionGlobal}
                      >
                        <X className="mr-1 h-4 w-4" />
                        Limpiar
                      </Button>
                    )}
                  </div>
                </div>
                {isLoadingRevisionGlobal ? (
                  <div className="py-8 text-center text-sm text-gray-500">
                    Cargando revisión global...
                  </div>
                ) : isRevisionGlobalError ? (
                  <div className="py-8 text-center text-sm text-red-600">
                    Error cargando pagos globales
                  </div>
                ) : !revisionGlobalRowsFiltradas.length ? (
                  <div className="py-8 text-center text-sm text-gray-500">
                    No hay pagos para esta búsqueda.
                  </div>
                ) : (
                  <>
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                      <Input
                        placeholder="Nota masiva para seleccionados"
                        value={bulkGlobalNota}
                        onChange={e => setBulkGlobalNota(e.target.value)}
                        className="max-w-sm"
                      />
                      <Button
                        variant="outline"
                        onClick={() => void handleGuardarGlobalMasivo()}
                        disabled={
                          selectedGlobalIds.size === 0 || isBulkSavingGlobal
                        }
                      >
                        {isBulkSavingGlobal
                          ? 'Guardando...'
                          : 'Guardar seleccionados'}
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => void handleEliminarGlobalMasivo()}
                        disabled={
                          selectedGlobalIds.size === 0 || isBulkDeletingGlobal
                        }
                      >
                        {isBulkDeletingGlobal
                          ? 'Eliminando...'
                          : 'Eliminar seleccionados'}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => handleEscanearGlobalMasivo()}
                        disabled={
                          selectedGlobalIds.size === 0 || isBulkScanningGlobal
                        }
                      >
                        {isBulkScanningGlobal
                          ? 'Abriendo escáner...'
                          : 'Escanear seleccionados (máx. 10)'}
                      </Button>
                      <span className="text-xs text-gray-600">
                        Seleccionados: {selectedGlobalIds.size}
                      </span>
                    </div>
                    <div className="mb-3 flex flex-wrap gap-2 text-xs">
                      <Badge variant="outline">
                        Duplicados: {resumenRevisionGlobal.duplicados}
                      </Badge>
                      <Badge variant="outline">
                        Irreales: {resumenRevisionGlobal.irreales}
                      </Badge>
                      <Badge variant="outline">
                        Sin crédito: {resumenRevisionGlobal.sinCredito}
                      </Badge>
                      <Badge variant="outline">
                        Sin aplicación: {resumenRevisionGlobal.sinAplicacion}
                      </Badge>
                      <Badge variant="outline">
                        Con notas: {resumenRevisionGlobal.conNotas}
                      </Badge>
                      <Badge variant="outline">
                        Rebasa total: {resumenRevisionGlobal.rebasaTotal}
                      </Badge>
                    </div>
                    <div className="overflow-hidden rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[44px]">
                              <input
                                type="checkbox"
                                checked={
                                  revisionGlobalRowsFiltradas.length > 0 &&
                                  revisionGlobalRowsFiltradas.every(r =>
                                    selectedGlobalIds.has(r.pago.id)
                                  )
                                }
                                onChange={toggleGlobalSeleccionTodas}
                              />
                            </TableHead>
                            <TableHead>ID</TableHead>
                            <TableHead>Cédula</TableHead>
                            <TableHead>Crédito</TableHead>
                            <TableHead>Monto</TableHead>
                            <TableHead>Fecha Pago</TableHead>
                            <TableHead>Nº Documento</TableHead>
                            <TableHead>Exceso USD</TableHead>
                            <TableHead>Motivos</TableHead>
                            <TableHead>Notas</TableHead>
                            <TableHead className="text-right">
                              Acciones
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {revisionGlobalRowsFiltradas.map(
                            ({ pago, motivos, score }) => (
                              <TableRow
                                key={pago.id}
                                className={
                                  score >= 2 ? 'bg-amber-50/40' : undefined
                                }
                              >
                                <TableCell>
                                  <input
                                    type="checkbox"
                                    checked={selectedGlobalIds.has(pago.id)}
                                    onChange={() =>
                                      toggleGlobalSeleccion(pago.id)
                                    }
                                  />
                                </TableCell>
                                <TableCell>{pago.id}</TableCell>
                                <TableCell>{pago.cedula_cliente}</TableCell>
                                <TableCell>
                                  {pago.prestamo_id
                                    ? `#${pago.prestamo_id}`
                                    : '-'}
                                </TableCell>
                                <TableCell>
                                  ${Number(pago.monto_pagado).toFixed(2)}
                                </TableCell>
                                <TableCell>
                                  {formatDate(pago.fecha_pago)}
                                </TableCell>
                                <TableCell>
                                  {textoDocumentoPagoParaListado(
                                    pago.numero_documento,
                                    pago.codigo_documento
                                  )}
                                </TableCell>
                                <TableCell>
                                  {Number(pago.exceso_sobre_total_usd ?? 0) >
                                  0 ? (
                                    <span className="font-semibold text-red-700">
                                      $
                                      {Number(
                                        pago.exceso_sobre_total_usd
                                      ).toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-500">-</span>
                                  )}
                                </TableCell>
                                <TableCell className="max-w-[260px]">
                                  <div className="flex flex-wrap gap-1">
                                    {motivos.length === 0 ? (
                                      <Badge variant="outline">Sin marca</Badge>
                                    ) : (
                                      motivos.map(m => (
                                        <Badge
                                          key={`${pago.id}-${m}`}
                                          variant="outline"
                                        >
                                          {m}
                                        </Badge>
                                      ))
                                    )}
                                  </div>
                                </TableCell>
                                <TableCell className="min-w-[260px]">
                                  {editingGlobalId === pago.id ? (
                                    <Input
                                      value={globalNotaDraft}
                                      onChange={e =>
                                        setGlobalNotaDraft(e.target.value)
                                      }
                                      onKeyDown={e => {
                                        if (e.key === 'Enter') {
                                          e.preventDefault()
                                          void handleGuardarNotaGlobal(pago.id)
                                        }
                                      }}
                                      placeholder="Nota de revisión rápida"
                                    />
                                  ) : (
                                    <span className="text-sm text-amber-700">
                                      {(pago.notas ?? '').trim() || '-'}
                                    </span>
                                  )}
                                </TableCell>
                                <TableCell className="text-right">
                                  <div className="inline-flex items-center gap-2">
                                    {(() => {
                                      const cerrado =
                                        pagoEstaCerradoSoloConsulta(pago)
                                      return (
                                        <Button
                                          size="icon"
                                          variant="outline"
                                          title={
                                            cerrado
                                              ? 'Ver pago (solo consulta - ya cargado a cuotas)'
                                              : 'Editar pago'
                                          }
                                          aria-label={
                                            cerrado
                                              ? 'Ver pago (solo consulta)'
                                              : 'Editar pago'
                                          }
                                          onClick={() => {
                                            setPagoEditando(pago)
                                            setShowRegistrarPago(true)
                                          }}
                                        >
                                          {cerrado ? (
                                            <Eye className="h-4 w-4" />
                                          ) : (
                                            <Edit className="h-4 w-4" />
                                          )}
                                        </Button>
                                      )
                                    })()}
                                    <Button
                                      size="icon"
                                      variant="outline"
                                      title="Editar nota"
                                      onClick={() => {
                                        setEditingGlobalId(pago.id)
                                        setGlobalNotaDraft(
                                          (pago.notas ?? '').trim()
                                        )
                                      }}
                                    >
                                      <FileText className="h-4 w-4" />
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="outline"
                                      title="Guardar nota"
                                      disabled={
                                        editingGlobalId !== pago.id ||
                                        savingGlobalId === pago.id
                                      }
                                      onClick={() =>
                                        void handleGuardarNotaGlobal(pago.id)
                                      }
                                    >
                                      {savingGlobalId === pago.id ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                      ) : (
                                        <Check className="h-4 w-4" />
                                      )}
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="default"
                                      className="bg-green-600 hover:bg-green-700"
                                      title="Visto - Validar, conciliar y aplicar"
                                      onClick={() =>
                                        void handleVistoIndividual(pago)
                                      }
                                    >
                                      <Check className="h-4 w-4" />
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="destructive"
                                      title="Eliminar pago"
                                      disabled={deletingGlobalId === pago.id}
                                      onClick={() =>
                                        void handleEliminarRevisionGlobal(
                                          pago.id
                                        )
                                      }
                                    >
                                      {deletingGlobalId === pago.id ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                      ) : (
                                        <Trash2 className="h-4 w-4" />
                                      )}
                                    </Button>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )
                          )}
                        </TableBody>
                      </Table>
                    </div>
                    <ListPaginationBar
                      className="mt-4"
                      page={revisionGlobalData?.page ?? 1}
                      totalPages={Math.max(
                        1,
                        revisionGlobalData?.total_pages ?? 1
                      )}
                      onPageChange={p => setRevisionGlobalPage(p)}
                      subtitle={`${revisionGlobalData?.total ?? 0} registros · ${revisionGlobalData?.per_page ?? perPage} por página`}
                    />
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          </>
          ) : null}
        </Tabs>
        {/* Registrar/Editar Pago Modal */}
        {showRegistrarPago && (
          <RegistrarPagoForm
            pagoId={pagoEditando?.id}
            modoGuardarYProcesar={
              activeTab === 'revision'
            }
            esPagoConError={activeTab === 'revision'}
            mostrarCampoCodigoDocumento={
              activeTab === 'revision'
            }
            prestamoContextoRevisionManualId={
              pagoEditando?.prestamo_id != null &&
              Number(pagoEditando.prestamo_id) > 0
                ? Number(pagoEditando.prestamo_id)
                : undefined
            }
            claveDocumentoPagosTablaRevision={new Set<string>()}
            bloquearCambioComprobanteCodigo={Boolean(
              pagoEditando &&
                !(
                  activeTab === 'revision'
                ) &&
                (pagoEditando.conciliado ||
                  String(pagoEditando.estado || '').toUpperCase() === 'PAGADO')
            )}
            onDuplicadoDetectado={pago => {
              // Cerrar formulario de registro
              setShowRegistrarPago(false)
              setPagoEditando(null)

              if (!REVISION_MANUAL_MODULE_ENABLED) {
                toast.info(
                  'Módulo de revisión manual desactivado. Resuelva el duplicado desde Pagos (préstamo asignado) u otras herramientas vigentes.'
                )
                return
              }

              // Navegar a Revisión Manual con el ID del pago y préstamo
              if (pago.prestamo_id) {
                toast.info(
                  'Abriendo Revisión Manual para resolver el duplicado...'
                )
                navigate(
                  `/revision-manual/editar/${pago.prestamo_id}?pago_id=${pago.id}`
                )
              } else {
                toast.error(
                  'No se puede abrir Revisión Manual: el pago no tiene préstamo asignado.'
                )
              }
            }}
            pagoInicial={
              pagoEditando
                ? {
                    cedula_cliente: pagoEditando.cedula_cliente,
                    prestamo_id: pagoEditando.prestamo_id,
                    fecha_pago: fechaPagoParaInputDate(pagoEditando.fecha_pago),
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
                    link_comprobante:
                      'link_comprobante' in pagoEditando
                        ? (pagoEditando.link_comprobante ?? null)
                        : null,
                    documento_ruta:
                      'documento_ruta' in pagoEditando
                        ? (pagoEditando.documento_ruta ?? null)
                        : null,
                    ...('duplicado_documento_en_pagos' in pagoEditando
                      ? {
                          duplicado_documento_en_pagos: (
                            pagoEditando as PagoConError
                          ).duplicado_documento_en_pagos,
                          duplicado_en_cartera_prestamo_id: (
                            pagoEditando as PagoConError
                          ).duplicado_en_cartera_prestamo_id,
                          duplicado_en_cartera_pago_id: (
                            pagoEditando as PagoConError
                          ).duplicado_en_cartera_pago_id,
                        }
                      : {}),
                  }
                : undefined
            }
            onClose={() => {
              setShowRegistrarPago(false)
              setPagoEditando(null)
            }}
            onSuccess={async (procesado, meta) => {
              setShowRegistrarPago(false)
              const pagoIdEliminado = pagoEditando?.id
              setPagoEditando(null)

              try {
                // Si fue "Guardar y Procesar", eliminar la fila de la tabla
                if (procesado && pagoIdEliminado) {
                  const omitirDeleteConErrores =
                    meta?.skipDeleteConError &&
                    (activeTab === 'revision')

                  if (omitirDeleteConErrores) {
                    toast.success(
                      'Pago guardado, conciliado y aplicado (movido a tabla operativa).'
                    )
                  } else {
                    try {
                      if (activeTab === 'revision') {
                        const resultado = await eliminarPagoRevisionOConError({
                          idConError: pagoIdEliminado,
                          idCartera: meta?.pagoCarteraId,
                        })
                        toast.success(
                          resultado === 'ya_ausente'
                            ? 'Pago guardado, conciliado y aplicado (ya no estaba en revisión).'
                            : resultado === 'cartera'
                              ? 'Pago guardado, conciliado, aplicado y eliminado de cartera.'
                              : 'Pago guardado, conciliado, aplicado y eliminado de la lista.'
                        )
                      } else {
                        await pagoService.deletePago(pagoIdEliminado)
                        toast.success(
                          'Pago guardado, conciliado, aplicado y eliminado de la lista.'
                        )
                      }
                    } catch (deleteErr) {
                      if (import.meta.env.DEV) {
                        console.warn('Error eliminando fila:', deleteErr)
                      }
                      toast.success('Pago guardado, conciliado y aplicado.')
                    }
                  }
                } else {
                  toast.success('Pago registrado exitosamente.')
                }

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
              } catch (error) {
                if (import.meta.env.DEV)
                  console.error('Error actualizando dashboard:', error)
                toast.error(
                  'Pago procesado, pero hubo un error al actualizar la vista'
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
    </div>
  )
}
