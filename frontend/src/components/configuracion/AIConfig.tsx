import { useState, useEffect, useRef } from 'react'
import { Brain, Save, Eye, EyeOff, Upload, FileText, Trash2, BarChart3, CheckCircle, AlertCircle, Loader2, TestTube, ChevronRight, MessageSquare, User, Edit, Zap } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import { apiClient } from '@/services/api'

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
  tamaño_bytes: number | null
  contenido_procesado: boolean
  activo: boolean
  creado_en: string
  actualizado_en: string
}

interface MetricasAI {
  documentos: {
    total: number
    activos: number
    procesados: number
    pendientes: number
    tamaño_total_bytes: number
    tamaño_total_mb: number
  }
  configuracion: {
    ai_activo: boolean
    modelo: string
    tiene_token: boolean
  }
  fecha_consulta: string
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
  const [metricas, setMetricas] = useState<MetricasAI | null>(null)
  const [cargandoMetricas, setCargandoMetricas] = useState(false)
  
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
  
  // Estado para verificar configuración correcta
  const [configuracionCorrecta, setConfiguracionCorrecta] = useState(false)
  const [verificandoConfig, setVerificandoConfig] = useState(false)
  const [tokenAnterior, setTokenAnterior] = useState<string>('')

  useEffect(() => {
    cargarConfiguracion()
    cargarDocumentos()
    cargarMetricas()
  }, [])

  // Verificar configuración solo cuando el usuario cambia el token manualmente
  // NO verificar en cada carga de página - el token se guarda permanentemente en BD
  useEffect(() => {
    // Solo verificar si el token cambió manualmente (no en la carga inicial)
    if (tokenAnterior && tokenAnterior !== config.openai_api_key && config.openai_api_key && config.openai_api_key.trim() && config.openai_api_key.startsWith('sk-')) {
      // El usuario cambió el token manualmente, verificar
      const timer = setTimeout(() => {
        verificarConfiguracion(false)
      }, 1000)
      return () => clearTimeout(timer)
    }
    
    // En la carga inicial, asumir que está correcto si ya está guardado (se guardó permanentemente en BD)
    if (config.openai_api_key && config.openai_api_key.trim() && config.openai_api_key.startsWith('sk-') && config.activo === 'true') {
      // El token está guardado permanentemente en BD, asumir que es válido
      setConfiguracionCorrecta(true)
    } else if (config.openai_api_key !== '') {
      setConfiguracionCorrecta(false)
    }
    
    // Actualizar token anterior solo después de la primera carga
    if (!tokenAnterior && config.openai_api_key) {
      setTokenAnterior(config.openai_api_key)
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
        pregunta: 'test',
        usar_documentos: false,
      })
      
      // Si la respuesta es exitosa o el error no es de autenticación, la config está correcta
      const esValida = resultado.success || !resultado.mensaje?.includes('API key')
      setConfiguracionCorrecta(esValida)
      
      // Si el token es válido y se debe guardar automáticamente, guardar la configuración
      if (esValida && guardarAutomaticamente) {
        try {
          await apiClient.put('/api/v1/configuracion/ai/configuracion', config)
          toast.success('✅ Token válido confirmado y guardado automáticamente')
          await cargarConfiguracion()
          await cargarMetricas()
        } catch (saveError: any) {
          console.error('Error guardando configuración automáticamente:', saveError)
          toast.error('Token válido pero error al guardar. Guarda manualmente.')
        }
      }
      
      return esValida
    } catch (error: any) {
      // Si el error es de autenticación, la config no está correcta
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
      setConfig({
        openai_api_key: data.openai_api_key || '',
        modelo: data.modelo || 'gpt-3.5-turbo',
        temperatura: data.temperatura || '0.7',
        max_tokens: data.max_tokens || '1000',
        activo: data.activo || 'false',
      })
    } catch (error) {
      console.error('Error cargando configuración de AI:', error)
      toast.error('Error cargando configuración')
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

  const cargarMetricas = async () => {
    setCargandoMetricas(true)
    try {
      const data = await apiClient.get<MetricasAI>('/api/v1/configuracion/ai/metricas')
      setMetricas(data)
    } catch (error) {
      console.error('Error cargando métricas:', error)
      toast.error('Error cargando métricas')
    } finally {
      setCargandoMetricas(false)
    }
  }

  const handleChange = (campo: keyof AIConfig, valor: string) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }

