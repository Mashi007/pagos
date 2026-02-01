import { useState, useEffect } from 'react'
import {
  FileText,
  Search,
  Zap,
  Loader2,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Upload,
  Edit,
  Trash2,
  Save,
} from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { aiTrainingService, DocumentoEmbedding } from '../../services/aiTrainingService'
import { apiClient } from '../../services/api'
import { toast } from 'sonner'

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

export function RAGTab() {
  // âœ… Por defecto mostrar la pestaña de Gestión de Documentos para facilitar la carga
  const [activeSubTab, setActiveSubTab] = useState('documentos')

  // Estados para embeddings
  const [estado, setEstado] = useState<{
    total_documentos: number
    documentos_con_embeddings: number
    total_embeddings: number
    ultima_actualizacion?: string
  } | null>(null)
  const [cargando, setCargando] = useState(false)
  const [generando, setGenerando] = useState(false)
  const [buscando, setBuscando] = useState(false)

  // Búsqueda semántica
  const [preguntaBusqueda, setPreguntaBusqueda] = useState('')
  const [resultados, setResultados] = useState<DocumentoEmbedding[]>([])
  const [topK, setTopK] = useState(3)

  // Estados para gestión de documentos
  const [documentos, setDocumentos] = useState<DocumentoAI[]>([])
  const [cargandoDocumentos, setCargandoDocumentos] = useState(false)
  const [nuevoDocumento, setNuevoDocumento] = useState({
    titulo: '',
    descripcion: '',
    archivo: null as File | null,
  })
  const [subiendoDocumento, setSubiendoDocumento] = useState(false)
  const [editandoDocumento, setEditandoDocumento] = useState<number | null>(null)
  const [documentoEditado, setDocumentoEditado] = useState({
    titulo: '',
    descripcion: '',
  })
  const [actualizandoDocumento, setActualizandoDocumento] = useState(false)
  const [procesandoDocumento, setProcesandoDocumento] = useState<number | null>(null)

  const cargarEstado = async () => {
    setCargando(true)
    try {
      const data = await aiTrainingService.getEstadoEmbeddings()
      setEstado(data)
    } catch (error: any) {
      console.error('Error cargando estado:', error)
      toast.error('Error al cargar estado de embeddings')
    } finally {
      setCargando(false)
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

  useEffect(() => {
    cargarEstado()
    cargarDocumentos()
  }, [])

  const handleGenerarEmbeddings = async (todos: boolean = true) => {
    setGenerando(true)
    try {
      const result = await aiTrainingService.generarEmbeddings(todos ? undefined : [])
      toast.success(
        `Embeddings generados: ${result.documentos_procesados} documentos, ${result.total_embeddings} embeddings`
      )
      cargarEstado()
    } catch (error: any) {
      toast.error('Error al generar embeddings')
    } finally {
      setGenerando(false)
    }
  }

  const handleBuscar = async () => {
    if (!preguntaBusqueda.trim()) {
      toast.error('Ingresa una pregunta para buscar')
      return
    }

    setBuscando(true)
    try {
      const result = await aiTrainingService.buscarDocumentosRelevantes(preguntaBusqueda, topK)
      setResultados(result.documentos || [])
      if (result.documentos && result.documentos.length === 0) {
        toast.info('No se encontraron documentos relevantes')
      }
    } catch (error: any) {
      toast.error('Error al buscar documentos')
    } finally {
      setBuscando(false)
    }
  }

  const porcentajeCompletado =
    estado && estado.total_documentos > 0
      ? (estado.documentos_con_embeddings / estado.total_documentos) * 100
      : 0

  // Funciones para gestión de documentos
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const tiposPermitidos = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
      if (!tiposPermitidos.includes(file.type)) {
        toast.error('Tipo de archivo no permitido. Use PDF, TXT o DOCX')
        return
      }
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
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      toast.success('Documento subido exitosamente')
      setNuevoDocumento({ titulo: '', descripcion: '', archivo: null })
      await cargarDocumentos()
      await cargarEstado()
    } catch (error: any) {
      console.error('Error subiendo documento:', error)
      toast.error(error?.response?.data?.detail || error?.message || 'Error subiendo documento')
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
      
      // Mensaje mejorado según el resultado
      if (respuesta.mensaje?.includes('ya estaba procesado') || respuesta.contenido_en_bd) {
        toast.success(`âœ… ${respuesta.mensaje || 'Documento procesado'} (${respuesta.caracteres_extraidos || 0} caracteres)`, {
          description: 'El contenido ya estaba disponible en la base de datos'
        })
      } else {
        toast.success(`Documento procesado exitosamente (${respuesta.caracteres_extraidos || 0} caracteres extraídos)`)
      }
      
      await cargarDocumentos()
      await cargarEstado()
    } catch (error: any) {
      console.error('Error procesando documento:', error)
      // Intentar obtener el mensaje del backend de múltiples fuentes
      let mensajeError = error?.response?.data?.detail || 
                        error?.response?.data?.message || 
                        error?.message || 
                        'Error procesando documento'

      // Simplificar mensajes largos de diagnóstico
      if (mensajeError.includes('El archivo físico no existe')) {
        mensajeError = 'El archivo físico no existe en el servidor. Por favor, elimina este documento y súbelo nuevamente.'
      } else if (mensajeError.length > 200) {
        // Truncar mensajes muy largos pero mantener la parte importante
        const partes = mensajeError.split('\n')
        mensajeError = partes[0] + (partes.length > 1 ? ' (Ver consola para más detalles)' : '')
      }

      toast.error(mensajeError, {
        duration: 8000, // Aumentar duración para mensajes importantes
      })
    } finally {
      setProcesandoDocumento(null)
    }
  }

  const handleEliminarDocumento = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar este documento?')) return

    try {
      await apiClient.delete(`/api/v1/configuracion/ai/documentos/${id}`)
      toast.success('Documento eliminado exitosamente')
      await cargarDocumentos()
      await cargarEstado()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error eliminando documento')
    }
  }

  const handleIniciarEdicion = (doc: DocumentoAI) => {
    setEditandoDocumento(doc.id)
    setDocumentoEditado({ titulo: doc.titulo, descripcion: doc.descripcion || '' })
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
      toast.error(error?.response?.data?.detail || 'Error actualizando documento')
    } finally {
      setActualizandoDocumento(false)
    }
  }

  const handleActivarDesactivarDocumento = async (id: number, activo: boolean) => {
    const documento = documentos.find(doc => doc.id === id)
    if (activo && documento && !documento.contenido_procesado) {
      if (!confirm('Este documento no está procesado. ¿Deseas procesarlo ahora antes de activarlo?')) {
        return
      }
      await handleProcesarDocumento(id)
    }

    try {
      await apiClient.patch(`/api/v1/configuracion/ai/documentos/${id}/activar`, { activo })
      toast.success(`Documento ${activo ? 'activado' : 'desactivado'} exitosamente`)
      await cargarDocumentos()
      await cargarEstado()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error cambiando estado del documento')
    }
  }

  const formatearTamaño = (bytes: number | null) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6" />
            RAG Mejorado - Documentos y Embeddings
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Gestiona documentos y búsqueda semántica mejorada con embeddings vectoriales
          </p>
        </div>
        <Button onClick={() => { cargarEstado(); cargarDocumentos(); }} variant="outline" size="sm" disabled={cargando || cargandoDocumentos}>
          {(cargando || cargandoDocumentos) ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Actualizando...
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4 mr-2" />
              Actualizar
            </>
          )}
        </Button>
      </div>

      {/* Tabs internos */}
      <Tabs value={activeSubTab} onValueChange={setActiveSubTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="documentos">
            <FileText className="h-4 w-4 mr-2" />
            Gestión de Documentos
          </TabsTrigger>
          <TabsTrigger value="embeddings">
            <Zap className="h-4 w-4 mr-2" />
            Embeddings y Búsqueda
          </TabsTrigger>
        </TabsList>

        {/* Tab: Gestión de Documentos */}
        <TabsContent value="documentos" className="space-y-4 mt-6">
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
                                {doc.activo && !doc.contenido_procesado && (
                                  <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                                    <AlertCircle className="h-3 w-3 mr-1" />
                                    âš ï¸ No disponible para AI
                                  </Badge>
                                )}
                                {doc.activo && doc.contenido_procesado && (
                                  <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                                    <CheckCircle className="h-3 w-3 mr-1" />
                                    âœ… Disponible para AI
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

        {/* Tab: Embeddings y Búsqueda */}
        <TabsContent value="embeddings" className="space-y-4 mt-6">
          {/* Estado de Embeddings */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="h-5 w-5 text-blue-600" />
            <h4 className="font-semibold">Estado de Embeddings</h4>
          </div>

          {cargando ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          ) : estado ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="border rounded-lg p-4">
                  <div className="text-sm text-gray-500 mb-1">Total Documentos</div>
                  <div className="text-2xl font-bold">{estado.total_documentos}</div>
                </div>
                <div className="border rounded-lg p-4">
                  <div className="text-sm text-gray-500 mb-1">Con Embeddings</div>
                  <div className="text-2xl font-bold text-green-600">
                    {estado.documentos_con_embeddings}
                  </div>
                </div>
                <div className="border rounded-lg p-4">
                  <div className="text-sm text-gray-500 mb-1">Total Embeddings</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {estado.total_embeddings}
                  </div>
                </div>
              </div>

              {/* Barra de progreso */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Progreso de procesamiento</span>
                  <span className="font-medium">{porcentajeCompletado.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all"
                    style={{ width: `${porcentajeCompletado}%` }}
                  />
                </div>
              </div>

              {estado.ultima_actualizacion && (
                <div className="text-sm text-gray-500">
                  Última actualización:{' '}
                  {new Date(estado.ultima_actualizacion).toLocaleString('es-ES')}
                </div>
              )}

              {/* Acciones */}
              <div className="flex gap-2 pt-4">
                <Button
                  onClick={() => handleGenerarEmbeddings(true)}
                  disabled={generando}
                  className="flex-1"
                >
                  {generando ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Generando...
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4 mr-2" />
                      Generar Embeddings para Todos los Documentos
                    </>
                  )}
                </Button>
              </div>

              {estado.documentos_con_embeddings < estado.total_documentos && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-amber-900">
                        Documentos pendientes de procesar
                      </p>
                      <p className="text-xs text-amber-700 mt-1">
                        {estado.total_documentos - estado.documentos_con_embeddings} documentos
                        aún no tienen embeddings. Genera embeddings para mejorar la búsqueda
                        semántica.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>No se pudo cargar el estado</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Búsqueda Semántica */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-4">
            <Search className="h-5 w-5 text-green-600" />
            <h4 className="font-semibold">Búsqueda Semántica de Prueba</h4>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Pregunta o consulta</label>
              <Textarea
                placeholder="Ej: ¿Cuáles son las políticas de préstamos para clientes nuevos?"
                value={preguntaBusqueda}
                onChange={(e) => setPreguntaBusqueda(e.target.value)}
                rows={3}
                className="mb-2"
              />
            </div>

            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">Documentos a retornar (Top K)</label>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value) || 3)}
                  className="w-24"
                />
              </div>
              <Button onClick={handleBuscar} disabled={buscando || !preguntaBusqueda.trim()}>
                {buscando ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Buscando...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Buscar Documentos Relevantes
                  </>
                )}
              </Button>
            </div>

            {/* Resultados */}
            {resultados.length > 0 && (
              <div className="mt-6 space-y-4">
                <h5 className="font-medium flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  Documentos Encontrados ({resultados.length})
                </h5>
                {resultados.map((doc, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="font-medium mb-1">
                          Documento ID: {doc.documento_id}
                          {doc.chunk_index !== undefined && (
                            <Badge variant="secondary" className="ml-2">
                              Chunk {doc.chunk_index}
                            </Badge>
                          )}
                        </div>
                        {doc.similitud !== undefined && (
                          <div className="text-sm text-gray-600 mb-2">
                            Similitud: {(doc.similitud * 100).toFixed(1)}%
                          </div>
                        )}
                        {doc.texto_chunk && (
                          <div className="text-sm text-gray-700 bg-gray-50 rounded p-2 mt-2">
                            <div className="line-clamp-3">{doc.texto_chunk}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {resultados.length === 0 && preguntaBusqueda && !buscando && (
              <div className="text-center py-8 text-gray-500">
                <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                <p>No se encontraron documentos relevantes</p>
                <p className="text-xs mt-1">
                  Intenta con otra pregunta o genera embeddings para más documentos
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

          {/* Información */}
          <Card>
            <CardContent className="pt-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <Zap className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="font-semibold text-blue-900 mb-1">¿Qué es RAG Mejorado?</p>
                    <p className="text-sm text-blue-800">
                      RAG (Retrieval-Augmented Generation) mejorado usa embeddings vectoriales para
                      encontrar documentos más relevantes a cada pregunta. Esto mejora la precisión de
                      las respuestas del AI al incluir solo el contexto más pertinente.
                    </p>
                    <ul className="text-xs text-blue-700 mt-2 list-disc list-inside space-y-1">
                      <li>Genera embeddings para todos tus documentos</li>
                      <li>El sistema busca automáticamente documentos relevantes</li>
                      <li>Mejora la precisión y reduce costos de tokens</li>
                    </ul>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

