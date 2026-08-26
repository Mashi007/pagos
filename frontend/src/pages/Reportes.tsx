import {
  useState,
  type ComponentType,
  type SVGProps,
} from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { motion } from 'framer-motion'

import {
  FileText,
  Download,
  Users,
  DollarSign,
  LayoutList,
  Loader2,
  CreditCard,
  Lock,
  Calculator,
  CheckCircle2,
  Copy,
} from 'lucide-react'

import { Card, CardContent } from '../components/ui/card'

import { getErrorMessage, getErrorDetail } from '../types/errors'

import { Button } from '../components/ui/button'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { reporteService } from '../services/reporteService'

import { toast } from 'sonner'

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
  validateFiltrosCarteraReporte,
  validateFiltrosCarteraCorteReporte,
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
  { value: 'CARTERA', label: 'Cuentas por cobrar', icon: DollarSign, subtitle: 'Solo cuotas en mora · Max 99 = todas', titleExtra: 'Cuenta cuotas en mora oficial (4 meses + 6 días). No incluye solo vencidas. Por defecto Min 1 / Max 99 (todas).' },

  {
    value: 'ASEGURADORA_IMPAGAS',
    label: 'Impagas cedula',
    icon: LayoutList,
    subtitle: 'Impagas a corte + monto · 3 columnas',
    titleExtra:
      'Mismo universo hoja Aseguradora. Cuotas/monto impagos acumulados hasta la fecha hasta (corte); recobrado USD en el periodo desde-hasta.',
  },

  { value: 'PAGOS', label: 'Pagos', icon: Users },

  { value: 'CONTABLE', label: 'Contable', icon: Calculator },

  { value: 'CEDULA', label: 'Por cédula', icon: CreditCard },

  {
    value: 'CEDULAS_CUOTA_HOJA',
    label: 'Cédulas y cuota',
    icon: DollarSign,
    subtitle: 'Al 1 jun (todas) · hoy sin abono parcial · saldo $',
    titleExtra:
      'Cédula, email, teléfono, cuota y mora al 1 jun (todas las MORA). Mora hoy: no cuenta las que tienen abono parcial ≥ 0.10. Columna de pagos parciales 1 jun–hoy. Última: saldo total del préstamo.',
  },

  {
    value: 'SALDOS_MENORES_200',
    label: 'Saldos menores 200',
    icon: DollarSign,
    subtitle: 'Saldo final ≤ $200 · vencidas y mora',
    titleExtra:
      'Deudores APROBADO con saldo final del préstamo ≤ 200 USD. Incluye cédula, nombres, teléfono, email, saldo final, nº cuotas vencidas y nº cuotas en mora (solo cuotas con saldo a pagar ≤ 200).',
  },

  { value: 'CONCILIACION', label: 'Conciliación', icon: CheckCircle2 },
]

const REPORTES_COBRANZA = [
  'CARTERA',
  'ASEGURADORA_IMPAGAS',
  'PAGOS',
  'SALDOS_MENORES_200',
]

const REPORTES_CONTABLE_CORE = [
  'CONTABLE',
  'CEDULA',
  'CEDULAS_CUOTA_HOJA',
  'CONCILIACION',
] as const

