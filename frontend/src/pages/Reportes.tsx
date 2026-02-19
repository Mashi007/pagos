import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  FileText,
  Download,
  BarChart3,
  PieChart,
  TrendingUp,
  Users,
  DollarSign,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { getErrorMessage, getErrorDetail } from '../types/errors'
import { Button } from '../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { formatCurrency } from '../utils'
import { reporteService } from '../services/reporteService'
import { TablaAmortizacionCompleta } from '../components/reportes/TablaAmortizacionCompleta'
import { toast } from 'sonner'

const tiposReporte = [
  { value: 'CARTERA', label: 'Cartera', icon: DollarSign },
  { value: 'MOROSIDAD', label: 'Pago vencido', icon: TrendingUp },
  { value: 'PAGOS', label: 'Pagos', icon: Users },
  { value: 'FINANCIERO', label: 'Financiero', icon: BarChart3 },
  { value: 'ASESORES', label: 'Asesores', icon: Users },
  { value: 'PRODUCTOS', label: 'Productos', icon: PieChart },
]

// Validación de cédula venezolana
const validarCedula = (cedula: string): boolean => {
  if (!cedula || cedula.trim().length === 0) return false
  // Formato: E/V/J/Z seguido de 6-12 dígitos
  return /^[VEJZ]\d{6,12}$/i.test(cedula.trim())
}

