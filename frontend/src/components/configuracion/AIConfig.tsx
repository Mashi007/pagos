import { useState, useEffect } from 'react'
import { Brain, Save, Eye, EyeOff, Upload, FileText, Trash2, BarChart3, CheckCircle, AlertCircle, Loader2, TestTube } from 'lucide-react'
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
  
  // Estado para pruebas
  const [probando, setProbando] = useState(false)
  const [preguntaPrueba, setPreguntaPrueba] = useState('')
  const [usarDocumentos, setUsarDocumentos] = useState(true)
  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)
  const [activeTab, setActiveTab] = useState('configuracion')

  useEffect(() => {
    cargarConfiguracion()
    cargarDocumentos()
    cargarMetricas()
  }, [])

  const cargarConfiguracion = async () => {
    try {
      const data = await apiClient.get<AIConfig>('/api/v1/configuracion/ai/configuracion')
      setConfig(data)
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
      await apiClient.put('/api/v1/configuracion/ai/configuracion', config)
      toast.success('Configuración de AI guardada exitosamente')
      await cargarConfiguracion()
      await cargarMetricas()
    } catch (error: any) {
      console.error('Error guardando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error guardando configuración'
      toast.error(mensajeError)
    } finally {
      setGuardando(false)
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

  const formatearTamaño = (bytes: number | null) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const handleProbar = async () => {
    if (!config.openai_api_key?.trim()) {
      toast.error('Debes configurar el OpenAI API Key primero')
      return
    }

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
        pregunta: preguntaPrueba.trim() || undefined,
        usar_documentos: usarDocumentos,
      })
      
      setResultadoPrueba(resultado)
      
      if (resultado.success) {
        toast.success('Respuesta generada exitosamente')
      } else {
        toast.error(resultado.mensaje || 'Error generando respuesta')
      }
    } catch (error: any) {
      console.error('Error probando AI:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error probando AI'
      toast.error(mensajeError)
      setResultadoPrueba({ success: false, mensaje: mensajeError })
    } finally {
      setProbando(false)
    }
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

                <div>
                  <label className="text-sm font-medium block mb-2">Estado</label>
                  <Select value={config.activo} onValueChange={(value) => handleChange('activo', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Activo</SelectItem>
                      <SelectItem value="false">Inactivo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <Button onClick={handleGuardar} disabled={guardando}>
                  {guardando ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Guardar Configuración
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Prueba de AI */}
          <div className="border-t pt-4 mt-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                <TestTube className="h-5 w-5" />
                Prueba de Respuesta de AI
              </h3>
              <p className="text-sm text-blue-700 mb-4">
                Envía una pregunta de prueba para verificar que la configuración de ChatGPT funciona correctamente y genera respuestas contextualizadas.
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium block mb-2">
                    Pregunta de Prueba <span className="text-gray-500">(opcional)</span>
                  </label>
                  <Textarea
                    value={preguntaPrueba}
                    onChange={(e) => setPreguntaPrueba(e.target.value)}
                    placeholder="Escribe aquí tu pregunta de prueba... (Ej: ¿Cuáles son los requisitos para un préstamo?)"
                    rows={4}
                    className="resize-y"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Si no especificas una pregunta, se usará una pregunta predeterminada.
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={usarDocumentos}
                    onChange={(e) => setUsarDocumentos(e.target.checked)}
                    className="rounded"
                  />
                  <label className="text-sm font-medium">
                    Usar documentos de contexto para la respuesta
                  </label>
                </div>
                
                <Button
                  type="button"
                  onClick={handleProbar}
                  disabled={probando || !config.openai_api_key?.trim()}
                  className="w-full"
                >
                  {probando ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generando Respuesta...
                    </>
                  ) : (
                    <>
                      <TestTube className="w-4 h-4 mr-2" />
                      Probar Respuesta de AI
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* Resultado de prueba */}
          {resultadoPrueba && (
            <div className={`p-4 rounded-lg border ${
              resultadoPrueba.success
                ? 'bg-green-50 border-green-200' 
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-start gap-2">
                {resultadoPrueba.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`text-sm font-medium mb-2 ${
                    resultadoPrueba.success ? 'text-green-900' : 'text-red-900'
                  }`}>
                    {resultadoPrueba.mensaje}
                  </p>
                  
                  {resultadoPrueba.success && resultadoPrueba.respuesta && (
                    <div className="mt-3 space-y-2">
                      <div className="bg-white rounded p-3 border">
                        <p className="text-xs font-semibold text-gray-600 mb-1">Pregunta:</p>
                        <p className="text-sm text-gray-800">{resultadoPrueba.pregunta}</p>
                      </div>
                      <div className="bg-white rounded p-3 border">
                        <p className="text-xs font-semibold text-gray-600 mb-1">Respuesta de AI:</p>
                        <p className="text-sm text-gray-800 whitespace-pre-wrap">{resultadoPrueba.respuesta}</p>
                      </div>
                      <div className="flex gap-4 text-xs text-gray-600 mt-2">
                        {resultadoPrueba.tokens_usados && (
                          <span>Tokens: {resultadoPrueba.tokens_usados}</span>
                        )}
                        {resultadoPrueba.tiempo_respuesta && (
                          <span>Tiempo: {resultadoPrueba.tiempo_respuesta}s</span>
                        )}
                        {resultadoPrueba.modelo_usado && (
                          <span>Modelo: {resultadoPrueba.modelo_usado}</span>
                        )}
                        {resultadoPrueba.documentos_consultados !== undefined && (
                          <span>Documentos: {resultadoPrueba.documentos_consultados}</span>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {!resultadoPrueba.success && resultadoPrueba.error_code && (
                    <p className="text-sm text-red-600 mt-1">Código de error: {resultadoPrueba.error_code}</p>
                  )}
                </div>
              </div>
            </div>
          )}
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
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <h5 className="font-semibold">{doc.titulo}</h5>
                              <Badge variant={doc.activo ? "default" : "secondary"}>
                                {doc.activo ? "Activo" : "Inactivo"}
                              </Badge>
                              {doc.contenido_procesado && (
                                <Badge variant="outline">
                                  <CheckCircle className="h-3 w-3 mr-1" />
                                  Procesado
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
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEliminarDocumento(doc.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
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
              {cargandoMetricas ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                </div>
              ) : metricas ? (
                <>
                  {/* Métricas de Documentos */}
                  <div>
                    <h4 className="font-semibold mb-4 flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      Documentos
                    </h4>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
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