  const handleGuardar = async () => {
    setGuardando(true)
    try {
      // Verificar el token antes de guardar
      const tokenValido = await verificarConfiguracion(false)
      
      if (!tokenValido && config.openai_api_key?.trim() && config.openai_api_key.startsWith('sk-')) {
        // Si hay un token pero no es válido, advertir pero permitir guardar
        const confirmar = confirm('⚠️ El token no parece ser válido. ¿Deseas guardarlo de todas formas?')
        if (!confirmar) {
          setGuardando(false)
          return
        }
      }
      
      await apiClient.put('/api/v1/configuracion/ai/configuracion', config)
      toast.success('✅ Configuración de AI guardada exitosamente y de forma permanente')
      await cargarConfiguracion()
      await cargarMetricas()
      // Verificar configuración después de guardar
      await verificarConfiguracion(false)
    } catch (error: any) {
      console.error('Error guardando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error guardando configuración'
      toast.error(mensajeError)
    } finally {
      setGuardando(false)
    }
  }
  
  const handleVerificarYGuardar = async () => {
    // Verificar y guardar automáticamente si el token es válido
    await verificarConfiguracion(true)
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
      
      // Validar tamaño (máximo 10MB)
      if (file.size > 10 * 1024 * 1024) {
        toast.error('El archivo es demasiado grande. Máximo 10MB')
        return
      }
      
      setNuevoDocumento(prev => ({ ...prev, archivo: file }))
    }
  }

  const handleSubirDocumento = async () => {
    if (!nuevoDocumento.titulo.trim()) {
      toast.error('El título es requerido')
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
      await cargarMetricas()
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
      }>(`/api/v1/configuracion/ai/documentos/${id}/procesar`)
      toast.success(`Documento procesado exitosamente (${respuesta.caracteres_extraidos || 0} caracteres extraídos)`)
      await cargarDocumentos()
      await cargarMetricas()
    } catch (error: any) {
      console.error('Error procesando documento:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error procesando documento'
      toast.error(`Error al procesar documento: ${mensajeError}`)
    } finally {
      setProcesandoDocumento(null)
    }
  }

