import { useState, useEffect, useRef, useCallback } from 'react'
import { aiTrainingService, ConversacionAI, FineTuningJob } from '../services/aiTrainingService'
import { toast } from 'sonner'
import { MINIMO_CONVERSACIONES_ENTRENAMIENTO, detectarFeedbackNegativo } from '../constants/fineTuning'

export interface UseFineTuningReturn {
  // State
  conversaciones: ConversacionAI[]
  jobs: FineTuningJob[]
  estadisticasFeedback: any
  cargando: boolean
  cargandoJobs: boolean
  cargandoEstadisticas: boolean
  tiempoActual: Date
  tablasYCampos: Record<string, string[]>
  cargandoTablasCampos: boolean
  ultimaActualizacion: string

  // Handlers
  handlers: {
    // Conversaciones
    cargarConversaciones: (params?: any) => Promise<void>
    cargarJobs: () => Promise<void>
    cargarEstadisticasFeedback: () => Promise<void>
    cargarTablasCampos: () => Promise<void>

    // Rating
    calificar: (conversacionId: number, calificacion: number, feedback: string) => Promise<void>

    // CRUD
    crearConversacion: (pregunta: string, respuesta: string) => Promise<void>
    actualizarConversacion: (conversacionId: number, pregunta: string, respuesta: string) => Promise<void>
    eliminarConversacion: (conversacionId: number) => Promise<void>

    // AI Enhancement
    mejorarPregunta: (pregunta: string) => Promise<string>
    mejorarRespuesta: (respuesta: string) => Promise<string>
    mejorarConversacionCompleta: (pregunta: string, respuesta: string) => Promise<{ pregunta: string; respuesta: string }>

    // Training
    prepararDatos: (conversacionesIds: number[], soloCalificadas: boolean) => Promise<void>
    iniciarEntrenamiento: (modeloBase: string, archivoId: string) => Promise<void>
    activarModelo: (modeloId: string) => Promise<void>
    cancelarJob: (jobId: string) => Promise<void>
    eliminarJob: (jobId: string) => Promise<void>
    eliminarTodosJobs: (soloFallidos: boolean) => Promise<void>

    // Import/Export
    exportarConversaciones: () => void
    importarConversaciones: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>
  }
}

