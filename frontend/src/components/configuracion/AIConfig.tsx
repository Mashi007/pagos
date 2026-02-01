import { useState, useEffect, useRef } from 'react'
import { Brain, Save, Eye, EyeOff, Upload, FileText, Trash2, BarChart3, CheckCircle, AlertCircle, Loader2, TestTube, ChevronRight, MessageSquare, User, Edit, Zap, RotateCcw, Copy, Settings, DollarSign, Database, X } from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'
// TrainingDashboard eliminado - redundante con EntrenamientoMejorado
import { FineTuningTab } from './FineTuningTab'
import { RAGTab } from './RAGTab'
import { EntrenamientoMejorado } from './EntrenamientoMejorado'
import { DiccionarioSemanticoTab } from './DiccionarioSemanticoTab'
import { DefinicionesCamposTab } from './DefinicionesCamposTab'
import { CalificacionesChatTab } from './CalificacionesChatTab'

interface AIConfig {
  openai_api_key: string
  modelo: string
  temperatura: string
  max_tokens: string
  activo: string
}

interface DocumentoAI {
  id: number
  titulo: string
  descripcion: string | null
  nombre_archivo: string
  tipo_archivo: string
  tamaÃ±o_bytes: number | null
  contenido_procesado: boolean
  activo: boolean
  creado_en: string
  actualizado_en: string
}

