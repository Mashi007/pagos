import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  FileText, 
  Download, 
  FileSpreadsheet,
  BarChart3,
  TrendingUp,
  Clock,
  Users,
  DollarSign,
  Eye
} from 'lucide-react'
import { cobranzasService } from '@/services/cobranzasService'
import { toast } from 'sonner'

export function InformesCobranzas() {
  const [informeSeleccionado, setInformeSeleccionado] = useState<string | null>(null)
  const [datosInforme, setDatosInforme] = useState<any>(null)
  const [cargandoInforme, setCargandoInforme] = useState(false)
  const [filtros, setFiltros] = useState({
    dias_retraso_min: '',
    dias_retraso_max: '',
    analista: '',
    fecha_inicio: '',
    fecha_fin: '',
  })

  // Informes disponibles
  const informes = [
    {
      id: 'clientes-atrasados',
      titulo: 'Clientes Atrasados Completo',
      descripcion: 'Lista detallada de todos los clientes con pagos atrasados, incluyendo días de retraso y montos adeudados',
      icono: Users,
      color: 'bg-red-500',
      tieneFiltros: true,
    },
    {
      id: 'rendimiento-analista',
      titulo: 'Rendimiento por Analista',
      descripcion: 'Estadísticas de cobranza por analista: clientes asignados, montos adeudados y promedios de retraso',
      icono: TrendingUp,
      color: 'bg-blue-500',
      tieneFiltros: false,
    },
    {
      id: 'montos-periodo',
      titulo: 'Montos Vencidos por Período',
      descripcion: 'Análisis temporal de montos vencidos agrupados por mes, con opción de filtrar por rango de fechas',
      icono: BarChart3,
      color: 'bg-green-500',
      tieneFiltros: true,
    },
    {
      id: 'antiguedad-saldos',
      titulo: 'Antigüedad de Saldos',
      descripcion: 'Distribución de mora por rangos de antigüedad (0-30 días, 31-60 días, etc.)',
      icono: Clock,
      color: 'bg-orange-500',
      tieneFiltros: false,
    },
    {
      id: 'resumen-ejecutivo',
      titulo: 'Resumen Ejecutivo',
      descripcion: 'Informe consolidado para gerencia con resumen general, top analistas y top clientes',
      icono: FileText,
      color: 'bg-purple-500',
      tieneFiltros: false,
    },
  ]

  // Función para descargar informe
  const descargarInforme = async (informeId: string, formato: 'pdf' | 'excel') => {
    try {
      toast.loading(`Generando informe en formato ${formato.toUpperCase()}...`)
      
      switch (informeId) {
        case 'clientes-atrasados':
          await cobranzasService.getInformeClientesAtrasados({
            dias_retraso_min: filtros.dias_retraso_min ? parseInt(filtros.dias_retraso_min) : undefined,
            dias_retraso_max: filtros.dias_retraso_max ? parseInt(filtros.dias_retraso_max) : undefined,
            analista: filtros.analista || undefined,
            formato,
          })
          break
          
        case 'rendimiento-analista':
          await cobranzasService.getInformeRendimientoAnalista(formato)
          break
          
        case 'montos-periodo':
          await cobranzasService.getInformeMontosPeriodo({
            fecha_inicio: filtros.fecha_inicio || undefined,
            fecha_fin: filtros.fecha_fin || undefined,
            formato,
          })
          break
          
        case 'antiguedad-saldos':
          await cobranzasService.getInformeAntiguedadSaldos(formato)
          break
          
        case 'resumen-ejecutivo':
          await cobranzasService.getInformeResumenEjecutivo(formato)
          break
      }
      
      toast.dismiss()
      toast.success(`Informe descargado exitosamente en formato ${formato.toUpperCase()}`)
    } catch (error: any) {
      toast.dismiss()
      toast.error(error.response?.data?.detail || 'Error al generar el informe')
    }
  }

  // Función para ver informe en línea
  const verInforme = async (informeId: string) => {
    try {
      setInformeSeleccionado(informeId)
      setCargandoInforme(true)
      setDatosInforme(null)
      toast.loading('Cargando informe...')
      
      let datos: any
      
      switch (informeId) {
        case 'clientes-atrasados':
          datos = await cobranzasService.getInformeClientesAtrasados({
            dias_retraso_min: filtros.dias_retraso_min ? parseInt(filtros.dias_retraso_min) : undefined,
            dias_retraso_max: filtros.dias_retraso_max ? parseInt(filtros.dias_retraso_max) : undefined,
            analista: filtros.analista || undefined,
            formato: 'json',
          })
          break
          
        case 'rendimiento-analista':
          datos = await cobranzasService.getInformeRendimientoAnalista('json')
          break
          
        case 'montos-periodo':
          datos = await cobranzasService.getInformeMontosPeriodo({
            fecha_inicio: filtros.fecha_inicio || undefined,
            fecha_fin: filtros.fecha_fin || undefined,
            formato: 'json',
          })
          break
          
        case 'antiguedad-saldos':
          datos = await cobranzasService.getInformeAntiguedadSaldos('json')
          break
          
        case 'resumen-ejecutivo':
          datos = await cobranzasService.getInformeResumenEjecutivo('json')
          break
      }
      
      setDatosInforme(datos)
      toast.dismiss()
      toast.success('Informe cargado correctamente')
    } catch (error: any) {
      toast.dismiss()
      toast.error(error.response?.data?.detail || 'Error al cargar el informe')
      setInformeSeleccionado(null)
      setDatosInforme(null)
    } finally {
      setCargandoInforme(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Informes de Cobranzas</h1>
        <p className="text-gray-600 mt-2">
          Genere y descargue informes detallados de cobranzas en formato PDF o Excel, o visualícelos en línea
        </p>
      </div>

      {/* Grid de Informes */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {informes.map((informe) => {
          const Icono = informe.icono
          return (
            <motion.div
              key={informe.id}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Card className="h-full hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className={`${informe.color} p-3 rounded-lg`}>
                      <Icono className="h-6 w-6 text-white" />
                    </div>
                  </div>
                  <CardTitle className="mt-4">{informe.titulo}</CardTitle>
                  <CardDescription>{informe.descripcion}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Filtros si aplica */}
                  {informe.tieneFiltros && informe.id === 'clientes-atrasados' && (
                    <div className="space-y-2 border-t pt-4">
                      <Input
                        type="number"
                        placeholder="Días retraso mínimo"
                        value={filtros.dias_retraso_min}
                        onChange={(e) => setFiltros({ ...filtros, dias_retraso_min: e.target.value })}
                      />
                      <Input
                        type="number"
                        placeholder="Días retraso máximo"
                        value={filtros.dias_retraso_max}
                        onChange={(e) => setFiltros({ ...filtros, dias_retraso_max: e.target.value })}
                      />
                      <Input
                        type="text"
                        placeholder="Analista (email)"
                        value={filtros.analista}
                        onChange={(e) => setFiltros({ ...filtros, analista: e.target.value })}
                      />
                    </div>
                  )}
                  
                  {informe.tieneFiltros && informe.id === 'montos-periodo' && (
                    <div className="space-y-2 border-t pt-4">
                      <Input
                        type="date"
                        placeholder="Fecha inicio"
                        value={filtros.fecha_inicio}
                        onChange={(e) => setFiltros({ ...filtros, fecha_inicio: e.target.value })}
                      />
                      <Input
                        type="date"
                        placeholder="Fecha fin"
                        value={filtros.fecha_fin}
                        onChange={(e) => setFiltros({ ...filtros, fecha_fin: e.target.value })}
                      />
                    </div>
                  )}

                  {/* Botones de acción */}
                  <div className="flex flex-col gap-2 border-t pt-4">
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => verInforme(informe.id)}
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      Ver en Línea
                    </Button>
                    <div className="flex gap-2">
                      <Button
                        variant="default"
                        className="flex-1"
                        onClick={() => descargarInforme(informe.id, 'pdf')}
                      >
                        <FileText className="h-4 w-4 mr-2" />
                        PDF
                      </Button>
                      <Button
                        variant="default"
                        className="flex-1"
                        onClick={() => descargarInforme(informe.id, 'excel')}
                      >
                        <FileSpreadsheet className="h-4 w-4 mr-2" />
                        Excel
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* Vista de informe en línea */}
      {informeSeleccionado && (
        <Card className="mt-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                {informes.find(i => i.id === informeSeleccionado)?.titulo}
              </CardTitle>
              <Button
                variant="ghost"
                onClick={() => {
                  setInformeSeleccionado(null)
                  setDatosInforme(null)
                }}
              >
                Cerrar
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {cargandoInforme ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
                <p className="text-gray-500">Cargando informe...</p>
              </div>
            ) : datosInforme ? (
              <div className="space-y-6">
                {/* Información general del informe */}
                {datosInforme.titulo && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-lg mb-2">{datosInforme.titulo}</h3>
                    {datosInforme.fecha_generacion && (
                      <p className="text-sm text-gray-600">
                        Generado: {new Date(datosInforme.fecha_generacion).toLocaleString('es-VE')}
                      </p>
                    )}
                  </div>
                )}

                {/* Renderizado según tipo de informe */}
                {informeSeleccionado === 'clientes-atrasados' && datosInforme.clientes && (
                  <div className="overflow-x-auto">
                    <h4 className="font-semibold mb-4">
                      Total de clientes: {datosInforme.clientes.length}
                    </h4>
                    <table className="w-full text-sm border-collapse">
                      <thead>
                        <tr className="bg-gray-100 border-b">
                          <th className="p-2 text-left">Cédula</th>
                          <th className="p-2 text-left">Nombres</th>
                          <th className="p-2 text-left">Teléfono</th>
                          <th className="p-2 text-right">Cuotas Vencidas</th>
                          <th className="p-2 text-center">Riesgo ML Impago</th>
                          <th className="p-2 text-right">Total Adeudado</th>
                          <th className="p-2 text-left">Primera Vencida</th>
                        </tr>
                      </thead>
                      <tbody>
                        {datosInforme.clientes.map((cliente: any, idx: number) => (
                          <tr key={idx} className="border-b hover:bg-gray-50">
                            <td className="p-2 font-mono text-xs">{cliente.cedula}</td>
                            <td className="p-2">{cliente.nombres}</td>
                            <td className="p-2">{cliente.telefono || 'N/A'}</td>
                            <td className="p-2 text-right">{cliente.cuotas_vencidas}</td>
                            <td className="p-2 text-center">
                              {cliente.ml_impago ? (
                                <div className="flex flex-col items-center gap-1">
                                  <Badge
                                    variant="outline"
                                    className={
                                      cliente.ml_impago.nivel_riesgo === 'Alto'
                                        ? "bg-red-100 text-red-800 border-red-300 font-semibold"
                                        : cliente.ml_impago.nivel_riesgo === 'Medio'
                                        ? "bg-orange-100 text-orange-800 border-orange-300"
                                        : "bg-green-100 text-green-800 border-green-300"
                                    }
                                  >
                                    {cliente.ml_impago.nivel_riesgo}
                                  </Badge>
                                  <span className="text-xs text-gray-600">
                                    {(cliente.ml_impago.probabilidad_impago * 100).toFixed(1)}%
                                  </span>
                                </div>
                              ) : (
                                <span className="text-xs text-gray-400">N/A</span>
                              )}
                            </td>
                            <td className="p-2 text-right font-semibold text-red-600">
                              ${(cliente.total_adeudado || 0).toLocaleString('es-VE')}
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

                {informeSeleccionado === 'rendimiento-analista' && datosInforme.datos && (
                  <div className="overflow-x-auto">
                    <h4 className="font-semibold mb-4">
                      Total de analistas: {datosInforme.total_analistas || datosInforme.datos.length}
                    </h4>
                    <table className="w-full text-sm border-collapse">
                      <thead>
                        <tr className="bg-gray-100 border-b">
                          <th className="p-2 text-left">Analista</th>
                          <th className="p-2 text-right">Total Clientes</th>
                          <th className="p-2 text-right">Total Préstamos</th>
                          <th className="p-2 text-right">Monto Adeudado</th>
                          <th className="p-2 text-right">Cuotas Vencidas</th>
                          <th className="p-2 text-right">Promedio Días Retraso</th>
                        </tr>
                      </thead>
                      <tbody>
                        {datosInforme.datos.map((analista: any, idx: number) => (
                          <tr key={idx} className="border-b hover:bg-gray-50">
                            <td className="p-2 font-semibold">{analista.analista}</td>
                            <td className="p-2 text-right">{analista.total_clientes}</td>
                            <td className="p-2 text-right">{analista.total_prestamos}</td>
                            <td className="p-2 text-right font-semibold text-red-600">
                              ${(analista.monto_total_adeudado || 0).toLocaleString('es-VE')}
                            </td>
                            <td className="p-2 text-right">{analista.total_cuotas_vencidas}</td>
                            <td className="p-2 text-right">
                              {analista.promedio_dias_retraso?.toFixed(1) || '0'} días
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {informeSeleccionado === 'montos-periodo' && datosInforme.meses && (
                  <div className="overflow-x-auto">
                    <h4 className="font-semibold mb-4">
                      Período analizado: {datosInforme.meses.length} meses
                    </h4>
                    <table className="w-full text-sm border-collapse">
                      <thead>
                        <tr className="bg-gray-100 border-b">
                          <th className="p-2 text-left">Mes</th>
                          <th className="p-2 text-right">Cantidad Cuotas</th>
                          <th className="p-2 text-right">Monto Total</th>
                          <th className="p-2 text-right">Clientes Únicos</th>
                        </tr>
                      </thead>
                      <tbody>
                        {datosInforme.meses.map((mes: any, idx: number) => (
                          <tr key={idx} className="border-b hover:bg-gray-50">
                            <td className="p-2 font-semibold">
                              {mes.mes_display || mes.mes || 'N/A'}
                            </td>
                            <td className="p-2 text-right">{mes.cantidad_cuotas}</td>
                            <td className="p-2 text-right font-semibold text-red-600">
                              ${(mes.monto_total || 0).toLocaleString('es-VE')}
                            </td>
                            <td className="p-2 text-right">{mes.clientes_unicos}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {informeSeleccionado === 'antiguedad-saldos' && datosInforme.rangos && (
                  <div className="overflow-x-auto">
                    <h4 className="font-semibold mb-4">Distribución por Antigüedad</h4>
                    <table className="w-full text-sm border-collapse">
                      <thead>
                        <tr className="bg-gray-100 border-b">
                          <th className="p-2 text-left">Rango de Días</th>
                          <th className="p-2 text-right">Cantidad Cuotas</th>
                          <th className="p-2 text-right">Monto Total</th>
                          <th className="p-2 text-right">Porcentaje</th>
                        </tr>
                      </thead>
                      <tbody>
                        {datosInforme.rangos.map((rango: any, idx: number) => (
                          <tr key={idx} className="border-b hover:bg-gray-50">
                            <td className="p-2 font-semibold">{rango.rango || 'N/A'}</td>
                            <td className="p-2 text-right">{rango.cantidad_cuotas}</td>
                            <td className="p-2 text-right font-semibold text-red-600">
                              ${(rango.monto_total || 0).toLocaleString('es-VE')}
                            </td>
                            <td className="p-2 text-right">
                              {rango.porcentaje?.toFixed(2) || '0'}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {informeSeleccionado === 'resumen-ejecutivo' && datosInforme.resumen && (
                  <div className="space-y-6">
                    {/* Resumen General */}
                    {datosInforme.resumen && (
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <h4 className="font-semibold text-lg mb-4">Resumen General</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <p className="text-sm text-gray-600">Total Cuotas Vencidas</p>
                            <p className="text-2xl font-bold">{datosInforme.resumen.total_cuotas_vencidas || 0}</p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Monto Total Adeudado</p>
                            <p className="text-2xl font-bold text-red-600">
                              ${(datosInforme.resumen.monto_total_adeudado || 0).toLocaleString('es-VE')}
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Clientes Atrasados</p>
                            <p className="text-2xl font-bold">{datosInforme.resumen.clientes_atrasados || 0}</p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Total Analistas</p>
                            <p className="text-2xl font-bold">{datosInforme.resumen.total_analistas || 0}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Top Analistas */}
                    {datosInforme.top_analistas && datosInforme.top_analistas.length > 0 && (
                      <div>
                        <h4 className="font-semibold mb-4">Top Analistas</h4>
                        <table className="w-full text-sm border-collapse">
                          <thead>
                            <tr className="bg-gray-100 border-b">
                              <th className="p-2 text-left">Analista</th>
                              <th className="p-2 text-right">Monto Adeudado</th>
                              <th className="p-2 text-right">Clientes</th>
                            </tr>
                          </thead>
                          <tbody>
                            {datosInforme.top_analistas.map((analista: any, idx: number) => (
                              <tr key={idx} className="border-b hover:bg-gray-50">
                                <td className="p-2 font-semibold">{analista.analista}</td>
                                <td className="p-2 text-right font-semibold text-red-600">
                                  ${(analista.monto_total_adeudado || 0).toLocaleString('es-VE')}
                                </td>
                                <td className="p-2 text-right">{analista.total_clientes}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Top Clientes */}
                    {datosInforme.top_clientes && datosInforme.top_clientes.length > 0 && (
                      <div>
                        <h4 className="font-semibold mb-4">Top Clientes</h4>
                        <table className="w-full text-sm border-collapse">
                          <thead>
                            <tr className="bg-gray-100 border-b">
                              <th className="p-2 text-left">Cédula</th>
                              <th className="p-2 text-left">Nombres</th>
                              <th className="p-2 text-right">Total Adeudado</th>
                              <th className="p-2 text-right">Cuotas Vencidas</th>
                            </tr>
                          </thead>
                          <tbody>
                            {datosInforme.top_clientes.map((cliente: any, idx: number) => (
                              <tr key={idx} className="border-b hover:bg-gray-50">
                                <td className="p-2 font-mono text-xs">{cliente.cedula}</td>
                                <td className="p-2">{cliente.nombres}</td>
                                <td className="p-2 text-right font-semibold text-red-600">
                                  ${(cliente.total_adeudado || 0).toLocaleString('es-VE')}
                                </td>
                                <td className="p-2 text-right">{cliente.cuotas_vencidas}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* Mensaje si no hay datos específicos */}
                {!datosInforme.clientes && 
                 !datosInforme.datos && 
                 !datosInforme.meses && 
                 !datosInforme.rangos && 
                 !datosInforme.resumen && (
                  <div className="text-center py-8 text-gray-500">
                    No hay datos disponibles para mostrar en este informe.
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No se pudieron cargar los datos del informe. Por favor, intente nuevamente.
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

