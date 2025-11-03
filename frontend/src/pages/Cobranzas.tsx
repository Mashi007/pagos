import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  AlertTriangle, 
  TrendingDown, 
  DollarSign,
  Users,
  Download,
  BarChart3,
  Bell,
  Loader2,
  ExternalLink
} from 'lucide-react'
import { cobranzasService } from '@/services/cobranzasService'
import { useQuery } from '@tanstack/react-query'
import type { ClienteAtrasado, CobranzasPorAnalista, MontosPorMes } from '@/services/cobranzasService'
import { InformesCobranzas } from '@/components/cobranzas/InformesCobranzas'
import { toast } from 'sonner'

export function Cobranzas() {
  const [tabActiva, setTabActiva] = useState('resumen')
  const [filtroDiasRetraso, setFiltroDiasRetraso] = useState<number | undefined>(undefined)
  const [procesandoNotificaciones, setProcesandoNotificaciones] = useState(false)

  // Query para resumen
  const { data: resumen, isLoading: cargandoResumen } = useQuery({
    queryKey: ['cobranzas-resumen'],
    queryFn: () => cobranzasService.getResumen(),
  })

  // Query para clientes atrasados
  const { data: clientesAtrasados, isLoading: cargandoClientes } = useQuery({
    queryKey: ['cobranzas-clientes', filtroDiasRetraso],
    queryFn: () => cobranzasService.getClientesAtrasados(filtroDiasRetraso),
  })

  // Query para por analista
  const { data: porAnalista, isLoading: cargandoAnalistas } = useQuery({
    queryKey: ['cobranzas-por-analista'],
    queryFn: () => cobranzasService.getCobranzasPorAnalista(),
  })

  // Query para montos por mes
  const { data: montosPorMes, isLoading: cargandoMontos } = useQuery({
    queryKey: ['cobranzas-montos-mes'],
    queryFn: () => cobranzasService.getMontosPorMes(),
  })

  // Función para exportar clientes de un analista
  const exportarClientesAnalista = async (nombreAnalista: string) => {
    try {
      const clientes = await cobranzasService.getClientesPorAnalista(nombreAnalista)
      await exportarAExcel(
        clientes,
        `clientes-${nombreAnalista.replace('@', '')}`,
        ['cedula', 'nombres', 'telefono', 'prestamo_id', 'cuotas_vencidas', 'total_adeudado', 'fecha_primera_vencida']
      )
    } catch (error) {
      console.error('Error obteniendo clientes del analista:', error)
      alert('Error al obtener clientes del analista')
    }
  }

  // Función para exportar a Excel
  const exportarAExcel = async (data: any[], nombre: string, columnas?: string[]) => {
    if (!data || data.length === 0) {
      alert('No hay datos para exportar')
      return
    }

    try {
      // Importar dinámicamente xlsx
      const XLSXModule = await import('xlsx')
      // @ts-ignore - xlsx es un CommonJS module, necesitamos usar 'as any'
      const XLSX: any = XLSXModule
      
      // Obtener columnas del primer objeto si no se especifican
      const keys = columnas || Object.keys(data[0])
      
      // Preparar datos para Excel
      const datosExcel = data.map(item => {
        const row: any = {}
        keys.forEach(key => {
          row[key] = item[key] ?? ''
        })
        return row
      })

      // Crear workbook y worksheet
      const ws = XLSX.utils.json_to_sheet(datosExcel)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'Datos')

      // Generar fecha para nombre de archivo
      const fecha = new Date().toISOString().split('T')[0]
      const nombreArchivo = `${nombre}_${fecha}.xlsx`

      // Descargar
      XLSX.writeFile(wb, nombreArchivo)
    } catch (error) {
      console.error('Error exportando a Excel:', error)
      alert('Error al exportar a Excel')
    }
  }

  // Función para determinar color del badge según días de retraso
  const getColorBadge = (diasRetraso: number) => {
    if (diasRetraso === 1) return 'bg-green-100 text-green-800'
    if (diasRetraso === 3) return 'bg-yellow-100 text-yellow-800'
    if (diasRetraso === 5) return 'bg-orange-100 text-orange-800'
    return 'bg-red-100 text-red-800'
  }

  // Procesar notificaciones de atrasos
  const procesarNotificaciones = async () => {
    setProcesandoNotificaciones(true)
    try {
      const resultado = await cobranzasService.procesarNotificacionesAtrasos()
      const stats = resultado.estadisticas || {}
      const enviadas = stats.enviadas || 0
      const fallidas = stats.fallidas || 0
      const errores = stats.errores || 0
      
      if (enviadas > 0 || fallidas > 0) {
        toast.success(
          `Notificaciones procesadas: ${enviadas} enviadas${fallidas > 0 ? `, ${fallidas} fallidas` : ''}`,
          {
            duration: 5000,
            action: {
              label: 'Ver Historial',
              onClick: () => window.location.href = '/notificaciones'
            }
          }
        )
      } else {
        toast.info('No hay notificaciones pendientes para procesar')
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al procesar notificaciones')
    } finally {
      setProcesandoNotificaciones(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Gestión de Cobranzas</h1>
          <p className="text-gray-600 mt-2">
            Seguimiento de pagos atrasados y cartera vencida
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={procesarNotificaciones}
            disabled={procesandoNotificaciones}
            className="flex items-center gap-2"
          >
            {procesandoNotificaciones ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Procesando...
              </>
            ) : (
              <>
                <Bell className="h-4 w-4" />
                Procesar Notificaciones Ahora
              </>
            )}
          </Button>
          <Button 
            variant="outline"
            onClick={() => window.location.href = '/notificaciones'}
            className="flex items-center gap-2"
          >
            <ExternalLink className="h-4 w-4" />
            Ver Historial
          </Button>
        </div>
      </div>

      {/* KPIs Resumen */}
      {resumen && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Cuotas Vencidas</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{resumen.total_cuotas_vencidas}</div>
              <p className="text-xs text-muted-foreground">Cuotas pendientes de cobro</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Monto Total Adeudado</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${resumen.monto_total_adeudado.toLocaleString('es-VE')}
              </div>
              <p className="text-xs text-muted-foreground">En cartera vencida</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Clientes Atrasados</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{resumen.clientes_atrasados}</div>
              <p className="text-xs text-muted-foreground">Requieren seguimiento</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs de análisis */}
      <Tabs value={tabActiva} onValueChange={setTabActiva}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="resumen">Resumen</TabsTrigger>
          <TabsTrigger value="por-dias">Por Días</TabsTrigger>
          <TabsTrigger value="por-analista">Por Analista</TabsTrigger>
          <TabsTrigger value="grafico">Gráfico</TabsTrigger>
          <TabsTrigger value="informes">📊 Informes</TabsTrigger>
        </TabsList>

        {/* Tab Resumen - Clientes atrasados */}
        <TabsContent value="resumen" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Clientes Atrasados</CardTitle>
                  <CardDescription>
                    Listado de todos los clientes con cuotas vencidas
                  </CardDescription>
                </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => await exportarAExcel(
                      clientesAtrasados || [],
                      'clientes-atrasados',
                      ['cedula', 'nombres', 'analista', 'prestamo_id', 'cuotas_vencidas', 'total_adeudado', 'fecha_primera_vencida']
                    )}
                  >
                  <Download className="h-4 w-4 mr-2" />
                  Exportar Excel
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {cargandoClientes ? (
                <div className="text-center py-8">Cargando...</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Cédula</th>
                        <th className="text-left p-2">Nombres</th>
                        <th className="text-left p-2">Analista</th>
                        <th className="text-right p-2">Cuotas Vencidas</th>
                        <th className="text-right p-2">Total Adeudado</th>
                        <th className="text-left p-2">Fecha Primera Vencida</th>
                      </tr>
                    </thead>
                    <tbody>
                      {clientesAtrasados?.map((cliente, index) => (
                        <tr key={index} className="border-b hover:bg-gray-50">
                          <td className="p-2 font-mono">{cliente.cedula}</td>
                          <td className="p-2">{cliente.nombres}</td>
                          <td className="p-2">{cliente.analista}</td>
                          <td className="p-2 text-right">{cliente.cuotas_vencidas}</td>
                          <td className="p-2 text-right">
                            ${cliente.total_adeudado.toLocaleString('es-VE')}
                          </td>
                          <td className="p-2">
                            {cliente.fecha_primera_vencida
                              ? new Date(cliente.fecha_primera_vencida).toLocaleDateString('es-VE')
                              : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Por Días de Retraso */}
        <TabsContent value="por-dias" className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {/* 1 día de retraso */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center">
                  <Badge className="bg-green-100 text-green-800 mr-2">1 Día</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => {
                    setFiltroDiasRetraso(1)
                    setTabActiva('resumen')
                  }}
                >
                  Ver Clientes
                </Button>
              </CardContent>
            </Card>

            {/* 3 días de retraso */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center">
                  <Badge className="bg-yellow-100 text-yellow-800 mr-2">3 Días</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => {
                    setFiltroDiasRetraso(3)
                    setTabActiva('resumen')
                  }}
                >
                  Ver Clientes
                </Button>
              </CardContent>
            </Card>

            {/* 5 días de retraso */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center">
                  <Badge className="bg-orange-100 text-orange-800 mr-2">5 Días</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => {
                    setFiltroDiasRetraso(5)
                    setTabActiva('resumen')
                  }}
                >
                  Ver Clientes
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab Por Analista */}
        <TabsContent value="por-analista" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Análisis por Analista</CardTitle>
              <CardDescription>
                Montos sin cobrar y cantidad de clientes atrasados por analista
              </CardDescription>
            </CardHeader>
            <CardContent>
              {cargandoAnalistas ? (
                <div className="text-center py-8">Cargando...</div>
              ) : (
                <div className="space-y-4">
                  {porAnalista?.map((analista, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">{analista.nombre}</h3>
                          <p className="text-sm text-gray-600">
                            {analista.cantidad_clientes} clientes atrasados
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-red-600">
                            ${analista.monto_total.toLocaleString('es-VE')}
                          </p>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => exportarClientesAnalista(analista.nombre)}
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Exportar
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Gráfico */}
        <TabsContent value="grafico" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Monto Vencido por Mes</CardTitle>
              <CardDescription>
                Distribución de montos no pagados agrupados por mes de vencimiento
              </CardDescription>
            </CardHeader>
            <CardContent>
              {cargandoMontos ? (
                <div className="text-center py-8">Cargando...</div>
              ) : (
                <div className="space-y-4">
                  {/* Gráfico de barras mejorado */}
                  {montosPorMes && montosPorMes.length > 0 ? (
                    <>
                      <div className="bg-gradient-to-b from-blue-50 to-white p-6 rounded-lg border-2 border-blue-100">
                        <h3 className="text-lg font-semibold mb-4 text-gray-800">
                          Distribución de Montos Vencidos por Mes
                        </h3>
                        <div className="space-y-3">
                          {montosPorMes.map((mes, index) => {
                            const maxMonto = Math.max(...(montosPorMes?.map(m => m.monto_total) || [0]))
                            const porcentaje = maxMonto > 0 ? (mes.monto_total / maxMonto) * 100 : 0
                            
                            return (
                              <div key={index} className="space-y-1">
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-sm font-medium text-gray-700">
                                    {mes.mes_display}
                                  </span>
                                  <div className="flex items-center gap-3">
                                    <span className="text-xs text-gray-500">
                                      {mes.cantidad_cuotas} cuotas
                                    </span>
                                    <span className="text-sm font-bold text-blue-700">
                                      ${mes.monto_total.toLocaleString('es-VE')}
                                    </span>
                                  </div>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-6 shadow-inner">
                                  <div
                                    className="bg-gradient-to-r from-blue-500 to-blue-600 h-6 rounded-full flex items-center justify-end pr-2 transition-all duration-500"
                                    style={{ width: `${porcentaje}%` }}
                                  >
                                    {porcentaje > 10 && (
                                      <span className="text-xs font-semibold text-white">
                                        {porcentaje.toFixed(0)}%
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                      
                      {/* Resumen numérico */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <Card>
                          <CardContent className="pt-4">
                            <p className="text-sm text-gray-600">Total Cuotas Vencidas</p>
                            <p className="text-2xl font-bold text-gray-900">
                              {montosPorMes.reduce((sum, m) => sum + m.cantidad_cuotas, 0)}
                            </p>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardContent className="pt-4">
                            <p className="text-sm text-gray-600">Monto Total Vencido</p>
                            <p className="text-2xl font-bold text-red-600">
                              ${montosPorMes.reduce((sum, m) => sum + m.monto_total, 0).toLocaleString('es-VE')}
                            </p>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardContent className="pt-4">
                            <p className="text-sm text-gray-600">Promedio por Mes</p>
                            <p className="text-2xl font-bold text-blue-600">
                              ${(montosPorMes.reduce((sum, m) => sum + m.monto_total, 0) / montosPorMes.length).toLocaleString('es-VE')}
                            </p>
                          </CardContent>
                        </Card>
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-12 text-gray-500">
                      <BarChart3 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                      <p>No hay montos vencidos por mes para mostrar</p>
                    </div>
                  )}
                  
                  <Button
                    variant="outline"
                    onClick={async () => await exportarAExcel(
                      montosPorMes || [],
                      'montos-por-mes',
                      ['mes', 'mes_display', 'cantidad_cuotas', 'monto_total']
                    )}
                    disabled={!montosPorMes || montosPorMes.length === 0}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Exportar Gráfico a Excel
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Informes */}
        <TabsContent value="informes" className="space-y-4">
          <InformesCobranzas />
        </TabsContent>
      </Tabs>
    </div>
  )
}