  const handleEliminarDocumento = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar este documento?')) {
      return
    }

    try {
      await apiClient.delete(`/api/v1/configuracion/ai/documentos/${id}`)
      toast.success('Documento eliminado exitosamente')
      await cargarDocumentos()
      await cargarMetricas()
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
      toast.error('El título es requerido')
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
    try {
      await apiClient.patch(`/api/v1/configuracion/ai/documentos/${id}/activar`, { activo })
      toast.success(`Documento ${activo ? 'activado' : 'desactivado'} exitosamente`)
      await cargarDocumentos()
      await cargarMetricas()
    } catch (error: any) {
      console.error('Error activando/desactivando documento:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error cambiando estado del documento'
      toast.error(mensajeError)
    }
  }

  const formatearTamaño = (bytes: number | null) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  // Scroll automático al final del chat
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
    
    // Validar formato básico de API key (debe empezar con sk-)
    if (!apiKey.startsWith('sk-')) {
      toast.error('El API Key debe empezar con "sk-". Verifica que sea un token válido de OpenAI.')
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
        texto: `❌ Error: ${mensajeError}`,
        timestamp: new Date(),
      }
      setMensajesChat(prev => [...prev, mensajeErrorChat])
      toast.error(mensajeError)
      setResultadoPrueba({ success: false, mensaje: mensajeError })
    } finally {
      setProbando(false)
    }
  }

  // Manejar Enter para enviar (Shift+Enter para nueva línea)
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

  return (
    <div className="space-y-6">
      {/* Información */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold text-blue-900">Configuración de Inteligencia Artificial</h3>
        </div>
        <p className="text-sm text-blue-700">
          Configura ChatGPT para respuestas automáticas contextualizadas en WhatsApp usando tus documentos como base de conocimiento.
        </p>
      </div>

      {/* Tabs con 3 pestañas */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="configuracion">Configuración</TabsTrigger>
          <TabsTrigger value="documentos">Documentos</TabsTrigger>
          <TabsTrigger value="metricas">Métricas</TabsTrigger>
        </TabsList>

        {/* Pestaña 1: Configuración */}
        <TabsContent value="configuracion" className="space-y-4">
          {/* ✅ Toggle Activar/Desactivar AI */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className="text-sm font-semibold text-gray-900 block mb-1">
                  Servicio de AI
                </label>
                <p className="text-xs text-gray-600">
                  {config.activo === 'true' 
                    ? '✅ El sistema está usando AI para generar respuestas automáticas' 
                    : '⚠️ El sistema NO usará AI. Activa el servicio para habilitar respuestas inteligentes.'}
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.activo === 'true'}
                  onChange={(e) => {
                    handleChange('activo', e.target.checked ? 'true' : 'false')
                    toast.info(e.target.checked ? 'AI activado - Las respuestas inteligentes se habilitarán al guardar' : 'AI desactivado - Las respuestas inteligentes se deshabilitarán al guardar')
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

          {/* ✅ Estado: Configuración correcta */}
          {config.openai_api_key?.trim() && config.openai_api_key.startsWith('sk-') && configuracionCorrecta && (
            <div className="bg-white border-2 border-green-500 rounded-lg p-4">
              <div className="flex items-center gap-3">
                {/* Semáforo Verde */}
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className="w-4 h-4 bg-green-500 rounded-full shadow-lg"></div>
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900">
                    Configuración correcta
                  </p>
                  <p className="text-sm text-gray-600">
                    OpenAI aceptó la conexión. Puedes usar AI para generar respuestas.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ⚠️ Estado: API Key no válida o no configurada */}
          {config.openai_api_key?.trim() && !configuracionCorrecta && !verificandoConfig && (
            <div className="bg-white border-2 border-amber-400 rounded-lg p-4">
              <div className="flex items-center gap-3">
                {/* Semáforo Amarillo */}
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                  <div className="w-4 h-4 bg-amber-500 rounded-full shadow-lg"></div>
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900 mb-2">
                    API Key no válida o no configurada
                  </p>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>1. Verifica que tu API Key comience con "sk-"</p>
                    <p>2. Asegúrate de que la API Key sea válida y tenga créditos disponibles</p>
                    <p>3. Obtén una nueva API Key en: <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="underline text-blue-600">platform.openai.com/api-keys</a></p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ❌ Estado: No configurado */}
          {(!config.openai_api_key?.trim() || !config.openai_api_key.startsWith('sk-')) && (
            <div className="bg-white border-2 border-red-500 rounded-lg p-4">
              <div className="flex items-center gap-3">
                {/* Semáforo Rojo */}
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                  <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                  <div className="w-4 h-4 bg-red-500 rounded-full shadow-lg"></div>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900">
                    Configuración incompleta
                  </p>
                  <p className="text-sm text-gray-600">
                    Ingresa una API Key válida de OpenAI para habilitar el servicio de AI.
                  </p>
                </div>
              </div>
            </div>
          )}

          <Card>
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
                  Obtén tu API Key en: <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">platform.openai.com/api-keys</a>
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
                      <SelectItem value="gpt-4">GPT-4 (Más potente)</SelectItem>
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
                  <p className="text-xs text-gray-500 mt-1">Máximo de tokens en la respuesta.</p>
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
                        ? '✅ Guardar Configuración (Token Válido)'
                        : 'Guardar Configuración'}
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
            <Card className="border-2">
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

                {/* Área de Chat */}
                <div className="bg-gray-50 h-[500px] flex flex-col">
                  {/* Mensajes */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {mensajesChat.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-gray-400">
                        <MessageSquare className="h-12 w-12 mb-3 opacity-50" />
                        <p className="text-sm">No hay mensajes aún</p>
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
                          placeholder="Escribe tu pregunta aquí... (Presiona Enter para enviar, Shift+Enter para nueva línea)"
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
                        Enter para enviar • Shift+Enter para nueva línea
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Pestaña 2: Documentos */}
        <TabsContent value="documentos" className="space-y-4">
          <Card>
            <CardContent className="pt-6 space-y-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="font-semibold text-amber-900 mb-1">Agregar Documento de Contexto</p>
                    <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
                      <li>Formatos permitidos: PDF, TXT, DOCX</li>
                      <li>Tamaño máximo: 10MB por archivo</li>
                      <li>Los documentos se procesarán para generar respuestas contextualizadas</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Formulario de nuevo documento */}
              <div className="border rounded-lg p-4 space-y-4">
                <h4 className="font-semibold">Nuevo Documento</h4>
                
                <div>
                  <label className="text-sm font-medium block mb-2">Título <span className="text-red-500">*</span></label>
                  <Input
                    value={nuevoDocumento.titulo}
                    onChange={(e) => setNuevoDocumento(prev => ({ ...prev, titulo: e.target.value }))}
                    placeholder="Ej: Políticas de Préstamos"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium block mb-2">Descripción</label>
                  <Textarea
                    value={nuevoDocumento.descripcion}
                    onChange={(e) => setNuevoDocumento(prev => ({ ...prev, descripcion: e.target.value }))}
                    placeholder="Describe de qué trata este documento..."
                    rows={3}
                  />
                </div>

                <div>
                  <label className="text-sm font-medium block mb-2">Archivo <span className="text-red-500">*</span></label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="file"
                      accept=".pdf,.txt,.docx"
                      onChange={handleFileChange}
                      className="flex-1"
                    />
                    {nuevoDocumento.archivo && (
                      <Badge variant="secondary">{nuevoDocumento.archivo.name}</Badge>
                    )}
                  </div>
                </div>

                <Button 
                  onClick={handleSubirDocumento} 
                  disabled={subiendoDocumento || !nuevoDocumento.titulo || !nuevoDocumento.archivo}
                  className="w-full"
                >
                  {subiendoDocumento ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Subiendo...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      Subir Documento
                    </>
                  )}
                </Button>
              </div>

              {/* Lista de documentos */}
              <div className="border-t pt-4">
                <h4 className="font-semibold mb-4">Documentos Existentes</h4>
                
                {cargandoDocumentos ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  </div>
                ) : documentos.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <FileText className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                    <p>No hay documentos cargados</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {documentos.map((doc) => (
                      <div key={doc.id} className="border rounded-lg p-4 hover:bg-gray-50">
                        {editandoDocumento === doc.id ? (
                          // Modo edición
                          <div className="space-y-3">
                            <div>
                              <label className="text-sm font-medium block mb-1">Título <span className="text-red-500">*</span></label>
                              <Input
                                value={documentoEditado.titulo}
                                onChange={(e) => setDocumentoEditado(prev => ({ ...prev, titulo: e.target.value }))}
                                placeholder="Título del documento"
                              />
                            </div>
                            <div>
                              <label className="text-sm font-medium block mb-1">Descripción</label>
                              <Textarea
                                value={documentoEditado.descripcion}
                                onChange={(e) => setDocumentoEditado(prev => ({ ...prev, descripcion: e.target.value }))}
                                placeholder="Descripción del documento"
                                rows={2}
                              />
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                size="sm"
                                onClick={() => handleActualizarDocumento(doc.id)}
                                disabled={actualizandoDocumento || !documentoEditado.titulo.trim()}
                              >
                                {actualizandoDocumento ? (
                                  <>
                                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                    Guardando...
                                  </>
                                ) : (
                                  <>
                                    <Save className="h-4 w-4 mr-1" />
                                    Guardar
                                  </>
                                )}
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={handleCancelarEdicion}
                                disabled={actualizandoDocumento}
                              >
                                Cancelar
                              </Button>
                            </div>
                          </div>
                        ) : (
                          // Modo visualización
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <h5 className="font-semibold">{doc.titulo}</h5>
                                <Badge variant={doc.activo ? "default" : "secondary"}>
                                  {doc.activo ? "Activo" : "Inactivo"}
                                </Badge>
                                {doc.contenido_procesado ? (
                                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                    <CheckCircle className="h-3 w-3 mr-1" />
                                    Procesado
                                  </Badge>
                                ) : (
                                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                                    <AlertCircle className="h-3 w-3 mr-1" />
                                    Sin procesar
                                  </Badge>
                                )}
                              </div>
                              {doc.descripcion && (
                                <p className="text-sm text-gray-600 mb-2">{doc.descripcion}</p>
                              )}
                              <div className="flex items-center gap-4 text-xs text-gray-500">
                                <span>{doc.nombre_archivo}</span>
                                <span>{doc.tipo_archivo.toUpperCase()}</span>
                                <span>{formatearTamaño(doc.tamaño_bytes)}</span>
                                <span>{new Date(doc.creado_en).toLocaleDateString()}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {!doc.contenido_procesado && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleProcesarDocumento(doc.id)}
                                  disabled={procesandoDocumento === doc.id || procesandoDocumento !== null}
                                  className="text-blue-600 hover:text-blue-700"
                                  title="Procesar documento para extraer texto"
                                >
                                  {procesandoDocumento === doc.id ? (
                                    <>
                                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                      Procesando...
                                    </>
                                  ) : (
                                    <>
                                      <FileText className="h-4 w-4 mr-1" />
                                      Procesar
                                    </>
                                  )}
                                </Button>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleIniciarEdicion(doc)}
                                className="text-blue-600 hover:text-blue-700"
                                title="Editar documento"
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleActivarDesactivarDocumento(doc.id, !doc.activo)}
                                className={doc.activo ? "text-amber-600 hover:text-amber-700" : "text-green-600 hover:text-green-700"}
                                title={doc.activo ? "Desactivar documento" : "Activar documento"}
                              >
                                <Zap className={`h-4 w-4 ${doc.activo ? '' : 'opacity-50'}`} />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEliminarDocumento(doc.id)}
                                className="text-red-600 hover:text-red-700"
                                title="Eliminar documento"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Pestaña 3: Métricas */}
        <TabsContent value="metricas" className="space-y-4">
          <Card>
            <CardContent className="pt-6 space-y-4">
              {/* Header con botón de refrescar */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Métricas de AI
                </h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={cargarMetricas}
                  disabled={cargandoMetricas}
                >
                  {cargandoMetricas ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Actualizando...
                    </>
                  ) : (
                    <>
                      <BarChart3 className="h-4 w-4 mr-2" />
                      Actualizar
                    </>
                  )}
                </Button>
              </div>

              {cargandoMetricas ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                </div>
              ) : metricas ? (
                <>
                  {/* Información de última actualización */}
                  {metricas.fecha_consulta && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <BarChart3 className="h-4 w-4 text-blue-600" />
                          <span className="text-sm font-medium text-blue-900">Última Actualización</span>
                        </div>
                        <span className="text-sm text-blue-700">
                          {new Date(metricas.fecha_consulta).toLocaleString('es-ES', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit'
                          })}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Métricas de Documentos */}
                  <div>
                    <h4 className="font-semibold mb-4 flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      Documentos
                    </h4>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                      <div className="border rounded-lg p-4">
                        <div className="text-sm text-gray-500">Total</div>
                        <div className="text-2xl font-bold">{metricas.documentos.total}</div>
                      </div>
                      <div className="border rounded-lg p-4">
                        <div className="text-sm text-gray-500">Activos</div>
                        <div className="text-2xl font-bold text-green-600">{metricas.documentos.activos}</div>
                      </div>
                      <div className="border rounded-lg p-4">
                        <div className="text-sm text-gray-500">Procesados</div>
                        <div className="text-2xl font-bold text-blue-600">{metricas.documentos.procesados}</div>
                      </div>
                      <div className="border rounded-lg p-4">
                        <div className="text-sm text-gray-500">Pendientes</div>
                        <div className="text-2xl font-bold text-amber-600">{metricas.documentos.pendientes}</div>
                      </div>
                      <div className="border rounded-lg p-4">
                        <div className="text-sm text-gray-500">Tamaño Total</div>
                        <div className="text-2xl font-bold">{metricas.documentos.tamaño_total_mb} MB</div>
                      </div>
                    </div>
                  </div>

                  {/* Estado de Configuración */}
                  <div className="border-t pt-4">
                    <h4 className="font-semibold mb-4 flex items-center gap-2">
                      <BarChart3 className="h-5 w-5" />
                      Estado de Configuración
                    </h4>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div className="border rounded-lg p-4">
                        <div className="text-sm text-gray-500 mb-2">AI Activo</div>
                        <Badge variant={metricas.configuracion.ai_activo ? "default" : "secondary"}>
                          {metricas.configuracion.ai_activo ? "✅ Activo" : "❌ Inactivo"}
                        </Badge>
                      </div>
                      <div className="border rounded-lg p-4">
                        <div className="text-sm text-gray-500 mb-2">Modelo</div>
                        <div className="font-semibold">{metricas.configuracion.modelo || "No configurado"}</div>
                      </div>
                      <div className="border rounded-lg p-4">
                        <div className="text-sm text-gray-500 mb-2">Token Configurado</div>
                        <Badge variant={metricas.configuracion.tiene_token ? "default" : "destructive"}>
                          {metricas.configuracion.tiene_token ? "✅ Sí" : "❌ No"}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                  <p>No se pudieron cargar las métricas</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

