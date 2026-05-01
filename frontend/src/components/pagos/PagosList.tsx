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
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { SEGMENTO_INFOPAGOS } from '../../constants/rutasIngresoPago'
import { BASE_PATH } from '../../config/env'
import {
  gmailRunSummaryHeadline,
  gmailRunSummaryLines,
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

type StaffComprobanteListPreview = {
  open: boolean
  href: string
  label: string
  pagoId: number | null
  blobUrl: string | null
  contentType: string | null
  loading: boolean
  rotDeg: number
}

const STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED: StaffComprobanteListPreview = {
  open: false,
  href: '',
  label: '',
  pagoId: null,
  blobUrl: null,
  contentType: null,
  loading: false,
  rotDeg: 0,
}

/** Visible en columna Observaciones (lista principal y revisar pagos). */
const OBSERVACION_COL_PAGO_DUPLICADO = 'PAGO DUPLICADO'

function observacionesConMarcaDuplicadoCartera(p: PagoConError): string {
  const obs = (p.observaciones ?? '').trim()
  if (p.duplicado_documento_en_pagos === true) {
    return obs
      ? `${OBSERVACION_COL_PAGO_DUPLICADO} ${obs}`
      : OBSERVACION_COL_PAGO_DUPLICADO
  }
  return obs
}

/** Si false, la opción "Descargar Excel" (Gmail) no se muestra en el submenú Agregar pago. */
const SHOW_DESCARGA_EXCEL_EN_SUBMENU = false
const GMAIL_METRICS_SNAPSHOT_KEY = 'pagos:last_gmail_metrics_snapshot'

export function PagosList() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('todos')
  const [page, setPage] = useState(1)
  const [perPage] = useState(10)
  const [showFilters, setShowFilters] = useState(false)
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
  const [isDescargandoGmailExcel, setIsDescargandoGmailExcel] = useState(false)
  const [showVaciarTablaGmail, setShowVaciarTablaGmail] = useState(false)
  const [isVaciarTablaGmail, setIsVaciarTablaGmail] = useState(false)
  const [showBorradoresEscanerDialog, setShowBorradoresEscanerDialog] =
    useState(false)
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
  const [revisionPage, setRevisionPage] = useState(1)
  const [revisionCedulaInput, setRevisionCedulaInput] = useState('')
  const [revisionCedulaFiltro, setRevisionCedulaFiltro] = useState('')
  const [revisionNumeroDocumentoInput, setRevisionNumeroDocumentoInput] =
    useState('')
  const [revisionNumeroDocumentoFiltro, setRevisionNumeroDocumentoFiltro] =
    useState('')
  const [revisionFechaPagoInput, setRevisionFechaPagoInput] = useState('')
  const [revisionFechaPagoFiltro, setRevisionFechaPagoFiltro] = useState('')
  const [revisionTipoFiltro, setRevisionTipoFiltro] = useState<
    '' | 'anomalo' | 'irreal' | 'duplicado'
  >('')
  const [revisionMotivoFiltro, setRevisionMotivoFiltro] = useState<
    | ''
    | 'sin_credito'
    | 'duplicado'
    | 'irreal'
    | 'con_observacion'
    | 'error_validacion'
  >('')
  const [includeRevisionExportados, setIncludeRevisionExportados] =
    useState(false)
  const [editingRevisionId, setEditingRevisionId] = useState<number | null>(
    null
  )
  const [revisionObservacionDraft, setRevisionObservacionDraft] = useState('')
  const [savingRevisionId, setSavingRevisionId] = useState<number | null>(null)
  const [deletingRevisionId, setDeletingRevisionId] = useState<number | null>(
    null
  )
  const [selectedRevisionIds, setSelectedRevisionIds] = useState<Set<number>>(
    new Set()
  )
  const [isBulkScanningRevision, setIsBulkScanningRevision] = useState(false)
  const [bulkRevisionObservacion, setBulkRevisionObservacion] = useState('')
  const [isBulkSavingRevision, setIsBulkSavingRevision] = useState(false)
  const [isBulkDeletingRevision, setIsBulkDeletingRevision] = useState(false)
  const [isBulkMovingRevision, setIsBulkMovingRevision] = useState(false)
  const [bulkMovingProgress, setBulkMovingProgress] = useState({
    movidos: 0,
    total: 0,
  })
  const [deletingBorradorId, setDeletingBorradorId] = useState<string | null>(
    null
  )
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

  const [lgViewport, setLgViewport] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia('(min-width: 1024px)')
    const apply = () => setLgViewport(mq.matches)
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

  const [staffComprobantePreview, setStaffComprobantePreview] =
    useState<StaffComprobanteListPreview>(STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED)

  useEffect(() => {
    if (!lgViewport && staffComprobantePreview.open) {
      setStaffComprobantePreview(prev => {
        if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
        return STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED
      })
    }
  }, [lgViewport, staffComprobantePreview.open])

  useEffect(() => {
    return () => {
      if (staffComprobantePreview.blobUrl) {
        URL.revokeObjectURL(staffComprobantePreview.blobUrl)
      }
    }
  }, [staffComprobantePreview.blobUrl])

  const closeStaffComprobanteListPreview = useCallback(() => {
    setStaffComprobantePreview(prev => {
      if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
      return STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED
    })
  }, [])

  const openStaffComprobanteForList = useCallback(
    async (href: string, label: string, pagoId: number | null) => {
      const u = String(href || '').trim()
      if (!u) {
        toast.error('No hay comprobante o recibo asociado.')
        return
      }
      if (!esUrlComprobanteImagenConAuth(u)) {
        await abrirStaffComprobanteDesdeHref(u)
        return
      }
      if (!lgViewport) {
        await abrirStaffComprobanteDesdeHref(u)
        return
      }
      setStaffComprobantePreview(prev => {
        if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
        return {
          ...STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED,
          open: true,
          href: u,
          label,
          pagoId,
          loading: true,
        }
      })
      try {
        const { blob, contentType } =
          await fetchStaffComprobanteBlobWithDisplayMime(u)
        const blobUrl = URL.createObjectURL(blob)
        setStaffComprobantePreview(prev => ({
          ...prev,
          blobUrl,
          contentType,
          loading: false,
          rotDeg: 0,
        }))
      } catch (e) {
        toast.error(getErrorMessage(e) || 'No se pudo cargar el comprobante.')
        setStaffComprobantePreview(prev => {
          if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
          return STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED
        })
      }
    },
    [lgViewport]
  )

  const dockStaffComprobante = staffComprobantePreview.open && lgViewport

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
    gmailStatus,
    setGmailStatus,
    run: runGmail,
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
    const pidNum = Number(pidRaw)
    if (pidRaw && Number.isFinite(pidNum) && pidNum >= 1) {
      setFilters(prev => ({
        ...prev,
        prestamo_id: String(Math.trunc(pidNum)),
        prestamo_cartera: 'todos',
      }))
      setActiveTab('todos')
      setPage(1)
    }
    if (searchParams.get('revisar') === '1') {
      setFilters(prev => ({ ...prev, sin_prestamo: 'si', conciliado: 'all' }))
      setActiveTab('todos')
      setPage(1)
      setSearchParams({}, { replace: true })
      return
    }
    const pestana = (searchParams.get('pestana') || '').trim().toLowerCase()
    if (pestana === 'revision' || pestana === 'revision-global') {
      setActiveTab('revision')
      const ndoc = (searchParams.get('numero_documento') || '').trim()
      if (ndoc) {
        setRevisionNumeroDocumentoInput(ndoc)
        setRevisionNumeroDocumentoFiltro(ndoc)
      }
      setRevisionPage(1)
      const next = new URLSearchParams(searchParams)
      next.delete('pestana')
      next.delete('numero_documento')
      if (next.toString()) {
        setSearchParams(next, { replace: true })
      } else {
        setSearchParams({}, { replace: true })
      }
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    if (activeTab === 'revision-global') {
      setActiveTab('revision')
    }
  }, [activeTab])

  const esRevisarPagos = filters.sin_prestamo === 'si'
  const filtrosPagosApi: Parameters<typeof pagoService.getAllPagos>[2] = {
    cedula: filters.cedula || undefined,
    estado: filters.estado || undefined,
    fechaDesde: filters.fechaDesde || undefined,
    fechaHasta: filters.fechaHasta || undefined,
    analista: filters.analista || undefined,
    conciliado: filters.conciliado || undefined,
    sin_prestamo: filters.sin_prestamo || undefined,
    prestamo_id:
      filters.prestamo_id && Number.isFinite(Number(filters.prestamo_id))
        ? Math.trunc(Number(filters.prestamo_id))
        : undefined,
    prestamo_cartera:
      filters.prestamo_cartera === 'activa' ||
      filters.prestamo_cartera === 'todos'
        ? filters.prestamo_cartera
        : undefined,
  }
  const { data, isLoading, error, isError } = useQuery({
    queryKey: esRevisarPagos
      ? ['pagos-con-errores', page, perPage, filters, includeRevisionExportados]
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
            includeExportados: includeRevisionExportados,
          })
        : pagoService.getAllPagos(page, perPage, filtrosPagosApi),
    // Con pestañas forceMount: no dispara los tres listados a la vez; la caché RQ se conserva al cambiar.
    enabled: activeTab === 'todos',
    staleTime: 15_000, // 15 s - evita múltiples refetch por re-renders y cambios de foco durante batch
    refetchOnMount: true,
    refetchOnWindowFocus: false, // Desactivado para no interrumpir batch con GETs innecesarios
  })
  const {
    data: revisionData,
    isLoading: isLoadingRevision,
    isError: isRevisionError,
  } = useQuery({
    queryKey: [
      'pagos-con-errores-tab',
      revisionPage,
      perPage,
      revisionCedulaFiltro,
      revisionNumeroDocumentoFiltro,
      includeRevisionExportados,
    ],
    queryFn: () =>
      pagoConErrorService.getAll(revisionPage, perPage, {
        cedula: revisionCedulaFiltro || undefined,
        numeroDocumento: revisionNumeroDocumentoFiltro || undefined,
        includeExportados: includeRevisionExportados,
      }),
    enabled: activeTab === 'revision',
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  })
  const {
    data: borradoresPendientesData,
    isLoading: isLoadingBorradoresPendientes,
    isError: isBorradoresPendientesError,
  } = useQuery({
    queryKey: ['escaner-infopagos-borradores-pendientes'],
    queryFn: () => listInfopagosBorradoresEscaneer(40),
    enabled: activeTab === 'revision',
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  })
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
  const revisionRowsAnalizadas = useMemo(() => {
    const rows = revisionData?.pagos ?? []
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
    return rows
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
        if ((p as PagoConError).duplicado_documento_en_pagos === true) {
          motivos.push('Documento duplicado (pagos)')
        }
        if (!p.prestamo_id) motivos.push('Sin crédito asociado')
        if ((p.observaciones ?? '').trim()) motivos.push('Con observación')
        if ((p.errores_descripcion ?? []).length > 0) {
          motivos.push('Error de validación')
        }
        if (
          revisionTipoFiltro === 'irreal' &&
          !motivos.includes('Monto no válido') &&
          !motivos.includes('Fecha futura')
        ) {
          motivos.push('Irreal detectado por regla de cartera')
        }
        return {
          pago: p,
          motivos,
          score: motivos.length,
          esDuplicadoFechaNumero,
        }
      })
      .sort((a, b) => {
        if (revisionGlobalMotivoFiltro === 'rebasa_total') {
          const ea = Number(a.pago.exceso_sobre_total_usd ?? 0)
          const eb = Number(b.pago.exceso_sobre_total_usd ?? 0)
          if (eb !== ea) return eb - ea
        }
        return b.score - a.score || b.pago.id - a.pago.id
      })
  }, [revisionData?.pagos, revisionTipoFiltro])
  const revisionRowsFiltradas = useMemo(() => {
    if (!revisionMotivoFiltro) return revisionRowsAnalizadas
    return revisionRowsAnalizadas.filter(row => {
      if (revisionMotivoFiltro === 'sin_credito') {
        return row.motivos.includes('Sin crédito asociado')
      }
      if (revisionMotivoFiltro === 'duplicado') {
        return (
          row.motivos.includes('Duplicado fecha + número') ||
          row.motivos.includes('Documento duplicado (pagos)')
        )
      }
      if (revisionMotivoFiltro === 'irreal') {
        return (
          row.motivos.includes('Monto no válido') ||
          row.motivos.includes('Fecha futura') ||
          row.motivos.includes('Irreal detectado por regla de cartera')
        )
      }
      if (revisionMotivoFiltro === 'con_observacion') {
        return row.motivos.includes('Con observación')
      }
      if (revisionMotivoFiltro === 'error_validacion') {
        return row.motivos.includes('Error de validación')
      }
      return true
    })
  }, [revisionRowsAnalizadas, revisionMotivoFiltro])
  const borradoresPendientes: InfopagosBorradorListItem[] =
    borradoresPendientesData?.items ?? []
  useEffect(() => {
    const idsVisibles = new Set(revisionRowsFiltradas.map(r => r.pago.id))
    setSelectedRevisionIds(prev => {
      const next = new Set<number>()
      prev.forEach(id => {
        if (idsVisibles.has(id)) next.add(id)
      })
      return next
    })
  }, [revisionRowsFiltradas])
  const resumenRevision = useMemo(() => {
    const resumen = {
      duplicados: 0,
      irreales: 0,
      sinCredito: 0,
      conObservacion: 0,
    }
    for (const row of revisionRowsAnalizadas) {
      if (row.esDuplicadoFechaNumero) resumen.duplicados += 1
      if (
        row.motivos.includes('Monto no válido') ||
        row.motivos.includes('Fecha futura') ||
        row.motivos.includes('Irreal detectado por regla de cartera')
      ) {
        resumen.irreales += 1
      }
      if (row.motivos.includes('Sin crédito asociado')) resumen.sinCredito += 1
      if (row.motivos.includes('Con observación')) resumen.conObservacion += 1
    }
    return resumen
  }, [revisionRowsAnalizadas])
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

  /**
   * Misma lógica que `EditarRevisionManual`: claves comprobante+código en la página actual,
   * excluyendo la fila del modal. Permite avisar duplicado en pantalla y habilitar «Visto».
   */
  const claveDocumentoPagosTablaRevision = useMemo(() => {
    const pagos = data?.pagos
    if (!pagos?.length) return new Set<string>()
    const editingId = pagoEditando?.id
    const s = new Set<string>()
    for (const p of pagos) {
      if (editingId != null && p.id === editingId) continue
      const k = claveDocumentoPagoListaNormalizada(
        p.numero_documento,
        p.codigo_documento ?? null
      )
      if (k) s.add(k)
    }
    return s
  }, [data?.pagos, pagoEditando?.id])

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
  const handleEditarRevision = (pago: PagoConError) => {
    setEditingRevisionId(pago.id)
    setRevisionObservacionDraft((pago.observaciones ?? '').trim())
  }
  const handleAbrirEditorPagoRevision = (pago: PagoConError) => {
    setPagoEditando(pago)
    setShowRegistrarPago(true)
  }
  const handleSiguienteAnomalia = () => {
    const candidatos = revisionRowsAnalizadas.filter(r => r.score > 0)
    if (candidatos.length === 0) {
      toast.info('No hay anomalías priorizadas en esta página.')
      return
    }
    const idxActual = candidatos.findIndex(r => r.pago.id === editingRevisionId)
    const siguiente =
      candidatos[(idxActual + 1 + candidatos.length) % candidatos.length]
    setEditingRevisionId(siguiente.pago.id)
    setRevisionObservacionDraft((siguiente.pago.observaciones ?? '').trim())
    setPagoEditando(siguiente.pago)
    setShowRegistrarPago(true)
    toast.success(
      `Abriendo anomalía ${idxActual >= 0 ? idxActual + 2 : 1}/${candidatos.length} (ID ${siguiente.pago.id})`
    )
  }
  const toggleRevisionSeleccion = (id: number) => {
    setSelectedRevisionIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  const toggleRevisionSeleccionTodas = () => {
    const visibles = revisionRowsFiltradas.map(r => r.pago.id)
    const todosSeleccionados =
      visibles.length > 0 && visibles.every(id => selectedRevisionIds.has(id))
    setSelectedRevisionIds(todosSeleccionados ? new Set() : new Set(visibles))
  }
  const handleGuardarRevisionMasivo = async () => {
    const ids = [...selectedRevisionIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }
    setIsBulkSavingRevision(true)
    try {
      await Promise.all(
        ids.map(id =>
          pagoConErrorService.update(id, {
            observaciones: bulkRevisionObservacion.trim() || null,
          })
        )
      )
      toast.success(`Observación guardada en ${ids.length} pago(s).`)
      setSelectedRevisionIds(new Set())
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsBulkSavingRevision(false)
    }
  }
  const handleEliminarRevisionMasivo = async () => {
    const ids = [...selectedRevisionIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }
    if (!window.confirm(`¿Eliminar ${ids.length} pago(s) seleccionados?`))
      return

    // Invalidar caché para evitar mostrar viejo
    queryClient.removeQueries({
      queryKey: ['pagos-con-errores-tab'],
    })

    setIsBulkDeletingRevision(true)
    try {
      // Ejecutar eliminaciones en paralelo
      await Promise.all(ids.map(id => pagoConErrorService.delete(id)))

      toast.success(`✅ ${ids.length} pago(s) eliminados de la BD`)
      setSelectedRevisionIds(new Set())

      // Refrescar tabla
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(`Error al eliminar: ${getErrorMessage(e)}`)

      // Refetch para sincronizar
      await refetchDiagnosticoRevision()
    } finally {
      setIsBulkDeletingRevision(false)
    }
  }
  const handleMoverRevisionMasivo = async () => {
    const ids = [...selectedRevisionIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }
    setIsBulkMovingRevision(true)
    setBulkMovingProgress({ movidos: 0, total: ids.length })
    try {
      const result = await pagoConErrorService.moverAPagosNormales(ids)

      // Mensaje principal con resultados
      let mensaje = `✅ ${result.movidos} pago(s) movido(s) a tabla principal.\n💰 ${result.cuotas_aplicadas ?? 0} cuota(s) aplicada(s).`

      // Avisar si hay errores
      if (result.errores && result.errores.length > 0) {
        mensaje += `\n⚠️ ${result.errores.length} error(es):\n${result.errores.join('\n')}`
        toast.warning(mensaje, { duration: 7000 })
      } else {
        toast.success(mensaje, { duration: 5000 })
      }

      setSelectedRevisionIds(new Set())
      setBulkMovingProgress({ movidos: 0, total: 0 })
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsBulkMovingRevision(false)
      setBulkMovingProgress({ movidos: 0, total: 0 })
    }
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
  const handleEscanearRevisionMasivo = () => {
    const ids = [...selectedRevisionIds]
    setIsBulkScanningRevision(true)
    try {
      abrirEscanerLoteConIds(ids)
    } finally {
      setIsBulkScanningRevision(false)
    }
  }
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

  const handleBuscarRevisionPorCedula = () => {
    setRevisionCedulaFiltro(revisionCedulaInput.trim())
    setRevisionNumeroDocumentoFiltro(revisionNumeroDocumentoInput.trim())
    setRevisionFechaPagoFiltro('')
    setRevisionFechaPagoInput('')
    setRevisionTipoFiltro('')
    setRevisionMotivoFiltro('')
    setRevisionPage(1)
  }
  const handleLimpiarRevisionCedula = () => {
    setRevisionCedulaInput('')
    setRevisionCedulaFiltro('')
    setRevisionNumeroDocumentoInput('')
    setRevisionNumeroDocumentoFiltro('')
    setRevisionFechaPagoInput('')
    setRevisionFechaPagoFiltro('')
    setRevisionTipoFiltro('')
    setRevisionMotivoFiltro('')
    setRevisionPage(1)
  }
  const handleGuardarRevision = async (id: number) => {
    if (editingRevisionId !== id) return
    setSavingRevisionId(id)
    try {
      await pagoConErrorService.update(id, {
        observaciones: revisionObservacionDraft.trim() || null,
      })
      toast.success('Observación guardada')
      setEditingRevisionId(null)
      setRevisionObservacionDraft('')
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setSavingRevisionId(null)
    }
  }
  const handleEliminarRevision = async (id: number) => {
    if (!window.confirm(`¿Eliminar el pago pendiente ID ${id}?`)) return

    // Invalidar caché para evitar mostrar viejo
    queryClient.removeQueries({
      queryKey: ['pagos-con-errores-tab'],
    })

    setDeletingRevisionId(id)
    try {
      // Enviar DELETE a backend
      await pagoConErrorService.delete(id)

      toast.success('✅ Pago pendiente eliminado de la BD')

      // Refrescar tabla desde servidor
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()

      if ((revisionData?.pagos?.length ?? 0) <= 1 && revisionPage > 1) {
        setRevisionPage(prev => Math.max(1, prev - 1))
      }
    } catch (e) {
      toast.error(`Error al eliminar: ${getErrorMessage(e)}`)

      // Refetch para sincronizar en caso de error
      await refetchDiagnosticoRevision()
    } finally {
      setDeletingRevisionId(null)
    }
  }
  const handleEliminarBorradorPendiente = useCallback(
    async (id: string) => {
      if (
        !window.confirm('¿Eliminar este borrador con validación pendiente?')
      ) {
        return
      }
      setDeletingBorradorId(id)
      try {
        await deleteInfopagosBorradorEscaneer(id)
        toast.success('Borrador eliminado')
        await queryClient.invalidateQueries({
          queryKey: ['escaner-infopagos-borradores-pendientes'],
        })
      } catch (e) {
        toast.error(getErrorMessage(e))
      } finally {
        setDeletingBorradorId(null)
      }
    },
    [queryClient]
  )
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
    <div
      className={cn(
        !dockStaffComprobante && 'space-y-6',
        dockStaffComprobante &&
          '-mx-6 flex w-[calc(100%+3rem)] max-w-none flex-col gap-0 border-y border-slate-200/70 bg-white lg:grid lg:h-[calc(100dvh-7.5rem)] lg:max-h-[calc(100dvh-7.5rem)] lg:grid-cols-2 lg:items-stretch lg:divide-x lg:divide-slate-200/70 lg:overflow-hidden'
      )}
    >
      {dockStaffComprobante ? (
        <aside className="flex min-h-[min(36vh,320px)] min-w-0 flex-col bg-slate-100 lg:h-full lg:max-h-full lg:min-h-0 lg:overflow-y-auto lg:overscroll-y-contain">
          <Card className="flex h-full min-h-0 flex-col rounded-none border-0 shadow-none">
            <CardHeader className="shrink-0 border-b border-slate-200/80 px-3 pb-2 pt-3">
              <CardTitle className="text-base">Comprobante</CardTitle>
              <p className="text-xs text-muted-foreground">
                {staffComprobantePreview.label}
              </p>
            </CardHeader>
            <CardContent className="flex min-h-0 flex-1 flex-col space-y-2 overflow-hidden p-2 sm:p-3 lg:pl-0 lg:pr-2">
              {staffComprobantePreview.loading ? (
                <div className="flex flex-1 items-center justify-center py-12">
                  <Loader2 className="h-10 w-10 animate-spin text-slate-500" />
                </div>
              ) : staffComprobantePreview.blobUrl &&
                staffComprobantePreview.contentType?.startsWith('image/') ? (
                <>
                  <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto rounded-md border border-slate-200/80 bg-white lg:rounded-l-none lg:border-l-0">
                    <div
                      className="inline-flex max-h-full max-w-full origin-center transition-transform duration-200"
                      style={{
                        transform: `rotate(${staffComprobantePreview.rotDeg}deg)`,
                      }}
                    >
                      <img
                        src={staffComprobantePreview.blobUrl}
                        alt="Comprobante"
                        className="max-h-full max-w-full object-contain"
                      />
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      title="Rotar 90° a la izquierda"
                      onClick={() =>
                        setStaffComprobantePreview(prev => ({
                          ...prev,
                          rotDeg: (prev.rotDeg - 90 + 360) % 360,
                        }))
                      }
                    >
                      <RotateCcw className="mr-1 h-4 w-4" />
                      Rotar
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      title="Rotar 90° a la derecha"
                      onClick={() =>
                        setStaffComprobantePreview(prev => ({
                          ...prev,
                          rotDeg: (prev.rotDeg + 90) % 360,
                        }))
                      }
                    >
                      <span className="inline-flex" aria-hidden>
                        <RotateCcw className="mr-1 h-4 w-4 scale-x-[-1]" />
                      </span>
                      Rotar der.
                    </Button>
                  </div>
                </>
              ) : staffComprobantePreview.blobUrl ? (
                <div className="min-h-0 flex-1 overflow-auto rounded-md border border-slate-200/80 bg-white lg:rounded-l-none lg:border-l-0">
                  <iframe
                    title={staffComprobantePreview.label || 'Comprobante'}
                    src={staffComprobantePreview.blobUrl}
                    className="h-[min(36vh,320px)] min-h-[200px] w-full border-0 lg:h-full lg:min-h-[min(50vh,520px)]"
                  />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No se pudo cargar el comprobante.
                </p>
              )}
              {staffComprobantePreview.href ? (
                <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="w-full sm:flex-1"
                    onClick={() =>
                      void abrirStaffComprobanteDesdeHref(
                        staffComprobantePreview.href
                      )
                    }
                  >
                    <Eye className="mr-1 h-4 w-4" />
                    Abrir en nueva pestaña
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    className="w-full sm:flex-1"
                    onClick={closeStaffComprobanteListPreview}
                  >
                    Cerrar panel
                  </Button>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </aside>
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
          <Button
            variant="outline"
            size="lg"
            type="button"
            onClick={() => void runGmail('all')}
            disabled={loadingGmail}
            className="px-6 py-6 text-base font-semibold"
            title="Ejecuta el pipeline Gmail (misma acción que Agregar pago → Generar Excel desde email → Procesar correos)"
          >
            {loadingGmail ? (
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            ) : (
              <Mail className="mr-2 h-5 w-5" />
            )}
            Procesar manualmente
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
            title="Borrar todos los pagos de un préstamo aprobado para volver a cargarlos desde Excel"
            onClick={abrirReemplazarPagos}
          >
            <Trash2 className="mr-2 h-5 w-5 shrink-0" aria-hidden />
            Reemplazar pagos
          </Button>
        </div>
        <div className="sticky top-2 z-20 rounded-lg border border-gray-200/80 bg-white px-4 py-3 text-sm text-gray-700 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Última corrida Gmail (métricas)
              </div>
              <div className="mt-1 break-words">
                {bannerSummary
                  ? gmailRunSummaryHeadline(bannerSummary)
                  : 'Sin corrida manual reciente. Ejecute "Buscar nuevos pagos (Gmail)" para generar métricas.'}
              </div>
              {bannerLastRun ? (
                <div className="mt-1 text-xs text-gray-500">
                  Sincronización: {formatLastSyncDate(bannerLastRun)}
                </div>
              ) : null}
            </div>
            <div className="shrink-0 text-xs text-gray-500">
              Queda fija en pantalla y se actualiza en la próxima corrida
              manual.
            </div>
          </div>
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
                    prestamoIdReemplazo != null
                      ? String(prestamoIdReemplazo)
                      : ''
                  }
                  onValueChange={v => setPrestamoIdReemplazo(Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccione préstamo" />
                  </SelectTrigger>
                  <SelectContent>
                    {prestamosReemplazo.map(p => (
                      <SelectItem key={p.id} value={String(p.id)}>
                        #{p.id} {p.modelo_vehiculo || p.producto || 'Préstamo'}{' '}
                        - {p.nombres}
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
                    <strong>{prestamoReemplazoSeleccionado.cedula}</strong> en
                    el préstamo <strong>#{prestamoIdReemplazo}</strong>
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
        {/* Pestañas: por defecto Resumen por Cliente (detalles por cliente, más reciente a más antiguo) */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-4">
            <TabsTrigger value="todos">Todos los Pagos</TabsTrigger>
            <TabsTrigger value="resumen">Detalle por Cliente</TabsTrigger>
            <TabsTrigger
              value="revision"
              title="Edita, elimina o escanea pagos con errores"
            >
              Revisión Manual
            </TabsTrigger>
          </TabsList>
          {/* Tab: Detalle por Cliente (resumen + ver pagos del cliente, más reciente a más antiguo) */}
          <TabsContent value="resumen" forceMount>
            <PagosListResumen />
          </TabsContent>
          <TabsContent value="revision" forceMount>
            <Card>
              <CardHeader>
                <CardTitle>Revisión Manual de Pagos</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Mesa de trabajo para revisar y procesar pagos con errores de
                  validación. Edita observaciones, elimina registros o mueve
                  pagos corregidos a la tabla principal.
                </p>
                <p className="mt-2 rounded bg-blue-50 p-2 text-xs font-medium text-blue-700">
                  ℹ️ Flujo: Edita observaciones → Mover a Pagos Normales → Se
                  aplican automáticamente a cuotas
                </p>
              </CardHeader>
              <CardContent>
                <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50/50 p-3">
                  <p className="text-sm font-medium text-blue-950">
                    ✅ Acciones Disponibles
                  </p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-blue-900/90">
                    <li>
                      <strong>Guardar Observación:</strong> Actualiza notas sin
                      mover el pago
                    </li>
                    <li>
                      <strong>Mover a Pagos Normales:</strong> Traslada a tabla
                      principal y aplica automáticamente a cuotas
                    </li>
                    <li>
                      <strong>Eliminar:</strong> Borra el pago de revisión (no
                      recuperable)
                    </li>
                    <li>
                      <strong>Escanear:</strong> Abre interfaz de escaneo para
                      este lote
                    </li>
                  </ul>
                </div>
                <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
                  <div className="flex-1">
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Filtrar por cédula
                    </label>
                    <Input
                      placeholder="Ej: V12345678"
                      value={revisionCedulaInput}
                      onChange={e => setRevisionCedulaInput(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleBuscarRevisionPorCedula()
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
                      value={revisionNumeroDocumentoInput}
                      onChange={e =>
                        setRevisionNumeroDocumentoInput(e.target.value)
                      }
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleBuscarRevisionPorCedula()
                        }
                      }}
                      className="max-w-md"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowBorradoresEscanerDialog(true)}
                    >
                      Borradores escáner (
                      {isLoadingBorradoresPendientes
                        ? '...'
                        : String(borradoresPendientes.length)}
                      )
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleBuscarRevisionPorCedula}
                    >
                      Buscar
                    </Button>
                    <Button
                      type="button"
                      onClick={handleSiguienteAnomalia}
                      title="Abrir la siguiente fila priorizada para edición"
                    >
                      Siguiente anomalía
                    </Button>
                    {(revisionCedulaFiltro ||
                      revisionNumeroDocumentoFiltro) && (
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={handleLimpiarRevisionCedula}
                      >
                        <X className="mr-1 h-4 w-4" />
                        Limpiar
                      </Button>
                    )}
                  </div>
                  <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={includeRevisionExportados}
                      onChange={e => {
                        setIncludeRevisionExportados(e.target.checked)
                        setRevisionPage(1)
                      }}
                    />
                    Incluir exportados/archivados
                  </label>
                </div>
                {isLoadingRevision ? (
                  <div className="py-8 text-center text-sm text-gray-500">
                    Cargando pendientes de revisión...
                  </div>
                ) : isRevisionError ? (
                  <div className="py-8 text-center text-sm text-red-600">
                    Error cargando pendientes de revisión
                  </div>
                ) : !revisionData?.pagos?.length ? (
                  <div className="py-8 text-center text-sm text-gray-500">
                    No hay pagos pendientes de revisión.
                  </div>
                ) : (
                  <>
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                      <Input
                        placeholder="Observación masiva para seleccionados"
                        value={bulkRevisionObservacion}
                        onChange={e =>
                          setBulkRevisionObservacion(e.target.value)
                        }
                        className="max-w-sm"
                      />
                      <Button
                        variant="outline"
                        onClick={() => void handleGuardarRevisionMasivo()}
                        disabled={
                          selectedRevisionIds.size === 0 || isBulkSavingRevision
                        }
                      >
                        {isBulkSavingRevision
                          ? 'Guardando...'
                          : 'Guardar seleccionados'}
                      </Button>
                      <Button
                        variant="default"
                        onClick={() => void handleMoverRevisionMasivo()}
                        disabled={
                          selectedRevisionIds.size === 0 || isBulkMovingRevision
                        }
                        className="bg-green-600 hover:bg-green-700"
                      >
                        {isBulkMovingRevision ? (
                          <>
                            <span className="mr-2 inline-block animate-spin">
                              ⏳
                            </span>
                            Moviendo {bulkMovingProgress.movidos}/
                            {bulkMovingProgress.total}...
                          </>
                        ) : (
                          '✓ Mover a Pagos Normales'
                        )}
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => void handleEliminarRevisionMasivo()}
                        disabled={
                          selectedRevisionIds.size === 0 ||
                          isBulkDeletingRevision
                        }
                      >
                        {isBulkDeletingRevision
                          ? 'Eliminando...'
                          : 'Eliminar seleccionados'}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => handleEscanearRevisionMasivo()}
                        disabled={
                          selectedRevisionIds.size === 0 ||
                          isBulkScanningRevision
                        }
                      >
                        {isBulkScanningRevision
                          ? 'Abriendo escáner...'
                          : 'Escanear seleccionados (máx. 10)'}
                      </Button>
                      <span className="text-xs text-gray-600">
                        Seleccionados: {selectedRevisionIds.size}
                      </span>
                    </div>
                    <div className="mb-3 flex flex-wrap gap-2 text-xs">
                      <Badge variant="outline">
                        Duplicados: {resumenRevision.duplicados}
                      </Badge>
                      <Badge variant="outline">
                        Irreales: {resumenRevision.irreales}
                      </Badge>
                      <Badge variant="outline">
                        Sin crédito: {resumenRevision.sinCredito}
                      </Badge>
                      <Badge variant="outline">
                        Con observación: {resumenRevision.conObservacion}
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
                                  revisionRowsFiltradas.length > 0 &&
                                  revisionRowsFiltradas.every(r =>
                                    selectedRevisionIds.has(r.pago.id)
                                  )
                                }
                                onChange={toggleRevisionSeleccionTodas}
                              />
                            </TableHead>
                            <TableHead>ID</TableHead>
                            <TableHead>Cédula</TableHead>
                            <TableHead>Crédito</TableHead>
                            <TableHead>Monto</TableHead>
                            <TableHead>Fecha Pago</TableHead>
                            <TableHead>Nº Documento</TableHead>
                            <TableHead>Motivos</TableHead>
                            <TableHead>Observación</TableHead>
                            <TableHead className="text-right">
                              Acciones
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {revisionRowsFiltradas.map(
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
                                    checked={selectedRevisionIds.has(pago.id)}
                                    onChange={() =>
                                      toggleRevisionSeleccion(pago.id)
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
                                  {editingRevisionId === pago.id ? (
                                    <Input
                                      value={revisionObservacionDraft}
                                      onChange={e =>
                                        setRevisionObservacionDraft(
                                          e.target.value
                                        )
                                      }
                                      onKeyDown={e => {
                                        if (e.key === 'Enter') {
                                          e.preventDefault()
                                          void handleGuardarRevision(pago.id)
                                        }
                                      }}
                                      placeholder="Motivo por el que no cumple"
                                    />
                                  ) : (
                                    <span
                                      className={cn(
                                        'text-sm text-amber-700',
                                        (pago as PagoConError)
                                          .duplicado_documento_en_pagos ===
                                          true &&
                                          'font-semibold text-orange-900'
                                      )}
                                    >
                                      {(() => {
                                        const pe = pago as PagoConError
                                        const texto =
                                          observacionesConMarcaDuplicadoCartera(
                                            pe
                                          ).trim()
                                        return (
                                          texto ||
                                          (!pe.duplicado_documento_en_pagos &&
                                            'No cumple validaciones automáticas') ||
                                          ''
                                        )
                                      })()}
                                    </span>
                                  )}
                                </TableCell>
                                <TableCell className="text-right">
                                  <div className="inline-flex items-center gap-2">
                                    <Button
                                      size="icon"
                                      variant="outline"
                                      title="Ver recibo"
                                      onClick={() => {
                                        if (!pago.documento_ruta) {
                                          toast.error(
                                            'Este pago no tiene recibo o comprobante asociado.'
                                          )
                                          return
                                        }
                                        void openStaffComprobanteForList(
                                          pago.documento_ruta,
                                          `Pago #${pago.id}`,
                                          pago.id
                                        )
                                      }}
                                    >
                                      <Eye className="h-4 w-4" />
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="outline"
                                      title="Editar pago"
                                      onClick={() =>
                                        handleAbrirEditorPagoRevision(pago)
                                      }
                                    >
                                      <Edit className="h-4 w-4" />
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="outline"
                                      title="Editar observación"
                                      onClick={() => handleEditarRevision(pago)}
                                    >
                                      <FileText className="h-4 w-4" />
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="outline"
                                      title="Guardar observación"
                                      disabled={
                                        editingRevisionId !== pago.id ||
                                        savingRevisionId === pago.id
                                      }
                                      onClick={() =>
                                        void handleGuardarRevision(pago.id)
                                      }
                                    >
                                      {savingRevisionId === pago.id ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                      ) : (
                                        <Check className="h-4 w-4" />
                                      )}
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="destructive"
                                      title="Eliminar fila"
                                      disabled={deletingRevisionId === pago.id}
                                      onClick={() =>
                                        void handleEliminarRevision(pago.id)
                                      }
                                    >
                                      {deletingRevisionId === pago.id ? (
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
                      page={revisionData.page}
                      totalPages={Math.max(1, revisionData.total_pages)}
                      onPageChange={p => setRevisionPage(p)}
                      subtitle={`${revisionData.total} registros · ${revisionData.per_page} por página`}
                    />
                  </>
                )}
              </CardContent>
            </Card>
            <Dialog
              open={showBorradoresEscanerDialog}
              onOpenChange={setShowBorradoresEscanerDialog}
            >
              <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
                <DialogHeader>
                  <DialogTitle>
                    Borradores con validación pendiente (Escáner)
                  </DialogTitle>
                </DialogHeader>
                {isLoadingBorradoresPendientes ? (
                  <p className="text-sm text-slate-600">Cargando lista...</p>
                ) : isBorradoresPendientesError ? (
                  <p className="text-sm text-red-700">
                    No se pudo cargar la lista de borradores del escáner.
                  </p>
                ) : borradoresPendientes.length === 0 ? (
                  <p className="text-sm text-slate-600">
                    No hay borradores pendientes.
                  </p>
                ) : (
                  <ul className="divide-y divide-amber-200 rounded-md border border-amber-200 bg-white">
                    {borradoresPendientes.map(row => (
                      <li
                        key={row.id}
                        className="flex flex-wrap items-start justify-between gap-2 px-3 py-2 text-sm"
                      >
                        <div className="min-w-0 flex-1 space-y-0.5">
                          <p className="font-medium text-slate-900">
                            {(
                              row.cliente_nombre ||
                              row.cedula_normalizada ||
                              ''
                            ).trim() || 'Cliente'}
                            <span className="ml-2 font-mono text-xs text-slate-600">
                              {row.comprobante_nombre}
                            </span>
                          </p>
                          <p className="text-xs text-slate-600">
                            {row.resumen_validacion}
                          </p>
                        </div>
                        <div className="flex shrink-0 gap-1">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-8 gap-1 px-2"
                            asChild
                          >
                            <Link
                              to={`/escaner?borrador=${encodeURIComponent(row.id)}`}
                            >
                              <Edit className="h-3.5 w-3.5" />
                              Editar
                            </Link>
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-8 gap-1 border-red-200 px-2 text-red-800 hover:bg-red-50"
                            disabled={deletingBorradorId === row.id}
                            onClick={() =>
                              void handleEliminarBorradorPendiente(row.id)
                            }
                          >
                            {deletingBorradorId === row.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
                            Eliminar
                          </Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </DialogContent>
            </Dialog>
          </TabsContent>
          <TabsContent value="revision-global" forceMount>
            <Card>
              <CardHeader>
                <CardTitle>Revision global de pagos</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Misma dinámica de revisión rápida, pero sobre todos los
                  registros de la tabla pagos.
                </p>
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
                                    <Button
                                      size="icon"
                                      variant="outline"
                                      title="Editar pago"
                                      onClick={() => {
                                        setPagoEditando(pago)
                                        setShowRegistrarPago(true)
                                      }}
                                    >
                                      <Edit className="h-4 w-4" />
                                    </Button>
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
          {/* Tab: Todos los Pagos */}
          <TabsContent value="todos" forceMount>
            {filters.conciliado === 'si' && (
              <Card className="mb-4 border-amber-200 bg-amber-50">
                <CardContent className="py-3 text-sm text-amber-800">
                  Filtro activo: mostrando solo pagos conciliados. Para
                  auditoría completa cambie conciliación a{' '}
                  <strong>Todos</strong> o <strong>No</strong>.
                </CardContent>
              </Card>
            )}
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
                  {filters.prestamo_id && (
                    <div className="flex items-end">
                      <Badge className="bg-blue-600 px-3 py-1.5 text-white">
                        Filtro rápido activo: Préstamo #{filters.prestamo_id}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setFilters(prev => ({
                            ...prev,
                            prestamo_id: '',
                            prestamo_cartera: '',
                          }))
                        }
                        className="ml-2"
                      >
                        <X className="mr-1 h-4 w-4" />
                        Quitar
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
                            <SelectItem value="ADELANTADO">
                              Adelantado
                            </SelectItem>
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
                      filters.prestamo_id ||
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
                            <TableHead>Observaciones</TableHead>
                            <TableHead>Monto</TableHead>
                            <TableHead>Fecha Pago</TableHead>
                            <TableHead>Nº Documento</TableHead>
                            <TableHead>Conciliado</TableHead>
                            <TableHead>Recibo cobros</TableHead>
                            <TableHead className="text-right">
                              Acciones
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {[...(data.pagos || [])]
                            .sort((a, b) => {
                              const fechaA = new Date(a.fecha_pago).getTime()
                              const fechaB = new Date(b.fecha_pago).getTime()
                              return fechaA - fechaB // Más antigua primero
                            })
                            .map((pago: Pago) => {
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
                                  <TableCell
                                    className={cn(
                                      'text-xs text-amber-700',
                                      esRevisarPagos &&
                                        (pago as PagoConError)
                                          .duplicado_documento_en_pagos ===
                                          true &&
                                        'font-semibold text-orange-900',
                                      !esRevisarPagos &&
                                        (documentoDuplicadoEnVista ||
                                          pago.dup_misma_pagina_otro_pago_id !=
                                            null) &&
                                        'align-top font-semibold text-orange-900'
                                    )}
                                  >
                                    {esRevisarPagos ? (
                                      observacionesConMarcaDuplicadoCartera(
                                        pago as PagoConError
                                      ).trim() || '-'
                                    ) : pago.dup_misma_pagina_otro_pago_id != null ? (
                                      <div className="max-w-[min(24rem,85vw)] rounded border border-orange-300 bg-orange-50 px-2 py-1.5 text-[11px] font-semibold leading-snug text-orange-950 dark:border-orange-800 dark:bg-orange-950/35 dark:text-orange-100">
                                        {OBSERVACION_COL_PAGO_DUPLICADO} — Misma clave
                                        (comprobante+código) que otro registro en esta
                                        página: Nº{' '}
                                        <span className="break-all font-mono font-normal">
                                          {pago.dup_misma_pagina_otro_numero_documento ??
                                            '—'}
                                        </span>
                                        {pago.dup_misma_pagina_otro_pago_id != null
                                          ? ` · pago #${pago.dup_misma_pagina_otro_pago_id}`
                                          : ''}
                                        {pago.dup_misma_pagina_otro_prestamo_id != null
                                          ? ` · préstamo #${pago.dup_misma_pagina_otro_prestamo_id}`
                                          : ''}
                                      </div>
                                    ) : documentoDuplicadoEnVista ? (
                                      OBSERVACION_COL_PAGO_DUPLICADO
                                    ) : (
                                      '-'
                                    )}
                                  </TableCell>
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
                                          (
                                            pago.link_comprobante || ''
                                          ).trim() ||
                                          (pago.documento_ruta || '').trim()
                                        const requiereSesion =
                                          u && esUrlComprobanteImagenConAuth(u)
                                        return u ? (
                                          <a
                                            href={requiereSesion ? '#' : u}
                                            target={
                                              requiereSesion
                                                ? undefined
                                                : '_blank'
                                            }
                                            rel={
                                              requiereSesion
                                                ? undefined
                                                : 'noopener noreferrer'
                                            }
                                            className="inline-flex cursor-pointer items-center gap-1 text-sm font-medium text-violet-700 hover:text-violet-900"
                                            title={
                                              requiereSesion
                                                ? 'Comprobante en el sistema (requiere sesión)'
                                                : 'Comprobante en Drive u otro enlace externo'
                                            }
                                            onClick={
                                              requiereSesion
                                                ? e => {
                                                    e.preventDefault()
                                                    void (async () => {
                                                      try {
                                                        await openStaffComprobanteForList(
                                                          u,
                                                          `Pago #${pago.id}`,
                                                          pago.id
                                                        )
                                                      } catch {
                                                        toast.error(
                                                          'No se pudo abrir el comprobante. Compruebe su sesión.'
                                                        )
                                                      }
                                                    })()
                                                  }
                                                : undefined
                                            }
                                          >
                                            <Eye className="h-4 w-4" />
                                            {requiereSesion
                                              ? 'Ver comprobante'
                                              : 'Ver en Drive'}
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
                                          {pago.verificado_concordancia ===
                                            'SI' || pago.conciliado ? (
                                            <button
                                              type="button"
                                              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-amber-700 transition-colors hover:bg-amber-50"
                                              disabled={
                                                conciliandoId === pago.id
                                              }
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
                                              disabled={
                                                conciliandoId === pago.id
                                              }
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
                                                        toast.success(
                                                          res.message
                                                        )
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
                                                        isAxiosError(
                                                          applyErr
                                                        ) &&
                                                        applyErr.response
                                                          ?.status === 409
                                                      ) {
                                                        toast.error(
                                                          getErrorMessage(
                                                            applyErr
                                                          )
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
                                                    {
                                                      includeDashboardMenu: true,
                                                    }
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
                          <span className="font-semibold">Suma de montos:</span>{' '}
                          ${resumenTotalCedula.sum.toFixed(2)} -{' '}
                          {resumenTotalCedula.cantidad} pago(s) con los filtros
                          actuales (incluye todas las páginas)
                        </span>
                      </div>
                    )}
                    {/* Paginación (formato: ← Anterior · 1…5 · Siguiente → + pie) */}
                    {data.total > 0 && (
                      <ListPaginationBar
                        className="mt-4"
                        page={page}
                        totalPages={Math.max(1, data.total_pages)}
                        onPageChange={p => setPage(p)}
                        subtitle={
                          typeof data.per_page === 'number'
                            ? `${data.total} registros · ${data.per_page} por página`
                            : `${data.total} registros`
                        }
                      />
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
            modoGuardarYProcesar={
              filters.sin_prestamo === 'si' || activeTab === 'revision'
            }
            esPagoConError={esRevisarPagos || activeTab === 'revision'}
            mostrarCampoCodigoDocumento={
              esRevisarPagos || activeTab === 'revision'
            }
            prestamoContextoRevisionManualId={
              pagoEditando?.prestamo_id != null &&
              Number(pagoEditando.prestamo_id) > 0
                ? Number(pagoEditando.prestamo_id)
                : undefined
            }
            claveDocumentoPagosTablaRevision={claveDocumentoPagosTablaRevision}
            bloquearCambioComprobanteCodigo={Boolean(
              pagoEditando &&
              (pagoEditando.conciliado ||
                String(pagoEditando.estado || '').toUpperCase() === 'PAGADO')
            )}
            onDuplicadoDetectado={pago => {
              // Cerrar formulario de registro y abrir Revisión Manual
              setShowRegistrarPago(false)
              setPagoEditando(null)

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
                    (esRevisarPagos || activeTab === 'revision')

                  if (omitirDeleteConErrores) {
                    toast.success(
                      'Pago guardado, conciliado y aplicado (movido a tabla operativa).'
                    )
                  } else {
                    try {
                      if (esRevisarPagos || activeTab === 'revision') {
                        await pagoConErrorService.delete(pagoIdEliminado)
                      } else {
                        await pagoService.deletePago(pagoIdEliminado)
                      }
                      toast.success(
                        'Pago guardado, conciliado, aplicado y eliminado de la lista.'
                      )
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
