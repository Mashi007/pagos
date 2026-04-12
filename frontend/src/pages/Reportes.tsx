import { useState, type ComponentType, type SVGProps } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { motion } from 'framer-motion'

import {
  FileText,
  Download,
  TrendingUp,
  Users,
  DollarSign,
  Loader2,
  UserCheck,
  CreditCard,
  Lock,
  Calculator,
  CheckCircle2,
  Mail,
  Search,
  Copy,
  Calendar,
  FileSpreadsheet,
  Wallet,
  Database,
  Car,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { getErrorMessage, getErrorDetail } from '../types/errors'

import { Button } from '../components/ui/button'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { formatCurrency } from '../utils'

import { reporteService } from '../services/reporteService'

import {
  notificacionService,
  type HistorialEnvioItem,
} from '../services/notificacionService'

import { toast } from 'sonner'

import { Input } from '../components/ui/input'

import {
  DialogReporteFiltros,
  type FiltrosReporte,
} from '../components/reportes/DialogReporteFiltros'

import {
  DialogReporteContableFiltros,
  type FiltrosReporteContable,
} from '../components/reportes/DialogReporteContableFiltros'

import { DialogConciliacion } from '../components/reportes/DialogConciliacion'

import { usePermissions } from '../hooks/usePermissions'

import {
  DEFAULT_MESES_VENTANA_PAGOS,
  REPORTES_TOAST,
} from '../constants/reportes'

import {
  validateFiltrosReporte,
  validateFiltrosReporteContable,
  validateLotesClientesHoja,
} from '../utils/reportesFiltros'

import { BASE_PATH, PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

/** Path público de estado de cuenta (consultar por cédula, PDF por correo). */

const PUBLIC_ESTADO_CUENTA_PATH = 'rapicredit-estadocuenta'

/** Ruta relativa de esta pagina (compartir URL del Centro de Reportes). */

const REPORTES_PAGE_PATH = 'reportes'

function getLinkParaCompartir(path: string): string {
  const base = typeof window !== 'undefined' ? window.location.origin : ''

  const pathBase = (BASE_PATH || '').replace(/\/$/, '')

  return `${base}${pathBase ? `/${pathBase}` : ''}/${path}`.replace(/\/+/g, '/')
}

/** Cada icono = un reporte. Click = abre diálogo años/meses, luego descarga Excel. */

type TipoReporteItem = {
  value: string
  label: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
  /** Tooltip opcional para no confundir reportes parecidos (p. ej. Fechas vs Fecha Drive). */
  titleExtra?: string
  /** Texto corto bajo la etiqueta (visible sin pasar el mouse). */
  subtitle?: string
}

function tituloDescargaReporte(tipo: TipoReporteItem): string {
  const base = `Descargar ${tipo.label} en Excel`
  return tipo.titleExtra ? `${base}. ${tipo.titleExtra}` : base
}

const tiposReporte: TipoReporteItem[] = [
  { value: 'CARTERA', label: 'Cuentas por cobrar', icon: DollarSign },

  { value: 'MOROSIDAD', label: 'Morosidad', icon: TrendingUp },

  { value: 'VENCIMIENTO', label: 'Vencimiento', icon: FileText },

  { value: 'PAGOS', label: 'Pagos', icon: Users },

  {
    value: 'FECHAS',
    label: 'Fechas préstamos',
    icon: Calendar,
    subtitle: '8 columnas · solo BD (sin hoja Drive)',
    /** Texto largo para tooltip: evitar confundir con Fecha Drive. */
    titleExtra:
      'Solo sistema: ID, cédula, estado, fechas y total (8 columnas). Para cruce con la hoja CONCILIACIÓN use "Fecha Drive" en Contable.',
  },

  { value: 'ASESORES', label: 'Pago vencido', icon: UserCheck },

  { value: 'CONTABLE', label: 'Contable', icon: Calculator },

  { value: 'CEDULA', label: 'Por cédula', icon: CreditCard },

  { value: 'CONCILIACION', label: 'Conciliación', icon: CheckCircle2 },

  {
    value: 'FECHA_DRIVE',
    label: 'Fecha Drive',
    icon: FileSpreadsheet,
    subtitle: '5 columnas · hoja vs sistema',
    titleExtra:
      'Comparación hoja CONCILIACIÓN (Drive) vs préstamos: 5 columnas; NE si falta dato en un lado.',
  },

  {
    value: 'ANALISIS_FINANCIAMIENTO',
    label: 'Análisis financiamiento',
    icon: Wallet,
    subtitle: '5 columnas · total hoja vs BD',
    titleExtra:
      'Misma lógica que Fecha Drive por cédula, pero compara total financiamiento en la hoja vs préstamos.',
  },

  {
    value: 'CLIENTES_HOJA',
    label: 'Clientes (hoja)',
    icon: Mail,
    subtitle: '4 columnas · filtro por lote (LOTE)',
    titleExtra:
      'Cédula, nombres, teléfono y email desde la hoja CONCILIACIÓN; solo filas cuya columna LOTE coincide con el o los números indicados (ej. 70).',
  },

  {
    value: 'PRESTAMOS_DRIVE',
    label: 'Préstamos Drive',
    icon: Car,
    subtitle: '10 columnas · filtro por lote (LOTE)',
    titleExtra:
      'Desde la hoja CONCILIACIÓN: cédula, total financiamiento, modalidad, fechas, producto, concesionario, analista, modelo y número de cuotas; solo filas cuya columna LOTE coincide con el o los números indicados (ej. 70).',
  },
]

const REPORTES_COBRANZA = [
  'CARTERA',
  'MOROSIDAD',
  'VENCIMIENTO',
  'PAGOS',
  'FECHAS',
  'ASESORES',
]

/** Excel desde snapshot de la pestaña CONCILIACIÓN (sync Drive → BD). */
const REPORTES_DESDE_DRIVE_SHEET = [
  'FECHA_DRIVE',
  'ANALISIS_FINANCIAMIENTO',
  'CLIENTES_HOJA',
  'PRESTAMOS_DRIVE',
] as const

const REPORTES_CONTABLE_CORE = ['CONTABLE', 'CEDULA', 'CONCILIACION'] as const

const REPORTES_CONTABLE = [
  ...REPORTES_CONTABLE_CORE,
  ...REPORTES_DESDE_DRIVE_SHEET,
] as const

export function Reportes() {
  const [generandoReporte, setGenerandoReporte] = useState<string | null>(null)

  const [dialogAbierto, setDialogAbierto] = useState(false)

  const [reporteSeleccionado, setReporteSeleccionado] = useState<string | null>(
    null
  )

  const [dialogConciliacionAbierto, setDialogConciliacionAbierto] =
    useState(false)

  const [isRefreshingManual, setIsRefreshingManual] = useState(false)

  const queryClient = useQueryClient()

  const { canViewReports, canDownloadReports, canAccessReport } =
    usePermissions()

  const puedeVerReportes = canViewReports()

  // Historial de notificaciones por cédula (reportes / legales)

  const [cedulaHistorial, setCedulaHistorial] = useState('')

  const [historialItems, setHistorialItems] = useState<HistorialEnvioItem[]>([])

  const [historialCedulaLabel, setHistorialCedulaLabel] = useState('')

  const [loadingHistorial, setLoadingHistorial] = useState(false)

  const [loadingExcelHistorial, setLoadingExcelHistorial] = useState(false)

  /** Clave de descarga en curso: html:ID, pdf:ID, mhtml:ID, mtxt:ID, adj:envioId:adjId */

  const [loadingHistorialDescarga, setLoadingHistorialDescarga] = useState<
    string | null
  >(null)

  // Bloque mostrado si canViewReports() restringe por rol (ej. solo admin). Restriccion por tipo de reporte: canAccessReport().

  if (!puedeVerReportes) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="space-y-8"
      >
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Lock className="h-5 w-5 text-red-600" />

              <div>
                <p className="font-semibold text-red-800">Acceso Restringido</p>

                <p className="mt-1 text-sm text-red-700">
                  No tienes permisos para acceder al Centro de Reportes.
                  Contacta al administrador.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    )
  }

  const copiarEnlaceServicio = (path: string, label: string) => {
    const url = getLinkParaCompartir(path)

    navigator.clipboard.writeText(url).then(
      () => toast.success(`Enlace copiado: ${label}`),

      () => toast.error('No se pudo copiar el enlace')
    )
  }

  // Descargar blob como archivo

  const descargarBlob = (blob: Blob, nombre: string) => {
    const url = window.URL.createObjectURL(blob)

    const link = document.createElement('a')

    link.href = url

    link.download = nombre

    document.body.appendChild(link)

    link.click()

    document.body.removeChild(link)

    window.URL.revokeObjectURL(url)
  }

  // Abrir diálogo al hacer clic en icono (o descargar directo si no requiere filtros)

  const abrirDialogoReporte = (tipo: string) => {
    if (tipo === 'CONCILIACION') {
      setDialogConciliacionAbierto(true)

      return
    }

    if (
      tipo === 'CEDULA' ||
      tipo === 'MOROSIDAD' ||
      tipo === 'FECHAS' ||
      tipo === 'FECHA_DRIVE' ||
      tipo === 'ANALISIS_FINANCIAMIENTO'
    ) {
      generarReporte(tipo, {
        ['a\u00f1os']: [],
        meses: [],
      } as unknown as FiltrosReporte)

      return
    }

    setReporteSeleccionado(tipo)

    setDialogAbierto(true)
  }

  const generarReporteContable = async (filtros: FiltrosReporteContable) => {
    try {
      const errContable = validateFiltrosReporteContable(filtros)
      if (errContable) {
        toast.error(errContable)
        return
      }

      setGenerandoReporte('CONTABLE')

      const toastId = toast.loading(
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />

          <span>Preparando descarga de Contable...</span>
        </div>
      )

      const fechaCorte = new Date().toISOString().split('T')[0]

      const cedulas = filtros.cedulas === 'todas' ? undefined : filtros.cedulas

      const { blob, vacio } = await reporteService.exportarReporteContable(
        filtros.años,
        filtros.meses,
        cedulas
      )

      descargarBlob(blob, `reporte_contable_${fechaCorte}.xlsx`)

      toast.dismiss(toastId)

      if (vacio) {
        toast.warning(
          'El reporte no tiene datos para el período seleccionado. Verifique que las fechas sean pasadas y que existan cuotas pagadas.'
        )
      } else {
        toast.success(REPORTES_TOAST.contableOk)
      }
    } catch (error: unknown) {
      console.error('Error generando reporte:', error)

      toast.dismiss()

      const errorMessage = getErrorMessage(error)

      const detail = getErrorDetail(error)

      toast.error(detail || errorMessage || 'No se pudo generar el reporte')
    } finally {
      setGenerandoReporte(null)
    }
  }

  const buscarHistorialNotificaciones = async () => {
    const ced = cedulaHistorial.trim()

    if (!ced) {
      toast.error('Ingrese una cédula para consultar el historial.')

      return
    }

    setLoadingHistorial(true)

    try {
      const res =
        await notificacionService.getHistorialNotificacionesPorCedula(ced)

      setHistorialItems(res.items || [])

      setHistorialCedulaLabel(res.cedula || ced)

      if ((res.items?.length ?? 0) === 0) {
        toast.info('No hay notificaciones registradas para esta cédula.')
      }
    } catch (e) {
      console.error(e)

      toast.error(getErrorMessage(e) || 'Error al cargar historial.')

      setHistorialItems([])
    } finally {
      setLoadingHistorial(false)
    }
  }

  const descargarHistorialExcel = async () => {
    const ced = historialCedulaLabel || cedulaHistorial.trim()

    if (!ced) return

    setLoadingExcelHistorial(true)

    try {
      const blob =
        await notificacionService.descargarHistorialNotificacionesExcel(ced)

      descargarBlob(
        blob,
        `historial_notificaciones_${ced.replace(/\s/g, '_')}.xlsx`
      )

      toast.success('Excel descargado.')
    } catch (e) {
      console.error(e)

      toast.error(getErrorMessage(e) || 'Error al descargar Excel.')
    } finally {
      setLoadingExcelHistorial(false)
    }
  }

  const abrirComprobantePdfEnVentana = async (envioId: number) => {
    const key = `pdf-view:${envioId}`

    setLoadingHistorialDescarga(key)

    try {
      const blob =
        await notificacionService.descargarHistorialComprobantePdf(envioId)

      const url = URL.createObjectURL(blob)

      const w = window.open(url, '_blank')

      if (!w) {
        URL.revokeObjectURL(url)
        toast.error('Permita ventanas emergentes para ver el comprobante PDF.')
      } else {
        window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
      }
    } catch (e) {
      console.error(e)

      toast.error(getErrorMessage(e) || 'Error al abrir el comprobante PDF.')
    } finally {
      setLoadingHistorialDescarga(null)
    }
  }

  const descargarHistorialComprobantePdf = async (envioId: number) => {
    const key = `pdf:${envioId}`

    setLoadingHistorialDescarga(key)

    try {
      const blob =
        await notificacionService.descargarHistorialComprobantePdf(envioId)

      descargarBlob(blob, `comprobante_notificacion_${envioId}.pdf`)

      toast.success('Comprobante PDF descargado.')
    } catch (e) {
      console.error(e)

      toast.error(
        getErrorMessage(e) ||
          'No hay PDF o no está disponible para este envío (registros antiguos).'
      )
    } finally {
      setLoadingHistorialDescarga(null)
    }
  }

  const descargarHistorialMensajePdf = async (envioId: number) => {
    const key = `mpdf:${envioId}`

    setLoadingHistorialDescarga(key)

    try {
      const blob =
        await notificacionService.descargarHistorialMensajePdf(envioId)

      descargarBlob(blob, `mensaje_notificacion_${envioId}.pdf`)

      toast.success('Cuerpo del mensaje descargado (PDF).')
    } catch (e) {
      console.error(e)

      toast.error(
        getErrorMessage(e) ||
          'No hay cuerpo almacenado o no se pudo generar el PDF (envíos sin snapshot).'
      )
    } finally {
      setLoadingHistorialDescarga(null)
    }
  }

  const descargarHistorialMensajeTexto = async (envioId: number) => {
    const key = `mtxt:${envioId}`

    setLoadingHistorialDescarga(key)

    try {
      const blob =
        await notificacionService.descargarHistorialMensajeTexto(envioId)

      descargarBlob(blob, `mensaje_notificacion_${envioId}.txt`)

      toast.success('Cuerpo texto descargado.')
    } catch (e) {
      console.error(e)

      toast.error(
        getErrorMessage(e) ||
          'No hay cuerpo de texto almacenado (envíos anteriores al snapshot).'
      )
    } finally {
      setLoadingHistorialDescarga(null)
    }
  }

  const descargarHistorialAdjunto = async (
    envioId: number,
    adjuntoId: number,
    nombreArchivo: string
  ) => {
    const key = `adj:${envioId}:${adjuntoId}`

    setLoadingHistorialDescarga(key)

    try {
      const blob = await notificacionService.descargarHistorialAdjunto(
        envioId,
        adjuntoId
      )

      const safe =
        (nombreArchivo || `adjunto_${adjuntoId}`)
          .replace(/[/\\?%*:|"<>]/g, '_')
          .slice(0, 180) || `adjunto_${adjuntoId}.pdf`

      descargarBlob(blob, safe)

      toast.success('Adjunto descargado.')
    } catch (e) {
      console.error(e)

      toast.error(getErrorMessage(e) || 'Error al descargar adjunto.')
    } finally {
      setLoadingHistorialDescarga(null)
    }
  }

  // Generar reporte tras confirmar filtros en el diálogo

  const generarReporte = async (tipo: string, filtros: FiltrosReporte) => {
    try {
      if (tipo === 'CLIENTES_HOJA' || tipo === 'PRESTAMOS_DRIVE') {
        const errL = validateLotesClientesHoja(filtros.lotes)
        if (errL) {
          toast.error(errL)
          return
        }
      } else if (
        tipo !== 'CEDULA' &&
        tipo !== 'MOROSIDAD' &&
        tipo !== 'FECHAS' &&
        tipo !== 'FECHA_DRIVE' &&
        tipo !== 'ANALISIS_FINANCIAMIENTO'
      ) {
        const errFiltros = validateFiltrosReporte(filtros)
        if (errFiltros) {
          toast.error(errFiltros)
          return
        }
      }

      setGenerandoReporte(tipo)

      const labelReporte =
        tiposReporte.find(t => t.value === tipo)?.label ?? tipo

      const toastId = toast.loading(
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />

          <span>Preparando descarga de {labelReporte}...</span>
        </div>
      )

      const fechaCorte = new Date().toISOString().split('T')[0]

      const ext = 'xlsx'

      if (tipo === 'CARTERA') {
        const blob = await reporteService.exportarReporteCartera(
          'excel',
          fechaCorte,
          filtros
        )

        descargarBlob(blob, `reporte_cartera_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.cartera)

        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
      } else if (tipo === 'PAGOS') {
        const blob = await reporteService.exportarReportePagos(
          'excel',
          undefined,
          undefined,
          DEFAULT_MESES_VENTANA_PAGOS,
          filtros
        )

        descargarBlob(blob, `reporte_pagos_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.pagos)

        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
      } else if (tipo === 'MOROSIDAD') {
        const blob = await reporteService.exportarReporteMorosidadCedulas()

        descargarBlob(blob, `reporte_morosidad_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.morosidad)
      } else if (tipo === 'VENCIMIENTO') {
        const blob = await reporteService.exportarReporteMorosidad(
          'excel',
          fechaCorte,
          filtros
        )

        descargarBlob(blob, `informe_vencimiento_pagos_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.vencimiento)
      } else if (tipo === 'ASESORES') {
        // ASESORES ahora es Pago vencido (antes MOROSIDAD)

        const blob = await reporteService.exportarReporteMorosidad(
          'excel',
          fechaCorte,
          filtros
        )

        descargarBlob(blob, `reporte_pago_vencido_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.pagoVencido)
      } else if (tipo === 'CEDULA') {
        const blob = await reporteService.exportarReporteCedula()

        descargarBlob(blob, `reporte_por_cedula_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.cedula)
      } else if (tipo === 'FECHAS') {
        const blob = await reporteService.exportarReporteFechasPrestamos()

        descargarBlob(blob, `FECHAS_solo_sistema_8cols_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.fechas)

        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
      } else if (tipo === 'FECHA_DRIVE') {
        const blob = await reporteService.exportarReporteFechaDrive()

        descargarBlob(
          blob,
          `FechaDrive_vs_hoja_CONCILIACION_5cols_${fechaCorte}.${ext}`
        )

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.fechaDrive)
      } else if (tipo === 'ANALISIS_FINANCIAMIENTO') {
        const blob =
          await reporteService.exportarReporteAnalisisFinanciamiento()

        descargarBlob(
          blob,
          `Analisis_financiamiento_vs_hoja_CONCILIACION_5cols_${fechaCorte}.${ext}`
        )

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.analisisFinanciamiento)
      } else if (tipo === 'CLIENTES_HOJA') {
        const blob = await reporteService.exportarReporteClientesHoja({
          lotes: filtros.lotes ?? [],
        })

        const lPart = (filtros.lotes ?? []).join('-')

        descargarBlob(
          blob,
          `Clientes_hoja_CONCILIACION_lotes_${lPart}_${fechaCorte}.${ext}`
        )

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.clientesHoja)
      } else if (tipo === 'PRESTAMOS_DRIVE') {
        const blob = await reporteService.exportarReportePrestamosDrive({
          lotes: filtros.lotes ?? [],
        })

        const lPart = (filtros.lotes ?? []).join('-')

        descargarBlob(
          blob,
          `Prestamos_drive_CONCILIACION_lotes_${lPart}_${fechaCorte}.${ext}`
        )

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.prestamosDrive)
      } else {
        toast.dismiss(toastId)

        toast.info(`Generación de reporte ${tipo} próximamente disponible`)
      }
    } catch (error: unknown) {
      console.error('Error generando reporte:', error)

      toast.dismiss()

      const errorMessage = getErrorMessage(error)

      const detail = getErrorDetail(error)

      let mensajeError = detail || errorMessage

      if (
        errorMessage?.includes('500') ||
        errorMessage?.includes('Error del servidor')
      ) {
        mensajeError =
          'Error del servidor. Por favor, intente nuevamente en unos momentos.'
      } else if (
        errorMessage?.includes('404') ||
        errorMessage?.includes('No se encontraron')
      ) {
        mensajeError = 'No se encontraron datos para los filtros seleccionados.'
      } else if (
        errorMessage?.includes('timeout') ||
        errorMessage?.includes('Timeout')
      ) {
        mensajeError =
          'La operación está tomando demasiado tiempo. Por favor, intente con un rango de fechas más corto.'
      } else if (!mensajeError) {
        mensajeError = 'No se pudo generar el reporte'
      }

      // Errores largos (ej. lista de columnas) → alert nativo para que sea legible
      if (mensajeError && mensajeError.length > 300) {
        window.alert(mensajeError)
      } else {
        toast.error(mensajeError)
      }
    } finally {
      setGenerandoReporte(null)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mx-auto max-w-5xl space-y-10"
    >
      {/* --- Encabezado de página --- */}

      <ModulePageHeader
        icon={FileText}
        title="Centro de Reportes"
        description="Descargue reportes en Excel, comparta enlaces y consulte el historial de notificaciones."
        actions={
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-11 w-11 shrink-0"
            onClick={() =>
              copiarEnlaceServicio(REPORTES_PAGE_PATH, 'Centro de Reportes')
            }
            title="Copiar enlace de esta pagina"
            aria-label="Copiar enlace del Centro de Reportes"
          >
            <Copy className="h-5 w-5" aria-hidden />
          </Button>
        }
      />

      {/* --- Sección: Enlaces para compartir --- */}

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-800">
          <span className="flex h-1 w-1 rounded-full bg-blue-500" aria-hidden />
          Enlaces para compartir
        </h2>

        <Card className="overflow-hidden border-gray-300/90 shadow-md">
          <CardContent className="space-y-5 p-5 sm:p-6">
            <p className="text-sm leading-relaxed text-gray-700">
              Copie el enlace o abra el portal según corresponda: abajo están
              agrupados los enlaces pensados para{' '}
              <strong className="font-semibold text-gray-900">clientes</strong>{' '}
              y los de uso de{' '}
              <strong className="font-semibold text-gray-900">
                personal y colaboradores
              </strong>
              .
            </p>

            <div className="grid gap-5 md:grid-cols-2">
              {/* Clientes */}
              <div className="rounded-xl border border-teal-200 bg-teal-50/60 p-4 shadow-sm ring-1 ring-teal-100/80">
                <div className="mb-3 flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-600 text-white shadow-sm">
                    <Users className="h-5 w-5" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold tracking-tight text-teal-950">
                      Clientes
                    </h3>
                    <p className="mt-0.5 text-xs leading-snug text-teal-900/80">
                      Enlaces públicos para compartir con el cliente: reporte de
                      pagos y estado de cuenta.
                    </p>
                  </div>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-10 w-full justify-start gap-2 border-teal-300/90 bg-white/90 text-teal-950 hover:bg-white sm:w-auto"
                    onClick={() =>
                      copiarEnlaceServicio(
                        PUBLIC_REPORTE_PAGO_PATH,
                        'Reporte de pagos'
                      )
                    }
                    title="Copiar enlace: Reporte de pagos"
                    aria-label="Copiar enlace reporte de pagos"
                  >
                    <DollarSign className="h-4 w-4 shrink-0" />
                    Reporte de pagos
                  </Button>

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-10 w-full justify-start gap-2 border-teal-300/90 bg-white/90 text-teal-950 hover:bg-white sm:w-auto"
                    onClick={() =>
                      copiarEnlaceServicio(
                        PUBLIC_ESTADO_CUENTA_PATH,
                        'Estado de cuenta'
                      )
                    }
                    title="Copiar enlace: Estado de cuenta"
                    aria-label="Copiar enlace estado de cuenta"
                  >
                    <FileText className="h-4 w-4 shrink-0" />
                    Estado de cuenta
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* --- Sección: Reportes para descargar --- */}

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
          <span
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm"
            aria-hidden
          >
            <Download className="h-4 w-4" />
          </span>
          Reportes para descargar
        </h2>

        <p className="max-w-3xl text-sm leading-relaxed text-gray-600">
          Elija un bloque:{' '}
          <span className="font-medium text-gray-800">Cobranza</span> (cartera,
          morosidad, pagos, etc.),{' '}
          <span className="font-medium text-violet-900">
            informes desde Drive
          </span>{' '}
          (hoja CONCILIACIÓN ya sincronizada en el servidor) o{' '}
          <span className="font-medium text-gray-800">
            contable y otros listados
          </span>
          . Varios informes abren un asistente (año/mes o, en{' '}
          <span className="font-medium text-gray-800">Clientes (hoja)</span> y{' '}
          <span className="font-medium text-gray-800">Préstamos Drive</span>,
          números de <span className="font-medium text-gray-800">LOTE</span>)
          antes de generar el Excel.
        </p>

        <Card className="overflow-hidden border border-gray-200/90 shadow-md ring-1 ring-gray-100/80">
          <CardContent className="space-y-10 pb-8 pt-8">
            {/* Cobranza y operativos */}

            <div>
              <h3 className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <span className="h-px max-w-[3rem] flex-1 rounded-full bg-slate-200" />
                Cobranza y operativos
                <span className="h-px flex-1 rounded-full bg-slate-200" />
              </h3>
              <p className="mb-4 text-xs text-slate-500">
                Datos del sistema (y en{' '}
                <span className="font-medium text-slate-700">
                  Fechas préstamos
                </span>{' '}
                solo BD). Los cruces con la hoja de Drive están en el apartado{' '}
                <span className="font-medium text-violet-800">
                  Informes desde la hoja (Drive)
                </span>{' '}
                más abajo.
              </p>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5 md:gap-4">
                {tiposReporte
                  .filter(t => REPORTES_COBRANZA.includes(t.value))
                  .map(tipo => {
                    const IconComponent = tipo.icon

                    const isGenerando = generandoReporte === tipo.value

                    const isDisponible = [
                      'CARTERA',
                      'PAGOS',
                      'MOROSIDAD',
                      'VENCIMIENTO',
                      'FECHAS',
                      'ASESORES',
                      'CONTABLE',
                      'CEDULA',
                      'CONCILIACION',
                    ].includes(tipo.value)

                    const tieneAcceso = canAccessReport(tipo.value)

                    return (
                      <button
                        key={tipo.value}
                        type="button"
                        disabled={!isDisponible || !tieneAcceso || isGenerando}
                        onClick={e => {
                          e.preventDefault()

                          e.stopPropagation()

                          if (!tieneAcceso) {
                            toast.error(
                              'No tienes permisos para acceder a este reporte'
                            )
                            return
                          }

                          abrirDialogoReporte(tipo.value)
                        }}
                        title={
                          !tieneAcceso
                            ? 'No tienes permisos para este reporte'
                            : tituloDescargaReporte(tipo)
                        }
                        className={`flex min-h-[110px] select-none flex-col items-center justify-center gap-2 rounded-xl border-2 bg-white p-5 transition-all ${
                          isDisponible && tieneAcceso
                            ? 'cursor-pointer hover:scale-[1.02] hover:border-blue-200 hover:bg-blue-50 active:scale-100'
                            : 'cursor-not-allowed opacity-50'
                        }`}
                        aria-label={
                          !tieneAcceso
                            ? 'No tienes permisos para este reporte'
                            : tituloDescargaReporte(tipo)
                        }
                      >
                        {isGenerando ? (
                          <Loader2
                            className="h-12 w-12 animate-spin text-blue-600"
                            aria-hidden
                          />
                        ) : !tieneAcceso ? (
                          <Lock
                            className="h-12 w-12 text-gray-400"
                            aria-hidden
                          />
                        ) : (
                          <IconComponent
                            className="h-12 w-12 text-blue-600"
                            aria-hidden
                          />
                        )}

                        <span className="text-center text-xs font-medium text-gray-600">
                          {tipo.label}
                        </span>

                        {tipo.subtitle && (
                          <span className="max-w-[140px] text-center text-[10px] leading-tight text-gray-400">
                            {tipo.subtitle}
                          </span>
                        )}

                        {!tieneAcceso && (
                          <span className="text-xs text-red-600">
                            Restringido
                          </span>
                        )}
                      </button>
                    )
                  })}
              </div>
            </div>

            {/* Informes desde snapshot de Drive (pestaña CONCILIACIÓN) */}

            <div className="rounded-2xl border border-violet-200/90 bg-gradient-to-br from-violet-50/95 via-white to-sky-50/40 p-5 shadow-md ring-1 ring-violet-100/60 sm:p-6">
              <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 gap-3">
                  <div
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white shadow-md"
                    aria-hidden
                  >
                    <Database className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-900/90">
                      Informes desde la hoja (Drive)
                    </h3>
                    <p className="mt-1 text-sm font-semibold leading-snug text-violet-950">
                      Pestaña{' '}
                      <span className="font-mono text-[13px]">
                        CONCILIACIÓN
                      </span>{' '}
                      sincronizada en el servidor
                    </p>
                    <p className="mt-2 max-w-2xl text-xs leading-relaxed text-violet-950/85">
                      Los botones de abajo leen el mismo snapshot en base de
                      datos (no abren el Google Sheet aquí). La copia en
                      servidor la actualiza quien opera el despliegue (cron o
                      proceso con credenciales Google). Si los datos no
                      coinciden con la hoja actual, contacte a soporte o
                      administración.
                    </p>
                  </div>
                </div>
              </div>

              <ul className="mb-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                <li className="rounded-lg border border-violet-100/90 bg-white/85 px-3 py-2 text-[11px] leading-snug text-violet-950 shadow-sm">
                  <span className="font-semibold text-violet-900">
                    Fecha Drive
                  </span>
                  : cédulas y fecha de aprobación hoja (col. Q) vs sistema.
                </li>
                <li className="rounded-lg border border-violet-100/90 bg-white/85 px-3 py-2 text-[11px] leading-snug text-violet-950 shadow-sm">
                  <span className="font-semibold text-violet-900">
                    Análisis financiamiento
                  </span>
                  : mismo cruce por cédula con montos de financiamiento.
                </li>
                <li className="rounded-lg border border-violet-100/90 bg-white/85 px-3 py-2 text-[11px] leading-snug text-violet-950 shadow-sm">
                  <span className="font-semibold text-violet-900">
                    Clientes (hoja)
                  </span>
                  : cédula, nombre, teléfono y correo filtrados por columna{' '}
                  <span className="font-medium">LOTE</span> (número(s) en el
                  asistente, ej. 70).
                </li>
                <li className="rounded-lg border border-violet-100/90 bg-white/85 px-3 py-2 text-[11px] leading-snug text-violet-950 shadow-sm">
                  <span className="font-semibold text-violet-900">
                    Préstamos Drive
                  </span>
                  : diez campos de la hoja (financiamiento, modalidad, fechas,
                  producto, concesionario, analista, modelo, cuotas) filtrados
                  por <span className="font-medium">LOTE</span>.
                </li>
              </ul>

              <div className="mt-1 grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
                {tiposReporte
                  .filter(t =>
                    (REPORTES_DESDE_DRIVE_SHEET as readonly string[]).includes(
                      t.value
                    )
                  )
                  .map(tipo => {
                    const IconComponent = tipo.icon

                    const isGenerando = generandoReporte === tipo.value

                    const isDisponible = (
                      REPORTES_DESDE_DRIVE_SHEET as readonly string[]
                    ).includes(tipo.value)

                    const tieneAcceso = canAccessReport(tipo.value)

                    return (
                      <button
                        key={tipo.value}
                        type="button"
                        disabled={!isDisponible || !tieneAcceso || isGenerando}
                        onClick={e => {
                          e.preventDefault()

                          e.stopPropagation()

                          if (!tieneAcceso) {
                            toast.error(
                              'No tienes permisos para acceder a este reporte'
                            )
                            return
                          }

                          abrirDialogoReporte(tipo.value)
                        }}
                        title={
                          !tieneAcceso
                            ? 'No tienes permisos para este reporte'
                            : tituloDescargaReporte(tipo)
                        }
                        className={`flex min-h-[118px] select-none flex-col items-center justify-center gap-2 rounded-xl border-2 border-violet-200/90 bg-white/95 p-4 shadow-sm transition-all ${
                          isDisponible && tieneAcceso
                            ? 'cursor-pointer hover:scale-[1.02] hover:border-violet-400 hover:bg-violet-50/90 active:scale-100'
                            : 'cursor-not-allowed opacity-50'
                        }`}
                        aria-label={
                          !tieneAcceso
                            ? 'No tienes permisos para este reporte'
                            : tituloDescargaReporte(tipo)
                        }
                      >
                        {isGenerando ? (
                          <Loader2
                            className="h-12 w-12 animate-spin text-violet-600"
                            aria-hidden
                          />
                        ) : !tieneAcceso ? (
                          <Lock
                            className="h-12 w-12 text-gray-400"
                            aria-hidden
                          />
                        ) : (
                          <IconComponent
                            className="h-12 w-12 text-violet-600"
                            aria-hidden
                          />
                        )}

                        <span className="text-center text-xs font-medium text-violet-950">
                          {tipo.label}
                        </span>

                        {tipo.subtitle && (
                          <span className="max-w-[160px] text-center text-[10px] leading-tight text-violet-800/80">
                            {tipo.subtitle}
                          </span>
                        )}

                        {!tieneAcceso && (
                          <span className="text-xs text-red-600">
                            Restringido
                          </span>
                        )}
                      </button>
                    )
                  })}
              </div>
            </div>

            {/* Contable, cédula y conciliación (sin hoja Drive) */}

            <div className="border-t border-slate-200/90 pt-8">
              <h3 className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <span className="h-px max-w-[3rem] flex-1 rounded-full bg-slate-200" />
                Contable y por cliente
                <span className="h-px flex-1 rounded-full bg-slate-200" />
              </h3>
              <p className="mb-4 max-w-2xl text-xs leading-relaxed text-slate-600">
                Reportes que salen de la base de datos y procesos internos:{' '}
                <span className="font-medium text-slate-800">Contable</span>{' '}
                (cuotas y cierre),{' '}
                <span className="font-medium text-slate-800">Por cédula</span> y
                la carga asistida de{' '}
                <span className="font-medium text-slate-800">Conciliación</span>{' '}
                (Excel hacia tablas temporales, distinto al snapshot de Drive de
                arriba).
              </p>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:gap-4">
                {tiposReporte
                  .filter(t =>
                    (REPORTES_CONTABLE_CORE as readonly string[]).includes(
                      t.value
                    )
                  )
                  .map(tipo => {
                    const IconComponent = tipo.icon

                    const isGenerando = generandoReporte === tipo.value

                    const isDisponible = (
                      REPORTES_CONTABLE_CORE as readonly string[]
                    ).includes(tipo.value)

                    const tieneAcceso = canAccessReport(tipo.value)

                    return (
                      <button
                        key={tipo.value}
                        type="button"
                        disabled={!isDisponible || !tieneAcceso || isGenerando}
                        onClick={e => {
                          e.preventDefault()

                          e.stopPropagation()

                          if (!tieneAcceso) {
                            toast.error(
                              'No tienes permisos para acceder a este reporte'
                            )
                            return
                          }

                          abrirDialogoReporte(tipo.value)
                        }}
                        title={
                          !tieneAcceso
                            ? 'No tienes permisos para este reporte'
                            : tituloDescargaReporte(tipo)
                        }
                        className={`flex min-h-[118px] select-none flex-col items-center justify-center gap-2 rounded-xl border-2 bg-white p-4 shadow-sm transition-all ${
                          isDisponible && tieneAcceso
                            ? 'cursor-pointer hover:scale-[1.02] hover:border-blue-300 hover:bg-blue-50/90 active:scale-100'
                            : 'cursor-not-allowed opacity-50'
                        }`}
                        aria-label={
                          !tieneAcceso
                            ? 'No tienes permisos para este reporte'
                            : tituloDescargaReporte(tipo)
                        }
                      >
                        {isGenerando ? (
                          <Loader2
                            className="h-12 w-12 animate-spin text-blue-600"
                            aria-hidden
                          />
                        ) : !tieneAcceso ? (
                          <Lock
                            className="h-12 w-12 text-gray-400"
                            aria-hidden
                          />
                        ) : (
                          <IconComponent
                            className="h-12 w-12 text-blue-600"
                            aria-hidden
                          />
                        )}

                        <span className="text-center text-xs font-medium text-slate-700">
                          {tipo.label}
                        </span>

                        {tipo.subtitle && (
                          <span className="max-w-[160px] text-center text-[10px] leading-tight text-slate-500">
                            {tipo.subtitle}
                          </span>
                        )}

                        {!tieneAcceso && (
                          <span className="text-xs text-red-600">
                            Restringido
                          </span>
                        )}
                      </button>
                    )
                  })}
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* --- Sección: Historial de notificaciones --- */}

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-800">
          <span className="flex h-1 w-1 rounded-full bg-blue-500" aria-hidden />
          Historial de notificaciones por cédula
        </h2>

        <Card className="border-gray-200/80 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base font-medium">
              <Mail className="h-5 w-5 text-blue-600" />
              Consultar y descargar historial
            </CardTitle>

            <p className="text-sm text-muted-foreground">
              Consulte por cédula el historial de notificaciones enviadas.
              Descargue Excel, comprobante PDF (oficial) y desde envíos
              recientes el cuerpo del correo y los PDFs adjuntos tal como se
              enviaron.
            </p>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Input
                type="text"
                placeholder="Cédula del cliente"
                value={cedulaHistorial}
                onChange={e => setCedulaHistorial(e.target.value)}
                onKeyDown={e =>
                  e.key === 'Enter' && buscarHistorialNotificaciones()
                }
                className="max-w-xs"
              />

              <Button
                type="button"
                onClick={buscarHistorialNotificaciones}
                disabled={loadingHistorial || !cedulaHistorial.trim()}
              >
                {loadingHistorial ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}

                <span className="ml-2">Buscar</span>
              </Button>

              {historialItems.length > 0 && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={descargarHistorialExcel}
                  disabled={loadingExcelHistorial}
                >
                  {loadingExcelHistorial ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}

                  <span className="ml-2">Descargar Excel (histórico)</span>
                </Button>
              )}
            </div>

            {historialCedulaLabel && (
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left font-semibold">
                        Fecha
                      </th>

                      <th className="px-3 py-2 text-left font-semibold">
                        Tipo
                      </th>

                      <th className="px-3 py-2 text-left font-semibold">
                        Asunto
                      </th>

                      <th className="px-3 py-2 text-left font-semibold">
                        Email
                      </th>

                      <th className="px-3 py-2 text-left font-semibold">
                        Estado
                      </th>

                      <th className="px-3 py-2 text-left font-semibold">
                        Acción
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {historialItems.length === 0 ? (
                      <tr>
                        <td
                          colSpan={6}
                          className="py-6 text-center text-gray-500"
                        >
                          No hay notificaciones para la cédula consultada.
                        </td>
                      </tr>
                    ) : (
                      historialItems.map(row => (
                        <tr key={row.id} className="border-b hover:bg-gray-50">
                          <td className="px-3 py-2">
                            {row.fecha_envio
                              ? new Date(row.fecha_envio).toLocaleString('es')
                              : '-'}
                          </td>

                          <td className="px-3 py-2">{row.tipo_tab || '-'}</td>

                          <td
                            className="max-w-[200px] truncate px-3 py-2"
                            title={row.asunto}
                          >
                            {row.asunto || '-'}
                          </td>

                          <td className="px-3 py-2">{row.email || '-'}</td>

                          <td className="px-3 py-2">
                            <span
                              className={
                                row.exito
                                  ? 'font-medium text-green-600'
                                  : 'font-medium text-red-600'
                              }
                            >
                              {row.estado_envio === 'entregado'
                                ? 'Entregado'
                                : 'Rebotado'}
                            </span>
                          </td>

                          <td className="min-w-[200px] max-w-[280px] px-3 py-2 align-top">
                            <div className="flex flex-col gap-1">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="h-8 justify-start px-2"
                                onClick={() =>
                                  abrirComprobantePdfEnVentana(row.id)
                                }
                                disabled={
                                  loadingHistorialDescarga ===
                                  `pdf-view:${row.id}`
                                }
                              >
                                {loadingHistorialDescarga ===
                                `pdf-view:${row.id}` ? (
                                  <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                                ) : (
                                  <FileText className="h-3.5 w-3.5 shrink-0" />
                                )}

                                <span className="ml-1 text-xs">
                                  Abrir comprobante (PDF)
                                </span>
                              </Button>

                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="h-8 justify-start px-2"
                                onClick={() =>
                                  descargarHistorialComprobantePdf(row.id)
                                }
                                disabled={
                                  loadingHistorialDescarga === `pdf:${row.id}`
                                }
                              >
                                {loadingHistorialDescarga ===
                                `pdf:${row.id}` ? (
                                  <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                                ) : (
                                  <Download className="h-3.5 w-3.5 shrink-0" />
                                )}

                                <span className="ml-1 text-xs">
                                  Descargar comprobante PDF
                                </span>
                              </Button>

                              {row.tiene_mensaje_pdf ? (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 justify-start px-2"
                                  onClick={() =>
                                    descargarHistorialMensajePdf(row.id)
                                  }
                                  disabled={
                                    loadingHistorialDescarga ===
                                    `mpdf:${row.id}`
                                  }
                                >
                                  {loadingHistorialDescarga ===
                                  `mpdf:${row.id}` ? (
                                    <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                                  ) : (
                                    <Mail className="h-3.5 w-3.5 shrink-0" />
                                  )}

                                  <span className="ml-1 text-xs">
                                    Cuerpo (PDF)
                                  </span>
                                </Button>
                              ) : null}

                              {row.tiene_mensaje_texto ? (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 justify-start px-2"
                                  onClick={() =>
                                    descargarHistorialMensajeTexto(row.id)
                                  }
                                  disabled={
                                    loadingHistorialDescarga ===
                                    `mtxt:${row.id}`
                                  }
                                >
                                  {loadingHistorialDescarga ===
                                  `mtxt:${row.id}` ? (
                                    <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                                  ) : (
                                    <FileText className="h-3.5 w-3.5 shrink-0" />
                                  )}

                                  <span className="ml-1 text-xs">
                                    Cuerpo (texto)
                                  </span>
                                </Button>
                              ) : null}

                              {(row.adjuntos ?? []).map(adj => (
                                <Button
                                  key={adj.id}
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 justify-start px-2"
                                  title={adj.nombre_archivo}
                                  onClick={() =>
                                    descargarHistorialAdjunto(
                                      row.id,
                                      adj.id,
                                      adj.nombre_archivo
                                    )
                                  }
                                  disabled={
                                    loadingHistorialDescarga ===
                                    `adj:${row.id}:${adj.id}`
                                  }
                                >
                                  {loadingHistorialDescarga ===
                                  `adj:${row.id}:${adj.id}` ? (
                                    <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                                  ) : (
                                    <Download className="h-3.5 w-3.5 shrink-0" />
                                  )}

                                  <span className="ml-1 line-clamp-2 text-left text-xs">
                                    {adj.nombre_archivo || `Adjunto ${adj.id}`}
                                  </span>
                                </Button>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <DialogReporteFiltros
        key={reporteSeleccionado ?? 'filtros'}
        open={dialogAbierto && reporteSeleccionado !== 'CONTABLE'}
        onOpenChange={setDialogAbierto}
        variant={
          reporteSeleccionado === 'CLIENTES_HOJA' ||
          reporteSeleccionado === 'PRESTAMOS_DRIVE'
            ? 'lotes'
            : 'periodo'
        }
        tituloReporte={
          reporteSeleccionado && reporteSeleccionado !== 'CONTABLE'
            ? (tiposReporte.find(t => t.value === reporteSeleccionado)?.label ??
              reporteSeleccionado)
            : ''
        }
        onConfirm={filtros => {
          if (reporteSeleccionado && reporteSeleccionado !== 'CONTABLE')
            generarReporte(reporteSeleccionado, filtros)
        }}
      />

      <DialogReporteContableFiltros
        key="contable"
        open={dialogAbierto && reporteSeleccionado === 'CONTABLE'}
        onOpenChange={setDialogAbierto}
        onConfirm={filtros => generarReporteContable(filtros)}
      />

      <DialogConciliacion
        open={dialogConciliacionAbierto}
        onOpenChange={setDialogConciliacionAbierto}
        onGuardar={() => {
          queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        }}
      />
    </motion.div>
  )
}

export default Reportes
