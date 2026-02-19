import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  FileText,
  Download,
  PieChart,
  TrendingUp,
  Users,
  DollarSign,
  RefreshCw,
  Loader2,
  UserCheck,
  CreditCard,
  Lock,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { getErrorMessage, getErrorDetail } from '../types/errors'
import { Button } from '../components/ui/button'
import { formatCurrency } from '../utils'
import { reporteService } from '../services/reporteService'
import { toast } from 'sonner'
import { DialogReporteFiltros, type FiltrosReporte } from '../components/reportes/DialogReporteFiltros'
import { usePermissions } from '../hooks/usePermissions'

/** Cada icono = un reporte. Click = abre diálogo años/meses, luego descarga Excel. */
const tiposReporte = [
  { value: 'CARTERA', label: 'Cuentas por cobrar', icon: DollarSign },
  { value: 'MOROSIDAD', label: 'Morosidad', icon: TrendingUp },
  { value: 'PAGOS', label: 'Pagos', icon: Users },
  { value: 'ASESORES', label: 'Pago vencido', icon: UserCheck },
  { value: 'PRODUCTOS', label: 'Productos', icon: PieChart },
  { value: 'CEDULA', label: 'Por cédula', icon: CreditCard },
]

export function Reportes() {
  const [generandoReporte, setGenerandoReporte] = useState<string | null>(null)
  const [dialogAbierto, setDialogAbierto] = useState(false)
  const [reporteSeleccionado, setReporteSeleccionado] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { canViewReports, canDownloadReports, canAccessReport } = usePermissions()

  // Si el usuario no es admin, no puede ver reportes
  if (!canViewReports()) {
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

  // Obtener resumen del dashboard para KPIs
  const {
    data: resumenData,
    isLoading: loadingResumen,
    isError: errorResumen,
    refetch: refetchResumen
  } = useQuery({
    queryKey: ['reportes-resumen'],
    queryFn: () => reporteService.getResumenDashboard(),
    staleTime: 2 * 60 * 1000, // 2 minutos - datos más frescos
    retry: 2, // Dos reintentos para asegurar conexión
    refetchOnWindowFocus: true, // Recargar cuando la ventana recupera el foco
    refetchInterval: 30 * 60 * 1000, // Refrescar cada 30 min
  })

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

  // Abrir diálogo al hacer clic en icono
  const abrirDialogoReporte = (tipo: string) => {
    setReporteSeleccionado(tipo)
    setDialogAbierto(true)
  }

  // Generar reporte tras confirmar filtros en el diálogo
  const generarReporte = async (tipo: string, filtros: FiltrosReporte) => {
    try {
      setGenerandoReporte(tipo)
      const toastId = toast.loading(
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Preparando descarga de {tipo}...</span>
        </div>
      )

      const fechaCorte = new Date().toISOString().split('T')[0]
      const ext = 'xlsx'

      if (tipo === 'CARTERA') {
        const blob = await reporteService.exportarReporteCartera('excel', fechaCorte, filtros)
        descargarBlob(blob, `reporte_cartera_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('✓ Reporte de Cartera descargado exitosamente')
        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        queryClient.invalidateQueries({ queryKey: ['kpis'] })
      } else if (tipo === 'PAGOS') {
        const blob = await reporteService.exportarReportePagos('excel', undefined, undefined, 12, filtros)
        descargarBlob(blob, `reporte_pagos_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('✓ Informe de Pagos descargado exitosamente')
        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        queryClient.invalidateQueries({ queryKey: ['kpis'] })
      } else if (tipo === 'MOROSIDAD') {
        const blob = await reporteService.exportarReporteMorosidad('excel', fechaCorte, filtros)
        descargarBlob(blob, `informe_vencimiento_pagos_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('✓ Reporte de Morosidad descargado exitosamente')
      } else if (tipo === 'ASESORES') {
        // ASESORES ahora es Pago vencido (antes MOROSIDAD)
        const blob = await reporteService.exportarReporteMorosidad('excel', fechaCorte, filtros)
        descargarBlob(blob, `reporte_pago_vencido_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('✓ Reporte de Pago Vencido descargado exitosamente')
      } else if (tipo === 'PRODUCTOS') {
        const blob = await reporteService.exportarReporteProductos('excel', fechaCorte, filtros)
        descargarBlob(blob, `reporte_productos_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('✓ Reporte de Productos descargado exitosamente')
      } else if (tipo === 'CEDULA') {
        const blob = await reporteService.exportarReporteCedula()
        descargarBlob(blob, `reporte_por_cedula_${fechaCorte}.${ext}`)
        toast.dismiss(toastId)
        toast.success('✓ Reporte por Cédula descargado exitosamente')
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

  // KPIs desde el backend (datos reales desde BD) - asegurar que sean números (validación robusta)
  const kpiCartera = Number(resumenData?.cartera_activa ?? 0) || 0
  const kpiPagosVencidos = Number(resumenData?.pagos_vencidos ?? 0) || 0
  const kpiTotalPrestamos = Number(resumenData?.total_prestamos ?? 0) || 0
  const kpiPagosMes = Number(resumenData?.pagos_mes ?? 0) || 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >
      {/* Header balanceado: columna en móvil, fila en desktop */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Centro de Reportes</h1>
          <p className="text-sm sm:text-base text-gray-600 max-w-xl">
            Genera y descarga reportes detallados del sistema. Datos en tiempo real desde la base de datos.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="shrink-0 w-fit"
          onClick={() => {
            refetchResumen()
            toast.info('Actualizando datos...')
          }}
          disabled={loadingResumen}
          aria-label="Actualizar indicadores clave de rendimiento"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${loadingResumen ? 'animate-spin' : ''}`} aria-hidden />
          Actualizar KPIs
        </Button>
      </div>

      {/* Mensaje de error si hay problema cargando datos */}
      {errorResumen && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-md">
          <p className="font-semibold">Error al cargar datos de KPIs</p>
          <p className="text-sm mt-1">
            No se pudieron obtener los datos del servidor. Por favor, intenta actualizar manualmente.
          </p>
        </div>
      )}

      {/* KPI Cards: altura uniforme para diseño balanceado */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="min-h-[120px] flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cartera Activa</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" aria-hidden />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold">{formatCurrency(kpiCartera)}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">Total en cartera</p>
          </CardContent>
        </Card>
        <Card className="min-h-[120px] flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pagos Vencidos</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" aria-hidden />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold text-red-600">{kpiPagosVencidos.toLocaleString()}</div>
            )}
            <p className="text-xs text-muted-foreground">Requieren atención</p>
          </CardContent>
        </Card>
        <Card className="min-h-[120px] flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Préstamos</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" aria-hidden />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold">{kpiTotalPrestamos.toLocaleString()}</div>
            )}
            <p className="text-xs text-muted-foreground">Préstamos activos</p>
          </CardContent>
        </Card>
        <Card className="min-h-[120px] flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pagos del Mes</CardTitle>
            <Download className="h-4 w-4 text-muted-foreground" aria-hidden />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold text-green-600">
                {formatCurrency(kpiPagosMes)}
              </div>
            )}
            <p className="text-xs text-muted-foreground">Este mes</p>
          </CardContent>
        </Card>
      </div>

      {/* Reportes: solo iconos. Click = descarga Excel con distribución según backend. */}
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="mr-2 h-5 w-5" aria-hidden />
            Descargar reportes
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Haz clic en un icono para elegir años y meses, luego descarga el reporte en Excel.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-6">
            {tiposReporte.map((tipo) => {
              const IconComponent = tipo.icon
              const isGenerando = generandoReporte === tipo.value
              const isDisponible = ['CARTERA', 'PAGOS', 'MOROSIDAD', 'ASESORES', 'PRODUCTOS', 'CEDULA'].includes(tipo.value)
              const tieneAcceso = canAccessReport(tipo.value)

              return (
                <button
                  key={tipo.value}
                  type="button"
                  disabled={!isDisponible || !tieneAcceso || isGenerando || !canDownloadReports()}
                  onClick={() => {
                    if (!tieneAcceso) {
                      toast.error('No tienes permisos para acceder a este reporte')
                      return
                    }
                    abrirDialogoReporte(tipo.value)
                  }}
                  title={!tieneAcceso ? 'No tienes permisos para este reporte' : `Descargar ${tipo.label} en Excel`}
                  className={`flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all min-h-[100px] ${
                    isDisponible && tieneAcceso && canDownloadReports()
                      ? 'hover:bg-blue-50 hover:border-blue-200 cursor-pointer hover:scale-105'
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
        open={dialogAbierto}
        onOpenChange={setDialogAbierto}
        tituloReporte={reporteSeleccionado ? tiposReporte.find((t) => t.value === reporteSeleccionado)?.label ?? reporteSeleccionado : ''}
        onConfirm={(filtros) => {
          if (reporteSeleccionado) generarReporte(reporteSeleccionado, filtros)
        }}
      />
    </motion.div>
  )
}

export default Reportes
