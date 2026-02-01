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
  Edit,
  Save,
  Zap,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Info,
  Trash2,
} from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { aiTrainingService, ConversacionAI, FineTuningJob } from '../../services/aiTrainingService'
import { toast } from 'sonner'

export function FineTuningTab() {
  const [conversaciones, setConversaciones] = useState<ConversacionAI[]>([])
  const [cargando, setCargando] = useState(false)
  const [jobs, setJobs] = useState<FineTuningJob[]>([])
  const [cargandoJobs, setCargandoJobs] = useState(false)
  const [tiempoActual, setTiempoActual] = useState(new Date())

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
  const [modeloBase, setModeloBase] = useState('gpt-4o-2024-08-06')
  const [archivoId, setArchivoId] = useState('')

  // Estados para crear conversaciÃ³n manual
  const [mostrarFormNuevaConversacion, setMostrarFormNuevaConversacion] = useState(false)
  const [nuevaPregunta, setNuevaPregunta] = useState('')
  const [nuevaRespuesta, setNuevaRespuesta] = useState('')
  const [guardandoConversacion, setGuardandoConversacion] = useState(false)

  // Estados para editar conversaciÃ³n
  const [editandoConversacionId, setEditandoConversacionId] = useState<number | null>(null)
  const [preguntaEditada, setPreguntaEditada] = useState('')
  const [respuestaEditada, setRespuestaEditada] = useState('')
  const [actualizandoConversacion, setActualizandoConversacion] = useState(false)
  const preguntaEditadaRef = useRef<HTMLTextAreaElement>(null)
  const respuestaEditadaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Estados para mejorador de IA
  const [mejorandoPregunta, setMejorandoPregunta] = useState(false)
  const [mejorandoRespuesta, setMejorandoRespuesta] = useState(false)
  const [mejorandoConversacion, setMejorandoConversacion] = useState(false)

  // Estados para estadÃ­sticas de feedback
  const [estadisticasFeedback, setEstadisticasFeedback] = useState<any>(null)
  const [cargandoEstadisticas, setCargandoEstadisticas] = useState(false)
  const [mostrarEstadisticas, setMostrarEstadisticas] = useState(false)
  const [filtrarFeedbackNegativo, setFiltrarFeedbackNegativo] = useState(true)

  // Estados para insertar tablas y campos
  const [tablaSeleccionada, setTablaSeleccionada] = useState<string>('')
  const [campoSeleccionado, setCampoSeleccionado] = useState<string>('')
  const [textareaActivo, setTextareaActivo] = useState<'pregunta' | 'respuesta' | null>(null)
  const preguntaTextareaRef = useRef<HTMLTextAreaElement>(null)
  const respuestaTextareaRef = useRef<HTMLTextAreaElement>(null)

  // Estados para tablas y campos dinÃ¡micos
  const [tablasYCampos, setTablasYCampos] = useState<Record<string, string[]>>({})
  const [cargandoTablasCampos, setCargandoTablasCampos] = useState(false)
  const [ultimaActualizacion, setUltimaActualizacion] = useState<string>('')

  // Obtener campos disponibles segÃºn la tabla seleccionada
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

  // FunciÃ³n para insertar tabla o campo en el textarea activo
  const insertarEnTextarea = (
    texto: string,
    valorActual?: string,
    setter?: (value: string) => void,
    textareaRef?: React.RefObject<HTMLTextAreaElement>
  ) => {
    let textarea: HTMLTextAreaElement | null = null
    let valor: string
    let setValue: (value: string) => void

    // Si estamos en modo ediciÃ³n y se pasaron los parÃ¡metros
    if (valorActual !== undefined && setter && textareaRef) {
      textarea = textareaRef.current
      valor = valorActual
      setValue = setter
    } else {
      // Modo creaciÃ³n (comportamiento original)
      if (textareaActivo === 'pregunta' || (document.activeElement === preguntaTextareaRef.current)) {
        textarea = preguntaTextareaRef.current
        valor = nuevaPregunta
        setValue = setNuevaPregunta
      } else if (textareaActivo === 'respuesta' || (document.activeElement === respuestaTextareaRef.current)) {
        textarea = respuestaTextareaRef.current
        valor = nuevaRespuesta
        setValue = setNuevaRespuesta
      } else {
        // Si no hay textarea activo, usar el de pregunta por defecto
        textarea = preguntaTextareaRef.current
        valor = nuevaPregunta
        setValue = setNuevaPregunta
      }
    }

    if (textarea) {
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const nuevoValor = valor.substring(0, start) + texto + valor.substring(end)

      setValue(nuevoValor)

      // Restaurar el foco y posiciÃ³n del cursor
      setTimeout(() => {
        textarea?.focus()
        const nuevaPosicion = start + texto.length
        textarea?.setSelectionRange(nuevaPosicion, nuevaPosicion)
      }, 0)
    }
  }

  // FunciÃ³n para insertar tabla
  const handleInsertarTabla = () => {
    if (!tablaSeleccionada) {
      toast.warning('Selecciona una tabla primero')
      return
    }
    insertarEnTextarea(tablaSeleccionada)
    setTablaSeleccionada('')
  }

  // FunciÃ³n para insertar campo
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

  // Actualizar tiempo actual cada minuto para mostrar tiempo transcurrido en tiempo real
  useEffect(() => {
    const interval = setInterval(() => {
      setTiempoActual(new Date())
    }, 60000) // Cada minuto

    return () => clearInterval(interval)
  }, [])

  const handleCalificar = async (conversacionId: number) => {
    if (calificacion < 1 || calificacion > 5) {
      toast.error('Selecciona una calificaciÃ³n de 1 a 5 estrellas')
      return
    }

    setCalificandoId(conversacionId)
    try {
      await aiTrainingService.calificarConversacion(conversacionId, calificacion, feedback)

      // Si la calificaciÃ³n es 4+ estrellas, la conversaciÃ³n estÃ¡ lista para entrenamiento
      if (calificacion >= 4) {
        const conversacionesCalificadas = conversaciones.filter(
          (c) => c.calificacion && c.calificacion >= 4
        ).length + 1 // +1 porque acabamos de calificar una
        const MINIMO_REQUERIDO = 10

        if (conversacionesCalificadas >= MINIMO_REQUERIDO) {
          toast.success(
            `âœ… ConversaciÃ³n calificada (${calificacion} estrellas) - Lista para entrenamiento. ` +
            `Total listas: ${conversacionesCalificadas} - Â¡Ya puedes preparar datos! (MÃ­nimo ${MINIMO_REQUERIDO} requerido)`
          )
        } else {
          toast.success(
            `âœ… ConversaciÃ³n calificada (${calificacion} estrellas) - Lista para entrenamiento. ` +
            `Total listas: ${conversacionesCalificadas} (necesitas ${MINIMO_REQUERIDO - conversacionesCalificadas} mÃ¡s para entrenar)`
          )
        }
      } else {
        toast.success(`ConversaciÃ³n calificada (${calificacion} estrellas)`)
      }

      setCalificacion(0)
      setFeedback('')
      cargarConversaciones()
    } catch (error: any) {
      toast.error('Error al calificar conversaciÃ³n')
    } finally {
      setCalificandoId(null)
    }
  }

  const cargarEstadisticasFeedback = async () => {
    setCargandoEstadisticas(true)
    try {
      const stats = await aiTrainingService.getEstadisticasFeedback()
      setEstadisticasFeedback(stats)
    } catch (error: any) {
      console.error('Error cargando estadÃ­sticas:', error)
      toast.error('Error al cargar estadÃ­sticas de feedback')
    } finally {
      setCargandoEstadisticas(false)
    }
  }

  // FunciÃ³n para detectar feedback negativo (similar a la del backend)
  const detectarFeedbackNegativo = (feedback: string | null | undefined): boolean => {
    if (!feedback) return false

    const feedbackLower = feedback.toLowerCase()

    // Palabras clave que indican feedback negativo (mismo que backend)
    const palabrasNegativas = [
      "mal", "malo", "incorrecto", "error", "equivocado", "confuso",
      "no entendÃ­", "no entiendo", "poco claro", "poco clara",
      "incompleto", "incompleta", "faltante", "falta", "deficiente",
      "mejorar", "deberÃ­a", "deberia", "podrÃ­a", "podria",
      "serÃ­a mejor", "no me gusta", "no me sirve", "no ayuda",
      "no es Ãºtil", "muy tÃ©cnico", "muy tÃ©cnica", "demasiado complejo",
      "compleja", "no responde", "no contesta", "no es lo que busco",
      "no es lo que necesito",
    ]

    // Contar palabras negativas
    const conteoNegativo = palabrasNegativas.filter(palabra => feedbackLower.includes(palabra)).length

    // Si hay 2 o mÃ¡s palabras negativas, considerar feedback negativo
    return conteoNegativo >= 2
  }

  const handlePrepararDatos = async () => {
    setPreparando(true)
    try {
      const conversacionesCalificadas = conversaciones.filter((c) => c.calificacion && c.calificacion >= 4)
      const conversacionesSeleccionadas = conversacionesCalificadas.map((c) => c.id)

      // MÃ­nimo requerido por OpenAI para fine-tuning: 10 conversaciones
      const MINIMO_CONVERSACIONES = 10

      if (conversacionesSeleccionadas.length < MINIMO_CONVERSACIONES) {
        toast.error(
          `Se necesita al menos ${MINIMO_CONVERSACIONES} conversaciones calificadas (4+ estrellas) para entrenar un modelo. OpenAI requiere mÃ­nimo 10 ejemplos. Actualmente tienes ${conversacionesSeleccionadas.length}.`
        )
        setPreparando(false)
        return
      }

      // ValidaciÃ³n temprana: simular filtrado de feedback negativo
      if (filtrarFeedbackNegativo) {
        const conversacionesConFeedbackNegativo = conversacionesCalificadas.filter(c =>
          detectarFeedbackNegativo(c.feedback || null)
        )
        const conversacionesDespuesFiltrado = conversacionesCalificadas.length - conversacionesConFeedbackNegativo.length

        if (conversacionesDespuesFiltrado < MINIMO_CONVERSACIONES) {
          const mensaje = `âš ï¸ Advertencia: DespuÃ©s de filtrar feedback negativo, solo quedarÃ­an ${conversacionesDespuesFiltrado} conversaciones (se excluirÃ­an ${conversacionesConFeedbackNegativo.length}). Se necesitan al menos ${MINIMO_CONVERSACIONES} conversaciones.\n\nÂ¿Deseas continuar de todas formas? El proceso fallarÃ¡ si quedan menos de ${MINIMO_CONVERSACIONES} conversaciones.`

          const continuar = window.confirm(mensaje)
          if (!continuar) {
            setPreparando(false)
            return
          }
        } else if (conversacionesConFeedbackNegativo.length > 0) {
          // Mostrar informaciÃ³n pero permitir continuar
          toast.info(
            `Se excluirÃ¡n ${conversacionesConFeedbackNegativo.length} conversaciones con feedback negativo. QuedarÃ¡n ${conversacionesDespuesFiltrado} conversaciones para entrenar.`,
            { duration: 5000 }
          )
        }
      }

      const result = await aiTrainingService.prepararDatosEntrenamiento(
        conversacionesSeleccionadas,
        filtrarFeedbackNegativo
      )
      setArchivoId(result.archivo_id)

      let mensaje = `Datos preparados: ${result.total_conversaciones} conversaciones`
      if (result.conversaciones_excluidas && result.conversaciones_excluidas > 0) {
        mensaje += ` (${result.conversaciones_excluidas} excluidas por feedback negativo)`
      }

      toast.success(mensaje)
      setMostrarFormEntrenamiento(true)

      // Recargar estadÃ­sticas despuÃ©s de preparar
      if (mostrarEstadisticas) {
        cargarEstadisticasFeedback()
      }
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

  const handleCancelarJob = async (jobId: string) => {
    if (!confirm('Â¿EstÃ¡s seguro de que deseas cancelar este job de entrenamiento?')) {
      return
    }

    try {
      await aiTrainingService.cancelarFineTuningJob(jobId)
      toast.success('Job cancelado exitosamente')
      cargarJobs()
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al cancelar job'
      toast.error(mensaje)
    }
  }

  const handleEliminarJob = async (jobId: string) => {
    if (!confirm('Â¿EstÃ¡s seguro de que deseas eliminar este job? Esta acciÃ³n no se puede deshacer.')) {
      return
    }

    try {
      await aiTrainingService.eliminarFineTuningJob(jobId)
      toast.success('Job eliminado exitosamente')
      cargarJobs()
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al eliminar job'
      toast.error(mensaje)
    }
  }

  const handleEliminarTodosJobs = async (soloFallidos: boolean = false) => {
    const mensaje = soloFallidos
      ? 'Â¿EstÃ¡s seguro de que deseas eliminar todos los jobs fallidos? Esta acciÃ³n no se puede deshacer.'
      : 'Â¿EstÃ¡s seguro de que deseas eliminar TODOS los jobs completados? Esta acciÃ³n no se puede deshacer.'

    if (!confirm(mensaje)) {
      return
    }

    try {
      const resultado = await aiTrainingService.eliminarTodosFineTuningJobs(soloFallidos)
      toast.success(resultado.mensaje)
      cargarJobs()
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al eliminar jobs'
      toast.error(mensaje)
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
      toast.success('ConversaciÃ³n creada exitosamente')
      setNuevaPregunta('')
      setNuevaRespuesta('')
      setTablaSeleccionada('')
      setCampoSeleccionado('')
      setTextareaActivo(null)
      setMostrarFormNuevaConversacion(false)
      cargarConversaciones()
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al crear conversaciÃ³n'
      toast.error(mensaje)
    } finally {
      setGuardandoConversacion(false)
    }
  }

  const handleIniciarEdicion = (conversacion: ConversacionAI) => {
    setEditandoConversacionId(conversacion.id)
    setPreguntaEditada(conversacion.pregunta)
    setRespuestaEditada(conversacion.respuesta)
  }

  const handleCancelarEdicion = () => {
    setEditandoConversacionId(null)
    setPreguntaEditada('')
    setRespuestaEditada('')
  }

  const handleGuardarEdicion = async () => {
    if (!editandoConversacionId || !preguntaEditada.trim() || !respuestaEditada.trim()) {
      toast.error('La pregunta y respuesta son requeridas')
      return
    }

    setActualizandoConversacion(true)
    try {
      await aiTrainingService.actualizarConversacion(editandoConversacionId, {
        pregunta: preguntaEditada.trim(),
        respuesta: respuestaEditada.trim(),
        modelo_usado: 'manual',
      })
      toast.success('ConversaciÃ³n actualizada exitosamente')
      handleCancelarEdicion()
      cargarConversaciones()
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al actualizar conversaciÃ³n'
      toast.error(mensaje)
    } finally {
      setActualizandoConversacion(false)
    }
  }

  const handleMejorarPregunta = async () => {
    if (!preguntaEditada.trim()) {
      toast.warning('Primero escribe una pregunta')
      return
    }

    setMejorandoPregunta(true)
    try {
      const resultado = await aiTrainingService.mejorarConversacion({
        pregunta: preguntaEditada,
        respuesta: '', // Solo mejorar pregunta
      })
      setPreguntaEditada(resultado.pregunta_mejorada)
      toast.success(`Pregunta mejorada: ${resultado.mejoras_aplicadas.join(', ')}`)
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar pregunta'
      toast.error(mensaje)
    } finally {
      setMejorandoPregunta(false)
    }
  }

  const handleMejorarRespuesta = async () => {
    if (!respuestaEditada.trim()) {
      toast.warning('Primero escribe una respuesta')
      return
    }

    setMejorandoRespuesta(true)
    try {
      const resultado = await aiTrainingService.mejorarConversacion({
        pregunta: '', // Solo mejorar respuesta
        respuesta: respuestaEditada,
      })
      setRespuestaEditada(resultado.respuesta_mejorada)
      toast.success(`Respuesta mejorada: ${resultado.mejoras_aplicadas.join(', ')}`)
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar respuesta'
      toast.error(mensaje)
    } finally {
      setMejorandoRespuesta(false)
    }
  }

  const handleMejorarConversacionCompleta = async () => {
    if (!preguntaEditada.trim() || !respuestaEditada.trim()) {
      toast.warning('Ambas pregunta y respuesta son requeridas')
      return
    }

    setMejorandoConversacion(true)
    try {
      const resultado = await aiTrainingService.mejorarConversacion({
        pregunta: preguntaEditada,
        respuesta: respuestaEditada,
      })
      setPreguntaEditada(resultado.pregunta_mejorada)
      setRespuestaEditada(resultado.respuesta_mejorada)
      toast.success(`ConversaciÃ³n mejorada: ${resultado.mejoras_aplicadas.join(', ')}`)
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar conversaciÃ³n'
      toast.error(mensaje)
    } finally {
      setMejorandoConversacion(false)
    }
  }

  // Funciones para mejorar en modo creaciÃ³n
  const handleMejorarNuevaPregunta = async () => {
    if (!nuevaPregunta.trim()) {
      toast.warning('Primero escribe una pregunta')
      return
    }

    setMejorandoPregunta(true)
    try {
      const resultado = await aiTrainingService.mejorarConversacion({
        pregunta: nuevaPregunta,
        respuesta: '',
      })
      setNuevaPregunta(resultado.pregunta_mejorada)
      toast.success(`Pregunta mejorada: ${resultado.mejoras_aplicadas.join(', ')}`)
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar pregunta'
      toast.error(mensaje)
    } finally {
      setMejorandoPregunta(false)
    }
  }

  const handleMejorarNuevaRespuesta = async () => {
    if (!nuevaRespuesta.trim()) {
      toast.warning('Primero escribe una respuesta')
      return
    }

    setMejorandoRespuesta(true)
    try {
      const resultado = await aiTrainingService.mejorarConversacion({
        pregunta: '',
        respuesta: nuevaRespuesta,
      })
      setNuevaRespuesta(resultado.respuesta_mejorada)
      toast.success(`Respuesta mejorada: ${resultado.mejoras_aplicadas.join(', ')}`)
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar respuesta'
      toast.error(mensaje)
    } finally {
      setMejorandoRespuesta(false)
    }
  }

  const handleMejorarNuevaConversacionCompleta = async () => {
    if (!nuevaPregunta.trim() || !nuevaRespuesta.trim()) {
      toast.warning('Ambas pregunta y respuesta son requeridas')
      return
    }

    setMejorandoConversacion(true)
    try {
      const resultado = await aiTrainingService.mejorarConversacion({
        pregunta: nuevaPregunta,
        respuesta: nuevaRespuesta,
      })
      setNuevaPregunta(resultado.pregunta_mejorada)
      setNuevaRespuesta(resultado.respuesta_mejorada)
      toast.success(`ConversaciÃ³n mejorada: ${resultado.mejoras_aplicadas.join(', ')}`)
    } catch (error: any) {
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar conversaciÃ³n'
      toast.error(mensaje)
    } finally {
      setMejorandoConversacion(false)
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
      toast.error('Error al leer el archivo. Verifica que sea un JSON vÃ¡lido.')
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

      {/* EstadÃ­sticas de Feedback */}
      {mostrarEstadisticas && estadisticasFeedback && (
        <Card className="bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold text-lg flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-purple-600" />
                EstadÃ­sticas de Feedback
              </h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMostrarEstadisticas(false)}
              >
                <XCircle className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <div className="bg-white rounded-lg p-4 border">
                <div className="text-sm text-gray-600 mb-1">Total Conversaciones</div>
                <div className="text-2xl font-bold text-gray-900">{estadisticasFeedback.total_conversaciones}</div>
              </div>
              <div className="bg-white rounded-lg p-4 border">
                <div className="text-sm text-gray-600 mb-1">Calificadas</div>
                <div className="text-2xl font-bold text-blue-600">{estadisticasFeedback.conversaciones_calificadas}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {((estadisticasFeedback.conversaciones_calificadas / estadisticasFeedback.total_conversaciones) * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-white rounded-lg p-4 border">
                <div className="text-sm text-gray-600 mb-1">Con Feedback</div>
                <div className="text-2xl font-bold text-purple-600">{estadisticasFeedback.conversaciones_con_feedback}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {estadisticasFeedback.conversaciones_calificadas > 0
                    ? ((estadisticasFeedback.conversaciones_con_feedback / estadisticasFeedback.conversaciones_calificadas) * 100).toFixed(1)
                    : 0}% de calificadas
                </div>
              </div>
              <div className="bg-white rounded-lg p-4 border">
                <div className="text-sm text-gray-600 mb-1">Listas para Entrenar</div>
                <div className="text-2xl font-bold text-green-600">
                  {estadisticasFeedback.conversaciones_listas_entrenamiento.sin_feedback_negativo}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {estadisticasFeedback.conversaciones_listas_entrenamiento.con_feedback_negativo > 0 && (
                    <span className="text-red-600">
                      {estadisticasFeedback.conversaciones_listas_entrenamiento.con_feedback_negativo} excluidas
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* AnÃ¡lisis de Feedback */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="h-4 w-4 text-green-600" />
                  <div className="text-sm font-semibold text-green-800">Feedback Positivo</div>
                </div>
                <div className="text-2xl font-bold text-green-700">
                  {estadisticasFeedback.analisis_feedback.positivo}
                </div>
                <div className="text-xs text-green-600 mt-1">
                  {estadisticasFeedback.analisis_feedback.total > 0
                    ? ((estadisticasFeedback.analisis_feedback.positivo / estadisticasFeedback.analisis_feedback.total) * 100).toFixed(1)
                    : 0}% del total
                </div>
              </div>

              <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingDown className="h-4 w-4 text-red-600" />
                  <div className="text-sm font-semibold text-red-800">Feedback Negativo</div>
                </div>
                <div className="text-2xl font-bold text-red-700">
                  {estadisticasFeedback.analisis_feedback.negativo}
                </div>
                <div className="text-xs text-red-600 mt-1">
                  {estadisticasFeedback.analisis_feedback.total > 0
                    ? ((estadisticasFeedback.analisis_feedback.negativo / estadisticasFeedback.analisis_feedback.total) * 100).toFixed(1)
                    : 0}% del total
                </div>
                {filtrarFeedbackNegativo && (
                  <div className="text-xs text-red-700 mt-2 font-semibold">
                    âš ï¸ Estas conversaciones se excluirÃ¡n automÃ¡ticamente
                  </div>
                )}
              </div>

              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center gap-2 mb-2">
                  <Info className="h-4 w-4 text-gray-600" />
                  <div className="text-sm font-semibold text-gray-800">Feedback Neutro</div>
                </div>
                <div className="text-2xl font-bold text-gray-700">
                  {estadisticasFeedback.analisis_feedback.neutro}
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  {estadisticasFeedback.analisis_feedback.total > 0
                    ? ((estadisticasFeedback.analisis_feedback.neutro / estadisticasFeedback.analisis_feedback.total) * 100).toFixed(1)
                    : 0}% del total
                </div>
              </div>
            </div>

            {/* DistribuciÃ³n de Calificaciones */}
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-sm font-semibold mb-3">DistribuciÃ³n de Calificaciones</div>
              <div className="flex items-end gap-2 h-32">
                {[1, 2, 3, 4, 5].map((star) => {
                  const cantidad = estadisticasFeedback.distribucion_calificaciones[star] || 0
                  const maxCantidad = Math.max(...Object.values(estadisticasFeedback.distribucion_calificaciones).map(Number), 1)
                  const altura = (cantidad / maxCantidad) * 100

                  return (
                    <div key={star} className="flex-1 flex flex-col items-center">
                      <div className="w-full bg-gray-200 rounded-t relative" style={{ height: '100px' }}>
                        <div
                          className={`absolute bottom-0 w-full rounded-t ${
                            star >= 4 ? 'bg-green-500' : star >= 3 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ height: `${altura}%` }}
                        />
                      </div>
                      <div className="mt-2 text-xs font-semibold">{star}â­</div>
                      <div className="text-xs text-gray-600">{cantidad}</div>
                    </div>
                  )
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* GuÃ­a de uso */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-blue-600" />
              Â¿CÃ³mo usar Fine-tuning?
            </h4>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (!mostrarEstadisticas) {
                  cargarEstadisticasFeedback()
                }
                setMostrarEstadisticas(!mostrarEstadisticas)
              }}
            >
              {mostrarEstadisticas ? (
                <>
                  <XCircle className="h-4 w-4 mr-2" />
                  Ocultar EstadÃ­sticas
                </>
              ) : (
                <>
                  <BarChart3 className="h-4 w-4 mr-2" />
                  Ver EstadÃ­sticas
                </>
              )}
            </Button>
          </div>
          <div className="space-y-2 text-sm text-gray-700">
            <div className="flex items-start gap-2">
              <span className="font-semibold text-blue-600">1.</span>
              <div>
                <strong>Agregar conversaciones:</strong> Usa "Nueva ConversaciÃ³n" para crear manualmente o "Importar desde JSON" para cargar mÃºltiples conversaciones.
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="font-semibold text-blue-600">2.</span>
              <div>
                <strong>Calificar conversaciones:</strong> Para cada conversaciÃ³n, califica con 1-5 estrellas. Solo las conversaciones con 4+ estrellas se usarÃ¡n para entrenar.
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="font-semibold text-blue-600">3.</span>
              <div>
                <strong>Preparar datos:</strong> Necesitas al menos 1 conversaciÃ³n calificada (4+ estrellas). Luego haz clic en "Preparar Datos para Entrenamiento".
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
                <SelectValue placeholder="CalificaciÃ³n" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas</SelectItem>
                <SelectItem value="con_calificacion">Con calificaciÃ³n</SelectItem>
                <SelectItem value="sin_calificacion">Sin calificaciÃ³n</SelectItem>
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

      {/* Formulario para crear conversaciÃ³n manual */}
      {mostrarFormNuevaConversacion && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold">Nueva ConversaciÃ³n</h4>
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
                      Ãšltima actualizaciÃ³n: {new Date(ultimaActualizacion).toLocaleString('es-ES')}
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
                    ðŸ’¡ Tip: Haz clic en el campo de Pregunta o Respuesta donde quieras insertar, luego selecciona la tabla/campo y presiona Insertar.
                  </p>
                </CardContent>
              </Card>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium">Pregunta *</label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleMejorarNuevaPregunta}
                    disabled={mejorandoPregunta || !nuevaPregunta.trim()}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    {mejorandoPregunta ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        Mejorando...
                      </>
                    ) : (
                      <>
                        <Zap className="h-3 w-3 mr-1" />
                        Mejorar con IA
                      </>
                    )}
                  </Button>
                </div>
                <Textarea
                  ref={preguntaTextareaRef}
                  placeholder="Ej: Â¿CuÃ¡l es el proceso para solicitar un prÃ©stamo?"
                  value={nuevaPregunta}
                  onChange={(e) => setNuevaPregunta(e.target.value)}
                  onFocus={() => setTextareaActivo('pregunta')}
                  rows={3}
                />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium">Respuesta *</label>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={handleMejorarNuevaRespuesta}
                      disabled={mejorandoRespuesta || !nuevaRespuesta.trim()}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      {mejorandoRespuesta ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Mejorando...
                        </>
                      ) : (
                        <>
                          <Zap className="h-3 w-3 mr-1" />
                          Mejorar
                        </>
                      )}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={handleMejorarNuevaConversacionCompleta}
                      disabled={mejorandoConversacion || !nuevaPregunta.trim() || !nuevaRespuesta.trim()}
                      className="text-purple-600 hover:text-purple-700"
                    >
                      {mejorandoConversacion ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Mejorando...
                        </>
                      ) : (
                        <>
                          <Zap className="h-3 w-3 mr-1" />
                          Mejorar Todo
                        </>
                      )}
                    </Button>
                  </div>
                </div>
                <Textarea
                  ref={respuestaTextareaRef}
                  placeholder="Ej: Para solicitar un prÃ©stamo necesitas..."
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
                      Guardar ConversaciÃ³n
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
                {mostrarFormNuevaConversacion ? 'Ocultar Formulario' : 'Nueva ConversaciÃ³n'}
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
              {(() => {
                const conversacionesListas = conversaciones.filter((c) => c.calificacion && c.calificacion >= 4)
                const totalListas = conversacionesListas.length
                const MINIMO_REQUERIDO = 10

                // Calcular impacto del filtrado de feedback negativo
                let conversacionesConFeedbackNegativo = 0
                let conversacionesDespuesFiltrado = totalListas
                if (filtrarFeedbackNegativo && totalListas > 0) {
                  conversacionesConFeedbackNegativo = conversacionesListas.filter(c =>
                    detectarFeedbackNegativo(c.feedback || null)
                  ).length
                  conversacionesDespuesFiltrado = totalListas - conversacionesConFeedbackNegativo
                }

                const puedePreparar = totalListas >= MINIMO_REQUERIDO
                const puedePrepararDespuesFiltrado = conversacionesDespuesFiltrado >= MINIMO_REQUERIDO

                return (
                  <div className="flex items-center gap-2 flex-wrap">
                    {totalListas > 0 && (
                      <Badge variant={puedePreparar ? "default" : "secondary"} className="mr-2">
                        {totalListas} lista{totalListas !== 1 ? 's' : ''} para entrenamiento
                        {!puedePreparar && totalListas < MINIMO_REQUERIDO && ` (${MINIMO_REQUERIDO - totalListas} mÃ¡s necesaria${MINIMO_REQUERIDO - totalListas !== 1 ? 's' : ''})`}
                      </Badge>
                    )}
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-gray-600 flex items-center gap-1">
                        <input
                          type="checkbox"
                          checked={filtrarFeedbackNegativo}
                          onChange={(e) => setFiltrarFeedbackNegativo(e.target.checked)}
                          className="rounded"
                        />
                        Filtrar feedback negativo
                      </label>
                      {filtrarFeedbackNegativo && totalListas > 0 && conversacionesConFeedbackNegativo > 0 && (
                        <Badge
                          variant={puedePrepararDespuesFiltrado ? "outline" : "destructive"}
                          className="text-xs"
                        >
                          {conversacionesConFeedbackNegativo} excluidas â†’ {conversacionesDespuesFiltrado} disponibles
                          {!puedePrepararDespuesFiltrado && ` (necesitas ${MINIMO_REQUERIDO - conversacionesDespuesFiltrado} mÃ¡s)`}
                        </Badge>
                      )}
                    </div>
                    <Button
                      onClick={handlePrepararDatos}
                      disabled={preparando || !puedePreparar}
                      variant={puedePreparar ? "default" : "outline"}
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
                )
              })()}
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
                  {editandoConversacionId === conv.id ? (
                    // Modo ediciÃ³n
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h5 className="font-semibold text-blue-600">Editando conversaciÃ³n</h5>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleCancelarEdicion}
                          disabled={actualizandoConversacion}
                        >
                          <XCircle className="h-4 w-4" />
                        </Button>
                      </div>

                      {/* Selector de Tablas y Campos (tambiÃ©n disponible en ediciÃ³n) */}
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
                              Ãšltima actualizaciÃ³n: {new Date(ultimaActualizacion).toLocaleString('es-ES')}
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
                                  onClick={() => {
                                    if (textareaActivo === 'pregunta') {
                                      insertarEnTextarea(tablaSeleccionada, preguntaEditada, setPreguntaEditada, preguntaEditadaRef)
                                    } else if (textareaActivo === 'respuesta') {
                                      insertarEnTextarea(tablaSeleccionada, respuestaEditada, setRespuestaEditada, respuestaEditadaRef)
                                    }
                                  }}
                                  disabled={!tablaSeleccionada || !textareaActivo}
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
                                  onClick={() => {
                                    if (textareaActivo === 'pregunta') {
                                      insertarEnTextarea(campoSeleccionado, preguntaEditada, setPreguntaEditada, preguntaEditadaRef)
                                    } else if (textareaActivo === 'respuesta') {
                                      insertarEnTextarea(campoSeleccionado, respuestaEditada, setRespuestaEditada, respuestaEditadaRef)
                                    }
                                  }}
                                  disabled={!campoSeleccionado || !textareaActivo}
                                  className="shrink-0"
                                >
                                  <Plus className="h-4 w-4 mr-1" />
                                  Insertar
                                </Button>
                              </div>
                            </div>
                          </div>
                          <p className="text-xs text-gray-500 mt-3">
                            ðŸ’¡ Tip: Haz clic en el campo de Pregunta o Respuesta donde quieras insertar, luego selecciona la tabla/campo y presiona Insertar.
                          </p>
                        </CardContent>
                      </Card>

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-sm font-medium">Pregunta *</label>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={handleMejorarPregunta}
                            disabled={mejorandoPregunta || !preguntaEditada.trim()}
                            className="text-blue-600 hover:text-blue-700"
                          >
                            {mejorandoPregunta ? (
                              <>
                                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                Mejorando...
                              </>
                            ) : (
                              <>
                                <Zap className="h-3 w-3 mr-1" />
                                Mejorar con IA
                              </>
                            )}
                          </Button>
                        </div>
                        <Textarea
                          ref={preguntaEditadaRef}
                          placeholder="Ej: Â¿QuÃ© es total_financiamiento en la tabla prestamos?"
                          value={preguntaEditada}
                          onChange={(e) => setPreguntaEditada(e.target.value)}
                          onFocus={() => setTextareaActivo('pregunta')}
                          rows={3}
                        />
                      </div>
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-sm font-medium">Respuesta *</label>
                          <div className="flex gap-2">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={handleMejorarRespuesta}
                              disabled={mejorandoRespuesta || !respuestaEditada.trim()}
                              className="text-blue-600 hover:text-blue-700"
                            >
                              {mejorandoRespuesta ? (
                                <>
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                  Mejorando...
                                </>
                              ) : (
                                <>
                                  <Zap className="h-3 w-3 mr-1" />
                                  Mejorar
                                </>
                              )}
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={handleMejorarConversacionCompleta}
                              disabled={mejorandoConversacion || !preguntaEditada.trim() || !respuestaEditada.trim()}
                              className="text-purple-600 hover:text-purple-700"
                            >
                              {mejorandoConversacion ? (
                                <>
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                  Mejorando...
                                </>
                              ) : (
                                <>
                                  <Zap className="h-3 w-3 mr-1" />
                                  Mejorar Todo
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                        <Textarea
                          ref={respuestaEditadaRef}
                          placeholder="Ej: En la tabla prestamos, el campo total_financiamiento representa..."
                          value={respuestaEditada}
                          onChange={(e) => setRespuestaEditada(e.target.value)}
                          onFocus={() => setTextareaActivo('respuesta')}
                          rows={5}
                        />
                      </div>
                      <div className="flex gap-2">
                        <Button
                          onClick={handleGuardarEdicion}
                          disabled={actualizandoConversacion || !preguntaEditada.trim() || !respuestaEditada.trim()}
                          size="sm"
                        >
                          {actualizandoConversacion ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Guardando...
                            </>
                          ) : (
                            <>
                              <Save className="h-4 w-4 mr-2" />
                              Guardar Cambios
                            </>
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            handleCancelarEdicion()
                            setTablaSeleccionada('')
                            setCampoSeleccionado('')
                            setTextareaActivo(null)
                          }}
                          disabled={actualizandoConversacion}
                          size="sm"
                        >
                          Cancelar
                        </Button>
                      </div>
                    </div>
                  ) : (
                    // Modo visualizaciÃ³n
                    <>
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
                        <div className="ml-4 flex flex-col gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleIniciarEdicion(conv)}
                            className="text-blue-600 hover:text-blue-700"
                          >
                            <Edit className="h-4 w-4 mr-1" />
                            Editar
                          </Button>
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
                    </>
                  )}

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
                          'Guardar CalificaciÃ³n'
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
                    <SelectItem value="gpt-4o-2024-08-06">gpt-4o-2024-08-06 (Recomendado - VersiÃ³n especÃ­fica)</SelectItem>
                    <SelectItem value="gpt-4o">gpt-4o (Puede no estar disponible)</SelectItem>
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
            <div className="flex gap-2">
              {jobs.some(job => job.status === 'failed' || job.status === 'cancelled') && (
                <Button
                  onClick={() => handleEliminarTodosJobs(true)}
                  variant="outline"
                  size="sm"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Eliminar Fallidos
                </Button>
              )}
              {jobs.some(job => job.status !== 'pending' && job.status !== 'running') && (
                <Button
                  onClick={() => handleEliminarTodosJobs(false)}
                  variant="outline"
                  size="sm"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Limpiar Todo
                </Button>
              )}
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
          </div>
          {jobs.some(job => job.status === 'pending' || job.status === 'running') && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-blue-600 mt-0.5" />
                <div className="text-xs text-blue-800">
                  <strong>â±ï¸ Tiempos tÃ­picos de entrenamiento:</strong>
                  <ul className="mt-1 ml-4 list-disc space-y-0.5">
                    <li><strong>gpt-4o:</strong> 2-4 horas (depende del tamaÃ±o del archivo)</li>
                  </ul>
                  <p className="mt-1 text-blue-600">
                    <strong>âš ï¸ Nota:</strong> Para fine-tuning, se recomienda usar <code className="bg-blue-100 px-1 rounded">gpt-4o-2024-08-06</code> (versiÃ³n especÃ­fica). gpt-3.5-turbo y gpt-4o-mini no soportan fine-tuning.
                  </p>
                  <p className="mt-2 text-blue-700">
                    El sistema actualiza automÃ¡ticamente el estado cada 10 segundos. Los jobs pueden tardar mÃ¡s tiempo si OpenAI tiene alta demanda.
                  </p>
                </div>
              </div>
            </div>
          )}

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
              {jobs.map((job) => {
                // Calcular tiempo transcurrido (usar tiempoActual para actualizaciÃ³n en tiempo real)
                const fechaCreacion = new Date(job.creado_en)
                const ahora = tiempoActual
                const tiempoTranscurridoMs = ahora.getTime() - fechaCreacion.getTime()
                const minutosTranscurridos = Math.floor(tiempoTranscurridoMs / 60000)
                const horasTranscurridas = Math.floor(minutosTranscurridos / 60)

                // Formatear tiempo transcurrido
                let tiempoTranscurridoTexto = ''
                if (horasTranscurridas > 0) {
                  tiempoTranscurridoTexto = `${horasTranscurridas}h ${minutosTranscurridos % 60}m`
                } else {
                  tiempoTranscurridoTexto = `${minutosTranscurridos}m`
                }

                // Tiempo estimado segÃºn modelo base
                const tiempoEstimado = '2-4 horas'  // gpt-4o tÃ­picamente toma 2-4 horas

                // Verificar si el job usa un modelo obsoleto
                const modeloObsoleto = job.modelo_base === 'gpt-3.5-turbo' || job.modelo_base === 'gpt-4o-mini'

                return (
                <div key={job.id} className={`border rounded-lg p-4 ${modeloObsoleto ? 'bg-yellow-50 border-yellow-200' : ''}`}>
                  {modeloObsoleto && (
                    <div className="mb-3 p-2 bg-yellow-100 border border-yellow-300 rounded text-xs">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="h-4 w-4 text-yellow-700 mt-0.5 flex-shrink-0" />
                        <div className="text-yellow-800">
                          <strong>âš ï¸ Modelo obsoleto:</strong> Este job usa <code className="bg-yellow-200 px-1 rounded">{job.modelo_base}</code>, que ya no estÃ¡ disponible para fine-tuning.
                          Los nuevos jobs usarÃ¡n <code className="bg-yellow-200 px-1 rounded">gpt-4o</code> automÃ¡ticamente.
                        </div>
                      </div>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium">Job ID: {job.id}</span>
                        {getStatusBadge(job.status)}
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        <div>Modelo Base: <span className={modeloObsoleto ? 'text-yellow-700 font-semibold' : ''}>{job.modelo_base}</span></div>
                        {job.modelo_entrenado && (
                          <div>Modelo Entrenado: {job.modelo_entrenado}</div>
                        )}
                        {job.progreso !== undefined && job.progreso !== null && (
                          <div>Progreso: {job.progreso.toFixed(1)}%</div>
                        )}
                        {(job.status === 'pending' || job.status === 'running') && (
                          <div className="flex items-center gap-2 mt-2">
                            <Clock className="h-3 w-3 text-gray-400" />
                            <span className="text-xs text-gray-500">
                              Tiempo transcurrido: <strong>{tiempoTranscurridoTexto}</strong>
                              {job.status === 'running' && minutosTranscurridos < 30 && (
                                <span className="ml-2 text-blue-600">
                                  (TÃ­pico: {tiempoEstimado})
                                </span>
                              )}
                            </span>
                          </div>
                        )}
                        {job.error && (
                          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs">
                            <div className="font-semibold text-red-800 mb-1 flex items-center gap-1">
                              <AlertCircle className="h-3 w-3" />
                              Error:
                            </div>
                            <div className="text-red-700 whitespace-pre-wrap break-words">
                              {typeof job.error === 'string'
                                ? job.error
                                : JSON.stringify(job.error, null, 2)}
                            </div>
                          </div>
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
                    <div className="flex gap-2">
                      {(job.status === 'pending' || job.status === 'running') && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleCancelarJob(job.id)}
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          Cancelar
                        </Button>
                      )}
                      {job.status === 'succeeded' && job.modelo_entrenado && (
                        <Button
                          size="sm"
                          onClick={() => handleActivarModelo(job.modelo_entrenado!)}
                        >
                          Activar Modelo
                        </Button>
                      )}
                      {(job.status === 'failed' || job.status === 'cancelled' || (job.status === 'succeeded' && !job.modelo_entrenado)) && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => handleEliminarJob(job.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          Eliminar
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

