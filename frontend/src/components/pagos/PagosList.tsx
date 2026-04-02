import { useState, useEffect, useRef, useMemo } from 'react'
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
  DollarSign,
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
import { useSearchParams } from 'react-router-dom'
import { SEGMENTO_INFOPAGOS } from '../../constants/rutasIngresoPago'
import { BASE_PATH } from '../../config/env'
import { useGmailPipeline } from '../../hooks/useGmailPipeline'

import { invalidateListasNotificacionesMora } from '../../constants/queryKeys'
import { getTasaHoy } from '../../services/tasaCambioService'
import { normalizarNumeroDocumento } from '../../utils/pagoExcelValidation'

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
  const [gmailScanFilter, setGmailScanFilter] = useState<
    'unread' | 'read' | 'all'
  >('unread')
  const [submenuGmailOpen, setSubmenuGmailOpen] = useState(false)
  const [cedulasReportarBsTotal, setCedulasReportarBsTotal] = useState<
    number | null
  >(null)
  const [isUploadingCedulasBs, setIsUploadingCedulasBs] = useState(false)
  const [isAgregandoCedulaBs, setIsAgregandoCedulaBs] = useState(false)
  const [isEliminandoCedulaBs, setIsEliminandoCedulaBs] = useState(false)
  const [nuevaCedulaBs, setNuevaCedulaBs] = useState('')
  const [consultaCedulaBs, setConsultaCedulaBs] = useState('')
  const [consultaCedulaBsResultado, setConsultaCedulaBsResultado] = useState<{
    en_lista: boolean
    cedula_normalizada: string | null
    total_en_lista: number
  } | null>(null)
  const [isConsultandoCedulaBs, setIsConsultandoCedulaBs] = useState(false)
  const [fechaTasaForm, setFechaTasaForm] = useState('')
  const [tasaForm, setTasaForm] = useState('')
  const [isGuardandoTasa, setIsGuardandoTasa] = useState(false)
  const [tasaExistenteDialogo, setTasaExistenteDialogo] = useState<{
    fecha: string
    tasaActual: number
    tasaNueva: number
  } | null>(null)
  const fileInputCedulasBsRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const { data: tasaHoyBanner, isLoading: tasaHoyBannerLoading } = useQuery({
    queryKey: ['tasa-hoy-banner-pagos'],
    queryFn: async () => {
      try {
        return await getTasaHoy()
      } catch {
        return null
      }
    },
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  })

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
    pagoService
      .getCedulasReportarBs()
      .then(r => setCedulasReportarBsTotal(r.total))
      .catch(() => setCedulasReportarBsTotal(0))
  }, [])

  useEffect(() => {
    return () => {
      stopGmailPolling()
    }
  }, [stopGmailPolling])

  const handleDetenerSeguimientoGmail = () => {
    stopGmailPolling()
    toast.info(
      'Seguimiento en pantalla detenido. El servidor puede seguir procesando el pipeline en segundo plano.'
    )
  }

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

  const handleGuardarTasa = async () => {
    if (!fechaTasaForm.trim()) {
      toast.error('Seleccione una fecha')
      return
    }
    const tasaNum = parseFloat(tasaForm)
    if (isNaN(tasaNum) || tasaNum <= 0) {
      toast.error('Ingrese una tasa válida mayor a 0')
      return
    }

    setIsGuardandoTasa(true)
    try {
      // Importar servicios
      const { getTasaPorFecha, guardarTasaPorFecha } =
        await import('../../services/tasaCambioService')

      // Verificar si ya existe tasa para esa fecha
      const tasaExistente = await getTasaPorFecha(fechaTasaForm)

      if (tasaExistente && tasaExistente.tasa_oficial !== tasaNum) {
        // Mostrar diálogo de confirmación
        setTasaExistenteDialogo({
          fecha: fechaTasaForm,
          tasaActual: tasaExistente.tasa_oficial,
          tasaNueva: tasaNum,
        })
        setIsGuardandoTasa(false)
        return
      }

      // Guardar la tasa
      await guardarTasaPorFecha(fechaTasaForm, tasaNum)

      const accion = tasaExistente ? 'Tasa actualizada' : 'Tasa guardada'
      toast.success(`✓ ${accion} para ${fechaTasaForm}`)
      setFechaTasaForm('')
      setTasaForm('')

      // Refrescar query de tasa
      await queryClient.invalidateQueries({
        queryKey: ['tasa-hoy-banner-pagos'],
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar la tasa')
    } finally {
      setIsGuardandoTasa(false)
    }
  }

  const handleConfirmarEditarTasa = async () => {
    if (!tasaExistenteDialogo) return

    setIsGuardandoTasa(true)
    try {
      const { guardarTasaPorFecha } =
        await import('../../services/tasaCambioService')
      await guardarTasaPorFecha(
        tasaExistenteDialogo.fecha,
        tasaExistenteDialogo.tasaNueva
      )

      toast.success(
        `✓ Tasa actualizada de ${tasaExistenteDialogo.tasaActual.toFixed(2)} a ${tasaExistenteDialogo.tasaNueva.toFixed(2)}`
      )
      setFechaTasaForm('')
      setTasaForm('')
      setTasaExistenteDialogo(null)

      // Refrescar query de tasa
      await queryClient.invalidateQueries({
        queryKey: ['tasa-hoy-banner-pagos'],
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo actualizar la tasa')
    } finally {
      setIsGuardandoTasa(false)
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
      await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.invalidateQueries({
        queryKey: ['pagos-kpis'],
        exact: false,
      })
      await queryClient.invalidateQueries({
        queryKey: ['pagos-con-errores'],
        exact: false,
      })
      await invalidateListasNotificacionesMora(queryClient)
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
        'Nº documento': p.numero_documento,
        'Institución bancaria': p.institucion_bancaria ?? '',
        Estado: p.estado,
        Observaciones: (p as PagoConError).observaciones ?? '',
      }))
      const nombre = `Revision_Pagos_${new Date().toISOString().slice(0, 10)}.xlsx`
      await createAndDownloadExcel(datos, 'Revisión pagos', nombre)
      const ids = pagos.map(p => p.id)
      await pagoConErrorService.eliminarPorDescarga(ids)
      await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.invalidateQueries({
        queryKey: ['pagos-con-errores'],
        exact: false,
      })
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
        'Nº documento': p.numero_documento,
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
      queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      queryClient.invalidateQueries({
        queryKey: ['pagos-con-errores'],
        exact: false,
      })
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

  /** Claves normalizadas de nº documento que aparecen más de una vez en la página actual (advertencia visual). */
  const documentosDuplicadosEnPagina = useMemo(() => {
    const pagos = data?.pagos
    if (!pagos?.length) return new Set<string>()
    const counts = new Map<string, number>()
    for (const p of pagos) {
      const key = normalizarNumeroDocumento(p.numero_documento)
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
      await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.invalidateQueries({
        queryKey: ['pagos-con-errores'],
        exact: false,
      })
      await queryClient.invalidateQueries({
        queryKey: ['pagos-kpis'],
        exact: false,
      })
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
  return (
    <div className="space-y-6">
      {/* Cédulas que pueden reportar en Bs (rapicredit-cobros / infopagos) - visible arriba */}
      <Card className="border-blue-200 bg-blue-50/80 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base font-semibold text-gray-800">
            <FileSpreadsheet className="h-5 w-5 text-blue-600" />
            Cédulas que pueden reportar en Bs (Bolívares)
          </CardTitle>
          <p className="mt-1 text-sm text-gray-600">
            Solo las cédulas de esta lista pueden elegir «Bs» en RapiCredit
            Cobros e Infopagos. Arriba puede consultar si una cédula está en la
            lista; abajo, cargue un Excel con columna <strong>cedula</strong> o
            agregue una cédula (ej. nuevo cliente que paga en bolívares).
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <p className="text-sm font-semibold text-slate-800">
              Consultar si la cédula está en la lista
            </p>
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
              <Input
                placeholder="Ej: V12345678"
                value={consultaCedulaBs}
                onChange={e => {
                  setConsultaCedulaBs(e.target.value)
                  setConsultaCedulaBsResultado(null)
                }}
                className="w-full min-w-0 border-blue-300 sm:min-w-[220px] sm:max-w-md sm:flex-1"
                maxLength={20}
                aria-label="Cédula a consultar"
                onKeyDown={e =>
                  e.key === 'Enter' &&
                  (e.preventDefault(),
                  document.getElementById('btn-consultar-cedula-bs')?.click())
                }
              />
              <Button
                id="btn-consultar-cedula-bs"
                variant="outline"
                size="sm"
                className="border-blue-400 text-blue-800 hover:bg-blue-100 sm:shrink-0"
                disabled={isConsultandoCedulaBs || !consultaCedulaBs.trim()}
                onClick={async () => {
                  const ced = consultaCedulaBs.trim()
                  if (!ced) return
                  setIsConsultandoCedulaBs(true)
                  try {
                    const res = await pagoService.consultarCedulaReportarBs(ced)
                    setConsultaCedulaBsResultado(res)
                    setCedulasReportarBsTotal(res.total_en_lista)
                  } catch (err) {
                    setConsultaCedulaBsResultado(null)
                    toast.error(getErrorMessage(err))
                  } finally {
                    setIsConsultandoCedulaBs(false)
                  }
                }}
              >
                {isConsultandoCedulaBs ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <Search className="mr-1 h-4 w-4" />
                )}
                Consultar
              </Button>
              {consultaCedulaBsResultado && (
                <div className="flex w-full flex-col gap-1 sm:w-auto sm:min-w-[220px]">
                  {consultaCedulaBsResultado.en_lista ? (
                    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-800">
                      <CheckCircle className="h-4 w-4 shrink-0" />
                      En lista: puede elegir Bs
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-800">
                      <XCircle className="h-4 w-4 shrink-0" />
                      No está en la lista
                    </span>
                  )}
                  {consultaCedulaBsResultado.cedula_normalizada && (
                    <span className="text-xs text-slate-600">
                      Normalizada:{' '}
                      <strong>
                        {consultaCedulaBsResultado.cedula_normalizada}
                      </strong>
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-blue-200/80 pt-4">
            <p className="mb-2 text-sm font-semibold text-slate-800">
              Agregar cédula o cargar Excel
            </p>
            <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center">
              <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center">
                <Input
                  placeholder="Ej: V12345678"
                  value={nuevaCedulaBs}
                  onChange={e => setNuevaCedulaBs(e.target.value)}
                  className="w-full min-w-0 border-blue-300 sm:w-44 sm:max-w-xs"
                  maxLength={20}
                  aria-label="Cédula a agregar a la lista"
                  onKeyDown={e =>
                    e.key === 'Enter' &&
                    (e.preventDefault(),
                    document.getElementById('btn-agregar-cedula-bs')?.click())
                  }
                />
                <Button
                  id="btn-agregar-cedula-bs"
                  variant="outline"
                  size="sm"
                  className="border-blue-400 text-blue-800 hover:bg-blue-100"
                  disabled={isAgregandoCedulaBs || !nuevaCedulaBs.trim()}
                  onClick={async () => {
                    const ced = nuevaCedulaBs.trim()
                    if (!ced) return
                    setIsAgregandoCedulaBs(true)
                    try {
                      const res = await pagoService.addCedulaReportarBs(ced)
                      setCedulasReportarBsTotal(res.total)
                      setNuevaCedulaBs('')
                      toast.success(res.mensaje)
                    } catch (err) {
                      toast.error(getErrorMessage(err))
                    } finally {
                      setIsAgregandoCedulaBs(false)
                    }
                  }}
                >
                  {isAgregandoCedulaBs ? (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="mr-1 h-4 w-4" />
                  )}
                  Agregar cédula
                </Button>
              </div>
              <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center">
                <Input
                  placeholder="Ej: V12345678 (eliminar)"
                  value={consultaCedulaBs}
                  onChange={e => setConsultaCedulaBs(e.target.value)}
                  className="w-full min-w-0 border-red-300 sm:w-44 sm:max-w-xs"
                  maxLength={20}
                  aria-label="Cédula a eliminar de la lista"
                  onKeyDown={e =>
                    e.key === 'Enter' &&
                    (e.preventDefault(),
                    document.getElementById('btn-eliminar-cedula-bs')?.click())
                  }
                />
                <Button
                  id="btn-eliminar-cedula-bs"
                  variant="outline"
                  size="sm"
                  className="border-red-400 text-red-800 hover:bg-red-100"
                  disabled={isEliminandoCedulaBs || !consultaCedulaBs.trim()}
                  onClick={async () => {
                    const ced = consultaCedulaBs.trim()
                    if (!ced) return
                    setIsEliminandoCedulaBs(true)
                    try {
                      const res = await pagoService.removeCedulaReportarBs(ced)
                      setCedulasReportarBsTotal(res.total)
                      setConsultaCedulaBs('')
                      toast.success(res.mensaje)
                    } catch (err) {
                      toast.error(getErrorMessage(err))
                    } finally {
                      setIsEliminandoCedulaBs(false)
                    }
                  }}
                >
                  {isEliminandoCedulaBs ? (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="mr-1 h-4 w-4" />
                  )}
                  Eliminar cédula
                </Button>
              </div>
              <input
                ref={fileInputCedulasBsRef}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={async e => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  setIsUploadingCedulasBs(true)
                  try {
                    const res = await pagoService.uploadCedulasReportarBs(file)
                    setCedulasReportarBsTotal(res.total)
                    toast.success(res.mensaje)
                    if (fileInputCedulasBsRef.current)
                      fileInputCedulasBsRef.current.value = ''
                  } catch (err) {
                    toast.error(getErrorMessage(err))
                  } finally {
                    setIsUploadingCedulasBs(false)
                  }
                }}
              />
              <Button
                variant="outline"
                size="sm"
                className="border-blue-400 text-blue-800 hover:bg-blue-100"
                onClick={() => fileInputCedulasBsRef.current?.click()}
                disabled={isUploadingCedulasBs}
              >
                {isUploadingCedulasBs ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Cargar Excel (columna cedula)
              </Button>
              {cedulasReportarBsTotal !== null && (
                <span className="text-sm text-gray-700">
                  <strong>{cedulasReportarBsTotal}</strong> cédula(s) cargada(s)
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="border-amber-200 bg-gradient-to-br from-amber-50 to-amber-50/50 shadow-sm">
        <CardContent className="space-y-6 py-6">
          {/* Header */}
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Plus className="h-5 w-5 text-amber-700" />
              <h3 className="text-lg font-bold text-gray-900">
                Agregar Tasa para Fecha de Pago
              </h3>
            </div>
            <p className="text-sm text-gray-700">
              Use la <strong>fecha de pago</strong> del reporte o comprobante.
              Es la tasa oficial Bs./USD para convertir bolívares a dólares.
              Ideal para días pasados o faltantes que no cuentan con tasa
              registrada.
            </p>
          </div>

          {/* Tasa Vigente Banner */}
          {tasaHoyBannerLoading ? (
            <div className="flex items-center gap-2 rounded-lg bg-white/80 p-4 text-sm text-amber-800">
              <Loader2 className="h-4 w-4 animate-spin text-amber-600" />
              Consultando tasa del día...
            </div>
          ) : tasaHoyBanner ? (
            <div className="flex items-center gap-3 rounded-lg bg-white/80 p-4">
              <DollarSign className="h-6 w-6 text-amber-700" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-gray-600">
                  Tasa Vigente Hoy
                </p>
                <p className="text-base font-semibold text-amber-900">
                  {(tasaHoyBanner.fecha || '').slice(0, 10)}: Bs.{' '}
                  {new Intl.NumberFormat('es-VE', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  }).format(tasaHoyBanner.tasa_oficial)}{' '}
                  por 1 USD
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2 rounded-lg bg-amber-100/60 p-4 text-sm text-amber-900">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>
                No hay tasa cargada para hoy. Ingrese la tasa en Administracion
                para operar pagos en bolivares.
              </span>
            </div>
          )}

          {/* Formulario: Fecha + Tasa */}
          <div className="rounded-lg bg-white p-5 shadow-sm">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {/* Fecha */}
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Fecha de Pago
                </label>
                <input
                  type="date"
                  value={fechaTasaForm}
                  onChange={e => setFechaTasaForm(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  placeholder="Seleccione una fecha"
                />
                <p className="text-xs text-gray-500">Máximo: hoy</p>
              </div>

              {/* Tasa */}
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Tasa Oficial (Bs. por 1 USD)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="999999.99"
                  value={tasaForm}
                  onChange={e => setTasaForm(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  placeholder="ej. 3105.75"
                />
                <p className="text-xs text-gray-500">2 decimales máximo</p>
              </div>

              {/* Botón */}
              <div className="flex flex-col justify-end gap-2">
                <button
                  onClick={handleGuardarTasa}
                  disabled={isGuardandoTasa}
                  className="rounded-lg bg-amber-700 px-6 py-2.5 font-semibold text-white shadow-sm transition hover:bg-amber-800 focus:ring-2 focus:ring-amber-400 disabled:cursor-not-allowed disabled:bg-gray-400"
                >
                  {isGuardandoTasa ? 'Guardando...' : 'Guardar Tasa'}
                </button>
                <p className="text-center text-xs text-gray-500">
                  Se agregará al historial
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Diálogo de confirmación para editar tasa existente */}
      {tasaExistenteDialogo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-2xl">
            <h3 className="mb-2 text-lg font-bold text-gray-900">
              Tasa ya existe para esta fecha
            </h3>
            <p className="mb-6 text-sm text-gray-600">
              Ya hay una tasa registrada para {tasaExistenteDialogo.fecha}.
              ¿Deseas actualizarla?
            </p>

            <div className="mb-6 space-y-3 rounded-lg bg-amber-50 p-4">
              <div className="flex justify-between">
                <span className="text-sm text-gray-700">Tasa actual:</span>
                <span className="font-semibold text-amber-700">
                  {tasaExistenteDialogo.tasaActual.toFixed(2)} Bs/USD
                </span>
              </div>
              <div className="flex justify-between border-t border-amber-200 pt-3">
                <span className="text-sm text-gray-700">Tasa nueva:</span>
                <span className="font-semibold text-green-700">
                  {tasaExistenteDialogo.tasaNueva.toFixed(2)} Bs/USD
                </span>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setTasaExistenteDialogo(null)}
                disabled={isGuardandoTasa}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmarEditarTasa}
                disabled={isGuardandoTasa}
                className="flex-1 rounded-lg bg-green-600 px-4 py-2.5 font-semibold text-white transition hover:bg-green-700 disabled:bg-gray-400"
              >
                {isGuardandoTasa ? 'Actualizando...' : 'Actualizar'}
              </button>
            </div>
          </div>
        </div>
      )}

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
                        <span className="text-amber-700">
                          {gmailStatus.last_correos_marcados_revision}{' '}
                          destacado(s) en Gmail (revisar formato).
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
                    <div>
                      <label className="mb-1 block text-xs text-gray-600">
                        Correos a escanear (Gmail)
                      </label>
                      <Select
                        value={gmailScanFilter}
                        onValueChange={(v: 'unread' | 'read' | 'all') =>
                          setGmailScanFilter(v)
                        }
                      >
                        <SelectTrigger className="h-9 text-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="unread">No leídos</SelectItem>
                          <SelectItem value="read">Leídos</SelectItem>
                          <SelectItem value="all">
                            Todos (leídos y no leídos)
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      {gmailScanFilter === 'all' && (
                        <p className="mt-1.5 text-xs text-gray-600">
                          Se descargarán todos los correos (leídos y no leídos)
                          del buzón principal.
                        </p>
                      )}
                    </div>
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
                        <span>
                          Detener seguimiento (deja de consultar el estado)
                        </span>
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
                          toast.success(
                            'Excel descargado (todas las filas guardadas).'
                          )
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
                          : 'Descargar Excel (todas las filas guardadas)'}
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
                        {isVaciarTablaGmail
                          ? 'Vaciando...'
                          : 'Vaciar tabla (solo cuando tú lo pidas)'}
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
                      toast.success('Excel descargado.')
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
      </div>
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
                          <TableHead>Fotografía</TableHead>
                          <TableHead className="text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.pagos.map((pago: Pago) => {
                          const docKey = normalizarNumeroDocumento(
                            pago.numero_documento
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
                                    ? 'Advertencia: mismo número de documento aparece más de una vez en esta página.'
                                    : undefined
                                }
                              >
                                {pago.numero_documento ?? '-'}
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
                                {pago.documento_ruta ? (
                                  <a
                                    href={pago.documento_ruta}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1.5 font-medium text-blue-600 hover:text-blue-800"
                                    title="Visualizar fotografía"
                                  >
                                    <Eye className="h-4 w-4" />
                                    Ver foto
                                  </a>
                                ) : (
                                  <span className="text-sm text-gray-500">
                                    NA
                                  </span>
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
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['pagos'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: [
                                                    'pagos-con-errores',
                                                  ],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['pagos-kpis'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['cuotas-prestamo'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['prestamos'],
                                                  exact: false,
                                                }
                                              )
                                              await invalidateListasNotificacionesMora(
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
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['pagos'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['pagos-kpis'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['cuotas-prestamo'],
                                                  exact: false,
                                                }
                                              )
                                              await invalidateListasNotificacionesMora(
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
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['pagos'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['pagos-kpis'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['dashboard'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['cuotas-prestamo'],
                                                  exact: false,
                                                }
                                              )
                                              await queryClient.invalidateQueries(
                                                {
                                                  queryKey: ['prestamos'],
                                                  exact: false,
                                                }
                                              )
                                              await invalidateListasNotificacionesMora(
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
                  monto_pagado: pagoEditando.monto_pagado,
                  numero_documento: pagoEditando.numero_documento,
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
              // Invalidar todas las queries relacionadas con pagos primero
              await queryClient.invalidateQueries({
                queryKey: ['pagos'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['pagos-kpis'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['kpis'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['dashboard'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['kpis-principales-menu'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['dashboard-menu'],
                exact: false,
              })
              // Invalidar también la query de últimos pagos (resumen)
              await queryClient.invalidateQueries({
                queryKey: ['pagos-ultimos'],
                exact: false,
              })
              // Cuotas y préstamos (Guardar y Procesar actualiza cuotas en BD)
              await queryClient.invalidateQueries({
                queryKey: ['cuotas-prestamo'],
                exact: false,
              })
              await queryClient.refetchQueries({
                queryKey: ['cuotas-prestamo'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['prestamos'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['pagos-por-cedula'],
                exact: false,
              })
              await invalidateListasNotificacionesMora(queryClient)
              // Refetch inmediato de KPIs para actualización en tiempo real
              await queryClient.refetchQueries({
                queryKey: ['pagos-kpis'],
                exact: false,
              })
              // Refetch de todas las queries relacionadas con pagos (no solo activas)
              // Esto asegura que las queries se actualicen incluso si no están montadas
              const refetchResult = await queryClient.refetchQueries({
                queryKey: ['pagos'],
                exact: false,
              })
              // Refetch también de queries activas para actualización inmediata
              const activeRefetchResult = await queryClient.refetchQueries({
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
            await queryClient.invalidateQueries({
              queryKey: ['pagos'],
              exact: false,
            })
            await queryClient.invalidateQueries({
              queryKey: ['pagos-kpis'],
              exact: false,
            })
            await queryClient.invalidateQueries({
              queryKey: ['pagos-ultimos'],
              exact: false,
            })
            await queryClient.refetchQueries({
              queryKey: ['pagos'],
              exact: false,
            })
            await queryClient.refetchQueries({
              queryKey: ['pagos-kpis'],
              exact: false,
            })
            await invalidateListasNotificacionesMora(queryClient)
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
            <DialogTitle>Vaciar tabla (Generar Excel desde Gmail)</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">
            Se borrarán todos los datos de la tabla usada por «Generar Excel
            desde Gmail» (pagos_gmail_sync_item). Esta acción no se puede
            deshacer. ¿Continuar?
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
