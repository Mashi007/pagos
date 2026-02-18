import { useState, useEffect, useRef, useCallback } from 'react'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'

export interface AIConfigState {
  configured?: boolean
  provider?: string
  openai_api_key?: string
  modelo_recomendado?: string
  modelo?: string
  temperatura?: string
  max_tokens?: string
  activo?: string
}

export interface DocumentoAI {
  id: number
  titulo: string
  descripcion?: string
  archivo_url?: string
  archivo_nombre?: string
  tamaño?: number
  contenido_procesado?: boolean
  contenido_texto?: string
  usuario_creacion?: string
  fecha_creacion?: string
  activo?: boolean
}

export interface MensajeChatAI {
  id: string
  tipo: 'user' | 'ai'
  texto: string
  timestamp: Date
  metadata?: {
    tokens?: number
    tiempo?: number
    modelo?: string
    documentos?: number
  }
}

export function useAIConfig() {
  // Configuration state
  const [config, setConfig] = useState<AIConfigState>({
    modelo: 'openai/gpt-4o-mini',
    temperatura: '0.7',
    max_tokens: '1000',
    activo: 'false',
  })

  const [guardando, setGuardando] = useState(false)
  const [documentos, setDocumentos] = useState<DocumentoAI[]>([])

  // New document form state
  const [nuevoDocumento, setNuevoDocumento] = useState({
    titulo: '',
    descripcion: '',
    archivo: null as File | null,
  })

  // Document editing state
  const [documentoEditado, setDocumentoEditado] = useState({
    titulo: '',
    descripcion: '',
  })

  // Chat/test state
  const [probando, setProbando] = useState(false)
  const [preguntaPrueba, setPreguntaPrueba] = useState('')
  const [usarDocumentos, setUsarDocumentos] = useState(true)
  const [mensajesChat, setMensajesChat] = useState<MensajeChatAI[]>([])

  // Tab management
  const [activeTab, setActiveTab] = useState('configuracion')
  const [activeHybridTab, setActiveHybridTab] = useState('fine-tuning')

  // Configuration verification
  const [configuracionCorrecta, setConfiguracionCorrecta] = useState(false)
  const [verificandoConfig, setVerificandoConfig] = useState(false)

  // Refs
  const chatEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Load configuration and documents on mount
  useEffect(() => {
    cargarConfiguracion()
    cargarDocumentos()
  }, [])

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajesChat, probando])

  // Configuration handlers
  const cargarConfiguracion = useCallback(async () => {
    try {
      const data = await apiClient.get<AIConfigState>('/api/v1/configuracion/ai/configuracion')
      const configCargada: AIConfigState = {
        configured: !!data.configured,
        provider: data.provider || 'openrouter',
        openai_api_key: data.openai_api_key ?? '',
        modelo_recomendado: data.modelo_recomendado || 'openai/gpt-4o-mini',
        modelo: data.modelo || 'openai/gpt-4o-mini',
        temperatura: data.temperatura || '0.7',
        max_tokens: data.max_tokens || '1000',
        activo: data.activo || 'false',
      }
      setConfig(configCargada)
      setConfiguracionCorrecta(!!data.configured && (data.activo || 'true').toLowerCase() === 'true')
    } catch (error) {
      console.error('Error cargando configuración de AI:', error)
      toast.error('Error cargando configuración')
    }
  }, [])

  const handleChange = useCallback((campo: keyof AIConfigState, valor: string) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }, [])

  const handleGuardar = useCallback(async () => {
    setGuardando(true)
    try {
      const tokenParaEnviar = config.openai_api_key && config.openai_api_key !== '***'
        ? config.openai_api_key
        : '***'
      await apiClient.put('/api/v1/configuracion/ai/configuracion', {
        modelo: config.modelo,
        temperatura: config.temperatura,
        max_tokens: config.max_tokens,
        activo: config.activo,
        openai_api_key: tokenParaEnviar,
      })
      toast.success('Configuración de AI guardada')
      await cargarConfiguracion()
      if (config.activo === 'true') setConfiguracionCorrecta(true)
    } catch (error: any) {
      console.error('Error guardando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error guardando configuración'
      toast.error(mensajeError)
    } finally {
      setGuardando(false)
    }
  }, [config, cargarConfiguracion])

  const verificarConfiguracion = useCallback(async (guardarAutomaticamente: boolean = false) => {
    setVerificandoConfig(true)
    try {
      const resultado = await apiClient.post<{ success: boolean; message?: string }>(
        '/api/v1/configuracion/ai/probar',
        { pregunta: 'Verificar conexión con OpenRouter' }
      )
      const esValida = !!resultado.success
      setConfiguracionCorrecta(esValida)
      if (esValida && guardarAutomaticamente) {
        try {
          await apiClient.put('/api/v1/configuracion/ai/configuracion', {
            modelo: config.modelo,
            temperatura: config.temperatura,
            max_tokens: config.max_tokens,
            activo: config.activo,
          })
          toast.success('Configuración verificada y guardada')
          await cargarConfiguracion()
        } catch (_saveError: any) {
          toast.error('Error al guardar. Guarda manualmente.')
        }
      }
      return esValida
    } catch (error: any) {
      setConfiguracionCorrecta(false)
      return false
    } finally {
      setVerificandoConfig(false)
    }
  }, [config, cargarConfiguracion])

  const handleVerificarYGuardar = useCallback(async () => {
    await verificarConfiguracion(true)
  }, [verificarConfiguracion])

  // Document handlers
  const cargarDocumentos = useCallback(async () => {
    try {
      const resultado = await apiClient.get<{ total: number; documentos: DocumentoAI[] }>('/api/v1/configuracion/ai/documentos')
      setDocumentos(resultado.documentos || [])
    } catch (error) {
      console.error('Error cargando documentos:', error)
      toast.error('Error cargando documentos')
    }
  }, [])

  const handleProcesarDocumento = useCallback(async (id: number) => {
    try {
      const respuesta = await apiClient.post<{
        mensaje: string
        documento: DocumentoAI
        caracteres_extraidos: number
        contenido_en_bd?: boolean
      }>(`/api/v1/configuracion/ai/documentos/${id}/procesar`)

      if (respuesta.mensaje?.includes('ya estaba procesado') || respuesta.contenido_en_bd) {
        toast.success(`📄 ${respuesta.mensaje || 'Documento procesado'} (${respuesta.caracteres_extraidos || 0} caracteres)`, {
          description: 'El contenido ya estaba disponible en la base de datos'
        })
      } else {
        toast.success(`Documento procesado exitosamente (${respuesta.caracteres_extraidos || 0} caracteres extraídos)`)
      }

      await cargarDocumentos()
    } catch (error: any) {
      console.error('Error procesando documento:', error)
      let mensajeError = error?.response?.data?.detail || 
                        error?.response?.data?.message || 
                        error?.message || 
                        'Error procesando documento'

      if (mensajeError.includes('El archivo físico no existe')) {
        mensajeError = 'El archivo físico no existe en el servidor. Por favor, elimina este documento y súbelo nuevamente.'
      } else if (mensajeError.length > 200) {
        const partes = mensajeError.split('\n')
        mensajeError = partes[0] + (partes.length > 1 ? ' (Ver consola para más detalles)' : '')
      }

      toast.error(`Error al procesar documento: ${mensajeError}`, {
        duration: 8000,
      })
    }
  }, [cargarDocumentos])

  // Chat handlers
  const handleProbar = useCallback(async () => {
    const pregunta = preguntaPrueba.trim()
    if (!pregunta) {
      toast.error('Por favor, escribe una pregunta')
      return
    }

    if (!config.configured) {
      toast.error('Ingresa tu API Key de OpenRouter en el campo de arriba y guarda, o configura OPENROUTER_API_KEY en variables de entorno del servidor.')
      return
    }

    const mensajeUsuario = {
      id: `user-${Date.now()}`,
      tipo: 'user' as const,
      texto: pregunta,
      timestamp: new Date(),
    }
    setMensajesChat(prev => [...prev, mensajeUsuario])
    setPreguntaPrueba('')
    setProbando(true)

    try {
      const resultado = await apiClient.post<{
        success: boolean
        mensaje: string
        pregunta?: string
        respuesta?: string
        tokens_usados?: number
        modelo_usado?: string
        tiempo_respuesta?: number
        usar_documentos?: boolean
        documentos_consultados?: number
        error_code?: string
      }>('/api/v1/configuracion/ai/probar', {
        pregunta: pregunta,
        usar_documentos: usarDocumentos,
      })

      if (resultado.success && resultado.respuesta) {
        const mensajeAI = {
          id: `ai-${Date.now()}`,
          tipo: 'ai' as const,
          texto: resultado.respuesta,
          timestamp: new Date(),
          metadata: {
            tokens: resultado.tokens_usados,
            tiempo: resultado.tiempo_respuesta,
            modelo: resultado.modelo_usado,
            documentos: resultado.documentos_consultados,
          },
        }
        setMensajesChat(prev => [...prev, mensajeAI])
        toast.success('Respuesta generada exitosamente')
      } else {
        const mensajeError = {
          id: `error-${Date.now()}`,
          tipo: 'ai' as const,
          texto: resultado.mensaje || 'Error generando respuesta',
          timestamp: new Date(),
        }
        setMensajesChat(prev => [...prev, mensajeError])
        toast.error(resultado.mensaje || 'Error generando respuesta')
      }
    } catch (error: any) {
      console.error('Error probando AI:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error probando AI'
      const mensajeErrorChat = {
        id: `error-${Date.now()}`,
        tipo: 'ai' as const,
        texto: `❌ Error: ${mensajeError}`,
        timestamp: new Date(),
      }
      setMensajesChat(prev => [...prev, mensajeErrorChat])
      toast.error(mensajeError)
    } finally {
      setProbando(false)
    }
  }, [preguntaPrueba, config.configured, usarDocumentos])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!probando && preguntaPrueba.trim()) {
        handleProbar()
      }
    }
  }, [probando, preguntaPrueba, handleProbar])

  const limpiarChat = useCallback(() => {
    setMensajesChat([])
  }, [])

  return {
    // Configuration
    config,
    handleChange,
    handleGuardar,
    verificarConfiguracion,
    handleVerificarYGuardar,
    cargarConfiguracion,
    guardando,
    configuracionCorrecta,
    verificandoConfig,

    // Documents
    documentos,
    cargarDocumentos,
    nuevoDocumento,
    setNuevoDocumento,
    documentoEditado,
    setDocumentoEditado,
    handleProcesarDocumento,

    // Chat
    probando,
    preguntaPrueba,
    setPreguntaPrueba,
    usarDocumentos,
    setUsarDocumentos,
    mensajesChat,
    handleProbar,
    handleKeyDown,
    limpiarChat,

    // Tabs
    activeTab,
    setActiveTab,
    activeHybridTab,
    setActiveHybridTab,

    // Refs
    chatEndRef,
    textareaRef,
  }
}
