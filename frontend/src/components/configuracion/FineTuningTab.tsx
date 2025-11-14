import { useState, useEffect } from 'react'
import {
  Brain,
  Heart,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Filter,
  Download,
  Upload,
  AlertCircle,
  MessageSquare,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { aiTrainingService, ConversacionAI, FineTuningJob } from '@/services/aiTrainingService'
import { toast } from 'sonner'

export function FineTuningTab() {
  const [conversaciones, setConversaciones] = useState<ConversacionAI[]>([])
  const [cargando, setCargando] = useState(false)
  const [jobs, setJobs] = useState<FineTuningJob[]>([])
  const [cargandoJobs, setCargandoJobs] = useState(false)

  // Filtros
  const [filtroCalificacion, setFiltroCalificacion] = useState<string>('todas')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')

  // Estados para acciones
  const [calificandoId, setCalificandoId] = useState<number | null>(null)
  const [calificacion, setCalificacion] = useState(0)
  const [feedback, setFeedback] = useState('')
  const [entrenando, setEntrenando] = useState(false)
  const [preparando, setPreparando] = useState(false)

  // Estados para nuevo entrenamiento
  const [mostrarFormEntrenamiento, setMostrarFormEntrenamiento] = useState(false)
  const [modeloBase, setModeloBase] = useState('gpt-3.5-turbo')
  const [archivoId, setArchivoId] = useState('')

  const cargarConversaciones = async () => {
    setCargando(true)
    try {
      const params: any = {}
      if (filtroCalificacion === 'con_calificacion') params.con_calificacion = true
      if (filtroCalificacion === 'sin_calificacion') params.con_calificacion = false
      if (fechaDesde) params.fecha_desde = fechaDesde
      if (fechaHasta) params.fecha_hasta = fechaHasta

      const data = await aiTrainingService.getConversaciones(params)
      setConversaciones(data.conversaciones || [])
    } catch (error: any) {
      console.error('Error cargando conversaciones:', error)
      toast.error('Error al cargar conversaciones')
    } finally {
      setCargando(false)
    }
  }

  const cargarJobs = async () => {
    setCargandoJobs(true)
    try {
      const data = await aiTrainingService.listarFineTuningJobs()
      setJobs(data || [])
    } catch (error: any) {
      console.error('Error cargando jobs:', error)
      toast.error('Error al cargar jobs de entrenamiento')
    } finally {
      setCargandoJobs(false)
    }
  }

  useEffect(() => {
    cargarConversaciones()
  }, [filtroCalificacion, fechaDesde, fechaHasta])

  useEffect(() => {
    cargarJobs()

    // Polling para jobs en progreso
    const interval = setInterval(() => {
      cargarJobs()
    }, 10000) // Cada 10 segundos

    return () => clearInterval(interval)
  }, [])

  const handleCalificar = async (conversacionId: number) => {
    if (calificacion < 1 || calificacion > 5) {
      toast.error('Selecciona una calificación de 1 a 5 estrellas')
      return
    }

    setCalificandoId(conversacionId)
    try {
      await aiTrainingService.calificarConversacion(conversacionId, calificacion, feedback)
      toast.success('Conversación calificada exitosamente')
      setCalificacion(0)
      setFeedback('')
      cargarConversaciones()
    } catch (error: any) {
      toast.error('Error al calificar conversación')
    } finally {
      setCalificandoId(null)
    }
  }

  const handlePrepararDatos = async () => {
    setPreparando(true)
    try {
      const conversacionesSeleccionadas = conversaciones
        .filter((c) => c.calificacion && c.calificacion >= 4)
        .map((c) => c.id)

      // Mínimo recomendado por OpenAI para fine-tuning
      const MINIMO_CONVERSACIONES = 10

      if (conversacionesSeleccionadas.length < MINIMO_CONVERSACIONES) {
        toast.error(
          `Se necesitan al menos ${MINIMO_CONVERSACIONES} conversaciones calificadas (4+ estrellas) para entrenar un modelo. Actualmente tienes ${conversacionesSeleccionadas.length}.`
        )
        return
      }

      const result = await aiTrainingService.prepararDatosEntrenamiento(conversacionesSeleccionadas)
      setArchivoId(result.archivo_id)
      toast.success(`Datos preparados: ${result.total_conversaciones} conversaciones`)
      setMostrarFormEntrenamiento(true)
    } catch (error: any) {
      const mensajeError =
        error?.response?.data?.detail ||
        error?.message ||
        'Error al preparar datos de entrenamiento'
      toast.error(mensajeError)
    } finally {
      setPreparando(false)
    }
  }

  const handleIniciarEntrenamiento = async () => {
    if (!archivoId) {
      toast.error('Primero prepara los datos de entrenamiento')
      return
    }

    setEntrenando(true)
    try {
      const job = await aiTrainingService.iniciarFineTuning({
        archivo_id: archivoId,
        modelo_base: modeloBase,
      })
      toast.success('Entrenamiento iniciado exitosamente')
      setMostrarFormEntrenamiento(false)
      cargarJobs()
    } catch (error: any) {
      toast.error('Error al iniciar entrenamiento')
    } finally {
      setEntrenando(false)
    }
  }

  const handleActivarModelo = async (modeloId: string) => {
    try {
      await aiTrainingService.activarModeloFineTuned(modeloId)
      toast.success('Modelo activado exitosamente')
      cargarJobs()
    } catch (error: any) {
      toast.error('Error al activar modelo')
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      pending: { variant: 'secondary' as const, icon: Clock, text: 'Pendiente' },
      running: { variant: 'default' as const, icon: Loader2, text: 'Ejecutando' },
      succeeded: { variant: 'default' as const, icon: CheckCircle, text: 'Exitoso' },
      failed: { variant: 'destructive' as const, icon: XCircle, text: 'Fallido' },
      cancelled: { variant: 'secondary' as const, icon: XCircle, text: 'Cancelado' },
    }

    const config = variants[status] || variants.pending
    const Icon = config.icon

    return (
      <Badge variant={config.variant} className="flex items-center gap-1">
        {status === 'running' && <Icon className="h-3 w-3 animate-spin" />}
        {status !== 'running' && <Icon className="h-3 w-3" />}
        {config.text}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="h-6 w-6" />
            Fine-tuning
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Gestiona conversaciones y entrena modelos personalizados
          </p>
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-4 w-4" />
            <h4 className="font-semibold">Filtros</h4>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <Select value={filtroCalificacion} onValueChange={setFiltroCalificacion}>
              <SelectTrigger>
                <SelectValue placeholder="Calificación" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas</SelectItem>
                <SelectItem value="con_calificacion">Con calificación</SelectItem>
                <SelectItem value="sin_calificacion">Sin calificación</SelectItem>
              </SelectContent>
            </Select>
            <Input
              type="date"
              placeholder="Fecha desde"
              value={fechaDesde}
              onChange={(e) => setFechaDesde(e.target.value)}
            />
            <Input
              type="date"
              placeholder="Fecha hasta"
              value={fechaHasta}
              onChange={(e) => setFechaHasta(e.target.value)}
            />
            <Button onClick={cargarConversaciones} variant="outline" disabled={cargando}>
              {cargando ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Cargando...
                </>
              ) : (
                'Aplicar Filtros'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Conversaciones */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Conversaciones ({conversaciones.length})
            </h4>
            <Button
              onClick={handlePrepararDatos}
              disabled={preparando || conversaciones.filter((c) => c.calificacion && c.calificacion >= 4).length < 10}
            >
              {preparando ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Preparando...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Preparar Datos para Entrenamiento
                </>
              )}
            </Button>
          </div>

          {cargando ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          ) : conversaciones.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>No hay conversaciones disponibles</p>
            </div>
          ) : (
            <div className="space-y-4">
              {conversaciones.map((conv) => (
                <div key={conv.id} className="border rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">Pregunta:</span>
                        <span className="text-sm text-gray-600">{conv.pregunta}</span>
                      </div>
                      <div className="text-sm text-gray-500 mt-2">
                        <div className="line-clamp-2">{conv.respuesta}</div>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                        {conv.modelo_usado && <span>Modelo: {conv.modelo_usado}</span>}
                        {conv.tokens_usados && <span>Tokens: {conv.tokens_usados}</span>}
                        {conv.tiempo_respuesta && (
                          <span>Tiempo: {conv.tiempo_respuesta}ms</span>
                        )}
                        <span>{new Date(conv.creado_en).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="ml-4">
                      {conv.calificacion ? (
                        <div className="flex items-center gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <Heart
                              key={star}
                              className={`h-4 w-4 ${
                                star <= conv.calificacion!
                                  ? 'fill-yellow-400 text-yellow-400'
                                  : 'text-gray-300'
                              }`}
                            />
                          ))}
                        </div>
                      ) : (
                        <Badge variant="secondary">Sin calificar</Badge>
                      )}
                    </div>
                  </div>

                  {!conv.calificacion && (
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium">Calificar:</span>
                        <div className="flex items-center gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              type="button"
                              onClick={() => setCalificacion(star)}
                              className={`${
                                star <= calificacion
                                  ? 'text-yellow-400'
                                  : 'text-gray-300 hover:text-yellow-300'
                              }`}
                            >
                              <Heart className="h-5 w-5" />
                            </button>
                          ))}
                        </div>
                      </div>
                      <Textarea
                        placeholder="Feedback opcional..."
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                        className="mb-2"
                        rows={2}
                      />
                      <Button
                        size="sm"
                        onClick={() => handleCalificar(conv.id)}
                        disabled={calificandoId === conv.id || calificacion === 0}
                      >
                        {calificandoId === conv.id ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Guardando...
                          </>
                        ) : (
                          'Guardar Calificación'
                        )}
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Formulario de Entrenamiento */}
      {mostrarFormEntrenamiento && (
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-semibold mb-4">Iniciar Entrenamiento</h4>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Modelo Base</label>
                <Select value={modeloBase} onValueChange={setModeloBase}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gpt-3.5-turbo">gpt-3.5-turbo</SelectItem>
                    <SelectItem value="gpt-4">gpt-4</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleIniciarEntrenamiento} disabled={entrenando}>
                  {entrenando ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Iniciando...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Iniciar Entrenamiento
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setMostrarFormEntrenamiento(false)}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Jobs de Entrenamiento */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Jobs de Entrenamiento
            </h4>
            <Button onClick={cargarJobs} variant="outline" size="sm" disabled={cargandoJobs}>
              {cargandoJobs ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Actualizando...
                </>
              ) : (
                'Actualizar'
              )}
            </Button>
          </div>

          {cargandoJobs ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No hay jobs de entrenamiento</p>
            </div>
          ) : (
            <div className="space-y-4">
              {jobs.map((job) => (
                <div key={job.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium">Job ID: {job.id}</span>
                        {getStatusBadge(job.status)}
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        <div>Modelo Base: {job.modelo_base}</div>
                        {job.modelo_entrenado && (
                          <div>Modelo Entrenado: {job.modelo_entrenado}</div>
                        )}
                        {job.progreso !== undefined && (
                          <div>Progreso: {job.progreso}%</div>
                        )}
                        {job.error && (
                          <div className="text-red-600">Error: {job.error}</div>
                        )}
                        <div className="text-xs text-gray-400">
                          Creado: {new Date(job.creado_en).toLocaleString()}
                        </div>
                        {job.completado_en && (
                          <div className="text-xs text-gray-400">
                            Completado: {new Date(job.completado_en).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                    {job.status === 'succeeded' && job.modelo_entrenado && (
                      <Button
                        size="sm"
                        onClick={() => handleActivarModelo(job.modelo_entrenado!)}
                      >
                        Activar Modelo
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