export function Reportes() {
  const [formatoExportacion, setFormatoExportacion] = useState<'excel' | 'pdf'>('excel')
  const [generandoReporte, setGenerandoReporte] = useState<string | null>(null)
  const queryClient = useQueryClient()

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
    refetchInterval: 5 * 60 * 1000, // Refrescar cada 5 minutos automáticamente
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

  // Funciones para generar reportes (datos reales desde BD; descarga Excel o PDF según corresponda)
  const generarReporte = async (tipo: string, formato: 'excel' | 'pdf' = 'excel') => {
    try {
      setGenerandoReporte(tipo)
      toast.loading(`Generando reporte de ${tipo}...`)

      const fechaCorte = new Date().toISOString().split('T')[0]
      const ext = formato === 'excel' ? 'xlsx' : 'pdf'

      if (tipo === 'CARTERA') {
        const blob = await reporteService.exportarReporteCartera(formato, fechaCorte)
        descargarBlob(blob, `reporte_cartera_${fechaCorte}.${ext}`)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} descargado`)
        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        queryClient.invalidateQueries({ queryKey: ['kpis'] })
      } else if (tipo === 'PAGOS') {
        const fechaFin = new Date()
        const fechaInicio = new Date()
        fechaInicio.setMonth(fechaInicio.getMonth() - 1)
        const fi = fechaInicio.toISOString().split('T')[0]
        const ff = fechaFin.toISOString().split('T')[0]
        const blob = await reporteService.exportarReportePagos(fi, ff, formato)
        descargarBlob(blob, `reporte_pagos_${fi}_${ff}.${ext}`)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} descargado`)
        queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
        queryClient.invalidateQueries({ queryKey: ['kpis'] })
      } else if (tipo === 'MOROSIDAD') {
        const blob = await reporteService.exportarReporteMorosidad(formato, fechaCorte)
        descargarBlob(blob, `reporte_morosidad_${fechaCorte}.${ext}`)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} descargado`)
      } else if (tipo === 'FINANCIERO') {
        const blob = await reporteService.exportarReporteFinanciero(formato, fechaCorte)
        descargarBlob(blob, `reporte_financiero_${fechaCorte}.${ext}`)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} descargado`)
      } else if (tipo === 'ASESORES') {
        const blob = await reporteService.exportarReporteAsesores(formato, fechaCorte)
        descargarBlob(blob, `reporte_asesores_${fechaCorte}.${ext}`)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} descargado`)
      } else if (tipo === 'PRODUCTOS') {
        const blob = await reporteService.exportarReporteProductos(formato, fechaCorte)
        descargarBlob(blob, `reporte_productos_${fechaCorte}.${ext}`)
        toast.dismiss()
        toast.success(`Reporte de ${tipo} descargado`)
      } else {
        toast.dismiss()
        toast.info(`Generación de reporte ${tipo} próximamente disponible`)
      }
    } catch (error: unknown) {
      console.error('Error generando reporte:', error)
      toast.dismiss()
      const errorMessage = getErrorMessage(error)
      const detail = getErrorDetail(error)
      
      // Mensajes de error más amigables
      let mensajeError = detail || errorMessage
      if (errorMessage?.includes('500') || errorMessage?.includes('Error del servidor')) {
        mensajeError = 'Error del servidor. Por favor, intente nuevamente en unos momentos.'
      } else if (errorMessage?.includes('404') || errorMessage?.includes('No se encontraron')) {
        mensajeError = 'No se encontraron datos para los filtros seleccionados.'
      } else if (errorMessage?.includes('timeout') || errorMessage?.includes('Timeout')) {
        mensajeError = 'La operación está tomando demasiado tiempo. Por favor, intente con un rango de fechas más corto.'
      } else if (!mensajeError) {
        mensajeError = `Error al generar reporte de ${tipo}. Por favor, contacte al soporte si el problema persiste.`
      }
      
      toast.error(mensajeError)
    } finally {
      setGenerandoReporte(null)
    }
  }

  // KPIs desde el backend (datos reales desde BD) - asegurar que sean números (validación robusta)
  const kpiCartera = Number(resumenData?.cartera_activa ?? 0) || 0
  const kpiPrestamosMora = Number(resumenData?.prestamos_mora ?? 0) || 0
  const kpiTotalPrestamos = Number(resumenData?.total_prestamos ?? 0) || 0
  const kpiPagosMes = Number(resumenData?.pagos_mes ?? 0) || 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
          <p className="text-gray-600">Genera y descarga reportes detallados del sistema.</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            refetchResumen()
            toast.info('Actualizando datos...')
          }}
          disabled={loadingResumen}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${loadingResumen ? 'animate-spin' : ''}`} />
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

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cartera Activa</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
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
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Préstamos en Mora</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Cargando...</span>
              </div>
            ) : errorResumen ? (
              <div className="text-2xl font-bold text-gray-400">--</div>
            ) : (
              <div className="text-2xl font-bold text-red-600">{kpiPrestamosMora.toLocaleString()}</div>
            )}
            <p className="text-xs text-muted-foreground">Requieren atención</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Préstamos</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
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
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pagos del Mes</CardTitle>
            <Download className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loadingResumen ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
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

      {/* Tabla de Amortización Completa */}
      <TablaAmortizacionCompleta />

      {/* Generate Report Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <RefreshCw className="mr-2 h-5 w-5" /> Generar Nuevo Reporte
          </CardTitle>
          <CardDescription>
            Selecciona el formato de descarga (Excel o PDF) y el tipo de reporte. Los datos se generan en tiempo real desde la base de datos.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <span className="text-sm font-medium text-gray-700">Formato de descarga:</span>
            <Select value={formatoExportacion} onValueChange={(v: 'excel' | 'pdf') => setFormatoExportacion(v)}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="excel">Excel (.xlsx)</SelectItem>
                <SelectItem value="pdf">PDF</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tiposReporte.map((tipo) => {
              const IconComponent = tipo.icon
              const isGenerando = generandoReporte === tipo.value
              const isDisponible = ['CARTERA', 'PAGOS', 'MOROSIDAD', 'FINANCIERO', 'ASESORES', 'PRODUCTOS'].includes(tipo.value)

              return (
                <Card
                  key={tipo.value}
                  className={`cursor-pointer hover:shadow-md transition-shadow ${
                    !isDisponible ? 'opacity-60' : ''
                  }`}
                  onClick={() => {
                    if (isDisponible && !isGenerando) {
                      generarReporte(tipo.value, formatoExportacion)
                    } else if (!isDisponible) {
                      toast.info(`El reporte de ${tipo.label} estará disponible próximamente`)
                    }
                  }}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <IconComponent className="h-8 w-8 text-blue-600" />
                        <div>
                          <h3 className="font-semibold">{tipo.label}</h3>
                          <p className="text-sm text-gray-600">
                            {isGenerando ? 'Generando...' : 'Generar reporte'}
                          </p>
                        </div>
                      </div>
                      {isGenerando && (
                        <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Reportes disponibles - datos reales desde BD */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="mr-2 h-5 w-5" />
            Reportes disponibles
          </CardTitle>
          <CardDescription>
            Todos los reportes se generan en tiempo real desde la base de datos. Seleccione el tipo, formato (Excel o PDF) y descargue.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tipo</TableHead>
                <TableHead>Descripción</TableHead>
                <TableHead className="text-right">Excel</TableHead>
                <TableHead className="text-right">PDF</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tiposReporte.map((tipo) => {
                const IconComponent = tipo.icon
                const isGenerando = generandoReporte === tipo.value
                const isDisponible = ['CARTERA', 'PAGOS', 'MOROSIDAD', 'FINANCIERO', 'ASESORES', 'PRODUCTOS'].includes(tipo.value)
                const descripciones: Record<string, string> = {
                  CARTERA: 'Cartera total, capital pendiente, mora, distribución por monto y mora',
                  PAGOS: 'Total pagos, cantidad y detalle por día en el período',
                  MOROSIDAD: 'Préstamos en mora, clientes, monto, por analista',
                  FINANCIERO: 'Ingresos, cartera, morosidad, flujo de caja',
                  ASESORES: 'Resumen por analista: préstamos, cartera, morosidad, cobrado',
                  PRODUCTOS: 'Resumen por producto y por concesionario',
                }
                return (
                  <TableRow key={tipo.value}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <IconComponent className="h-4 w-4 text-blue-600" />
                        <span className="font-medium">{tipo.label}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-gray-600 text-sm">{descripciones[tipo.value] || '—'}</TableCell>
                    <TableCell className="text-right">
                      {isDisponible ? (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isGenerando}
                          onClick={() => generarReporte(tipo.value, 'excel')}
                        >
                          {isGenerando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                        </Button>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {isDisponible ? (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isGenerando}
                          onClick={() => generarReporte(tipo.value, 'pdf')}
                        >
                          {isGenerando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                        </Button>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default Reportes
