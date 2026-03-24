import { useState } from 'react'

import { Link } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { motion } from 'framer-motion'

import {
  FileText,
  Download,
  TrendingUp,
  Users,
  DollarSign,
  RefreshCw,
  Loader2,
  UserCheck,
  CreditCard,
  Lock,
  Calculator,
  CheckCircle2,
  Mail,
  Search,
  Building2,
  Copy,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { getErrorMessage, getErrorDetail } from '../types/errors'

import { Button } from '../components/ui/button'

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

import { BASE_PATH, PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

/** Path público de estado de cuenta (consultar por cédula, PDF por correo). */

const PUBLIC_ESTADO_CUENTA_PATH = 'rapicredit-estadocuenta'

/** Path para personal: registro de pago a nombre del deudor (sin token; recibo al email y descarga). */

const INFOPAGOS_PATH = 'infopagos'

/** Portal público Finiquito (colaboradores: código por correo). */

const PUBLIC_FINIQUITO_PATH = 'finiquitos'

/** Ruta relativa de esta pagina (compartir URL del Centro de Reportes). */

const REPORTES_PAGE_PATH = 'reportes'

function getLinkParaCompartir(path: string): string {
  const base = typeof window !== 'undefined' ? window.location.origin : ''

  const pathBase = (BASE_PATH || '').replace(/\/$/, '')

  return `${base}${pathBase ? `/${pathBase}` : ''}/${path}`.replace(/\/+/g, '/')
}

/** Cada icono = un reporte. Click = abre diálogo años/meses, luego descarga Excel. */

const tiposReporte = [
  { value: 'CARTERA', label: 'Cuentas por cobrar', icon: DollarSign },

  { value: 'MOROSIDAD', label: 'Morosidad', icon: TrendingUp },

  { value: 'VENCIMIENTO', label: 'Vencimiento', icon: FileText },

  { value: 'PAGOS', label: 'Pagos', icon: Users },

  { value: 'ASESORES', label: 'Pago vencido', icon: UserCheck },

  { value: 'CONTABLE', label: 'Contable', icon: Calculator },

  { value: 'CEDULA', label: 'Por cédula', icon: CreditCard },

  { value: 'CONCILIACION', label: 'Conciliación', icon: CheckCircle2 },
]

const REPORTES_COBRANZA = [
  'CARTERA',
  'MOROSIDAD',
  'VENCIMIENTO',
  'PAGOS',
  'ASESORES',
]

const REPORTES_CONTABLE = ['CONTABLE', 'CEDULA', 'CONCILIACION']

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

  const [loadingComprobanteId, setLoadingComprobanteId] = useState<
    number | null
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

    if (tipo === 'MOROSIDAD') {
      generarReporte(tipo, { años: [], meses: [] })

      return
    }

    if (tipo === 'CEDULA') {
      generarReporte(tipo, { años: [], meses: [] })

      return
    }

    setReporteSeleccionado(tipo)

    setDialogAbierto(true)
  }

  const generarReporteContable = async (filtros: FiltrosReporteContable) => {
    try {
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
        toast.success('âœ" Reporte Contable descargado exitosamente')
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

  const abrirComprobante = async (envioId: number) => {
    setLoadingComprobanteId(envioId)

    try {
      const html = await notificacionService.getComprobanteEnvioHtml(envioId)

      const w = window.open('', '_blank')

      if (w) {
        w.document.write(html)

        w.document.close()
      } else {
        toast.error('Permita ventanas emergentes para ver el comprobante.')
      }
    } catch (e) {
      console.error(e)

      toast.error(getErrorMessage(e) || 'Error al abrir comprobante.')
    } finally {
      setLoadingComprobanteId(null)
    }
  }

  // Generar reporte tras confirmar filtros en el diálogo

  const generarReporte = async (tipo: string, filtros: FiltrosReporte) => {
    try {
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

        toast.success('âœ" Reporte de Cartera descargado exitosamente')

        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
      } else if (tipo === 'PAGOS') {
        const blob = await reporteService.exportarReportePagos(
          'excel',
          undefined,
          undefined,
          12,
          filtros
        )

        descargarBlob(blob, `reporte_pagos_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success('âœ" Informe de Pagos descargado exitosamente')

        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
      } else if (tipo === 'MOROSIDAD') {
        const blob =
          await reporteService.exportarReporteMorosidadClientes(fechaCorte)

        descargarBlob(blob, `reporte_morosidad_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success('âœ" Reporte de Morosidad descargado exitosamente')
      } else if (tipo === 'VENCIMIENTO') {
        const blob = await reporteService.exportarReporteMorosidad(
          'excel',
          fechaCorte,
          filtros
        )

        descargarBlob(blob, `informe_vencimiento_pagos_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success('âœ" Reporte de Vencimiento descargado exitosamente')
      } else if (tipo === 'ASESORES') {
        // ASESORES ahora es Pago vencido (antes MOROSIDAD)

        const blob = await reporteService.exportarReporteMorosidad(
          'excel',
          fechaCorte,
          filtros
        )

        descargarBlob(blob, `reporte_pago_vencido_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success('âœ" Reporte de Pago Vencido descargado exitosamente')
      } else if (tipo === 'CEDULA') {
        const blob = await reporteService.exportarReporteCedula()

        descargarBlob(blob, `reporte_por_cedula_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success('âœ" Reporte por Cédula descargado exitosamente')
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

      toast.error(mensajeError)
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

      <header className="border-b border-gray-200 pb-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-100">
              <FileText className="h-7 w-7 text-blue-600" />
            </div>

            <div className="min-w-0">
              <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
                Centro de Reportes
              </h1>

              <p className="mt-1 text-sm text-gray-500 sm:text-base">
                Descargue reportes en Excel, comparta enlaces y consulte el
                historial de notificaciones.
              </p>
            </div>
          </div>

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
        </div>
      </header>

      {/* --- Sección: Enlaces para compartir --- */}

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-800">
          <span className="flex h-1 w-1 rounded-full bg-blue-500" aria-hidden />
          Enlaces para compartir
        </h2>

        <Card className="border-gray-200/80 shadow-sm">
          <CardContent className="py-4">
            <p className="mb-4 text-sm text-gray-500">
              Copie el enlace y compártalo con clientes o equipos para consulta
              de reporte de pagos, estado de cuenta o finiquito (colaboradores).
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                asChild
                variant="outline"
                size="sm"
                className="h-11 gap-2"
              >
                <Link
                  to="/admin/tasas-cambio"
                  title="Ir a Tasa de cambio (ingreso manual)"
                  aria-label="Ir a Tasa de cambio"
                >
                  <Copy className="h-5 w-5" aria-hidden />
                  Tasa de cambio
                </Link>
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-11 gap-2"
                onClick={() =>
                  copiarEnlaceServicio(
                    PUBLIC_REPORTE_PAGO_PATH,
                    'Reporte de pagos'
                  )
                }
                title="Copiar enlace: Reporte de pagos"
                aria-label="Copiar enlace reporte de pagos"
              >
                <DollarSign className="h-5 w-5" />
                Reporte de pagos
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-11 gap-2"
                onClick={() =>
                  copiarEnlaceServicio(
                    PUBLIC_ESTADO_CUENTA_PATH,
                    'Estado de cuenta'
                  )
                }
                title="Copiar enlace: Estado de cuenta"
                aria-label="Copiar enlace estado de cuenta"
              >
                <FileText className="h-5 w-5" />
                Estado de cuenta
              </Button>

              <Button
                asChild
                variant="outline"
                size="sm"
                className="h-11 gap-2"
              >
                <Link
                  to={`/${PUBLIC_FINIQUITO_PATH}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Abrir portal Finiquito (colaboradores, código por correo)"
                  aria-label="Abrir Finiquito en nueva pestaña"
                >
                  <CheckCircle2 className="h-5 w-5" aria-hidden />
                  Abrir Finiquito
                </Link>
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-11 gap-2"
                onClick={() =>
                  copiarEnlaceServicio(PUBLIC_FINIQUITO_PATH, 'Finiquito')
                }
                title="Copiar enlace: Finiquito (acceso colaboradores con código por correo)"
                aria-label="Copiar enlace Finiquito"
              >
                <Copy className="h-5 w-5" aria-hidden />
                Copiar enlace Finiquito
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-11 gap-2"
                onClick={() =>
                  copiarEnlaceServicio(INFOPAGOS_PATH, 'Infopagos')
                }
                title="Copiar enlace: Infopagos (pago a nombre del deudor)"
                aria-label="Copiar enlace Infopagos"
              >
                <Building2 className="h-5 w-5" />
                Infopagos
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* --- Sección: Reportes para descargar --- */}

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-800">
          <span className="flex h-1 w-1 rounded-full bg-blue-500" aria-hidden />
          Reportes para descargar
        </h2>

        <p className="text-sm text-gray-500">
          Seleccione un reporte para elegir período (año/mes) y descargar en
          Excel.
        </p>

        <Card className="border-gray-200/80 shadow-sm">
          <CardContent className="space-y-8 pb-6 pt-6">
            {/* Cobranza y operativos */}

            <div>
              <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-gray-500">
                Cobranza y operativos
              </h3>

              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
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
                            : `Descargar ${tipo.label} en Excel`
                        }
                        className={`flex min-h-[110px] select-none flex-col items-center justify-center gap-2 rounded-xl border-2 bg-white p-5 transition-all ${
                          isDisponible && tieneAcceso
                            ? 'cursor-pointer hover:scale-[1.02] hover:border-blue-200 hover:bg-blue-50 active:scale-100'
                            : 'cursor-not-allowed opacity-50'
                        }`}
                        aria-label={`Descargar reporte ${tipo.label} en Excel`}
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

            {/* Contable y por cliente */}

            <div className="border-t border-gray-100 pt-4">
              <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-gray-500">
                Contable y por cliente
              </h3>

              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                {tiposReporte
                  .filter(t => REPORTES_CONTABLE.includes(t.value))
                  .map(tipo => {
                    const IconComponent = tipo.icon

                    const isGenerando = generandoReporte === tipo.value

                    const isDisponible = [
                      'CARTERA',
                      'PAGOS',
                      'MOROSIDAD',
                      'VENCIMIENTO',
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
                            : `Descargar ${tipo.label} en Excel`
                        }
                        className={`flex min-h-[110px] select-none flex-col items-center justify-center gap-2 rounded-xl border-2 bg-white p-5 transition-all ${
                          isDisponible && tieneAcceso
                            ? 'cursor-pointer hover:scale-[1.02] hover:border-blue-200 hover:bg-blue-50 active:scale-100'
                            : 'cursor-not-allowed opacity-50'
                        }`}
                        aria-label={`Descargar reporte ${tipo.label} en Excel`}
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
              Descargue un Excel con todo el historial o abra cada comprobante
              de envío (para fines administrativos y legales).
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

                          <td className="px-3 py-2">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => abrirComprobante(row.id)}
                              disabled={loadingComprobanteId === row.id}
                            >
                              {loadingComprobanteId === row.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <FileText className="h-4 w-4" />
                              )}

                              <span className="ml-1">Ver comprobante</span>
                            </Button>
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
        open={
          dialogAbierto &&
          reporteSeleccionado !== 'CONTABLE' &&
          reporteSeleccionado !== 'MOROSIDAD'
        }
        onOpenChange={setDialogAbierto}
        tituloReporte={
          reporteSeleccionado &&
          reporteSeleccionado !== 'CONTABLE' &&
          reporteSeleccionado !== 'MOROSIDAD'
            ? (tiposReporte.find(t => t.value === reporteSeleccionado)?.label ??
              reporteSeleccionado)
            : ''
        }
        onConfirm={filtros => {
          if (
            reporteSeleccionado &&
            reporteSeleccionado !== 'CONTABLE' &&
            reporteSeleccionado !== 'MOROSIDAD'
          )
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
