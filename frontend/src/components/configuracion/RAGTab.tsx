import { useState, useEffect } from 'react'
import {
  FileText,
  Search,
  Zap,
  Loader2,
  CheckCircle,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { aiTrainingService, DocumentoEmbedding } from '@/services/aiTrainingService'
import { toast } from 'sonner'

export function RAGTab() {
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

  useEffect(() => {
    cargarEstado()
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6" />
            RAG Mejorado - Embeddings
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Búsqueda semántica mejorada con embeddings vectoriales
          </p>
        </div>
        <Button onClick={cargarEstado} variant="outline" size="sm" disabled={cargando}>
          {cargando ? (
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
    </div>
  )
}

