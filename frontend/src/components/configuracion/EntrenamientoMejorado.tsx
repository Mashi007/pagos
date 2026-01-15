import { useState, useEffect } from 'react'
import {
  Brain,
  Zap,
  TrendingUp,
  BarChart3,
  Play,
  CheckCircle,
  AlertCircle,
  Loader2,
  RefreshCw,
  Download,
  Upload,
  FileText,
  Target,
  Info,
  Settings,
  ChevronRight,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'
import { apiClient } from '@/services/api'
import { aiTrainingService, ConversacionAI, MetricasEntrenamiento } from '@/services/aiTrainingService'
import { PromptEditor } from './PromptEditor'

interface Recomendacion {
  tipo: 'recoleccion' | 'calidad' | 'entrenar' | 'mas_datos'
  titulo: string
  descripcion: string
  accion: string
  icono: JSX.Element
  color: 'blue' | 'amber' | 'green'
}

export function EntrenamientoMejorado() {
  const [activeTab, setActiveTab] = useState('asistente')
  const [metricas, setMetricas] = useState<MetricasEntrenamiento | null>(null)
  const [cargandoMetricas, setCargandoMetricas] = useState(false)
  const [recolectandoAutomatico, setRecolectandoAutomatico] = useState(false)
  const [analizandoCalidad, setAnalizandoCalidad] = useState(false)
  const [analisisCalidad, setAnalisisCalidad] = useState<any>(null)

  // Cargar métricas al montar
  useEffect(() => {
    cargarMetricas()
  }, [])

  const cargarMetricas = async () => {
    setCargandoMetricas(true)
    try {
      const data = await aiTrainingService.getMetricasEntrenamiento()
      setMetricas(data)
    } catch (error: any) {
      console.error('Error cargando métricas:', error)
      toast.error('Error al cargar métricas de entrenamiento')
    } finally {
      setCargandoMetricas(false)
    }
  }

  const handleRecoleccionAutomatica = async () => {
    setRecolectandoAutomatico(true)
    try {
      const resultado = await apiClient.post<{ total_recolectadas: number }>('/api/v1/ai/training/recolectar-automatico')
      toast.success(`✅ Recolección completada: ${resultado.total_recolectadas} conversaciones nuevas`)
      cargarMetricas()
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error en recolección automática'
      toast.error(mensaje)
    } finally {
      setRecolectandoAutomatico(false)
    }
  }

  const handleAnalizarCalidad = async () => {
    setAnalizandoCalidad(true)
    try {
      const resultado = await apiClient.post('/api/v1/ai/training/analizar-calidad')
      setAnalisisCalidad(resultado)
      toast.success('Análisis de calidad completado')
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error analizando calidad'
      toast.error(mensaje)
    } finally {
      setAnalizandoCalidad(false)
    }
  }

  const calcularProgresoEntrenamiento = () => {
    if (!metricas) return 0
    const totalNecesario = 50 // Recomendado para buen entrenamiento
    const totalDisponible = metricas.conversaciones.listas_entrenamiento
    return Math.min((totalDisponible / totalNecesario) * 100, 100)
  }

  const obtenerRecomendaciones = (): Recomendacion[] => {
    const recomendaciones: Recomendacion[] = []
    
    if (!metricas) return recomendaciones

    // Recomendación 1: Recolección automática
    if (metricas.conversaciones.total < 20) {
      recomendaciones.push({
        tipo: 'recoleccion',
        titulo: 'Activar Recolección Automática',
        descripcion: 'Habilita la recolección automática de conversaciones del Chat AI para construir tu dataset de entrenamiento.',
        accion: 'Activar',
        icono: <RefreshCw className="h-5 w-5" />,
        color: 'blue',
      })
    }

    // Recomendación 2: Calidad de datos
    if (metricas.conversaciones.con_calificacion > 0 && metricas.conversaciones.promedio_calificacion < 3.5) {
      recomendaciones.push({
        tipo: 'calidad',
        titulo: 'Mejorar Calidad de Conversaciones',
        descripcion: `El promedio de calificaciones es ${metricas.conversaciones.promedio_calificacion.toFixed(1)}/5. Revisa y mejora las conversaciones con baja calificación.`,
        accion: 'Revisar',
        icono: <Target className="h-5 w-5" />,
        color: 'amber',
      })
    }

    // Recomendación 3: Entrenamiento listo
    if (metricas.conversaciones.listas_entrenamiento >= 10) {
      recomendaciones.push({
        tipo: 'entrenar',
        titulo: '¡Listo para Entrenar!',
        descripcion: `Tienes ${metricas.conversaciones.listas_entrenamiento} conversaciones listas. Puedes iniciar el fine-tuning ahora.`,
        accion: 'Entrenar',
        icono: <Play className="h-5 w-5" />,
        color: 'green',
      })
    }

    // Recomendación 4: Más datos
    if (metricas.conversaciones.listas_entrenamiento < 10) {
      recomendaciones.push({
        tipo: 'mas_datos',
        titulo: 'Necesitas Más Conversaciones',
        descripcion: `Tienes ${metricas.conversaciones.listas_entrenamiento} conversaciones listas. Se recomiendan al menos 10 para entrenar (ideal: 50+).`,
        accion: 'Ver Cómo',
        icono: <Info className="h-5 w-5" />,
        color: 'blue',
      })
    }

    return recomendaciones
  }

  return (
    <div className="space-y-6">
      {/* Header con métricas rápidas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600 font-medium">Conversaciones</p>
                <p className="text-2xl font-bold text-blue-900">
                  {metricas?.conversaciones.total || 0}
                </p>
                <p className="text-xs text-blue-600 mt-1">
                  {metricas?.conversaciones.listas_entrenamiento || 0} listas
                </p>
              </div>
              <FileText className="h-8 w-8 text-blue-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-600 font-medium">Calificación Promedio</p>
                <p className="text-2xl font-bold text-green-900">
                  {metricas?.conversaciones.promedio_calificacion
                    ? metricas.conversaciones.promedio_calificacion.toFixed(1)
                    : '0.0'}
                </p>
                <p className="text-xs text-green-600 mt-1">
                  {metricas?.conversaciones.con_calificacion || 0} calificadas
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-200 bg-purple-50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-purple-600 font-medium">Modelos Entrenados</p>
                <p className="text-2xl font-bold text-purple-900">
                  {metricas?.fine_tuning.jobs_exitosos || 0}
                </p>
                <p className="text-xs text-purple-600 mt-1">
                  {metricas?.fine_tuning.modelo_activo ? '1 activo' : 'Ninguno activo'}
                </p>
              </div>
              <Brain className="h-8 w-8 text-purple-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-orange-600 font-medium">Progreso Entrenamiento</p>
                <p className="text-2xl font-bold text-orange-900">
                  {calcularProgresoEntrenamiento().toFixed(0)}%
                </p>
                <Progress
                  value={calcularProgresoEntrenamiento()}
                  className="mt-2 h-2"
                />
              </div>
              <BarChart3 className="h-8 w-8 text-orange-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs principales */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-gray-100/50 p-1 rounded-lg">
          <TabsTrigger
            value="asistente"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <Zap className="h-4 w-4" />
            Asistente Inteligente
          </TabsTrigger>
          <TabsTrigger
            value="recoleccion"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <RefreshCw className="h-4 w-4" />
            Recolección
          </TabsTrigger>
          <TabsTrigger
            value="calidad"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <Target className="h-4 w-4" />
            Calidad de Datos
          </TabsTrigger>
          <TabsTrigger
            value="prompt"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <Settings className="h-4 w-4" />
            Prompt
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Asistente Inteligente */}
        <TabsContent value="asistente" className="mt-6">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-6">
                <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <Zap className="h-8 w-8" />
                    <h2 className="text-2xl font-bold">Asistente de Entrenamiento Inteligente</h2>
                  </div>
                  <p className="text-blue-100">
                    Te guiaré paso a paso para mejorar el entrenamiento de tu Chat AI. 
                    Analizo tus datos y te sugiero las mejores acciones.
                  </p>
                </div>

                {/* Recomendaciones */}
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Info className="h-5 w-5 text-yellow-500" />
                    Recomendaciones Personalizadas
                  </h3>
                  <div className="grid gap-4 md:grid-cols-2">
                    {obtenerRecomendaciones().map((rec, idx) => (
                      <Card
                        key={idx}
                        className={`border-2 ${
                          rec.color === 'green'
                            ? 'border-green-300 bg-green-50'
                            : rec.color === 'amber'
                            ? 'border-amber-300 bg-amber-50'
                            : 'border-blue-300 bg-blue-50'
                        }`}
                      >
                        <CardContent className="pt-4">
                          <div className="flex items-start gap-3">
                            <div
                              className={`p-2 rounded-lg ${
                                rec.color === 'green'
                                  ? 'bg-green-100 text-green-600'
                                  : rec.color === 'amber'
                                  ? 'bg-amber-100 text-amber-600'
                                  : 'bg-blue-100 text-blue-600'
                              }`}
                            >
                              {rec.icono}
                            </div>
                            <div className="flex-1">
                              <h4 className="font-semibold mb-1">{rec.titulo}</h4>
                              <p className="text-sm text-gray-600 mb-3">{rec.descripcion}</p>
                              <Button
                                size="sm"
                                variant={rec.color === 'green' ? 'default' : 'outline'}
                                className={
                                  rec.color === 'green'
                                    ? 'bg-green-600 hover:bg-green-700'
                                    : ''
                                }
                                onClick={() => {
                                  if (rec.tipo === 'recoleccion') {
                                    handleRecoleccionAutomatica()
                                  } else if (rec.tipo === 'calidad') {
                                    setActiveTab('calidad')
                                  } else if (rec.tipo === 'entrenar') {
                                    window.location.href = '/configuracion?tab=ai&subtab=fine-tuning'
                                  } else {
                                    toast.info('Consulta la pestaña de Recolección para más información')
                                  }
                                }}
                              >
                                {rec.accion}
                                <ChevronRight className="ml-2 h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>

                {/* Guía rápida */}
                <Card className="border-blue-200">
                  <CardContent className="pt-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <Info className="h-5 w-5 text-blue-600" />
                      Guía Rápida de Entrenamiento
                    </h3>
                    <div className="space-y-3">
                      <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold">
                          1
                        </div>
                        <div>
                          <p className="font-medium">Recolecta Conversaciones</p>
                          <p className="text-sm text-gray-600">
                            Activa la recolección automática o crea conversaciones manualmente. 
                            Mínimo 10 conversaciones, ideal 50+.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
                        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-600 text-white flex items-center justify-center text-sm font-bold">
                          2
                        </div>
                        <div>
                          <p className="font-medium">Califica y Mejora</p>
                          <p className="text-sm text-gray-600">
                            Califica las conversaciones (4-5 estrellas) y revisa la calidad de los datos.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg">
                        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-600 text-white flex items-center justify-center text-sm font-bold">
                          3
                        </div>
                        <div>
                          <p className="font-medium">Prepara Datos</p>
                          <p className="text-sm text-gray-600">
                            Prepara los datos en formato JSONL para OpenAI Fine-tuning.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg">
                        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-600 text-white flex items-center justify-center text-sm font-bold">
                          4
                        </div>
                        <div>
                          <p className="font-medium">Entrena el Modelo</p>
                          <p className="text-sm text-gray-600">
                            Inicia el fine-tuning con OpenAI. El proceso toma 1-3 horas.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 p-3 bg-indigo-50 rounded-lg">
                        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center text-sm font-bold">
                          5
                        </div>
                        <div>
                          <p className="font-medium">Activa y Prueba</p>
                          <p className="text-sm text-gray-600">
                            Activa el modelo entrenado y prueba en el Chat AI. Compara con el modelo base.
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Recolección */}
        <TabsContent value="recoleccion" className="mt-6">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-4">Recolección Automática de Conversaciones</h3>
                  <p className="text-gray-600 mb-4">
                    El sistema puede recolectar automáticamente las conversaciones del Chat AI para usarlas en el entrenamiento.
                  </p>
                  
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                    <div className="flex items-start gap-3">
                      <Info className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-blue-900 mb-2">¿Cómo funciona?</p>
                        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                          <li>Se guardan automáticamente todas las conversaciones del Chat AI</li>
                          <li>Incluye pregunta, respuesta, contexto usado y métricas</li>
                          <li>Puedes calificarlas después para filtrar las mejores</li>
                          <li>Las conversaciones con 4+ estrellas se usan para entrenamiento</li>
                        </ul>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <Button
                      onClick={handleRecoleccionAutomatica}
                      disabled={recolectandoAutomatico}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {recolectandoAutomatico ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Recolectando...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4" />
                          Recolectar Conversaciones Ahora
                        </>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => window.location.href = '/configuracion?tab=ai&subtab=fine-tuning'}
                    >
                      Ver Conversaciones
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* Estadísticas de recolección */}
                {metricas && (
                  <Card className="border-gray-200">
                    <CardContent className="pt-4">
                      <h4 className="font-semibold mb-3">Estadísticas de Recolección</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-sm text-gray-600">Total Recolectadas</p>
                          <p className="text-2xl font-bold">{metricas.conversaciones.total}</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Con Calificación</p>
                          <p className="text-2xl font-bold">{metricas.conversaciones.con_calificacion}</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Listas (4+ estrellas)</p>
                          <p className="text-2xl font-bold text-green-600">
                            {metricas.conversaciones.listas_entrenamiento}
                          </p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Promedio</p>
                          <p className="text-2xl font-bold">
                            {metricas.conversaciones.promedio_calificacion.toFixed(1)}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Calidad de Datos */}
        <TabsContent value="calidad" className="mt-6">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-4">Análisis de Calidad de Datos</h3>
                  <p className="text-gray-600 mb-4">
                    Analiza la calidad de tus conversaciones para identificar áreas de mejora y optimizar el entrenamiento.
                  </p>

                  <Button
                    onClick={handleAnalizarCalidad}
                    disabled={analizandoCalidad}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {analizandoCalidad ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Analizando...
                      </>
                    ) : (
                      <>
                        <Target className="mr-2 h-4 w-4" />
                        Analizar Calidad de Datos
                      </>
                    )}
                  </Button>
                </div>

                {analisisCalidad && (
                  <div className="space-y-4">
                    <Card className="border-green-200 bg-green-50">
                      <CardContent className="pt-4">
                        <h4 className="font-semibold mb-3 flex items-center gap-2">
                          <CheckCircle className="h-5 w-5 text-green-600" />
                          Métricas de Calidad
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <p className="text-sm text-gray-600">Completitud</p>
                            <p className="text-2xl font-bold text-green-600">
                              {analisisCalidad.completitud?.toFixed(1) || 0}%
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Consistencia</p>
                            <p className="text-2xl font-bold text-blue-600">
                              {analisisCalidad.consistencia?.toFixed(1) || 0}%
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Relevancia</p>
                            <p className="text-2xl font-bold text-purple-600">
                              {analisisCalidad.relevancia?.toFixed(1) || 0}%
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Calidad General</p>
                            <p className="text-2xl font-bold text-orange-600">
                              {analisisCalidad.calidad_general?.toFixed(1) || 0}%
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {analisisCalidad.sugerencias && analisisCalidad.sugerencias.length > 0 && (
                      <Card>
                        <CardContent className="pt-4">
                          <h4 className="font-semibold mb-3 flex items-center gap-2">
                            <Info className="h-5 w-5 text-yellow-500" />
                            Sugerencias de Mejora
                          </h4>
                          <ul className="space-y-2">
                            {analisisCalidad.sugerencias.map((sug: string, idx: number) => (
                              <li key={idx} className="flex items-start gap-2 text-sm">
                                <ChevronRight className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                                <span>{sug}</span>
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Prompt */}
        <TabsContent value="prompt" className="mt-6">
          <Card>
            <CardContent className="pt-6">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
                <div className="flex items-start gap-2">
                  <Brain className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="font-semibold text-blue-900 mb-1">Editor de Prompt Personalizado</p>
                    <p className="text-sm text-blue-800">
                      Personaliza el prompt del AI para ajustar su comportamiento, tono y capacidades.
                      El prompt personalizado reemplazará al prompt por defecto.
                    </p>
                  </div>
                </div>
              </div>
              <PromptEditor />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