const REPORTES_CONTABLE = [...REPORTES_CONTABLE_CORE] as const

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

  const {
    canViewReports,
    canDownloadReports,
    canAccessReport,
  } = usePermissions()

  const puedeVerReportes = canViewReports()

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

    if (tipo === 'CEDULA' || tipo === 'CEDULAS_CUOTA_HOJA' || tipo === 'SALDOS_MENORES_200') {
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

  // Generar reporte tras confirmar filtros en el diálogo

  const generarReporte = async (tipo: string, filtros: FiltrosReporte) => {
    try {
      if (tipo === 'CARTERA') {
        const errC = validateFiltrosCarteraCorteReporte(filtros)
        if (errC) {
          toast.error(errC)
          return
        }
      } else if (tipo === 'ASEGURADORA_IMPAGAS') {
        const a = (filtros.fecha_desde || '').trim()
        const b = (filtros.fecha_hasta || '').trim()
        if (a && b && a > b) {
          filtros = { ...filtros, fecha_desde: b, fecha_hasta: a }
        }
        const errC = validateFiltrosCarteraReporte(filtros)
        if (errC) {
          toast.error(errC)
          return
        }
      } else if (
        tipo !== 'CEDULA' &&
        tipo !== 'CEDULAS_CUOTA_HOJA' &&
        tipo !== 'SALDOS_MENORES_200' &&
        tipo !== 'CARTERA' &&
        tipo !== 'ASEGURADORA_IMPAGAS'
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

      const _hoyLocal = new Date()
      const fechaCorte = `${_hoyLocal.getFullYear()}-${String(_hoyLocal.getMonth() + 1).padStart(2, '0')}-${String(_hoyLocal.getDate()).padStart(2, '0')}`

      const ext = 'xlsx'

      if (tipo === 'CARTERA') {
        const formato = filtros.formato === 'pdf' ? 'pdf' : 'excel'
        const fhRaw = (filtros.fecha_hasta || fechaCorte).trim()
        const blob = await reporteService.exportarReporteCartera(
          formato,
          fhRaw,
          {
            fecha_hasta: fhRaw,
            cuotas_impagas_min: filtros.cuotas_impagas_min,
            cuotas_impagas_max: filtros.cuotas_impagas_max,
          }
        )

        const fh = fhRaw.replace(/-/g, '')
        const fileExt = formato === 'pdf' ? 'pdf' : 'xlsx'
        descargarBlob(blob, `cuentas_por_cobrar_${fh}.${fileExt}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.cartera)

        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
      } else if (tipo === 'ASEGURADORA_IMPAGAS') {
        const formato = filtros.formato === 'pdf' ? 'pdf' : 'excel'
        let fdRaw = (filtros.fecha_desde || fechaCorte).trim()
        let fhRaw = (filtros.fecha_hasta || fechaCorte).trim()
        if (fdRaw && fhRaw && fdRaw > fhRaw) {
          ;[fdRaw, fhRaw] = [fhRaw, fdRaw]
        }
        try {
          const upd = await reporteService.actualizarCuotasHojaPeriodo({
            fecha_desde: fdRaw,
            fecha_hasta: fhRaw,
            dry_run: false,
          })
          toast.success(
            `${REPORTES_TOAST.cuotasHojaPeriodo}: ${upd.filas_cambiaron} filas (de ${upd.filas_leidas})`
          )
        } catch (eUpd) {
          console.error(eUpd)
          toast.error(
            getErrorMessage(eUpd) ||
              'No se pudo actualizar la hoja Drive de cuotas'
          )
        }
        const blob = await reporteService.exportarReporteAseguradoraImpagas(
          formato,
          {
            fecha_desde: fdRaw,
            fecha_hasta: fhRaw,
            cuotas_impagas_min: filtros.cuotas_impagas_min,
            cuotas_impagas_max: filtros.cuotas_impagas_max,
          }
        )
        const fh = fhRaw.replace(/-/g, '')
        const fileExt = formato === 'pdf' ? 'pdf' : 'xlsx'
        descargarBlob(blob, `impagas_cedula_${fh}.${fileExt}`)
        toast.dismiss(toastId)
        toast.success(REPORTES_TOAST.aseguradoraImpagas)
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
      } else if (tipo === 'CEDULA') {
        const blob = await reporteService.exportarReporteCedula()

        descargarBlob(blob, `reporte_por_cedula_${fechaCorte}.${ext}`)

        toast.dismiss(toastId)

        toast.success(REPORTES_TOAST.cedula)
      } else if (tipo === 'CEDULAS_CUOTA_HOJA') {
        const blob = await reporteService.exportarReporteCedulasCuotaHoja()
        descargarBlob(blob, `cedulas_cuota_hoja_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success(REPORTES_TOAST.cedulasCuotaHoja)
      } else if (tipo === 'SALDOS_MENORES_200') {
        const blob = await reporteService.exportarSaldosMenores200()
        descargarBlob(blob, `saldos_menores_200_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success(REPORTES_TOAST.saldosMenores200)
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
        /502|bad gateway|no respondió a tiempo/i.test(errorMessage || '') ||
        /502|bad gateway|no respondió a tiempo/i.test(String(detail || ''))
      ) {
        mensajeError =
          'El servidor no respondió a tiempo (502). Espere unos segundos y vuelva a generar el reporte.'
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

      // No alertar HTML de proxy / mensajes enormes ilegibles
      if (
        mensajeError &&
        (/<!doctype|<html/i.test(mensajeError) || mensajeError.length > 800)
      ) {
        toast.error(
          'Error del servidor al generar el reporte. Espere unos segundos y reintente.'
        )
      } else if (mensajeError && mensajeError.length > 300) {
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
        description="Descargue reportes en Excel y comparta enlaces de consulta."
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
          pagos, etc.) o{' '}
          <span className="font-medium text-gray-800">
            contable y otros listados
          </span>
          . Varios informes abren un asistente (año/mes) antes de generar el
          Excel.
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
                Datos del sistema (cartera, impagas y pagos).
              </p>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5 md:gap-4">
                {tiposReporte
                  .filter(t => REPORTES_COBRANZA.includes(t.value))
                  .map(tipo => {
                    const IconComponent = tipo.icon

                    const isGenerando = generandoReporte === tipo.value

                    const isDisponible = [
                      'CARTERA',
                      'ASEGURADORA_IMPAGAS',
                      'PAGOS',
                      'SALDOS_MENORES_200',
                      'CONTABLE',
                      'CEDULA',
                      'CEDULAS_CUOTA_HOJA',
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

            <div className="border-t border-slate-200/90 pt-8">
              <h3 className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <span className="h-px max-w-[3rem] flex-1 rounded-full bg-slate-200" />
                Contable y por cliente
                <span className="h-px flex-1 rounded-full bg-slate-200" />
              </h3>
              <p className="mb-4 max-w-2xl text-xs leading-relaxed text-slate-600">
                Reportes desde la base de datos:{' '}
                <span className="font-medium text-slate-800">Contable</span>{' '}
                (cuotas y cierre),{' '}
                <span className="font-medium text-slate-800">Por cédula</span> y
                la carga asistida de{' '}
                <span className="font-medium text-slate-800">Conciliación</span>.
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

      <DialogReporteFiltros
        key={reporteSeleccionado ?? 'filtros'}
        open={dialogAbierto && reporteSeleccionado !== 'CONTABLE'}
        onOpenChange={setDialogAbierto}
        variant={
          reporteSeleccionado === 'CARTERA'
            ? 'cartera_corte'
            : reporteSeleccionado === 'ASEGURADORA_IMPAGAS'
              ? 'cartera'
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