export function AIConfig() {
  const [config, setConfig] = useState<AIConfig>({
    openai_api_key: '',
    modelo: 'gpt-3.5-turbo',
    temperatura: '0.7',
    max_tokens: '1000',
    activo: 'false',
  })

  const [mostrarToken, setMostrarToken] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [documentos, setDocumentos] = useState<DocumentoAI[]>([])
  const [cargandoDocumentos, setCargandoDocumentos] = useState(false)

  // Formulario de nuevo documento
  const [nuevoDocumento, setNuevoDocumento] = useState({
    titulo: '',
    descripcion: '',
    archivo: null as File | null,
  })
  const [subiendoDocumento, setSubiendoDocumento] = useState(false)

  // Estado para editar documento
  const [editandoDocumento, setEditandoDocumento] = useState<number | null>(null)
  const [documentoEditado, setDocumentoEditado] = useState({
    titulo: '',
    descripcion: '',
  })
  const [actualizandoDocumento, setActualizandoDocumento] = useState(false)
  const [procesandoDocumento, setProcesandoDocumento] = useState<number | null>(null)

  // Estado para pruebas (chat)
  const [probando, setProbando] = useState(false)
  const [preguntaPrueba, setPreguntaPrueba] = useState('')
  const [usarDocumentos, setUsarDocumentos] = useState(true)
  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)
  const [mensajesChat, setMensajesChat] = useState<Array<{
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
  }>>([])
  const chatEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [activeTab, setActiveTab] = useState('configuracion')
  const [activeHybridTab, setActiveHybridTab] = useState('fine-tuning') // Cambiado de 'dashboard' a 'fine-tuning'

  // Estado para verificar configuraciÃ³n correcta
  const [configuracionCorrecta, setConfiguracionCorrecta] = useState(false)
  const [verificandoConfig, setVerificandoConfig] = useState(false)
  const [tokenAnterior, setTokenAnterior] = useState<string>('')

  useEffect(() => {
    cargarConfiguracion()
    cargarDocumentos()
  }, [])

  // Verificar configuraciÃ³n solo cuando el usuario cambia el token manualmente
  // NO verificar en cada carga de pÃ¡gina - el token se guarda permanentemente en BD
  useEffect(() => {
    // En la carga inicial, si hay token guardado, asumir que estÃ¡ correcto (se guardÃ³ permanentemente en BD)
    if (!tokenAnterior && config.openai_api_key && config.openai_api_key.trim() && config.openai_api_key.startsWith('sk-')) {
      // Token guardado permanentemente en BD - establecer estado
      if (config.activo === 'true') {
        setConfiguracionCorrecta(true)
      }
      setTokenAnterior(config.openai_api_key)
      console.log('âœ… Token detectado desde BD - guardado permanentemente, no requiere confirmaciÃ³n')
      return
    }

    // Solo verificar si el token cambiÃ³ manualmente (no en la carga inicial)
    if (tokenAnterior && tokenAnterior !== config.openai_api_key && config.openai_api_key && config.openai_api_key.trim() && config.openai_api_key.startsWith('sk-')) {
      // El usuario cambiÃ³ el token manualmente, verificar despuÃ©s de un delay
      const timer = setTimeout(() => {
        verificarConfiguracion(false)
      }, 1000)
      return () => clearTimeout(timer)
    }

    // Actualizar estado basado en configuraciÃ³n actual
    if (config.openai_api_key && config.openai_api_key.trim() && config.openai_api_key.startsWith('sk-')) {
      if (config.activo === 'true') {
        setConfiguracionCorrecta(true)
      } else {
        setConfiguracionCorrecta(false)
      }
    } else if (config.openai_api_key === '') {
      setConfiguracionCorrecta(false)
    }
  }, [config.openai_api_key, config.activo, tokenAnterior])

  const verificarConfiguracion = async (guardarAutomaticamente: boolean = false) => {
    if (!config.openai_api_key?.trim() || !config.openai_api_key.startsWith('sk-')) {
      setConfiguracionCorrecta(false)
      return false
    }

    setVerificandoConfig(true)
    try {
      // Hacer una prueba simple para verificar que la API key funciona
      const resultado = await apiClient.post<{
        success: boolean
        mensaje?: string
      }>('/api/v1/configuracion/ai/probar', {
        pregunta: 'Verificar conexiÃ³n con OpenAI',
        usar_documentos: false,
      })

      // Si la respuesta es exitosa o el error no es de autenticaciÃ³n, la config estÃ¡ correcta
      const esValida = resultado.success || !resultado.mensaje?.includes('API key')
      setConfiguracionCorrecta(esValida)

      // Si el token es vÃ¡lido y se debe guardar automÃ¡ticamente, guardar la configuraciÃ³n
      if (esValida && guardarAutomaticamente) {
        try {
          await apiClient.put('/api/v1/configuracion/ai/configuracion', config)
          toast.success('âœ… Token vÃ¡lido confirmado y guardado automÃ¡ticamente')
          await cargarConfiguracion()
        } catch (saveError: any) {
          console.error('Error guardando configuraciÃ³n automÃ¡ticamente:', saveError)
          toast.error('Token vÃ¡lido pero error al guardar. Guarda manualmente.')
        }
      }

      return esValida
    } catch (error: any) {
      // Si el error es de autenticaciÃ³n, la config no estÃ¡ correcta
      const errorMsg = error?.response?.data?.detail || error?.message || ''
      const esValida = !errorMsg.toLowerCase().includes('api key') && !errorMsg.toLowerCase().includes('authentication')
      setConfiguracionCorrecta(esValida)
      return esValida
    } finally {
      setVerificandoConfig(false)
    }
  }

  const cargarConfiguracion = async () => {
    try {
      const data = await apiClient.get<AIConfig>('/api/v1/configuracion/ai/configuracion')
      // Asegurar que todos los campos tengan valores por defecto si vienen como null/undefined
      const configCargada = {
        openai_api_key: data.openai_api_key || '',
        modelo: data.modelo || 'gpt-3.5-turbo',
        temperatura: data.temperatura || '0.7',
        max_tokens: data.max_tokens || '1000',
        activo: data.activo || 'false',
      }
      setConfig(configCargada)

      // Log para depuraciÃ³n
      console.log('ðŸ“‹ ConfiguraciÃ³n cargada desde BD:', {
        tieneToken: !!(configCargada.openai_api_key && configCargada.openai_api_key.trim()),
        tokenValido: configCargada.openai_api_key?.startsWith('sk-'),
        activo: configCargada.activo === 'true',
        tokenLength: configCargada.openai_api_key?.length || 0
      })
    } catch (error) {
      console.error('Error cargando configuraciÃ³n de AI:', error)
      toast.error('Error cargando configuraciÃ³n')
    }
  }

  const cargarDocumentos = async () => {
    setCargandoDocumentos(true)
    try {
      const resultado = await apiClient.get<{ total: number; documentos: DocumentoAI[] }>('/api/v1/configuracion/ai/documentos')
      setDocumentos(resultado.documentos || [])
    } catch (error) {
      console.error('Error cargando documentos:', error)
      toast.error('Error cargando documentos')
    } finally {
      setCargandoDocumentos(false)
    }
  }


  const handleChange = (campo: keyof AIConfig, valor: string) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }

  const handleGuardar = async () => {
    setGuardando(true)
    try {
      // Guardar directamente - el token se guarda permanentemente en BD
      console.log('ðŸ’¾ Guardando configuraciÃ³n:', {
        tieneToken: !!(config.openai_api_key && config.openai_api_key.trim()),
        activo: config.activo
      })

      await apiClient.put('/api/v1/configuracion/ai/configuracion', config)
      toast.success('âœ… ConfiguraciÃ³n de AI guardada exitosamente y de forma permanente')

      // Recargar configuraciÃ³n desde BD para confirmar que se guardÃ³
      await cargarConfiguracion()

      // Si hay token guardado, actualizar estado
      if (config.openai_api_key?.trim() && config.openai_api_key.startsWith('sk-')) {
        if (config.activo === 'true') {
          setConfiguracionCorrecta(true)
        }
        // Actualizar token anterior para evitar verificaciones innecesarias
        setTokenAnterior(config.openai_api_key)
        console.log('âœ… Token guardado permanentemente. No se requiere confirmaciÃ³n adicional.')
      }
    } catch (error: any) {
      console.error('Error guardando configuraciÃ³n:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error guardando configuraciÃ³n'
      toast.error(mensajeError)
    } finally {
      setGuardando(false)
    }
  }

  const handleVerificarYGuardar = async () => {
    // Verificar y guardar automÃ¡ticamente si el token es vÃ¡lido
    const tokenValido = await verificarConfiguracion(true)
    if (tokenValido) {
      // Si el token es vÃ¡lido y se guardÃ³, actualizar token anterior
      setTokenAnterior(config.openai_api_key)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validar tipo de archivo
      const tiposPermitidos = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
      if (!tiposPermitidos.includes(file.type)) {
        toast.error('Tipo de archivo no permitido. Use PDF, TXT o DOCX')
        return
      }

      // Validar tamaÃ±o (mÃ¡ximo 10MB)
      if (file.size > 10 * 1024 * 1024) {
        toast.error('El archivo es demasiado grande. MÃ¡ximo 10MB')
        return
      }

      setNuevoDocumento(prev => ({ ...prev, archivo: file }))
    }
  }

  const handleSubirDocumento = async () => {
    if (!nuevoDocumento.titulo.trim()) {
      toast.error('El tÃ­tulo es requerido')
      return
    }

    if (!nuevoDocumento.archivo) {
      toast.error('Debe seleccionar un archivo')
      return
    }

    setSubiendoDocumento(true)
    try {
      const formData = new FormData()
      formData.append('archivo', nuevoDocumento.archivo)
      formData.append('titulo', nuevoDocumento.titulo)
      if (nuevoDocumento.descripcion) {
        formData.append('descripcion', nuevoDocumento.descripcion)
      }

      await apiClient.post('/api/v1/configuracion/ai/documentos', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      toast.success('Documento subido exitosamente')
      setNuevoDocumento({ titulo: '', descripcion: '', archivo: null })
      await cargarDocumentos()
    } catch (error: any) {
      console.error('Error subiendo documento:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error subiendo documento'
      toast.error(mensajeError)
    } finally {
      setSubiendoDocumento(false)
    }
  }

  const handleProcesarDocumento = async (id: number) => {
    setProcesandoDocumento(id)
    try {
      const respuesta = await apiClient.post<{
        mensaje: string
        documento: DocumentoAI
        caracteres_extraidos: number
        contenido_en_bd?: boolean
      }>(`/api/v1/configuracion/ai/documentos/${id}/procesar`)
      
      // Mensaje mejorado segÃºn el resultado
      if (respuesta.mensaje?.includes('ya estaba procesado') || respuesta.contenido_en_bd) {
        toast.success(`âœ… ${respuesta.mensaje || 'Documento procesado'} (${respuesta.caracteres_extraidos || 0} caracteres)`, {
          description: 'El contenido ya estaba disponible en la base de datos'
        })
      } else {
        toast.success(`Documento procesado exitosamente (${respuesta.caracteres_extraidos || 0} caracteres extraÃ­dos)`)
      }
      
      await cargarDocumentos()
    } catch (error: any) {
      console.error('Error procesando documento:', error)
      // Intentar obtener el mensaje del backend de mÃºltiples fuentes
      let mensajeError = error?.response?.data?.detail || 
                        error?.response?.data?.message || 
                        error?.message || 
                        'Error procesando documento'

      // Simplificar mensajes largos de diagnÃ³stico
      if (mensajeError.includes('El archivo fÃ­sico no existe')) {
        mensajeError = 'El archivo fÃ­sico no existe en el servidor. Por favor, elimina este documento y sÃºbelo nuevamente.'
      } else if (mensajeError.length > 200) {
        // Truncar mensajes muy largos pero mantener la parte importante
        const partes = mensajeError.split('\n')
        mensajeError = partes[0] + (partes.length > 1 ? ' (Ver consola para mÃ¡s detalles)' : '')
      }

      toast.error(`Error al procesar documento: ${mensajeError}`, {
        duration: 8000, // Aumentar duraciÃ³n para mensajes importantes
      })
    } finally {
      setProcesandoDocumento(null)
    }
  }

  const handleEliminarDocumento = async (id: number) => {
    if (!confirm('Â¿EstÃ¡ seguro de eliminar este documento?')) {
      return
    }

    try {
      await apiClient.delete(`/api/v1/configuracion/ai/documentos/${id}`)
      toast.success('Documento eliminado exitosamente')
      await cargarDocumentos()
    } catch (error: any) {
      console.error('Error eliminando documento:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error eliminando documento'
      toast.error(mensajeError)
    }
  }

  const handleIniciarEdicion = (doc: DocumentoAI) => {
    setEditandoDocumento(doc.id)
    setDocumentoEditado({
      titulo: doc.titulo,
      descripcion: doc.descripcion || '',
    })
  }

  const handleCancelarEdicion = () => {
    setEditandoDocumento(null)
    setDocumentoEditado({ titulo: '', descripcion: '' })
  }

  const handleActualizarDocumento = async (id: number) => {
    if (!documentoEditado.titulo.trim()) {
      toast.error('El tÃ­tulo es requerido')
      return
    }

    setActualizandoDocumento(true)
    try {
      await apiClient.put(`/api/v1/configuracion/ai/documentos/${id}`, {
        titulo: documentoEditado.titulo,
        descripcion: documentoEditado.descripcion || null,
      })
      toast.success('Documento actualizado exitosamente')
      setEditandoDocumento(null)
      setDocumentoEditado({ titulo: '', descripcion: '' })
      await cargarDocumentos()
    } catch (error: any) {
      console.error('Error actualizando documento:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error actualizando documento'
      toast.error(mensajeError)
    } finally {
      setActualizandoDocumento(false)
    }
  }

  const handleActivarDesactivarDocumento = async (id: number, activo: boolean) => {
    // Encontrar el documento para validar
    const documento = documentos.find(doc => doc.id === id)

    // Si se estÃ¡ intentando activar, verificar que estÃ© procesado
    if (activo && documento && !documento.contenido_procesado) {
      const confirmar = confirm(
        'âš ï¸ Este documento no estÃ¡ procesado.\n\n' +
        'Para que el AI pueda usar este documento como contexto, debe estar:\n' +
        '1. âœ… Procesado (extraer texto del archivo)\n' +
        '2. âœ… Activo\n' +
        '3. âœ… Con contenido_texto vÃ¡lido\n\n' +
        'Â¿Deseas procesarlo ahora antes de activarlo?'
      )

      if (confirmar) {
        // Procesar primero
        try {
          await handleProcesarDocumento(id)
          // DespuÃ©s de procesar, activar
          await apiClient.patch(`/api/v1/configuracion/ai/documentos/${id}/activar`, { activo: true })
          toast.success('âœ… Documento procesado y activado exitosamente')
          await cargarDocumentos()
        } catch (error: any) {
          console.error('Error procesando/activando documento:', error)
          const mensajeError = error?.response?.data?.detail || error?.message || 'Error procesando documento'
          toast.error(`Error: ${mensajeError}`)
        }
        return
      } else {
        // Si no quiere procesar, solo activar (pero mostrar advertencia)
        toast.warning('âš ï¸ Documento activado pero no procesado. El AI no podrÃ¡ usarlo como contexto hasta que sea procesado.')
      }
    }

    try {
      await apiClient.patch(`/api/v1/configuracion/ai/documentos/${id}/activar`, { activo })
      toast.success(`Documento ${activo ? 'activado' : 'desactivado'} exitosamente`)
      await cargarDocumentos()
    } catch (error: any) {
      console.error('Error activando/desactivando documento:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error cambiando estado del documento'
      toast.error(mensajeError)
    }
  }

  const formatearTamaÃ±o = (bytes: number | null) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  // Scroll automÃ¡tico al final del chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajesChat, probando])

  const handleProbar = async () => {
    const pregunta = preguntaPrueba.trim()
    if (!pregunta) {
      toast.error('Por favor, escribe una pregunta')
      return
    }

    const apiKey = config.openai_api_key?.trim()
    if (!apiKey) {
      toast.error('Debes configurar el OpenAI API Key primero')
      return
    }

    // Validar formato bÃ¡sico de API key (debe empezar con sk-)
    if (!apiKey.startsWith('sk-')) {
      toast.error('El API Key debe empezar con "sk-". Verifica que sea un token vÃ¡lido de OpenAI.')
      return
    }

    // Agregar mensaje del usuario al chat
    const mensajeUsuario = {
      id: `user-${Date.now()}`,
      tipo: 'user' as const,
      texto: pregunta,
      timestamp: new Date(),
    }
    setMensajesChat(prev => [...prev, mensajeUsuario])
    setPreguntaPrueba('')
    setProbando(true)
    setResultadoPrueba(null)

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

      setResultadoPrueba(resultado)

      if (resultado.success && resultado.respuesta) {
        // Agregar respuesta de AI al chat
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
        // Agregar mensaje de error al chat
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
        texto: `âŒ Error: ${mensajeError}`,
        timestamp: new Date(),
      }
      setMensajesChat(prev => [...prev, mensajeErrorChat])
      toast.error(mensajeError)
      setResultadoPrueba({ success: false, mensaje: mensajeError })
    } finally {
      setProbando(false)
    }
  }

  // Manejar Enter para enviar (Shift+Enter para nueva lÃ­nea)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!probando && preguntaPrueba.trim()) {
        handleProbar()
      }
    }
  }

  const limpiarChat = () => {
    setMensajesChat([])
    setResultadoPrueba(null)
  }

  // Componente para editar el prompt
  const PromptEditor = () => {
    const [promptPersonalizado, setPromptPersonalizado] = useState('')
    const [cargandoPrompt, setCargandoPrompt] = useState(true)
    const [guardandoPrompt, setGuardandoPrompt] = useState(false)
    const [tienePromptPersonalizado, setTienePromptPersonalizado] = useState(false)
    const [mostrarPlaceholders, setMostrarPlaceholders] = useState(true)

    // Estados para variables personalizadas
    const [variablesPersonalizadas, setVariablesPersonalizadas] = useState<Array<{
      id: number
      variable: string
      descripcion: string
      activo: boolean
      orden: number
    }>>([])
    const [cargandoVariables, setCargandoVariables] = useState(false)
    const [mostrarGestionVariables, setMostrarGestionVariables] = useState(false)
    const [nuevaVariable, setNuevaVariable] = useState({ variable: '', descripcion: '' })
    const [creandoVariable, setCreandoVariable] = useState(false)
    const [editandoVariable, setEditandoVariable] = useState<number | null>(null)
    const [variableEditada, setVariableEditada] = useState({ variable: '', descripcion: '' })

    useEffect(() => {
      cargarPrompt()
      cargarVariables()
    }, [])

    const cargarPrompt = async () => {
      setCargandoPrompt(true)
      try {
        const data = await apiClient.get<{
          prompt_personalizado: string
          tiene_prompt_personalizado: boolean
          usando_prompt_default: boolean
          variables_personalizadas?: Array<{
            id: number
            variable: string
            descripcion: string
            activo: boolean
            orden: number
          }>
        }>('/api/v1/configuracion/ai/prompt')

        setPromptPersonalizado(data.prompt_personalizado || '')
        setTienePromptPersonalizado(data.tiene_prompt_personalizado)
        if (data.variables_personalizadas) {
          setVariablesPersonalizadas(data.variables_personalizadas)
        }
      } catch (error) {
        console.error('Error cargando prompt:', error)
        toast.error('Error cargando prompt')
      } finally {
        setCargandoPrompt(false)
      }
    }

    const handleGuardarPrompt = async () => {
      setGuardandoPrompt(true)
      try {
        await apiClient.put('/api/v1/configuracion/ai/prompt', {
          prompt: promptPersonalizado
        })
        toast.success('âœ… Prompt personalizado guardado exitosamente')
        await cargarPrompt()
      } catch (error: any) {
        console.error('Error guardando prompt:', error)
        const errorDetail = error?.response?.data?.detail || error?.message || 'Error guardando prompt'
        toast.error(errorDetail)
      } finally {
        setGuardandoPrompt(false)
      }
    }

    const handleRestaurarDefault = async () => {
      if (!confirm('Â¿EstÃ¡s seguro de restaurar el prompt por defecto? Se perderÃ¡ el prompt personalizado.')) {
        return
      }

      setGuardandoPrompt(true)
      try {
        await apiClient.put('/api/v1/configuracion/ai/prompt', {
          prompt: ''
        })
        toast.success('âœ… Prompt restaurado al valor por defecto')
        await cargarPrompt()
      } catch (error: any) {
        console.error('Error restaurando prompt:', error)
        toast.error('Error restaurando prompt')
      } finally {
        setGuardandoPrompt(false)
      }
    }

    const cargarVariables = async () => {
      setCargandoVariables(true)
      try {
        const data = await apiClient.get<{
          variables: Array<{
            id: number
            variable: string
            descripcion: string
            activo: boolean
            orden: number
          }>
          total: number
        }>('/api/v1/configuracion/ai/prompt/variables')
        setVariablesPersonalizadas(data.variables || [])
      } catch (error) {
        console.error('Error cargando variables:', error)
        // No mostrar error si la tabla no existe aÃºn
      } finally {
        setCargandoVariables(false)
      }
    }

    const handleCrearVariable = async () => {
      if (!nuevaVariable.variable.trim() || !nuevaVariable.descripcion.trim()) {
        toast.error('Variable y descripciÃ³n son requeridos')
        return
      }

      // Validar formato de variable
      let variable = nuevaVariable.variable.trim()
      if (!variable.startsWith('{') || !variable.endsWith('}')) {
        variable = `{${variable.replace(/[{}]/g, '')}}`
      }

      setCreandoVariable(true)
      try {
        await apiClient.post('/api/v1/configuracion/ai/prompt/variables', {
          variable,
          descripcion: nuevaVariable.descripcion.trim(),
          activo: true,
          orden: variablesPersonalizadas.length,
        })
        toast.success('Variable creada exitosamente')
        setNuevaVariable({ variable: '', descripcion: '' })
        await cargarVariables()
        await cargarPrompt() // Recargar para incluir nuevas variables
      } catch (error: any) {
        console.error('Error creando variable:', error)
        toast.error(error?.response?.data?.detail || 'Error creando variable')
      } finally {
        setCreandoVariable(false)
      }
    }

    const handleIniciarEdicionVariable = (variable: typeof variablesPersonalizadas[0]) => {
      setEditandoVariable(variable.id)
      setVariableEditada({ variable: variable.variable, descripcion: variable.descripcion })
    }

    const handleCancelarEdicionVariable = () => {
      setEditandoVariable(null)
      setVariableEditada({ variable: '', descripcion: '' })
    }

    const handleActualizarVariable = async (id: number) => {
      if (!variableEditada.variable.trim() || !variableEditada.descripcion.trim()) {
        toast.error('Variable y descripciÃ³n son requeridos')
        return
      }

      let variable = variableEditada.variable.trim()
      if (!variable.startsWith('{') || !variable.endsWith('}')) {
        variable = `{${variable.replace(/[{}]/g, '')}}`
      }

      try {
        await apiClient.put(`/api/v1/configuracion/ai/prompt/variables/${id}`, {
          variable,
          descripcion: variableEditada.descripcion.trim(),
        })
        toast.success('Variable actualizada exitosamente')
        setEditandoVariable(null)
        setVariableEditada({ variable: '', descripcion: '' })
        await cargarVariables()
        await cargarPrompt()
      } catch (error: any) {
        console.error('Error actualizando variable:', error)
        toast.error(error?.response?.data?.detail || 'Error actualizando variable')
      }
    }

    const handleEliminarVariable = async (id: number) => {
      if (!confirm('Â¿EstÃ¡s seguro de eliminar esta variable?')) return

      try {
        await apiClient.delete(`/api/v1/configuracion/ai/prompt/variables/${id}`)
        toast.success('Variable eliminada exitosamente')
        await cargarVariables()
        await cargarPrompt()
      } catch (error: any) {
        console.error('Error eliminando variable:', error)
        toast.error(error?.response?.data?.detail || 'Error eliminando variable')
      }
    }

    const handleCopiarPlaceholders = () => {
      const placeholdersDefault = `{resumen_bd}
{info_cliente_buscado}
{datos_adicionales}
{info_esquema}
{contexto_documentos}`

      const placeholdersPersonalizados = variablesPersonalizadas
        .filter(v => v.activo)
        .map(v => v.variable)
        .join('\n')

      const todos = placeholdersDefault + (placeholdersPersonalizados ? '\n' + placeholdersPersonalizados : '')
      navigator.clipboard.writeText(todos)
      toast.success('Placeholders copiados al portapapeles')
    }

    const promptTemplate = `Eres un ANALISTA ESPECIALIZADO en prÃ©stamos y cobranzas con capacidad de anÃ¡lisis de KPIs operativos. Tu funciÃ³n es proporcionar informaciÃ³n precisa, anÃ¡lisis de tendencias y mÃ©tricas clave basÃ¡ndote EXCLUSIVAMENTE en los datos almacenados en las bases de datos del sistema.

ROL Y CONTEXTO:
- Eres un analista especializado en prÃ©stamos y cobranzas con capacidad de anÃ¡lisis de KPIs operativos
- Tu funciÃ³n es proporcionar informaciÃ³n precisa, anÃ¡lisis de tendencias y mÃ©tricas clave
- Basas tus respuestas EXCLUSIVAMENTE en los datos almacenados en las bases de datos del sistema
- Tienes acceso a informaciÃ³n en tiempo real de la base de datos del sistema
- Proporcionas anÃ¡lisis, estadÃ­sticas y recomendaciones basadas en datos reales
- Eres profesional, claro y preciso en tus respuestas
- Proporcionas respuestas accionables con contexto e interpretaciÃ³n

RESTRICCIÃ“N IMPORTANTE: Solo puedes responder preguntas relacionadas con la base de datos del sistema. Si recibes una pregunta que NO estÃ© relacionada con clientes, prÃ©stamos, pagos, cuotas, cobranzas, moras, estadÃ­sticas del sistema, o la fecha/hora actual, debes responder:

"Lo siento, el Chat AI solo responde preguntas sobre la base de datos del sistema (clientes, prÃ©stamos, pagos, cuotas, cobranzas, moras, estadÃ­sticas, etc.). Para preguntas generales, por favor usa el Chat de Prueba en la configuraciÃ³n de AI."

Tienes acceso a informaciÃ³n de la base de datos del sistema y a la fecha/hora actual. AquÃ­ tienes un resumen actualizado:

=== RESUMEN DE BASE DE DATOS ===
{resumen_bd}
{info_cliente_buscado}
{datos_adicionales}
{info_esquema}

[El sistema incluirÃ¡ automÃ¡ticamente el inventario completo de campos, mapeo semÃ¡ntico, y documentos de contexto]

=== DOCUMENTOS DE CONTEXTO ADICIONAL ===
{contexto_documentos}
NOTA: Si hay documentos de contexto arriba, Ãºsalos como informaciÃ³n adicional para responder preguntas. Los documentos pueden contener polÃ­ticas, procedimientos, o informaciÃ³n relevante sobre el sistema.

CAPACIDADES PRINCIPALES:
1. **Consulta de datos individuales**: InformaciÃ³n de prÃ©stamos, clientes y pagos especÃ­ficos
2. **AnÃ¡lisis de KPIs**: Morosidad, recuperaciÃ³n, cartera en riesgo, efectividad de cobranza
3. **AnÃ¡lisis de tendencias**: Comparaciones temporales (aumentos/disminuciones)
4. **Proyecciones operativas**: CuÃ¡nto se debe cobrar hoy, esta semana, este mes
5. **SegmentaciÃ³n**: AnÃ¡lisis por rangos de mora, montos, productos, zonas
6. **AnÃ¡lisis de Machine Learning**: PredicciÃ³n de morosidad, segmentaciÃ³n de clientes, detecciÃ³n de anomalÃ­as, clustering de prÃ©stamos

REGLAS FUNDAMENTALES:
1. **SOLO usa datos reales**: Accede a los Ã­ndices de las bases de datos y consulta los campos especÃ­ficos necesarios
2. **NUNCA inventes informaciÃ³n**: Si un dato no existe en la base de datos, indica claramente que no estÃ¡ disponible
3. **Muestra tus cÃ¡lculos**: Cuando calcules KPIs, indica la fÃ³rmula y los valores utilizados
4. **Compara con contexto**: Para tendencias, muestra perÃ­odo actual vs perÃ­odo anterior
5. **Respuestas accionables**: Incluye el "Â¿quÃ© significa esto?" cuando sea relevante
6. **SOLO responde preguntas sobre la base de datos del sistema relacionadas con cobranzas y prÃ©stamos**
7. Si la pregunta NO es sobre la BD, responde con el mensaje de restricciÃ³n mencionado arriba

PROCESO DE ANÃLISIS:
1. Identifica quÃ© mÃ©trica o anÃ¡lisis solicita el usuario
2. Determina quÃ© tabla(s), campo(s) y perÃ­odo de tiempo necesitas
3. Accede a los datos y realiza los cÃ¡lculos necesarios
4. Compara con perÃ­odos anteriores si es relevante
5. Presenta resultados con contexto y conclusiones claras

INSTRUCCIONES ESPECÃFICAS PARA BÃšSQUEDAS Y CONSULTAS:

**BÃšSQUEDAS POR IDENTIFICACIÃ“N (CÃ©dula/Documento)**:
- Cuando el usuario pregunta "Â¿CÃ³mo se llama quien tiene este nÃºmero de cÃ©dula: V19226493?" o similar:
  1. Busca en la tabla \`clientes\` usando el campo \`cedula\` (indexed para bÃºsquedas rÃ¡pidas)
  2. Si encuentras el cliente, proporciona: nombres, cÃ©dula, telÃ©fono, email, estado, fecha_registro
  3. Si no encuentras el cliente, indica claramente: "No se encontrÃ³ ningÃºn cliente con la cÃ©dula V19226493"
  4. Puedes buscar tambiÃ©n en \`prestamos.cedula\` si el cliente no estÃ¡ en la tabla clientes pero tiene prÃ©stamos
  5. Usa el mapeo semÃ¡ntico: "cedula", "cÃ©dula", "documento", "dni", "ci" son equivalentes

**FORMATO DE RESPUESTA PARA BÃšSQUEDAS**:
- Si encuentras el cliente:
  ðŸ‘¤ Cliente encontrado:
  â€¢ Nombre: [nombres]
  â€¢ CÃ©dula: [cedula]
  â€¢ TelÃ©fono: [telefono]
  â€¢ Email: [email]
  â€¢ Estado: [estado]
  â€¢ Fecha de registro: [fecha_registro]
- Si no encuentras: "âŒ No se encontrÃ³ ningÃºn cliente con la cÃ©dula [cedula] en la base de datos."

RESTRICCIONES IMPORTANTES:
- âš ï¸ PROHIBIDO INVENTAR DATOS: Solo usa la informaciÃ³n proporcionada en el resumen. NO inventes, NO uses tu conocimiento de entrenamiento, NO asumas datos.
- âš ï¸ NO hagas suposiciones sobre datos faltantes
- âš ï¸ NO uses promedios histÃ³ricos como datos reales sin aclararlo
- âš ï¸ FECHA ACTUAL: La fecha y hora actual estÃ¡n incluidas en el resumen. DEBES usar EXACTAMENTE esa informaciÃ³n.
- âš ï¸ DATOS DE BD: Solo usa los nÃºmeros y estadÃ­sticas del resumen. Si no estÃ¡ en el resumen, di que no tienes esa informaciÃ³n especÃ­fica.
- âš ï¸ NO INVENTES: Si no tienes la informaciÃ³n exacta, di "No tengo esa informaciÃ³n especÃ­fica en el resumen proporcionado" en lugar de inventar.
- âš ï¸ ANÃLISIS PROFESIONAL: Como especialista, proporciona anÃ¡lisis y contexto cuando sea relevante, pero siempre basado en los datos del resumen.
- Si faltan datos para un anÃ¡lisis completo, indÃ­calo claramente
- Para tendencias, necesitas al menos 2 perÃ­odos de comparaciÃ³n
- Si hay valores atÃ­picos, seÃ±Ã¡lalos

CUANDO NO PUEDAS RESPONDER:
- **Datos insuficientes**: "Para este anÃ¡lisis necesito datos de [especificar], que no estÃ¡n disponibles actualmente"
- **PerÃ­odo no disponible**: "Solo tengo datos desde [fecha]. Â¿Deseas el anÃ¡lisis con la informaciÃ³n disponible?"
- **CÃ¡lculo complejo**: "Este anÃ¡lisis requiere: [listar requisitos]. Â¿Confirmas que proceda?"

OBJETIVO:
Tu objetivo es ser el asistente analÃ­tico que permita tomar decisiones informadas sobre la gestiÃ³n de prÃ©stamos y cobranzas, proporcionando anÃ¡lisis precisos, tendencias claras y mÃ©tricas accionables basadas exclusivamente en los datos reales del sistema.

RECUERDA: Si la pregunta NO es sobre la base de datos, debes rechazarla con el mensaje de restricciÃ³n.`

    if (cargandoPrompt) {
      return (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Prompt Personalizado
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {tienePromptPersonalizado
                ? 'âœ… Usando prompt personalizado'
                : 'â„¹ï¸ Usando prompt por defecto'}
            </p>
          </div>
          <div className="flex gap-2">
            {tienePromptPersonalizado && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRestaurarDefault}
                disabled={guardandoPrompt}
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Restaurar Default
              </Button>
            )}
            <Button
              onClick={handleGuardarPrompt}
              disabled={guardandoPrompt}
            >
              {guardandoPrompt ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Guardar Prompt
                </>
              )}
            </Button>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <p className="font-semibold text-amber-900">Placeholders Disponibles</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setMostrarGestionVariables(!mostrarGestionVariables)}
                  className="text-xs"
                >
                  {mostrarGestionVariables ? 'Ocultar' : 'Gestionar Variables'}
                </Button>
              </div>
              <p className="text-sm text-amber-800 mb-2">
                El sistema reemplazarÃ¡ automÃ¡ticamente estos placeholders con datos reales:
              </p>

              {/* Placeholders predeterminados */}
              <div className="bg-white rounded p-3 font-mono text-xs space-y-1 mb-3">
                <div className="font-semibold text-amber-900 mb-1">Predeterminados:</div>
                <div><code className="text-blue-600">{'{resumen_bd}'}</code> - Resumen de la base de datos</div>
                <div><code className="text-blue-600">{'{info_cliente_buscado}'}</code> - InformaciÃ³n del cliente si se busca por cÃ©dula</div>
                <div><code className="text-blue-600">{'{datos_adicionales}'}</code> - CÃ¡lculos y anÃ¡lisis adicionales</div>
                <div><code className="text-blue-600">{'{info_esquema}'}</code> - Esquema completo de la base de datos</div>
                <div><code className="text-blue-600">{'{contexto_documentos}'}</code> - Documentos de contexto adicionales</div>
              </div>

              {/* Variables personalizadas */}
              {variablesPersonalizadas.length > 0 && (
                <div className="bg-white rounded p-3 font-mono text-xs space-y-1 mb-3">
                  <div className="font-semibold text-green-700 mb-1">Personalizadas:</div>
                  {variablesPersonalizadas.filter(v => v.activo).map((varItem) => (
                    <div key={varItem.id}>
                      <code className="text-green-600">{varItem.variable}</code> - {varItem.descripcion}
                    </div>
                  ))}
                </div>
              )}

              {/* GestiÃ³n de Variables Personalizadas */}
              {mostrarGestionVariables && (
                <div className="bg-white rounded-lg p-4 border border-amber-300 mt-3">
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    GestiÃ³n de Variables Personalizadas
                  </h4>

                  {/* Formulario para nueva variable */}
                  <div className="border rounded-lg p-3 mb-4 space-y-3">
                    <h5 className="font-medium text-sm">Nueva Variable</h5>
                    <div>
                      <label className="text-xs font-medium block mb-1">Variable <span className="text-red-500">*</span></label>
                      <Input
                        value={nuevaVariable.variable}
                        onChange={(e) => setNuevaVariable(prev => ({ ...prev, variable: e.target.value }))}
                        placeholder="Ej: {mi_variable} o mi_variable"
                        className="font-mono text-xs"
                      />
                      <p className="text-xs text-gray-500 mt-1">Se agregarÃ¡n llaves automÃ¡ticamente si no las incluyes</p>
                    </div>
                    <div>
                      <label className="text-xs font-medium block mb-1">DescripciÃ³n <span className="text-red-500">*</span></label>
                      <Input
                        value={nuevaVariable.descripcion}
                        onChange={(e) => setNuevaVariable(prev => ({ ...prev, descripcion: e.target.value }))}
                        placeholder="Describe quÃ© contiene esta variable"
                        className="text-xs"
                      />
                    </div>
                    <Button
                      onClick={handleCrearVariable}
                      disabled={creandoVariable || !nuevaVariable.variable.trim() || !nuevaVariable.descripcion.trim()}
                      size="sm"
                      className="w-full"
                    >
                      {creandoVariable ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Creando...
                        </>
                      ) : (
                        <>
                          <FileText className="h-3 w-3 mr-1" />
                          Agregar Variable
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Tabla de variables existentes */}
                  {cargandoVariables ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    </div>
                  ) : variablesPersonalizadas.length === 0 ? (
                    <div className="text-center py-4 text-gray-500 text-sm">
                      No hay variables personalizadas. Agrega una arriba.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-gray-700 mb-2">Variables Existentes:</div>
                      {variablesPersonalizadas.map((varItem) => (
                        <div key={varItem.id} className="border rounded p-2 hover:bg-gray-50">
                          {editandoVariable === varItem.id ? (
                            <div className="space-y-2">
                              <div>
                                <label className="text-xs font-medium block mb-1">Variable</label>
                                <Input
                                  value={variableEditada.variable}
                                  onChange={(e) => setVariableEditada(prev => ({ ...prev, variable: e.target.value }))}
                                  className="font-mono text-xs"
                                  size={1}
                                />
                              </div>
                              <div>
                                <label className="text-xs font-medium block mb-1">DescripciÃ³n</label>
                                <Input
                                  value={variableEditada.descripcion}
                                  onChange={(e) => setVariableEditada(prev => ({ ...prev, descripcion: e.target.value }))}
                                  className="text-xs"
                                  size={1}
                                />
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  onClick={() => handleActualizarVariable(varItem.id)}
                                  disabled={!variableEditada.variable.trim() || !variableEditada.descripcion.trim()}
                                  className="text-xs h-7"
                                >
                                  <Save className="h-3 w-3 mr-1" />
                                  Guardar
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={handleCancelarEdicionVariable}
                                  className="text-xs h-7"
                                >
                                  Cancelar
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <code className="text-green-600 font-mono text-xs">{varItem.variable}</code>
                                  <Badge variant={varItem.activo ? "default" : "secondary"} className="text-xs">
                                    {varItem.activo ? "Activo" : "Inactivo"}
                                  </Badge>
                                </div>
                                <p className="text-xs text-gray-600">{varItem.descripcion}</p>
                              </div>
                              <div className="flex items-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleIniciarEdicionVariable(varItem)}
                                  className="text-blue-600 hover:text-blue-700 h-7 w-7 p-0"
                                  title="Editar variable"
                                >
                                  <Edit className="h-3 w-3" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleEliminarVariable(varItem.id)}
                                  className="text-red-600 hover:text-red-700 h-7 w-7 p-0"
                                  title="Eliminar variable"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={handleCopiarPlaceholders}
                className="mt-2"
              >
                <Copy className="h-4 w-4 mr-2" />
                Copiar Placeholders
              </Button>
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium">Prompt Personalizado</label>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMostrarPlaceholders(!mostrarPlaceholders)}
              >
                {mostrarPlaceholders ? 'Ocultar' : 'Mostrar'} Template
              </Button>
            </div>
          </div>

          {mostrarPlaceholders && !tienePromptPersonalizado && (
            <div className="mb-4 p-4 bg-gray-50 border rounded-lg">
              <p className="text-sm font-medium mb-2">Template de Prompt (para referencia):</p>
              <Textarea
                value={promptTemplate}
                readOnly
                className="font-mono text-xs h-40"
                onClick={(e) => (e.target as HTMLTextAreaElement).select()}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPromptPersonalizado(promptTemplate)}
                className="mt-2"
              >
                Usar como Base
              </Button>
            </div>
          )}

          <Textarea
            value={promptPersonalizado}
            onChange={(e) => setPromptPersonalizado(e.target.value)}
            placeholder="Escribe tu prompt personalizado aquÃ­. AsegÃºrate de incluir los placeholders: {resumen_bd}, {info_cliente_buscado}, {datos_adicionales}, {info_esquema}, {contexto_documentos}"
            className="font-mono text-sm min-h-[500px]"
          />
          <p className="text-xs text-gray-500 mt-2">
            {promptPersonalizado.length} caracteres. El prompt debe incluir los placeholders mencionados arriba.
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            ðŸ’¡ <strong>Tip:</strong> Puedes personalizar el comportamiento del AI ajustando el prompt.
            Los placeholders se reemplazarÃ¡n automÃ¡ticamente con datos reales del sistema.
            Si dejas el prompt vacÃ­o, se usarÃ¡ el prompt por defecto.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* InformaciÃ³n mejorada */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Brain className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h3 className="font-bold text-lg text-blue-900">ConfiguraciÃ³n de Inteligencia Artificial</h3>
            <p className="text-sm text-blue-700 mt-1">
              Configura ChatGPT para respuestas automÃ¡ticas contextualizadas en WhatsApp usando tus documentos como base de conocimiento.
            </p>
          </div>
        </div>
      </div>

      {/* Tabs con 3 pestaÃ±as - diseÃ±o mejorado */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 bg-gray-100/50 p-1 rounded-lg">
          <TabsTrigger
            value="configuracion"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
          >
            <Settings className="h-4 w-4" />
            ConfiguraciÃ³n
          </TabsTrigger>
          <TabsTrigger
            value="entrenamiento"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
          >
            <FileText className="h-4 w-4" />
            Entrenamiento
          </TabsTrigger>
          <TabsTrigger
            value="sistema-hibrido"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
          >
            <Zap className="h-4 w-4" />
            Sistema HÃ­brido
          </TabsTrigger>
        </TabsList>

        {/* PestaÃ±a 1: ConfiguraciÃ³n */}
        <TabsContent value="configuracion" className="space-y-4 mt-6">
          {/* âœ… Toggle Activar/Desactivar AI */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className="text-sm font-semibold text-gray-900 block mb-1">
                  Servicio de AI
                </label>
                <p className="text-xs text-gray-600">
                  {config.activo === 'true'
                    ? 'âœ… El sistema estÃ¡ usando AI para generar respuestas automÃ¡ticas'
                    : 'âš ï¸ El sistema NO usarÃ¡ AI. Activa el servicio para habilitar respuestas inteligentes.'}
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.activo === 'true'}
                      onChange={async (e) => {
                        const nuevoEstado = e.target.checked ? 'true' : 'false'
                        handleChange('activo', nuevoEstado)

                        // Si hay token vÃ¡lido y se estÃ¡ activando, guardar automÃ¡ticamente
                        if (e.target.checked && config.openai_api_key?.trim() && config.openai_api_key.startsWith('sk-')) {
                          try {
                            const configParaGuardar = { ...config, activo: nuevoEstado }
                            await apiClient.put('/api/v1/configuracion/ai/configuracion', configParaGuardar)
                            toast.success('âœ… AI activado y guardado automÃ¡ticamente')
                            await cargarConfiguracion()
                            setConfiguracionCorrecta(true)
                            setTokenAnterior(config.openai_api_key)
                          } catch (error) {
                            console.error('Error guardando automÃ¡ticamente:', error)
                            toast.warning('AI activado localmente. Recuerda guardar la configuraciÃ³n.')
                          }
                        } else {
                          toast.info(e.target.checked ? 'AI activado - Las respuestas inteligentes se habilitarÃ¡n al guardar' : 'AI desactivado - Las respuestas inteligentes se deshabilitarÃ¡n al guardar')
                        }
                      }}
                      className="sr-only peer"
                    />
                <div className="w-14 h-7 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-blue-600"></div>
                <span className="ml-3 text-sm font-medium text-gray-700">
                  {config.activo === 'true' ? 'Activo' : 'Inactivo'}
                </span>
              </label>
            </div>
          </div>

          {/* âœ… Estado: ConfiguraciÃ³n correcta */}
          {config.openai_api_key?.trim() && config.openai_api_key.startsWith('sk-') && configuracionCorrecta && (
            <div className="bg-white border-2 border-green-500 rounded-xl p-5 shadow-sm">
              <div className="flex items-center gap-3">
                {/* SemÃ¡foro Verde */}
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className="w-4 h-4 bg-green-500 rounded-full shadow-lg"></div>
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900">
                    ConfiguraciÃ³n correcta
                  </p>
                  <p className="text-sm text-gray-600">
                    OpenAI aceptÃ³ la conexiÃ³n. Puedes usar AI para generar respuestas.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* âš ï¸ Estado: API Key no vÃ¡lida o no configurada */}
          {config.openai_api_key?.trim() && !configuracionCorrecta && !verificandoConfig && (
            <div className="bg-white border-2 border-amber-400 rounded-xl p-5 shadow-sm">
              <div className="flex items-center gap-3">
                {/* SemÃ¡foro Amarillo */}
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                  <div className="w-4 h-4 bg-amber-500 rounded-full shadow-lg"></div>
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900 mb-2">
                    API Key no vÃ¡lida o no configurada
                  </p>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>1. Verifica que tu API Key comience con "sk-"</p>
                    <p>2. AsegÃºrate de que la API Key sea vÃ¡lida y tenga crÃ©ditos disponibles</p>
                    <p>3. ObtÃ©n una nueva API Key en: <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="underline text-blue-600">platform.openai.com/api-keys</a></p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* âŒ Estado: No configurado */}
          {(!config.openai_api_key?.trim() || !config.openai_api_key.startsWith('sk-')) && (
            <div className="bg-white border-2 border-red-500 rounded-xl p-5 shadow-sm">
              <div className="flex items-center gap-3">
                {/* SemÃ¡foro Rojo */}
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                  <div className="w-4 h-4 bg-red-500 rounded-full shadow-lg"></div>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900">
                    ConfiguraciÃ³n incompleta
                  </p>
                  <p className="text-sm text-gray-600">
                    Ingresa una API Key vÃ¡lida de OpenAI para habilitar el servicio de AI.
                  </p>
                </div>
              </div>
            </div>
          )}

          <Card className="shadow-sm border-gray-200">
            <CardContent className="pt-6 space-y-4">
              <div>
                <label className="text-sm font-medium block mb-2">OpenAI API Key <span className="text-red-500">*</span></label>
                <div className="relative">
                  <Input
                    type={mostrarToken ? 'text' : 'password'}
                    value={config.openai_api_key || ''}
                    onChange={(e) => handleChange('openai_api_key', e.target.value)}
                    placeholder="sk-..."
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setMostrarToken(!mostrarToken)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {mostrarToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  ObtÃ©n tu API Key en: <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">platform.openai.com/api-keys</a>
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium block mb-2">Modelo</label>
                  <Select value={config.modelo} onValueChange={(value) => handleChange('modelo', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo (Recomendado)</SelectItem>
                      <SelectItem value="gpt-4">GPT-4 (MÃ¡s potente)</SelectItem>
                      <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium block mb-2">Temperatura</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={config.temperatura}
                    onChange={(e) => handleChange('temperatura', e.target.value)}
                    placeholder="0.7"
                  />
                  <p className="text-xs text-gray-500 mt-1">Controla la creatividad (0-2). 0.7 es un buen balance.</p>
                </div>

                <div>
                  <label className="text-sm font-medium block mb-2">Max Tokens</label>
                  <Input
                    type="number"
                    value={config.max_tokens}
                    onChange={(e) => handleChange('max_tokens', e.target.value)}
                    placeholder="1000"
                  />
                  <p className="text-xs text-gray-500 mt-1">MÃ¡ximo de tokens en la respuesta.</p>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <Button
                  onClick={handleGuardar}
                  disabled={guardando}
                  className={configuracionCorrecta && config.openai_api_key?.trim() && config.openai_api_key.startsWith('sk-')
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : ''}
                >
                  {guardando ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      {configuracionCorrecta && config.openai_api_key?.trim() && config.openai_api_key.startsWith('sk-')
                        ? 'âœ… Guardar ConfiguraciÃ³n (Token VÃ¡lido)'
                        : 'Guardar ConfiguraciÃ³n'}
                    </>
                  )}
                </Button>
                {config.openai_api_key?.trim() && config.openai_api_key.startsWith('sk-') && !configuracionCorrecta && (
                  <Button
                    onClick={handleVerificarYGuardar}
                    disabled={verificandoConfig}
                    variant="outline"
                    className="border-blue-600 text-blue-600 hover:bg-blue-50"
                  >
                    {verificandoConfig ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Verificando...
                      </>
                    ) : (
                      <>
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Verificar y Guardar
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Chat de Prueba de AI */}
          <div className="border-t pt-4 mt-4">
            <Card className="border-2 shadow-sm border-gray-200">
              <CardContent className="pt-6 p-0">
                {/* Header del Chat */}
                <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-4 rounded-t-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-5 w-5" />
                      <h3 className="font-semibold">Chat de Prueba de AI</h3>
                    </div>
                    {mensajesChat.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={limpiarChat}
                        className="text-white hover:bg-blue-700"
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Limpiar
                      </Button>
                    )}
                  </div>
                  <p className="text-sm text-blue-100 mt-1">
                    Haz cualquier pregunta y recibe respuestas. Puedes usar documentos como contexto. Presiona Enter para enviar.
                  </p>
                </div>

                {/* Ãrea de Chat */}
                <div className="bg-gray-50 h-[500px] flex flex-col">
                  {/* Mensajes */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {mensajesChat.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-gray-400">
                        <MessageSquare className="h-12 w-12 mb-3 opacity-50" />
                        <p className="text-sm">No hay mensajes aÃºn</p>
                        <p className="text-xs mt-1">Escribe una pregunta para comenzar</p>
                      </div>
                    ) : (
                      mensajesChat.map((mensaje) => (
                        <div
                          key={mensaje.id}
                          className={`flex gap-3 ${
                            mensaje.tipo === 'user' ? 'justify-end' : 'justify-start'
                          }`}
                        >
                          {mensaje.tipo === 'ai' && (
                            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
                              <Brain className="h-4 w-4 text-white" />
                            </div>
                          )}
                          <div
                            className={`max-w-[80%] rounded-lg p-3 ${
                              mensaje.tipo === 'user'
                                ? 'bg-blue-500 text-white'
                                : 'bg-white border border-gray-200 text-gray-800'
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap break-words">
                              {mensaje.texto}
                            </p>
                            {mensaje.metadata && mensaje.tipo === 'ai' && (
                              <div className="mt-2 pt-2 border-t border-gray-200 flex flex-wrap gap-2 text-xs text-gray-500">
                                {mensaje.metadata.tokens && (
                                  <span>Tokens: {mensaje.metadata.tokens}</span>
                                )}
                                {mensaje.metadata.tiempo && (
                                  <span>Tiempo: {mensaje.metadata.tiempo.toFixed(2)}s</span>
                                )}
                                {mensaje.metadata.modelo && (
                                  <span>Modelo: {mensaje.metadata.modelo}</span>
                                )}
                                {mensaje.metadata.documentos !== undefined && (
                                  <span>Documentos: {mensaje.metadata.documentos}</span>
                                )}
                              </div>
                            )}
                            <p className="text-xs mt-1 opacity-70">
                              {mensaje.timestamp.toLocaleTimeString('es-ES', {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </p>
                          </div>
                          {mensaje.tipo === 'user' && (
                            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">
                              <User className="h-4 w-4 text-gray-600" />
                            </div>
                          )}
                        </div>
                      ))
                    )}

                    {/* Indicador de escritura */}
                    {probando && (
                      <div className="flex gap-3 justify-start">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
                          <Brain className="h-4 w-4 text-white" />
                        </div>
                        <div className="bg-white border border-gray-200 rounded-lg p-3">
                          <div className="flex gap-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Input de mensaje */}
                  <div className="border-t bg-white p-4">
                    <div className="flex items-end gap-2">
                      <div className="flex-1 relative">
                        <Textarea
                          ref={textareaRef}
                          value={preguntaPrueba}
                          onChange={(e) => setPreguntaPrueba(e.target.value)}
                          onKeyDown={handleKeyDown}
                          placeholder="Escribe tu pregunta aquÃ­... (Presiona Enter para enviar, Shift+Enter para nueva lÃ­nea)"
                          rows={3}
                          className="resize-none pr-12"
                          disabled={probando || !config.openai_api_key?.trim()}
                        />
                        <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                          {preguntaPrueba.length > 0 && `${preguntaPrueba.length} caracteres`}
                        </div>
                      </div>
                      <Button
                        onClick={handleProbar}
                        disabled={probando || !preguntaPrueba.trim() || !config.openai_api_key?.trim()}
                        className="h-[72px] px-4"
                      >
                        {probando ? (
                          <Loader2 className="h-5 w-5 animate-spin" />
                        ) : (
                          <ChevronRight className="h-5 w-5" />
                        )}
                      </Button>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="usar-documentos"
                          checked={usarDocumentos}
                          onChange={(e) => setUsarDocumentos(e.target.checked)}
                          className="rounded"
                        />
                        <label htmlFor="usar-documentos" className="text-xs text-gray-600 cursor-pointer">
                          Usar documentos de contexto
                        </label>
                      </div>
                      <p className="text-xs text-gray-500">
                        Enter para enviar â€¢ Shift+Enter para nueva lÃ­nea
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* PestaÃ±a 2: Entrenamiento Mejorado */}
        <TabsContent value="entrenamiento" className="space-y-4 mt-6">
          <EntrenamientoMejorado />
        </TabsContent>

        {/* PestaÃ±a 3: Sistema HÃ­brido */}
        <TabsContent value="sistema-hibrido" className="space-y-4 mt-6">
          <Tabs value={activeHybridTab} onValueChange={setActiveHybridTab} className="w-full">
            {/* Dashboard eliminado - redundante con EntrenamientoMejorado */}
            <TabsList className="grid w-full grid-cols-6 bg-gray-100/50 p-1 rounded-lg">
              <TabsTrigger
                value="fine-tuning"
                className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
              >
                <Brain className="h-4 w-4" />
                Fine-tuning
              </TabsTrigger>
              <TabsTrigger
                value="rag"
                className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
              >
                <Zap className="h-4 w-4" />
                RAG
              </TabsTrigger>
              <TabsTrigger
                value="diccionario-semantico"
                className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
              >
                <FileText className="h-4 w-4" />
                Diccionario
              </TabsTrigger>
              <TabsTrigger
                value="definiciones-campos"
                className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
              >
                <Database className="h-4 w-4" />
                Campos
              </TabsTrigger>
              <TabsTrigger
                value="calificaciones-chat"
                className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
              >
                <X className="h-4 w-4" />
                Calificaciones
              </TabsTrigger>
            </TabsList>

            <TabsContent value="fine-tuning" className="mt-6">
              <FineTuningTab />
            </TabsContent>

            <TabsContent value="rag" className="mt-6">
              <RAGTab />
            </TabsContent>

            <TabsContent value="diccionario-semantico" className="mt-6">
              <DiccionarioSemanticoTab />
            </TabsContent>

            <TabsContent value="definiciones-campos" className="mt-6">
              <DefinicionesCamposTab />
            </TabsContent>

            <TabsContent value="calificaciones-chat" className="mt-6">
              <CalificacionesChatTab />
            </TabsContent>
          </Tabs>
        </TabsContent>
      </Tabs>
    </div>
  )
}

