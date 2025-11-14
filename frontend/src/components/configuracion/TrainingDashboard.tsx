import { useState, useEffect } from 'react'
import { BarChart3, Brain, FileText, TrendingUp, RefreshCw, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { aiTrainingService, MetricasEntrenamiento } from '@/services/aiTrainingService'
import { toast } from 'sonner'

export function TrainingDashboard() {
  const [metricas, setMetricas] = useState<MetricasEntrenamiento | null>(null)
  const [cargando, setCargando] = useState(false)

  const cargarMetricas = async () => {
    setCargando(true)
    try {
      const data = await aiTrainingService.getMetricasEntrenamiento()
      // Validar que la respuesta tenga la estructura esperada
      if (data && data.conversaciones && data.fine_tuning && data.rag && data.ml_riesgo) {
        setMetricas(data)
      } else {
        // Si el endpoint no existe o devuelve estructura incorrecta, usar valores por defecto
        setMetricas({
          conversaciones: {
            total: 0,
            con_calificacion: 0,
            promedio_calificacion: 0,
            listas_entrenamiento: 0,
          },
          fine_tuning: {
            jobs_totales: 0,
            jobs_exitosos: 0,
            jobs_fallidos: 0,
          },
          rag: {
            documentos_con_embeddings: 0,
            total_embeddings: 0,
          },
          ml_riesgo: {
            modelos_disponibles: 0,
          },
        })
      }
    } catch (error: any) {
      console.error('Error cargando métricas:', error)
      // Si es un 404, el endpoint no existe aún - mostrar mensaje informativo
      if (error?.response?.status === 404) {
        setMetricas({
          conversaciones: {
            total: 0,
            con_calificacion: 0,
            promedio_calificacion: 0,
            listas_entrenamiento: 0,
          },
          fine_tuning: {
            jobs_totales: 0,
            jobs_exitosos: 0,
            jobs_fallidos: 0,
          },
          rag: {
            documentos_con_embeddings: 0,
            total_embeddings: 0,
          },
          ml_riesgo: {
            modelos_disponibles: 0,
          },
        })
        // No mostrar toast de error para 404, es esperado si el endpoint no está implementado
      } else {
        toast.error('Error al cargar métricas de entrenamiento')
        setMetricas(null)
      }
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargarMetricas()
  }, [])

  if (cargando && !metricas) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (!metricas) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
        <p className="text-gray-500 mb-2">No se pudieron cargar las métricas</p>
        <p className="text-sm text-gray-400 mb-4">
          El endpoint de métricas aún no está implementado en el backend
        </p>
        <Button onClick={cargarMetricas} variant="outline" className="mt-4">
          Reintentar
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="h-6 w-6" />
            Dashboard de Entrenamiento
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Métricas consolidadas del sistema híbrido de AI
          </p>
        </div>
        <Button onClick={cargarMetricas} variant="outline" size="sm" disabled={cargando}>
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

      {/* Métricas de Conversaciones */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="h-5 w-5 text-blue-600" />
            <h4 className="font-semibold">Fine-tuning - Conversaciones</h4>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Total Conversaciones</div>
              <div className="text-2xl font-bold">{metricas.conversaciones?.total ?? 0}</div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Con Calificación</div>
              <div className="text-2xl font-bold text-green-600">
                {metricas.conversaciones?.con_calificacion ?? 0}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Promedio Calificación</div>
              <div className="text-2xl font-bold text-blue-600">
                {(metricas.conversaciones?.promedio_calificacion ?? 0) > 0
                  ? (metricas.conversaciones?.promedio_calificacion ?? 0).toFixed(1)
                  : 'N/A'}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Listas para Entrenamiento</div>
              <div className="text-2xl font-bold text-purple-600">
                {metricas.conversaciones?.listas_entrenamiento ?? 0}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Métricas de Fine-tuning */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-5 w-5 text-purple-600" />
            <h4 className="font-semibold">Fine-tuning - Jobs</h4>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Jobs Totales</div>
              <div className="text-2xl font-bold">{metricas.fine_tuning?.jobs_totales ?? 0}</div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Exitosos</div>
              <div className="text-2xl font-bold text-green-600">
                {metricas.fine_tuning?.jobs_exitosos ?? 0}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Fallidos</div>
              <div className="text-2xl font-bold text-red-600">
                {metricas.fine_tuning?.jobs_fallidos ?? 0}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Modelo Activo</div>
              <div className="text-lg font-semibold">
                {metricas.fine_tuning?.modelo_activo ? (
                  <Badge variant="default" className="text-xs">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    {metricas.fine_tuning.modelo_activo}
                  </Badge>
                ) : (
                  <span className="text-gray-400">Ninguno</span>
                )}
              </div>
              {metricas.fine_tuning?.ultimo_entrenamiento && (
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(metricas.fine_tuning.ultimo_entrenamiento).toLocaleDateString()}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Métricas de RAG */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="h-5 w-5 text-green-600" />
            <h4 className="font-semibold">RAG - Embeddings</h4>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Documentos con Embeddings</div>
              <div className="text-2xl font-bold text-green-600">
                {metricas.rag?.documentos_con_embeddings ?? 0}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Total Embeddings</div>
              <div className="text-2xl font-bold text-blue-600">
                {metricas.rag?.total_embeddings ?? 0}
              </div>
            </div>
            <div className="border rounded-lg p-4 col-span-2">
              <div className="text-sm text-gray-500 mb-1">Última Actualización</div>
              <div className="text-lg font-semibold">
                {metricas.rag?.ultima_actualizacion ? (
                  new Date(metricas.rag.ultima_actualizacion).toLocaleString('es-ES')
                ) : (
                  <span className="text-gray-400">Nunca</span>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Métricas de ML Riesgo */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="h-5 w-5 text-orange-600" />
            <h4 className="font-semibold">ML - Modelo de Riesgo</h4>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Modelos Disponibles</div>
              <div className="text-2xl font-bold">{metricas.ml_riesgo?.modelos_disponibles ?? 0}</div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Modelo Activo</div>
              <div className="text-lg font-semibold">
                {metricas.ml_riesgo?.modelo_activo ? (
                  <Badge variant="default" className="text-xs">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    {metricas.ml_riesgo.modelo_activo}
                  </Badge>
                ) : (
                  <span className="text-gray-400">Ninguno</span>
                )}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Accuracy Promedio</div>
              <div className="text-2xl font-bold text-blue-600">
                {metricas.ml_riesgo?.accuracy_promedio
                  ? `${(metricas.ml_riesgo.accuracy_promedio * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">Último Entrenamiento</div>
              <div className="text-sm font-semibold">
                {metricas.ml_riesgo?.ultimo_entrenamiento ? (
                  new Date(metricas.ml_riesgo.ultimo_entrenamiento).toLocaleDateString()
                ) : (
                  <span className="text-gray-400">Nunca</span>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Estado General */}
      <Card>
        <CardContent className="pt-6">
          <h4 className="font-semibold mb-4">Estado General del Sistema</h4>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="border rounded-lg p-4 bg-blue-50">
              <div className="flex items-center justify-between">
                <span className="font-medium">Fine-tuning</span>
                <Badge
                  variant={
                    metricas.fine_tuning?.modelo_activo ? 'default' : 'secondary'
                  }
                >
                  {metricas.fine_tuning?.modelo_activo ? 'Activo' : 'Inactivo'}
                </Badge>
              </div>
            </div>
            <div className="border rounded-lg p-4 bg-green-50">
              <div className="flex items-center justify-between">
                <span className="font-medium">RAG</span>
                <Badge
                  variant={
                    (metricas.rag?.documentos_con_embeddings ?? 0) > 0 ? 'default' : 'secondary'
                  }
                >
                  {(metricas.rag?.documentos_con_embeddings ?? 0) > 0 ? 'Configurado' : 'Sin configurar'}
                </Badge>
              </div>
            </div>
            <div className="border rounded-lg p-4 bg-orange-50">
              <div className="flex items-center justify-between">
                <span className="font-medium">ML Riesgo</span>
                <Badge
                  variant={
                    metricas.ml_riesgo?.modelo_activo ? 'default' : 'secondary'
                  }
                >
                  {metricas.ml_riesgo?.modelo_activo ? 'Activo' : 'Inactivo'}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