export function useFineTuning(): UseFineTuningReturn {
  // Main state
  const [conversaciones, setConversaciones] = useState<ConversacionAI[]>([])
  const [cargando, setCargando] = useState(false)
  const [jobs, setJobs] = useState<FineTuningJob[]>([])
  const [cargandoJobs, setCargandoJobs] = useState(false)
  const [tiempoActual, setTiempoActual] = useState(new Date())

  // Statistics state
  const [estadisticasFeedback, setEstadisticasFeedback] = useState<any>(null)
  const [cargandoEstadisticas, setCargandoEstadisticas] = useState(false)

  // Tables and fields state
  const [tablasYCampos, setTablasYCampos] = useState<Record<string, string[]>>({})
  const [cargandoTablasCampos, setCargandoTablasCampos] = useState(false)
  const [ultimaActualizacion, setUltimaActualizacion] = useState<string>('')

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Load conversations
  const cargarConversaciones = useCallback(
    async (params: any = {}) => {
      setCargando(true)
      try {
        const data = await aiTrainingService.getConversaciones(params)
        setConversaciones(data.conversaciones)
      } catch (error: any) {
        console.error('Error cargando conversaciones:', error)
        toast.error('Error al cargar conversaciones')
      } finally {
        setCargando(false)
      }
    },
    []
  )

  // Load jobs
  const cargarJobs = useCallback(async () => {
    setCargandoJobs(true)
    try {
      const data = await aiTrainingService.listarFineTuningJobs()
      setJobs(data)
    } catch (error: any) {
      console.error('Error cargando jobs:', error)
      toast.error('Error al cargar jobs')
    } finally {
      setCargandoJobs(false)
    }
  }, [])

  // Load feedback statistics
  const cargarEstadisticasFeedback = useCallback(async () => {
    setCargandoEstadisticas(true)
    try {
      const stats = await aiTrainingService.getEstadisticasFeedback()
      setEstadisticasFeedback(stats)
    } catch (error: any) {
      console.error('Error cargando estadísticas:', error)
      toast.error('Error al cargar estadísticas')
    } finally {
      setCargandoEstadisticas(false)
    }
  }, [])

  // Load tables and fields
  const cargarTablasCampos = useCallback(async () => {
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
  }, [])

  // Rating handler
  const calificar = useCallback(
    async (conversacionId: number, calificacion: number, feedback: string) => {
      try {
        await aiTrainingService.calificarConversacion(conversacionId, calificacion, feedback)
        toast.success('Conversación calificada exitosamente')

        const conversacionesCalificadas = conversaciones.filter((c) => c.calificacion && c.calificacion >= 3)
        setEstadisticasFeedback({
          ...estadisticasFeedback,
          conversaciones_calificadas: conversacionesCalificadas.length,
        })

        cargarConversaciones()
      } catch (error: any) {
        console.error('Error calificando:', error)
        const mensaje = error?.response?.data?.detail || error?.message || 'Error al calificar conversación'
        toast.error(mensaje)
      }
    },
    [conversaciones, estadisticasFeedback, cargarConversaciones]
  )

  // Create conversation
  const crearConversacion = useCallback(
    async (pregunta: string, respuesta: string) => {
      try {
        await aiTrainingService.guardarConversacion({
          pregunta,
          respuesta,
          modelo_usado: 'manual',
        })
        toast.success('Conversación creada exitosamente')
        cargarConversaciones()
      } catch (error: any) {
        console.error('Error creando conversación:', error)
        const mensaje = error?.response?.data?.detail || error?.message || 'Error al crear conversación'
        toast.error(mensaje)
      }
    },
    [cargarConversaciones]
  )

  // Update conversation
  const actualizarConversacion = useCallback(
    async (conversacionId: number, pregunta: string, respuesta: string) => {
      try {
        await aiTrainingService.actualizarConversacion(conversacionId, {
          pregunta,
          respuesta,
        })
        toast.success('Conversación actualizada exitosamente')
        cargarConversaciones()
      } catch (error: any) {
        console.error('Error actualizando conversación:', error)
        const mensaje = error?.response?.data?.detail || error?.message || 'Error al actualizar conversación'
        toast.error(mensaje)
      }
    },
    [cargarConversaciones]
  )

  // Delete conversation
  const eliminarConversacion = useCallback(
    async (conversacionId: number) => {
      try {
        await aiTrainingService.eliminarConversacion(conversacionId)
        toast.success('Conversación eliminada exitosamente')
        cargarConversaciones()
      } catch (error: any) {
        console.error('Error eliminando conversación:', error)
        const mensaje = error?.response?.data?.detail || error?.message || 'Error al eliminar conversación'
        toast.error(mensaje)
      }
    },
    [cargarConversaciones]
  )

  // AI Enhancement - Improve question
  const mejorarPregunta = useCallback(async (pregunta: string): Promise<string> => {
    try {
      const resultado = await aiTrainingService.mejorarConversacion({
        tipo: 'pregunta',
        pregunta,
      })
      return resultado.pregunta_mejorada
    } catch (error: any) {
      console.error('Error mejorando pregunta:', error)
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar pregunta'
      toast.error(mensaje)
      throw error
    }
  }, [])

  // AI Enhancement - Improve response
  const mejorarRespuesta = useCallback(async (respuesta: string): Promise<string> => {
    try {
      const resultado = await aiTrainingService.mejorarConversacion({
        tipo: 'respuesta',
        respuesta,
      })
      return resultado.respuesta_mejorada
    } catch (error: any) {
      console.error('Error mejorando respuesta:', error)
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar respuesta'
      toast.error(mensaje)
      throw error
    }
  }, [])

  // AI Enhancement - Improve complete conversation
  const mejorarConversacionCompleta = useCallback(
    async (pregunta: string, respuesta: string): Promise<{ pregunta: string; respuesta: string }> => {
      try {
        const resultado = await aiTrainingService.mejorarConversacion({
          tipo: 'conversacion',
          pregunta,
          respuesta,
        })
        return {
          pregunta: resultado.pregunta_mejorada,
          respuesta: resultado.respuesta_mejorada,
        }
      } catch (error: any) {
        console.error('Error mejorando conversación:', error)
        const mensaje = error?.response?.data?.detail || error?.message || 'Error al mejorar conversación'
        toast.error(mensaje)
        throw error
      }
    },
    []
  )

  // Prepare data for training
  const prepararDatos = useCallback(
    async (conversacionesIds: number[], soloCalificadas: boolean) => {
      try {
        const result = await aiTrainingService.prepararDatosEntrenamiento(
          conversacionesIds,
          soloCalificadas
        )

        if (result.archivo_id && result.total_conversaciones) {
          toast.success(
            `Datos preparados exitosamente: ${result.total_conversaciones} conversaciones en archivo ${result.archivo_id}`
          )
          cargarConversaciones()
        }
      } catch (error: any) {
        console.error('Error preparando datos:', error)
        const mensajeError =
          error?.response?.data?.detail || error?.message || 'Error preparando los datos para entrenamiento'
        toast.error(mensajeError)
        throw error
      }
    },
    [cargarConversaciones]
  )

  // Start fine-tuning
  const iniciarEntrenamiento = useCallback(
    async (modeloBase: string, archivoId: string) => {
      try {
        const job = await aiTrainingService.iniciarFineTuning({
          modelo_base: modeloBase,
          archivo_id: archivoId,
        })
        toast.success(`Entrenamiento iniciado. Job ID: ${job.id}`)
        cargarJobs()
      } catch (error: any) {
        console.error('Error iniciando entrenamiento:', error)
        const mensaje = error?.response?.data?.detail || error?.message || 'Error al iniciar entrenamiento'
        toast.error(mensaje)
        throw error
      }
    },
    [cargarJobs]
  )

  // Activate model
  const activarModelo = useCallback(async (modeloId: string) => {
    try {
      await aiTrainingService.activarModelo(modeloId)
      toast.success('Modelo activado exitosamente')
      cargarJobs()
    } catch (error: any) {
      console.error('Error activando modelo:', error)
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al activar modelo'
      toast.error(mensaje)
    }
  }, [cargarJobs])

  // Cancel job
  const cancelarJob = useCallback(async (jobId: string) => {
    try {
      await aiTrainingService.cancelarFineTuningJob(jobId)
      toast.success('Job cancelado exitosamente')
      cargarJobs()
    } catch (error: any) {
      console.error('Error cancelando job:', error)
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al cancelar job'
      toast.error(mensaje)
    }
  }, [cargarJobs])

  // Delete job
  const eliminarJob = useCallback(async (jobId: string) => {
    try {
      await aiTrainingService.eliminarFineTuningJob(jobId)
      toast.success('Job eliminado exitosamente')
      cargarJobs()
    } catch (error: any) {
      console.error('Error eliminando job:', error)
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al eliminar job'
      toast.error(mensaje)
    }
  }, [cargarJobs])

  // Delete all jobs
  const eliminarTodosJobs = useCallback(
    async (soloFallidos: boolean = false) => {
      try {
        const resultado = await aiTrainingService.eliminarTodosFineTuningJobs(soloFallidos)
        toast.success(`${resultado.eliminados} jobs eliminados exitosamente`)
        cargarJobs()
      } catch (error: any) {
        console.error('Error eliminando jobs:', error)
        const mensaje = error?.response?.data?.detail || error?.message || 'Error al eliminar jobs'
        toast.error(mensaje)
      }
    },
    [cargarJobs]
  )

  // Export conversations
  const exportarConversaciones = useCallback(() => {
    const datos = conversaciones.map((c) => ({
      pregunta: c.pregunta,
      respuesta: c.respuesta,
      modelo_usado: c.modelo_usado || 'unknown',
      tokens_usados: c.tokens_usados || 0,
      calificacion: c.calificacion || null,
      feedback: c.feedback || '',
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
  }, [conversaciones])

  // Import conversations
  const importarConversaciones = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (!file) return

      try {
        const text = await file.text()
        const datos = JSON.parse(text)

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
          toast.success(
            `${importadas} conversaciones importadas exitosamente${errores > 0 ? ` (${errores} errores)` : ''}`
          )
          cargarConversaciones()
        } else {
          toast.error('No se pudieron importar conversaciones')
        }

        // Clean up input
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      } catch (error: any) {
        toast.error('Error al leer el archivo. Verifica que sea un JSON válido.')
      }
    },
    [cargarConversaciones]
  )

  // Setup polling for time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setTiempoActual(new Date())
    }, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [])

  // Setup polling for jobs
  useEffect(() => {
    const interval = setInterval(() => {
      cargarJobs()
    }, 10000) // Poll every 10 seconds

    return () => clearInterval(interval)
  }, [cargarJobs])

  return {
    conversaciones,
    jobs,
    estadisticasFeedback,
    cargando,
    cargandoJobs,
    cargandoEstadisticas,
    tiempoActual,
    tablasYCampos,
    cargandoTablasCampos,
    ultimaActualizacion,
    handlers: {
      cargarConversaciones,
      cargarJobs,
      cargarEstadisticasFeedback,
      cargarTablasCampos,
      calificar,
      crearConversacion,
      actualizarConversacion,
      eliminarConversacion,
      mejorarPregunta,
      mejorarRespuesta,
      mejorarConversacionCompleta,
      prepararDatos,
      iniciarEntrenamiento,
      activarModelo,
      cancelarJob,
      eliminarJob,
      eliminarTodosJobs,
      exportarConversaciones,
      importarConversaciones,
    },
  }
}
