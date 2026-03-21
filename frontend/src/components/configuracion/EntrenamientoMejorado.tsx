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

import { Card, CardContent } from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Badge } from '../../components/ui/badge'

import { Progress } from '../../components/ui/progress'

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../../components/ui/tabs'

import { toast } from 'sonner'

import { apiClient } from '../../services/api'

import {
  aiTrainingService,
  ConversacionAI,
  MetricasEntrenamiento,
} from '../../services/aiTrainingService'

import { PromptEditor } from './PromptEditor'

import { BASE_PATH } from '../../config/env'

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

  const [recoleccionAutomaticaActiva, setRecoleccionAutomaticaActiva] =
    useState(false)

  const [cargandoEstadoRecoleccion, setCargandoEstadoRecoleccion] =
    useState(false)

  // Cargar métricas al montar

  useEffect(() => {
    cargarMetricas()

    cargarEstadoRecoleccionAutomatica()
  }, [])

  const cargarEstadoRecoleccionAutomatica = async () => {
    try {
      const response = await apiClient.get<{
        recoleccion_automatica_activa?: string
      }>('/api/v1/configuracion/ai/configuracion')

      // Manejar tanto string como boolean

      const valor = response?.recoleccion_automatica_activa

      const activa = valor === 'true' || valor === 'True'

      setRecoleccionAutomaticaActiva(activa)

      console.debug(`Estado de recolección automática cargado: ${activa}`)
    } catch (error: any) {
      console.error('Error cargando estado de recolección automática:', error)

      // Si no existe la configuración, asumir que está desactivada

      setRecoleccionAutomaticaActiva(false)
    }
  }

  const handleActivarRecoleccionAutomatica = async () => {
    setCargandoEstadoRecoleccion(true)

    try {
      const nuevoEstado = !recoleccionAutomaticaActiva

      // Guardar configuración

      const response = await apiClient.put(
        '/api/v1/configuracion/ai/configuracion',
        {
          recoleccion_automatica_activa: nuevoEstado.toString(),
        }
      )

      setRecoleccionAutomaticaActiva(nuevoEstado)

      // Recargar estado para confirmar

      await cargarEstadoRecoleccionAutomatica()

      if (nuevoEstado) {
        toast.success(
          'âœ… Recolección automática activada. Las conversaciones se guardarán automáticamente.',
          {
            duration: 5000,
          }
        )
      } else {
        toast.info('Recolección automática desactivada', {
          duration: 3000,
        })
      }
    } catch (error: any) {
      console.error('Error activando recolección automática:', error)

      const errorMsg =
        error?.response?.data?.detail ||
        'Error al cambiar el estado de recolección automática'

      toast.error(errorMsg, {
        duration: 5000,
      })

      // Recargar estado en caso de error para mantener sincronización

      await cargarEstadoRecoleccionAutomatica()
    } finally {
      setCargandoEstadoRecoleccion(false)
    }
  }

  const metricasPorDefecto: MetricasEntrenamiento = {
    conversaciones: {
      total: 0,
      con_calificacion: 0,
      promedio_calificacion: 0,
      listas_entrenamiento: 0,
    },

    fine_tuning: { jobs_totales: 0, jobs_exitosos: 0, jobs_fallidos: 0 },

    rag: { documentos_con_embeddings: 0, total_embeddings: 0 },

    ml_riesgo: { modelos_disponibles: 0 },
  }

  const cargarMetricas = async () => {
    setCargandoMetricas(true)

    try {
      const data = await aiTrainingService.getMetricasEntrenamiento()

      if (
        data &&
        data.conversaciones &&
        data.fine_tuning &&
        data.rag &&
        data.ml_riesgo
      ) {
        setMetricas(data as MetricasEntrenamiento)
      } else {
        setMetricas({
          conversaciones:
            data?.conversaciones ?? metricasPorDefecto.conversaciones,

          fine_tuning: data?.fine_tuning ?? metricasPorDefecto.fine_tuning,

          rag: data?.rag ?? metricasPorDefecto.rag,

          ml_riesgo: data?.ml_riesgo ?? metricasPorDefecto.ml_riesgo,
        } as MetricasEntrenamiento)
      }
    } catch (error: any) {
      console.error('Error cargando métricas:', error)

      if (error?.response?.status === 404) {
        setMetricas(metricasPorDefecto)
      } else {
        toast.error('Error al cargar métricas de entrenamiento')
      }
    } finally {
      setCargandoMetricas(false)
    }
  }

  const handleRecoleccionAutomatica = async () => {
    setRecolectandoAutomatico(true)

    try {
      const resultado = await apiClient.post<{ total_recolectadas: number }>(
        '/api/v1/ai/training/recolectar-automatico'
      )

      toast.success(
        `âœ… Recolección completada: ${resultado.total_recolectadas} conversaciones nuevas`
      )

      cargarMetricas()
    } catch (error: any) {
      const mensaje =
        error?.response?.data?.detail ||
        error?.message ||
        'Error en recolección automática'

      toast.error(mensaje)
    } finally {
      setRecolectandoAutomatico(false)
    }
  }

  const handleAnalizarCalidad = async () => {
    setAnalizandoCalidad(true)

    try {
      const resultado = await apiClient.post(
        '/api/v1/ai/training/analizar-calidad'
      )

      setAnalisisCalidad(resultado)

      toast.success('Análisis de calidad completado')
    } catch (error: any) {
      const mensaje =
        error?.response?.data?.detail ||
        error?.message ||
        'Error analizando calidad'

      toast.error(mensaje)
    } finally {
      setAnalizandoCalidad(false)
    }
  }

  const calcularProgresoEntrenamiento = () => {
    if (!metricas?.conversaciones) return 0

    const totalNecesario = 50 // Recomendado para buen entrenamiento

    const totalDisponible = metricas.conversaciones.listas_entrenamiento ?? 0

    return Math.min((totalDisponible / totalNecesario) * 100, 100)
  }

  const obtenerRecomendaciones = (): Recomendacion[] => {
    const recomendaciones: Recomendacion[] = []

    if (!metricas?.conversaciones) return recomendaciones

    const conv = metricas.conversaciones

    // Recomendación 1: Recolección automática

    if ((conv.total ?? 0) < 20) {
      recomendaciones.push({
        tipo: 'recoleccion',

        titulo: recoleccionAutomaticaActiva
          ? 'Recolección Automática Activada'
          : 'Activar Recolección Automática',

        descripcion: recoleccionAutomaticaActiva
          ? 'La recolección automática está activa. Las conversaciones del Chat AI se guardan automáticamente para construir tu dataset de entrenamiento.'
          : 'Habilita la recolección automática de conversaciones del Chat AI para construir tu dataset de entrenamiento.',

        accion: recoleccionAutomaticaActiva ? 'Desactivar' : 'Activar',

        icono: <RefreshCw className="h-5 w-5" />,

        color: recoleccionAutomaticaActiva ? 'green' : 'blue',
      })
    }

    // Recomendación 2: Calidad de datos

    if (
      (conv.con_calificacion ?? 0) > 0 &&
      (conv.promedio_calificacion ?? 0) < 3.5
    ) {
      recomendaciones.push({
        tipo: 'calidad',

        titulo: 'Mejorar Calidad de Conversaciones',

        descripcion: `El promedio de calificaciones es ${(conv.promedio_calificacion ?? 0).toFixed(1)}/5. Revisa y mejora las conversaciones con baja calificación.`,

        accion: 'Revisar',

        icono: <Target className="h-5 w-5" />,

        color: 'amber',
      })
    }

    // Recomendación 3: Entrenamiento listo

    if ((conv.listas_entrenamiento ?? 0) >= 10) {
      recomendaciones.push({
        tipo: 'entrenar',

        titulo: '¡Listo para Entrenar!',

        descripcion: `Tienes ${conv.listas_entrenamiento ?? 0} conversaciones listas. Puedes iniciar el fine-tuning ahora.`,

        accion: 'Entrenar',

        icono: <Play className="h-5 w-5" />,

        color: 'green',
      })
    }

    // Recomendación 4: Más datos

    if ((conv.listas_entrenamiento ?? 0) < 10) {
      recomendaciones.push({
        tipo: 'mas_datos',

        titulo: 'Necesitas Más Conversaciones',

        descripcion: `Tienes ${conv.listas_entrenamiento ?? 0} conversaciones listas. Se recomiendan al menos 10 para entrenar (ideal: 50+).`,

        accion: 'Ver Cómo',

        icono: <Info className="h-5 w-5" />,

        color: 'blue',
      })
    }

    return recomendaciones
  }

  return (
    <div className="space-y-6">
      {/* Header con título y descripción */}

      <div className="mb-6">
        <h2 className="mb-2 flex items-center gap-3 text-3xl font-bold text-gray-900">
          <Brain className="h-8 w-8 text-blue-600" />
          Herramientas de Entrenamiento AI
        </h2>

        <p className="text-gray-600">
          Gestiona la recolección de datos, calidad y entrenamiento de tu modelo
          de Chat AI
        </p>
      </div>

      {/* Métricas rápidas - Mejorado */}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-blue-100 transition-shadow hover:shadow-md">
          <CardContent className="pb-5 pt-5">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-600" />

                  <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
                    Conversaciones
                  </p>
                </div>

                <p className="mb-1 text-3xl font-bold text-blue-900">
                  {metricas?.conversaciones?.total ?? 0}
                </p>

                <div className="mt-2 flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className="border-blue-300 bg-white/50 text-xs text-blue-700"
                  >
                    {metricas?.conversaciones?.listas_entrenamiento ?? 0} listas
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-green-200 bg-gradient-to-br from-green-50 to-green-100 transition-shadow hover:shadow-md">
          <CardContent className="pb-5 pt-5">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />

                  <p className="text-sm font-semibold uppercase tracking-wide text-green-700">
                    Calificación
                  </p>
                </div>

                <p className="mb-1 text-3xl font-bold text-green-900">
                  {metricas?.conversaciones?.promedio_calificacion != null
                    ? metricas.conversaciones.promedio_calificacion.toFixed(1)
                    : '0.0'}

                  <span className="ml-1 text-lg text-green-600">/5</span>
                </p>

                <div className="mt-2 flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className="border-green-300 bg-white/50 text-xs text-green-700"
                  >
                    {metricas?.conversaciones?.con_calificacion ?? 0}{' '}
                    calificadas
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-200 bg-gradient-to-br from-purple-50 to-purple-100 transition-shadow hover:shadow-md">
          <CardContent className="pb-5 pt-5">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-2">
                  <Brain className="h-5 w-5 text-purple-600" />

                  <p className="text-sm font-semibold uppercase tracking-wide text-purple-700">
                    Modelos
                  </p>
                </div>

                <p className="mb-1 text-3xl font-bold text-purple-900">
                  {metricas?.fine_tuning?.jobs_exitosos ?? 0}
                </p>

                <div className="mt-2 flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={`bg-white/50 text-xs ${
                      metricas?.fine_tuning?.modelo_activo
                        ? 'border-purple-300 text-purple-700'
                        : 'border-gray-300 text-gray-600'
                    }`}
                  >
                    {metricas?.fine_tuning?.modelo_activo
                      ? '✓ Activo'
                      : 'Sin activar'}
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-orange-200 bg-gradient-to-br from-orange-50 to-orange-100 transition-shadow hover:shadow-md">
          <CardContent className="pb-5 pt-5">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-orange-600" />

                  <p className="text-sm font-semibold uppercase tracking-wide text-orange-700">
                    Progreso
                  </p>
                </div>

                <p className="mb-2 text-3xl font-bold text-orange-900">
                  {calcularProgresoEntrenamiento().toFixed(0)}%
                </p>

                <Progress
                  value={calcularProgresoEntrenamiento()}
                  className="h-2.5 bg-orange-200"
                />

                <p className="mt-2 text-xs text-orange-600">
                  {metricas?.conversaciones?.listas_entrenamiento ?? 0} / 50
                  conversaciones
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs principales - Mejorado */}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 rounded-xl border border-gray-200 bg-white p-1.5 shadow-sm lg:grid-cols-4">
          <TabsTrigger
            value="asistente"
            className="flex items-center gap-2 rounded-lg px-4 py-2.5 transition-all data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=active]:shadow-md"
          >
            <Zap className="h-4 w-4" />

            <span className="font-medium">Asistente</span>
          </TabsTrigger>

          <TabsTrigger
            value="recoleccion"
            className="flex items-center gap-2 rounded-lg px-4 py-2.5 transition-all data-[state=active]:bg-green-600 data-[state=active]:text-white data-[state=active]:shadow-md"
          >
            <RefreshCw className="h-4 w-4" />

            <span className="font-medium">Recolección</span>
          </TabsTrigger>

          <TabsTrigger
            value="calidad"
            className="flex items-center gap-2 rounded-lg px-4 py-2.5 transition-all data-[state=active]:bg-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md"
          >
            <Target className="h-4 w-4" />

            <span className="font-medium">Calidad</span>
          </TabsTrigger>

          <TabsTrigger
            value="prompt"
            className="flex items-center gap-2 rounded-lg px-4 py-2.5 transition-all data-[state=active]:bg-orange-600 data-[state=active]:text-white data-[state=active]:shadow-md"
          >
            <Settings className="h-4 w-4" />

            <span className="font-medium">Prompt</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Asistente Inteligente */}

        <TabsContent value="asistente" className="mt-6">
          <div className="space-y-6">
            {/* Header mejorado */}

            <Card className="border-blue-200 bg-gradient-to-r from-blue-50 via-blue-50 to-purple-50">
              <CardContent className="pb-6 pt-6">
                <div className="flex items-start gap-4">
                  <div className="rounded-xl bg-blue-600 p-3">
                    <Zap className="h-6 w-6 text-white" />
                  </div>

                  <div className="flex-1">
                    <h2 className="mb-2 text-2xl font-bold text-gray-900">
                      Asistente de Entrenamiento Inteligente
                    </h2>

                    <p className="text-gray-700">
                      Te guiaré paso a paso para mejorar el entrenamiento de tu
                      Chat AI. Analizo tus datos y te sugiero las mejores
                      acciones.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recomendaciones - Mejorado */}

            <div>
              <div className="mb-4 flex items-center justify-between">
                <h3 className="flex items-center gap-2 text-xl font-bold text-gray-900">
                  <Info className="h-5 w-5 text-blue-600" />
                  Recomendaciones Personalizadas
                </h3>

                <Badge
                  variant="outline"
                  className="border-blue-200 bg-blue-50 text-blue-700"
                >
                  {obtenerRecomendaciones().length} sugerencias
                </Badge>
              </div>

              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {obtenerRecomendaciones().map((rec, idx) => {
                  const isActive =
                    rec.tipo === 'recoleccion' && recoleccionAutomaticaActiva

                  const cardColor = isActive ? 'green' : rec.color

                  return (
                    <Card
                      key={idx}
                      className={`cursor-pointer border-2 transition-all hover:shadow-lg ${
                        cardColor === 'green'
                          ? 'border-green-400 bg-gradient-to-br from-green-50 to-green-100'
                          : cardColor === 'amber'
                            ? 'border-amber-400 bg-gradient-to-br from-amber-50 to-amber-100'
                            : 'border-blue-400 bg-gradient-to-br from-blue-50 to-blue-100'
                      }`}
                    >
                      <CardContent className="pb-5 pt-5">
                        <div className="space-y-3">
                          <div className="flex items-start justify-between">
                            <div
                              className={`rounded-xl p-3 ${
                                cardColor === 'green'
                                  ? 'bg-green-200 text-green-700'
                                  : cardColor === 'amber'
                                    ? 'bg-amber-200 text-amber-700'
                                    : 'bg-blue-200 text-blue-700'
                              }`}
                            >
                              {rec.icono}
                            </div>

                            {isActive && (
                              <Badge className="bg-green-600 text-white">
                                <CheckCircle className="mr-1 h-3 w-3" />
                                Activo
                              </Badge>
                            )}
                          </div>

                          <div>
                            <h4 className="mb-2 text-lg font-bold text-gray-900">
                              {rec.titulo}
                            </h4>

                            <p className="mb-4 text-sm leading-relaxed text-gray-700">
                              {rec.descripcion}
                            </p>

                            <Button
                              size="sm"
                              variant={
                                cardColor === 'green' ? 'default' : 'outline'
                              }
                              className={`w-full ${
                                cardColor === 'green'
                                  ? 'bg-green-600 text-white hover:bg-green-700'
                                  : cardColor === 'amber'
                                    ? 'border-amber-600 text-amber-700 hover:bg-amber-50'
                                    : 'border-blue-600 text-blue-700 hover:bg-blue-50'
                              }`}
                              disabled={
                                rec.tipo === 'recoleccion' &&
                                cargandoEstadoRecoleccion
                              }
                              onClick={() => {
                                if (rec.tipo === 'recoleccion') {
                                  handleActivarRecoleccionAutomatica()
                                } else if (rec.tipo === 'calidad') {
                                  setActiveTab('calidad')
                                } else if (rec.tipo === 'entrenar') {
                                  window.location.href =
                                    BASE_PATH +
                                    '/configuracion?tab=ai&subtab=fine-tuning'
                                } else {
                                  toast.info(
                                    'Consulta la pestaña de Recolección para más información'
                                  )
                                }
                              }}
                            >
                              {rec.tipo === 'recoleccion' &&
                              cargandoEstadoRecoleccion ? (
                                <>
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />

                                  {recoleccionAutomaticaActiva
                                    ? 'Desactivando...'
                                    : 'Activando...'}
                                </>
                              ) : (
                                <>
                                  {rec.accion}

                                  <ChevronRight className="ml-2 h-4 w-4" />
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>

            {/* Guía rápida - Mejorado */}

            <Card className="border-gray-200 shadow-sm">
              <CardContent className="pt-6">
                <div className="mb-6 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-xl font-bold text-gray-900">
                    <Info className="h-5 w-5 text-blue-600" />
                    Guía Rápida de Entrenamiento
                  </h3>

                  <Badge variant="outline" className="bg-gray-50">
                    5 pasos
                  </Badge>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  <div className="relative rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-blue-100 p-4 transition-shadow hover:shadow-md">
                    <div className="absolute -left-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white shadow-lg">
                      1
                    </div>

                    <div className="mt-4">
                      <p className="mb-2 font-bold text-gray-900">
                        Recolecta Conversaciones
                      </p>

                      <p className="text-sm leading-relaxed text-gray-700">
                        Activa la recolección automática o crea conversaciones
                        manualmente. Mínimo 10 conversaciones, ideal 50+.
                      </p>
                    </div>
                  </div>

                  <div className="relative rounded-xl border border-green-200 bg-gradient-to-br from-green-50 to-green-100 p-4 transition-shadow hover:shadow-md">
                    <div className="absolute -left-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-green-600 text-sm font-bold text-white shadow-lg">
                      2
                    </div>

                    <div className="mt-4">
                      <p className="mb-2 font-bold text-gray-900">
                        Califica y Mejora
                      </p>

                      <p className="text-sm leading-relaxed text-gray-700">
                        Califica las conversaciones (4-5 estrellas) y revisa la
                        calidad de los datos.
                      </p>
                    </div>
                  </div>

                  <div className="relative rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50 to-purple-100 p-4 transition-shadow hover:shadow-md">
                    <div className="absolute -left-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-purple-600 text-sm font-bold text-white shadow-lg">
                      3
                    </div>

                    <div className="mt-4">
                      <p className="mb-2 font-bold text-gray-900">
                        Prepara Datos
                      </p>

                      <p className="text-sm leading-relaxed text-gray-700">
                        Prepara los datos en formato JSONL para OpenAI
                        Fine-tuning.
                      </p>
                    </div>
                  </div>

                  <div className="relative rounded-xl border border-orange-200 bg-gradient-to-br from-orange-50 to-orange-100 p-4 transition-shadow hover:shadow-md">
                    <div className="absolute -left-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-orange-600 text-sm font-bold text-white shadow-lg">
                      4
                    </div>

                    <div className="mt-4">
                      <p className="mb-2 font-bold text-gray-900">
                        Entrena el Modelo
                      </p>

                      <p className="text-sm leading-relaxed text-gray-700">
                        Inicia el fine-tuning con OpenAI. El proceso toma 1-3
                        horas.
                      </p>
                    </div>
                  </div>

                  <div className="relative rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-indigo-100 p-4 transition-shadow hover:shadow-md md:col-span-2 lg:col-span-1">
                    <div className="absolute -left-2 -top-2 flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white shadow-lg">
                      5
                    </div>

                    <div className="mt-4">
                      <p className="mb-2 font-bold text-gray-900">
                        Activa y Prueba
                      </p>

                      <p className="text-sm leading-relaxed text-gray-700">
                        Activa el modelo entrenado y prueba en el Chat AI.
                        Compara con el modelo base.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab 2: Recolección - Mejorado */}

        <TabsContent value="recoleccion" className="mt-6">
          <div className="space-y-6">
            {/* Header */}

            <Card className="border-green-200 bg-gradient-to-r from-green-50 to-emerald-50">
              <CardContent className="pb-6 pt-6">
                <div className="flex items-start gap-4">
                  <div className="rounded-xl bg-green-600 p-3">
                    <RefreshCw className="h-6 w-6 text-white" />
                  </div>

                  <div className="flex-1">
                    <h2 className="mb-2 text-2xl font-bold text-gray-900">
                      Recolección de Conversaciones
                    </h2>

                    <p className="text-gray-700">
                      Gestiona la recolección automática y manual de
                      conversaciones del Chat AI para entrenamiento
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Estado de activación - Mejorado */}

            <Card
              className={`border-2 shadow-lg ${recoleccionAutomaticaActiva ? 'border-green-400 bg-gradient-to-br from-green-50 to-emerald-50' : 'border-gray-300 bg-gradient-to-br from-gray-50 to-gray-100'}`}
            >
              <CardContent className="pb-6 pt-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-start gap-4">
                    <div
                      className={`rounded-xl p-3 ${recoleccionAutomaticaActiva ? 'bg-green-200' : 'bg-gray-200'}`}
                    >
                      {recoleccionAutomaticaActiva ? (
                        <CheckCircle className="h-6 w-6 text-green-700" />
                      ) : (
                        <AlertCircle className="h-6 w-6 text-gray-600" />
                      )}
                    </div>

                    <div>
                      <h3 className="mb-1 text-xl font-bold text-gray-900">
                        {recoleccionAutomaticaActiva
                          ? 'Recolección Automática Activada'
                          : 'Recolección Automática Desactivada'}
                      </h3>

                      <p className="text-gray-700">
                        {recoleccionAutomaticaActiva
                          ? 'Las conversaciones del Chat AI se guardan automáticamente en tiempo real'
                          : 'Activa la recolección para guardar conversaciones automáticamente'}
                      </p>
                    </div>
                  </div>

                  <Button
                    onClick={handleActivarRecoleccionAutomatica}
                    disabled={cargandoEstadoRecoleccion}
                    size="lg"
                    variant={
                      recoleccionAutomaticaActiva ? 'outline' : 'default'
                    }
                    className={`min-w-[140px] ${
                      recoleccionAutomaticaActiva
                        ? 'border-2 border-green-600 text-green-700 hover:bg-green-50'
                        : 'bg-green-600 text-white shadow-md hover:bg-green-700'
                    }`}
                  >
                    {cargandoEstadoRecoleccion ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />

                        {recoleccionAutomaticaActiva
                          ? 'Desactivando...'
                          : 'Activando...'}
                      </>
                    ) : (
                      <>
                        <RefreshCw
                          className={`mr-2 h-4 w-4 ${recoleccionAutomaticaActiva ? 'text-green-600' : ''}`}
                        />

                        {recoleccionAutomaticaActiva ? 'Desactivar' : 'Activar'}
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Información y acciones */}

            <div className="grid gap-6 md:grid-cols-2">
              {/* Información */}

              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="pt-6">
                  <div className="mb-4 flex items-start gap-3">
                    <Info className="mt-0.5 h-6 w-6 flex-shrink-0 text-blue-600" />

                    <div>
                      <h4 className="mb-2 text-lg font-bold text-blue-900">
                        ¿Cómo funciona?
                      </h4>

                      <ul className="space-y-2 text-sm text-blue-800">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />

                          <span>
                            Se guardan automáticamente todas las conversaciones
                            del Chat AI
                          </span>
                        </li>

                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />

                          <span>
                            Incluye pregunta, respuesta, contexto usado y
                            métricas
                          </span>
                        </li>

                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />

                          <span>
                            Puedes calificarlas después para filtrar las mejores
                          </span>
                        </li>

                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />

                          <span>
                            Las conversaciones con 4+ estrellas se usan para
                            entrenamiento
                          </span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Acciones rápidas */}

              <Card className="border-gray-200">
                <CardContent className="pt-6">
                  <h4 className="mb-4 text-lg font-bold text-gray-900">
                    Acciones Rápidas
                  </h4>

                  <div className="space-y-3">
                    <Button
                      onClick={handleRecoleccionAutomatica}
                      disabled={recolectandoAutomatico}
                      variant="outline"
                      className="w-full justify-start border-blue-600 text-blue-700 hover:bg-blue-50"
                      size="lg"
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
                      onClick={() =>
                        (window.location.href =
                          BASE_PATH +
                          '/configuracion?tab=ai&subtab=fine-tuning')
                      }
                      className="w-full justify-start"
                      size="lg"
                    >
                      <FileText className="mr-2 h-4 w-4" />
                      Ver Conversaciones Recolectadas
                      <ChevronRight className="ml-auto h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Estadísticas de recolección - Mejorado */}

            {metricas?.conversaciones && (
              <Card className="border-gray-200 shadow-sm">
                <CardContent className="pt-6">
                  <div className="mb-6 flex items-center justify-between">
                    <h4 className="text-xl font-bold text-gray-900">
                      Estadísticas de Recolección
                    </h4>

                    <Badge variant="outline" className="bg-gray-50">
                      Actualizado
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-700">
                        Total
                      </p>

                      <p className="text-3xl font-bold text-blue-900">
                        {metricas.conversaciones.total ?? 0}
                      </p>

                      <p className="mt-1 text-xs text-blue-600">
                        conversaciones
                      </p>
                    </div>

                    <div className="rounded-xl border border-purple-200 bg-purple-50 p-4">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-purple-700">
                        Calificadas
                      </p>

                      <p className="text-3xl font-bold text-purple-900">
                        {metricas.conversaciones.con_calificacion ?? 0}
                      </p>

                      <p className="mt-1 text-xs text-purple-600">
                        con calificación
                      </p>
                    </div>

                    <div className="rounded-xl border border-green-200 bg-green-50 p-4">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-green-700">
                        Listas
                      </p>

                      <p className="text-3xl font-bold text-green-900">
                        {metricas.conversaciones.listas_entrenamiento ?? 0}
                      </p>

                      <p className="mt-1 text-xs text-green-600">
                        4+ estrellas
                      </p>
                    </div>

                    <div className="rounded-xl border border-orange-200 bg-orange-50 p-4">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-orange-700">
                        Promedio
                      </p>

                      <p className="text-3xl font-bold text-orange-900">
                        {(
                          metricas.conversaciones.promedio_calificacion ?? 0
                        ).toFixed(1)}
                      </p>

                      <p className="mt-1 text-xs text-orange-600">de 5.0</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Tab 3: Calidad de Datos - Mejorado */}

        <TabsContent value="calidad" className="mt-6">
          <div className="space-y-6">
            {/* Header */}

            <Card className="border-purple-200 bg-gradient-to-r from-purple-50 to-pink-50">
              <CardContent className="pb-6 pt-6">
                <div className="flex items-start gap-4">
                  <div className="rounded-xl bg-purple-600 p-3">
                    <Target className="h-6 w-6 text-white" />
                  </div>

                  <div className="flex-1">
                    <h2 className="mb-2 text-2xl font-bold text-gray-900">
                      Análisis de Calidad de Datos
                    </h2>

                    <p className="text-gray-700">
                      Analiza la calidad de tus conversaciones para identificar
                      áreas de mejora y optimizar el entrenamiento.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Botón de análisis */}

            <Card className="border-purple-200">
              <CardContent className="pt-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h3 className="mb-2 text-lg font-bold text-gray-900">
                      Iniciar Análisis
                    </h3>

                    <p className="text-gray-600">
                      Ejecuta un análisis completo de la calidad de tus
                      conversaciones recolectadas
                    </p>
                  </div>

                  <Button
                    onClick={handleAnalizarCalidad}
                    disabled={analizandoCalidad}
                    size="lg"
                    className="min-w-[200px] bg-purple-600 text-white shadow-md hover:bg-purple-700"
                  >
                    {analizandoCalidad ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Analizando...
                      </>
                    ) : (
                      <>
                        <Target className="mr-2 h-5 w-5" />
                        Analizar Calidad
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Resultados del análisis */}

            {analisisCalidad && (
              <div className="space-y-6">
                <Card className="border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 shadow-md">
                  <CardContent className="pt-6">
                    <div className="mb-6 flex items-center gap-3">
                      <CheckCircle className="h-6 w-6 text-green-600" />

                      <h4 className="text-xl font-bold text-gray-900">
                        Métricas de Calidad
                      </h4>
                    </div>

                    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                      <div className="rounded-xl border border-green-200 bg-white p-4">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-green-700">
                          Completitud
                        </p>

                        <p className="text-3xl font-bold text-green-900">
                          {analisisCalidad.completitud?.toFixed(1) || 0}%
                        </p>

                        <Progress
                          value={analisisCalidad.completitud || 0}
                          className="mt-2 h-2"
                        />
                      </div>

                      <div className="rounded-xl border border-blue-200 bg-white p-4">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-700">
                          Consistencia
                        </p>

                        <p className="text-3xl font-bold text-blue-900">
                          {analisisCalidad.consistencia?.toFixed(1) || 0}%
                        </p>

                        <Progress
                          value={analisisCalidad.consistencia || 0}
                          className="mt-2 h-2"
                        />
                      </div>

                      <div className="rounded-xl border border-purple-200 bg-white p-4">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-purple-700">
                          Relevancia
                        </p>

                        <p className="text-3xl font-bold text-purple-900">
                          {analisisCalidad.relevancia?.toFixed(1) || 0}%
                        </p>

                        <Progress
                          value={analisisCalidad.relevancia || 0}
                          className="mt-2 h-2"
                        />
                      </div>

                      <div className="rounded-xl border border-orange-200 bg-white p-4">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-orange-700">
                          Calidad General
                        </p>

                        <p className="text-3xl font-bold text-orange-900">
                          {analisisCalidad.calidad_general?.toFixed(1) || 0}%
                        </p>

                        <Progress
                          value={analisisCalidad.calidad_general || 0}
                          className="mt-2 h-2"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {analisisCalidad.sugerencias &&
                  analisisCalidad.sugerencias.length > 0 && (
                    <Card className="border-yellow-200 bg-yellow-50">
                      <CardContent className="pt-6">
                        <div className="mb-4 flex items-center gap-3">
                          <Info className="h-6 w-6 text-yellow-600" />

                          <h4 className="text-xl font-bold text-gray-900">
                            Sugerencias de Mejora
                          </h4>

                          <Badge
                            variant="outline"
                            className="border-yellow-300 bg-yellow-100 text-yellow-700"
                          >
                            {analisisCalidad.sugerencias.length} sugerencias
                          </Badge>
                        </div>

                        <div className="space-y-3">
                          {analisisCalidad.sugerencias.map(
                            (sug: string, idx: number) => (
                              <div
                                key={idx}
                                className="flex items-start gap-3 rounded-lg border border-yellow-200 bg-white p-3"
                              >
                                <ChevronRight className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-600" />

                                <span className="text-gray-800">{sug}</span>
                              </div>
                            )
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 4: Prompt - Mejorado */}

        <TabsContent value="prompt" className="mt-6">
          <div className="space-y-6">
            {/* Header */}

            <Card className="border-orange-200 bg-gradient-to-r from-orange-50 to-amber-50">
              <CardContent className="pb-6 pt-6">
                <div className="flex items-start gap-4">
                  <div className="rounded-xl bg-orange-600 p-3">
                    <Settings className="h-6 w-6 text-white" />
                  </div>

                  <div className="flex-1">
                    <h2 className="mb-2 text-2xl font-bold text-gray-900">
                      Editor de Prompt Personalizado
                    </h2>

                    <p className="text-gray-700">
                      Personaliza el prompt del AI para ajustar su
                      comportamiento, tono y capacidades. El prompt
                      personalizado reemplazará al prompt por defecto.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Editor */}

            <Card className="border-gray-200 shadow-sm">
              <CardContent className="pt-6">
                <PromptEditor />
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
