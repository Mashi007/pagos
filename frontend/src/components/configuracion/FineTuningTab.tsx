import { useState, useEffect, useRef } from 'react'
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
  Plus,
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

  // Estados para crear conversación manual
  const [mostrarFormNuevaConversacion, setMostrarFormNuevaConversacion] = useState(false)
  const [nuevaPregunta, setNuevaPregunta] = useState('')
  const [nuevaRespuesta, setNuevaRespuesta] = useState('')
  const [guardandoConversacion, setGuardandoConversacion] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Estados para insertar tablas y campos
  const [tablaSeleccionada, setTablaSeleccionada] = useState<string>('')
  const [campoSeleccionado, setCampoSeleccionado] = useState<string>('')
  const [textareaActivo, setTextareaActivo] = useState<'pregunta' | 'respuesta' | null>(null)
  const preguntaTextareaRef = useRef<HTMLTextAreaElement>(null)
  const respuestaTextareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Estados para tablas y campos dinámicos
  const [tablasYCampos, setTablasYCampos] = useState<Record<string, string[]>>({})
  const [cargandoTablasCampos, setCargandoTablasCampos] = useState(false)
  const [ultimaActualizacion, setUltimaActualizacion] = useState<string>('')

  // Obtener campos disponibles según la tabla seleccionada
  const camposDisponibles = tablaSeleccionada ? (tablasYCampos[tablaSeleccionada] || []) : []

  // Cargar tablas y campos desde el backend
  const cargarTablasCampos = async () => {
    setCargandoTablasCampos(true)
    try {
      const data = await aiTrainingService.getTablasCampos()
      setTablasYCampos(data.tablas_campos)
      setUltimaActualizacion(data.fecha_consulta)
      toast.success(`Cargadas ${data.total_tablas} tablas con sus campos`)
    } catch (error: any) {
      console.error('Error cargando tablas y campos:', error)
      toast.error('Error al cargar tablas y campos desde la base de datos')
    } finally {
      setCargandoTablasCampos(false)
    }
  }

  // Cargar tablas y campos al montar el componente
  useEffect(() => {
    cargarTablasCampos()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Limpiar campo seleccionado cuando cambia la tabla
  useEffect(() => {
    if (tablaSeleccionada && campoSeleccionado && !camposDisponibles.includes(campoSeleccionado)) {
      setCampoSeleccionado('')
    }
  }, [tablaSeleccionada, campoSeleccionado, camposDisponibles])

  // Función para insertar tabla o campo en el textarea activo
  const insertarEnTextarea = (texto: string) => {
    let textarea: HTMLTextAreaElement | null = null
    let setter: (value: string) => void

    // Determinar qué textarea usar
    if (textareaActivo === 'pregunta' || (document.activeElement === preguntaTextareaRef.current)) {
      textarea = preguntaTextareaRef.current
      setter = setNuevaPregunta
    } else if (textareaActivo === 'respuesta' || (document.activeElement === respuestaTextareaRef.current)) {
      textarea = respuestaTextareaRef.current
      setter = setNuevaRespuesta
    } else {
      // Si no hay textarea activo, usar el de pregunta por defecto
      textarea = preguntaTextareaRef.current
      setter = setNuevaPregunta
    }

    if (textarea) {
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const valorActual = textarea.value
      const nuevoValor = valorActual.substring(0, start) + texto + valorActual.substring(end)
      
      setter(nuevoValor)
      
      // Restaurar el foco y posición del cursor
      setTimeout(() => {
        textarea?.focus()
        const nuevaPosicion = start + texto.length
        textarea?.setSelectionRange(nuevaPosicion, nuevaPosicion)
      }, 0)
    }
  }

  // Función para insertar tabla
  const handleInsertarTabla = () => {
    if (!tablaSeleccionada) {
      toast.warning('Selecciona una tabla primero')
      return
    }
    insertarEnTextarea(tablaSeleccionada)
    setTablaSeleccionada('')
  }

  // Función para insertar campo
  const handleInsertarCampo = () => {
    if (!campoSeleccionado) {
      toast.warning('Selecciona un campo primero')
      return
    }
    insertarEnTextarea(campoSeleccionado)
    setCampoSeleccionado('')
  }

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

  const handleCrearConversacion = async () => {
    if (!nuevaPregunta.trim() || !nuevaRespuesta.trim()) {
      toast.error('La pregunta y respuesta son requeridas')
      return
    }

    setGuardandoConversacion(true)
    try {
      await aiTrainingService.guardarConversacion({
        pregunta: nuevaPregunta.trim(),
        respuesta: nuevaRespuesta.trim(),
        modelo_usado: 'manual',
      })
      toast.success('Conversación creada exitosamente')
      setNuevaPregunta('')
      setNuevaRespuesta('')
      setTablaSeleccionada('')
      setCampoSeleccionado('')
      setTextareaActivo(null)
      setMostrarFormNuevaConversacion(false)
      cargarConversaciones()
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al crear conversación'
      toast.error(mensaje)
    } finally {
      setGuardandoConversacion(false)
    }
  }

  const handleExportarConversaciones = () => {
    try {
      const datos = conversaciones.map((c) => ({
        id: c.id,
        pregunta: c.pregunta,
        respuesta: c.respuesta,
        calificacion: c.calificacion || null,
        feedback: c.feedback || null,
        modelo_usado: c.modelo_usado || null,
        tokens_usados: c.tokens_usados || null,
        creado_en: c.creado_en,
      }))

      const json = JSON.stringify(datos, null, 2)
      const blob = new Blob([json], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `conversaciones_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      toast.success('Conversaciones exportadas exitosamente')
    } catch (error: any) {
      toast.error('Error al exportar conversaciones')
    }
  }

  const handleImportarConversaciones = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const datos = JSON.parse(text)

      if (!Array.isArray(datos)) {
        toast.error('El archivo debe contener un array de conversaciones')
        return
      }

      let importadas = 0
      let errores = 0

      for (const item of datos) {
        if (!item.pregunta || !item.respuesta) {
          errores++
          continue
        }

        try {
          await aiTrainingService.guardarConversacion({
            pregunta: item.pregunta,
            respuesta: item.respuesta,
            modelo_usado: item.modelo_usado || 'importado',
            tokens_usados: item.tokens_usados,
          })
          importadas++
        } catch (error) {
          errores++
        }
      }

      if (importadas > 0) {
        toast.success(`${importadas} conversaciones importadas exitosamente${errores > 0 ? ` (${errores} errores)` : ''}`)
        cargarConversaciones()
      } else {
        toast.error('No se pudieron importar conversaciones')
      }

      // Limpiar el input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (error: any) {
      toast.error('Error al leer el archivo. Verifica que sea un JSON válido.')
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

      {/* Guía de uso */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h4 className="font-semibold mb-3 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-blue-600" />
            ¿Cómo usar Fine-tuning?
          </h4>
          <div className="space-y-2 text-sm text-gray-700">
            <div className="flex items-start gap-2">
              <span className="font-semibold text-blue-600">1.</span>
              <div>
                <strong>Agregar conversaciones:</strong> Usa "Nueva Conversación" para crear manualmente o "Importar desde JSON" para cargar múltiples conversaciones.
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="font-semibold text-blue-600">2.</span>
              <div>
                <strong>Calificar conversaciones:</strong> Para cada conversación, califica con 1-5 estrellas. Solo las conversaciones con 4+ estrellas se usarán para entrenar.
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="font-semibold text-blue-600">3.</span>
              <div>
                <strong>Preparar datos:</strong> Necesitas al menos 10 conversaciones calificadas (4+ estrellas). Luego haz clic en "Preparar Datos para Entrenamiento".
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="font-semibold text-blue-600">4.</span>
              <div>
                <strong>Iniciar entrenamiento:</strong> Selecciona el modelo base y haz clic en "Iniciar Entrenamiento". El proceso puede tardar varios minutos.
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="font-semibold text-blue-600">5.</span>
              <div>
                <strong>Activar modelo:</strong> Una vez completado el entrenamiento, puedes activar el modelo entrenado para usarlo en el sistema.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

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

      {/* Formulario para crear conversación manual */}
      {mostrarFormNuevaConversacion && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold">Nueva Conversación</h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setMostrarFormNuevaConversacion(false)
                  setNuevaPregunta('')
                  setNuevaRespuesta('')
                  setTablaSeleccionada('')
                  setCampoSeleccionado('')
                  setTextareaActivo(null)
                }}
              >
                <XCircle className="h-4 w-4" />
              </Button>
            </div>
            <div className="space-y-4">
              {/* Selector de Tablas y Campos */}
              <Card className="bg-gray-50 border-gray-200">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-gray-600" />
                      <h5 className="text-sm font-semibold text-gray-700">Insertar Tablas y Campos</h5>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={cargarTablasCampos}
                      disabled={cargandoTablasCampos}
                      className="shrink-0"
                    >
                      {cargandoTablasCampos ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Cargando...
                        </>
                      ) : (
                        <>
                          <Download className="h-3 w-3 mr-1" />
                          Actualizar
                        </>
                      )}
                    </Button>
                  </div>
                  {ultimaActualizacion && (
                    <p className="text-xs text-gray-500 mb-3">
                      Última actualización: {new Date(ultimaActualizacion).toLocaleString('es-ES')} 
                      ({Object.keys(tablasYCampos).length} tablas)
                    </p>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Selector de Tablas */}
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-600">Tabla</label>
                      <div className="flex gap-2">
                        <Select value={tablaSeleccionada} onValueChange={setTablaSeleccionada}>
                          <SelectTrigger className="flex-1">
                            <SelectValue placeholder="Selecciona una tabla" />
                          </SelectTrigger>
                          <SelectContent>
                            {Object.keys(tablasYCampos).length === 0 ? (
                              <div className="px-2 py-1.5 text-sm text-gray-500">
                                {cargandoTablasCampos ? 'Cargando tablas...' : 'No hay tablas disponibles'}
                              </div>
                            ) : (
                              Object.keys(tablasYCampos).map((tabla) => (
                                <SelectItem key={tabla} value={tabla}>
                                  {tabla}
                                </SelectItem>
                              ))
                            )}
                          </SelectContent>
                        </Select>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleInsertarTabla}
                          disabled={!tablaSeleccionada}
                          className="shrink-0"
                        >
                          <Plus className="h-4 w-4 mr-1" />
                          Insertar
                        </Button>
                      </div>
                    </div>

                    {/* Selector de Campos */}
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-600">Campo</label>
                      <div className="flex gap-2">
                        <Select
                          value={campoSeleccionado}
                          onValueChange={setCampoSeleccionado}
                          disabled={!tablaSeleccionada}
                        >
                          <SelectTrigger className="flex-1">
                            <SelectValue placeholder={tablaSeleccionada ? "Selecciona un campo" : "Selecciona tabla primero"} />
                          </SelectTrigger>
                          <SelectContent>
                            {camposDisponibles.length === 0 ? (
                              <div className="px-2 py-1.5 text-sm text-gray-500">
                                {!tablaSeleccionada ? 'Selecciona una tabla primero' : 'No hay campos disponibles'}
                              </div>
                            ) : (
                              camposDisponibles.map((campo) => (
                                <SelectItem key={campo} value={campo}>
                                  {campo}
                                </SelectItem>
                              ))
                            )}
                          </SelectContent>
                        </Select>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleInsertarCampo}
                          disabled={!campoSeleccionado}
                          className="shrink-0"
                        >
                          <Plus className="h-4 w-4 mr-1" />
                          Insertar
                        </Button>
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-3">
                    💡 Tip: Haz clic en el campo de Pregunta o Respuesta donde quieras insertar, luego selecciona la tabla/campo y presiona Insertar.
                  </p>
                </CardContent>
              </Card>

              <div>
                <label className="text-sm font-medium mb-2 block">Pregunta *</label>
                <Textarea
                  ref={preguntaTextareaRef}
                  placeholder="Ej: ¿Cuál es el proceso para solicitar un préstamo?"
                  value={nuevaPregunta}
                  onChange={(e) => setNuevaPregunta(e.target.value)}
                  onFocus={() => setTextareaActivo('pregunta')}
                  rows={3}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Respuesta *</label>
                <Textarea
                  ref={respuestaTextareaRef}
                  placeholder="Ej: Para solicitar un préstamo necesitas..."
                  value={nuevaRespuesta}
                  onChange={(e) => setNuevaRespuesta(e.target.value)}
                  onFocus={() => setTextareaActivo('respuesta')}
                  rows={5}
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCrearConversacion} disabled={guardandoConversacion}>
                  {guardandoConversacion ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Guardar Conversación
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setMostrarFormNuevaConversacion(false)
                    setNuevaPregunta('')
                    setNuevaRespuesta('')
                    setTablaSeleccionada('')
                    setCampoSeleccionado('')
                    setTextareaActivo(null)
                  }}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Conversaciones */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Conversaciones ({conversaciones.length})
            </h4>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant="outline"
                onClick={() => setMostrarFormNuevaConversacion(!mostrarFormNuevaConversacion)}
              >
                <Upload className="h-4 w-4 mr-2" />
                {mostrarFormNuevaConversacion ? 'Ocultar Formulario' : 'Nueva Conversación'}
              </Button>
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-4 w-4 mr-2" />
                Importar desde JSON
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleImportarConversaciones}
                className="hidden"
              />
              {conversaciones.length > 0 && (
                <Button variant="outline" onClick={handleExportarConversaciones}>
                  <Download className="h-4 w-4 mr-2" />
                  Exportar JSON
                </Button>
              )}
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

