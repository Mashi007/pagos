import { useState } from 'react'
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
  Copy,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { getErrorMessage, getErrorDetail } from '../types/errors'
import { Button } from '../components/ui/button'
import { formatCurrency } from '../utils'
import { reporteService } from '../services/reporteService'
import { toast } from 'sonner'
import { DialogReporteFiltros, type FiltrosReporte } from '../components/reportes/DialogReporteFiltros'
import { DialogReporteContableFiltros, type FiltrosReporteContable } from '../components/reportes/DialogReporteContableFiltros'
import { DialogConciliacion } from '../components/reportes/DialogConciliacion'
import { usePermissions } from '../hooks/usePermissions'
import { BASE_PATH, PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

/** Path público de estado de cuenta (consultar por cédula, PDF por correo). */
const PUBLIC_ESTADO_CUENTA_PATH = 'rapicredit-estadocuenta'

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

export function Reportes() {
  const [generandoReporte, setGenerandoReporte] = useState<string | null>(null)
  const [dialogAbierto, setDialogAbierto] = useState(false)
  const [reporteSeleccionado, setReporteSeleccionado] = useState<string | null>(null)
  const [dialogConciliacionAbierto, setDialogConciliacionAbierto] = useState(false)
  const [isRefreshingManual, setIsRefreshingManual] = useState(false)
  const queryClient = useQueryClient()
  const { canViewReports, canDownloadReports, canAccessReport } = usePermissions()
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
                <p className="text-sm text-red-700 mt-1">
                  No tienes permisos para acceder al Centro de Reportes. Contacta al administrador.
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
      const { blob, vacio } = await reporteService.exportarReporteContable(filtros.años, filtros.meses, cedulas)
      descargarBlob(blob, `reporte_contable_${fechaCorte}.xlsx`)
      toast.dismiss(toastId)
      if (vacio) {
        toast.warning(
          'El reporte no tiene datos para el período seleccionado. Verifique que las fechas sean pasadas y que existan cuotas pagadas.'
        )
      } else {
        toast.success('âœ“ Reporte Contable descargado exitosamente')
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
      setGenerandoReporte(tipo)
      const labelReporte = tiposReporte.find((t) => t.value === tipo)?.label ?? tipo
      const toastId = toast.loading(
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Preparando descarga de {labelReporte}...</span>
        </div>
      )

      const fechaCorte = new Date().toISOString().split('T')[0]
      const ext = 'xlsx'

      if (tipo === 'CARTERA') {
        const blob = await reporteService.exportarReporteCartera('excel', fechaCorte, filtros)
        descargarBlob(blob, `reporte_cartera_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('âœ“ Reporte de Cartera descargado exitosamente')
        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        
      } else if (tipo === 'PAGOS') {
        const blob = await reporteService.exportarReportePagos('excel', undefined, undefined, 12, filtros)
        descargarBlob(blob, `reporte_pagos_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('âœ“ Informe de Pagos descargado exitosamente')
        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        
      } else if (tipo === 'MOROSIDAD') {
        const blob = await reporteService.exportarReporteMorosidadClientes(fechaCorte)
        descargarBlob(blob, `reporte_morosidad_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('âœ“ Reporte de Morosidad descargado exitosamente')
      } else if (tipo === 'VENCIMIENTO') {
        const blob = await reporteService.exportarReporteMorosidad('excel', fechaCorte, filtros)
        descargarBlob(blob, `informe_vencimiento_pagos_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('âœ“ Reporte de Vencimiento descargado exitosamente')
      } else if (tipo === 'ASESORES') {
        // ASESORES ahora es Pago vencido (antes MOROSIDAD)
        const blob = await reporteService.exportarReporteMorosidad('excel', fechaCorte, filtros)
        descargarBlob(blob, `reporte_pago_vencido_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('âœ“ Reporte de Pago Vencido descargado exitosamente')
      } else if (tipo === 'CEDULA') {
        const blob = await reporteService.exportarReporteCedula()
        descargarBlob(blob, `reporte_por_cedula_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('âœ“ Reporte por Cédula descargado exitosamente')
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
      if (errorMessage?.includes('500') || errorMessage?.includes('Error del servidor')) {
        mensajeError = 'Error del servidor. Por favor, intente nuevamente en unos momentos.'
      } else if (errorMessage?.includes('404') || errorMessage?.includes('No se encontraron')) {
        mensajeError = 'No se encontraron datos para los filtros seleccionados.'
      } else if (errorMessage?.includes('timeout') || errorMessage?.includes('Timeout')) {
        mensajeError = 'La operación está tomando demasiado tiempo. Por favor, intente con un rango de fechas más corto.'
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
      className="space-y-8"
    >
      {/* Header con título */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
        </div>
      </div>

      {/* Enlaces públicos: copiar link para compartir (Pagos y Estado de cuenta) */}
      <div className="flex flex-wrap gap-3 mb-6">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="inline-flex items-center gap-2"
          onClick={() => copiarEnlaceServicio(PUBLIC_REPORTE_PAGO_PATH, 'Reporte de pagos')}
          title="Copiar enlace del servicio de reporte de pagos para compartir"
        >
          <DollarSign className="h-4 w-4" />
          <span>Pagos</span>
          <Copy className="h-3.5 w-3.5 opacity-70" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="inline-flex items-center gap-2"
          onClick={() => copiarEnlaceServicio(PUBLIC_ESTADO_CUENTA_PATH, 'Estado de cuenta')}
          title="Copiar enlace del servicio de estado de cuenta para compartir"
        >
          <FileText className="h-4 w-4" />
          <span>Estado de cuenta</span>
          <Copy className="h-3.5 w-3.5 opacity-70" />
        </Button>
      </div>

      {/* Reportes: solo iconos. Click = descarga Excel con distribución segÃºn backend. */}
      <Card className="shadow-sm">
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 sm:gap-6">
            {tiposReporte.map((tipo) => {
              const IconComponent = tipo.icon
              const isGenerando = generandoReporte === tipo.value
              const isDisponible = ['CARTERA', 'PAGOS', 'MOROSIDAD', 'VENCIMIENTO', 'ASESORES', 'CONTABLE', 'CEDULA', 'CONCILIACION'].includes(tipo.value)
              const tieneAcceso = canAccessReport(tipo.value)

              return (
                <button
                  key={tipo.value}
                  type="button"
                  disabled={!isDisponible || !tieneAcceso || isGenerando}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    if (!tieneAcceso) {
                      toast.error('No tienes permisos para acceder a este reporte')
                      return
                    }
                    abrirDialogoReporte(tipo.value)
                  }}
                  title={!tieneAcceso ? 'No tienes permisos para este reporte' : `Descargar ${tipo.label} en Excel`}
                  className={`flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all min-h-[100px] select-none ${
                    isDisponible && tieneAcceso
                      ? 'hover:bg-blue-50 hover:border-blue-200 cursor-pointer hover:scale-105 active:scale-100'
                      : 'opacity-50 cursor-not-allowed'
                  }`}
                  aria-label={`Descargar reporte ${tipo.label} en Excel`}
                >
                  {isGenerando ? (
                    <Loader2 className="h-12 w-12 animate-spin text-blue-600" aria-hidden />
                  ) : !tieneAcceso ? (
                    <Lock className="h-12 w-12 text-gray-400" aria-hidden />
                  ) : (
                    <IconComponent className="h-12 w-12 text-blue-600" aria-hidden />
                  )}
                  <span className="text-xs font-medium text-center text-gray-600">{tipo.label}</span>
                  {!tieneAcceso && <span className="text-xs text-red-600">Restringido</span>}
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <DialogReporteFiltros
        key={reporteSeleccionado ?? 'filtros'}
        open={dialogAbierto && reporteSeleccionado !== 'CONTABLE' && reporteSeleccionado !== 'MOROSIDAD'}
        onOpenChange={setDialogAbierto}
        tituloReporte={reporteSeleccionado && reporteSeleccionado !== 'CONTABLE' && reporteSeleccionado !== 'MOROSIDAD' ? tiposReporte.find((t) => t.value === reporteSeleccionado)?.label ?? reporteSeleccionado : ''}
        onConfirm={(filtros) => {
          if (reporteSeleccionado && reporteSeleccionado !== 'CONTABLE' && reporteSeleccionado !== 'MOROSIDAD') generarReporte(reporteSeleccionado, filtros)
        }}
      />
      <DialogReporteContableFiltros
        key="contable"
        open={dialogAbierto && reporteSeleccionado === 'CONTABLE'}
        onOpenChange={setDialogAbierto}
        onConfirm={(filtros) => generarReporteContable(filtros)}
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
