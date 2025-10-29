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
  BarChart3
} from 'lucide-react'
import { cobranzasService } from '@/services/cobranzasService'
import { useQuery } from '@tanstack/react-query'
import type { ClienteAtrasado, CobranzasPorAnalista, MontosPorMes } from '@/services/cobranzasService'

export function Cobranzas() {
  const [tabActiva, setTabActiva] = useState('resumen')
  const [filtroDiasRetraso, setFiltroDiasRetraso] = useState<number | undefined>(undefined)

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

  // Función para exportar a Excel
  const exportarAExcel = (data: any[], nombre: string) => {
    // TODO: Implementar exportación a Excel
    console.log('Exportar:', nombre, data)
  }

  // Función para determinar color del badge según días de retraso
  const getColorBadge = (diasRetraso: number) => {
    if (diasRetraso === 1) return 'bg-green-100 text-green-800'
    if (diasRetraso === 3) return 'bg-yellow-100 text-yellow-800'
    if (diasRetraso === 5) return 'bg-orange-100 text-orange-800'
    return 'bg-red-100 text-red-800'
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
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="resumen">Resumen</TabsTrigger>
          <TabsTrigger value="por-dias">Por Días</TabsTrigger>
          <TabsTrigger value="por-analista">Por Analista</TabsTrigger>
          <TabsTrigger value="grafico">Gráfico</TabsTrigger>
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
                  onClick={() => exportarAExcel(clientesAtrasados, 'clientes-atrasados')}
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
                            onClick={() => exportarAExcel([analista], `${analista.nombre}-clientes`)}
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
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {montosPorMes?.map((mes, index) => (
                      <div key={index} className="border rounded-lg p-4">
                        <h4 className="font-semibold mb-2">{mes.mes_display}</h4>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">{mes.cantidad_cuotas} cuotas</span>
                          <span className="text-lg font-bold">
                            ${mes.monto_total.toLocaleString('es-VE')}
                          </span>
                        </div>
                        {/* Barra de progreso visual */}
                        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${Math.min(100, (mes.cantidad_cuotas / 50) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => exportarAExcel(montosPorMes, 'montos-por-mes')}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Exportar Gráfico a Excel
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

