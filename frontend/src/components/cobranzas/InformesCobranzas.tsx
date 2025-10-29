import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'

export function InformesCobranzas() {
  const [informeSeleccionado, setInformeSeleccionado] = useState<string | null>(null)
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
      
      toast.dismiss()
      toast.success('Informe cargado correctamente')
    } catch (error: any) {
      toast.dismiss()
      toast.error(error.response?.data?.detail || 'Error al cargar el informe')
      setInformeSeleccionado(null)
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
                onClick={() => setInformeSeleccionado(null)}
              >
                Cerrar
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8 text-gray-500">
              Los datos del informe se mostrarán aquí cuando se implemente la visualización completa.
              Por ahora, utilice las opciones de descarga PDF o Excel.
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

