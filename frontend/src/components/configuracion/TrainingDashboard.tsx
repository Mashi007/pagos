import { useState, useEffect } from 'react'

import {
  BarChart3,
  Brain,
  FileText,
  TrendingUp,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react'

import { Card, CardContent } from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Badge } from '../../components/ui/badge'

import {
  aiTrainingService,
  MetricasEntrenamiento,
} from '../../services/aiTrainingService'

import { toast } from 'sonner'

export function TrainingDashboard() {
  const [metricas, setMetricas] = useState<MetricasEntrenamiento | null>(null)

  const [cargando, setCargando] = useState(false)

  const cargarMetricas = async () => {
    setCargando(true)

    try {
      const data = await aiTrainingService.getMetricasEntrenamiento()

      // Validar que la respuesta tenga la estructura esperada

      if (
        data &&
        data.conversaciones &&
        data.fine_tuning &&
        data.rag &&
        data.ml_riesgo
      ) {
        setMetricas(data as MetricasEntrenamiento)
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
        } as MetricasEntrenamiento)
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
        } as MetricasEntrenamiento)

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
      <div className="py-12 text-center">
        <AlertCircle className="mx-auto mb-4 h-12 w-12 text-gray-400" />

        <p className="mb-2 text-gray-500">No se pudieron cargar las métricas</p>

        <p className="mb-4 text-sm text-gray-400">
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
          <h3 className="flex items-center gap-2 text-2xl font-bold">
            <BarChart3 className="h-6 w-6" />
            Dashboard de Entrenamiento
          </h3>

          <p className="mt-1 text-sm text-gray-500">
            Métricas consolidadas del sistema híbrido de AI
          </p>
        </div>

        <Button
          onClick={cargarMetricas}
          variant="outline"
          size="sm"
          disabled={cargando}
        >
          {cargando ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Actualizando...
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 h-4 w-4" />
              Actualizar
            </>
          )}
        </Button>
      </div>

      {/* Métricas de Conversaciones */}

      <Card>
        <CardContent className="pt-6">
          <div className="mb-4 flex items-center gap-2">
            <Brain className="h-5 w-5 text-blue-600" />

            <h4 className="font-semibold">Fine-tuning - Conversaciones</h4>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">
                Total Conversaciones
              </div>

              <div className="text-2xl font-bold">
                {metricas.conversaciones?.total ?? 0}
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">Con Calificación</div>

              <div className="text-2xl font-bold text-green-600">
                {metricas.conversaciones?.con_calificacion ?? 0}
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">
                Promedio Calificación
              </div>

              <div className="text-2xl font-bold text-blue-600">
                {(metricas.conversaciones?.promedio_calificacion ?? 0) > 0
                  ? (
                      metricas.conversaciones?.promedio_calificacion ?? 0
                    ).toFixed(1)
                  : 'N/A'}
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">
                Listas para Entrenamiento
              </div>

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
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-purple-600" />

            <h4 className="font-semibold">Fine-tuning - Jobs</h4>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">Jobs Totales</div>

              <div className="text-2xl font-bold">
                {metricas.fine_tuning?.jobs_totales ?? 0}
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">Exitosos</div>

              <div className="text-2xl font-bold text-green-600">
                {metricas.fine_tuning?.jobs_exitosos ?? 0}
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">Fallidos</div>

              <div className="text-2xl font-bold text-red-600">
                {metricas.fine_tuning?.jobs_fallidos ?? 0}
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">Modelo Activo</div>

              <div className="text-lg font-semibold">
                {metricas.fine_tuning?.modelo_activo ? (
                  <Badge variant="default" className="text-xs">
                    <CheckCircle className="mr-1 h-3 w-3" />

                    {metricas.fine_tuning.modelo_activo}
                  </Badge>
                ) : (
                  <span className="text-gray-400">Ninguno</span>
                )}
              </div>

              {metricas.fine_tuning?.ultimo_entrenamiento && (
                <div className="mt-1 text-xs text-gray-500">
                  {new Date(
                    metricas.fine_tuning.ultimo_entrenamiento
                  ).toLocaleDateString()}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Métricas de RAG */}

      <Card>
        <CardContent className="pt-6">
          <div className="mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-green-600" />

            <h4 className="font-semibold">RAG - Embeddings</h4>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">
                Documentos con Embeddings
              </div>

              <div className="text-2xl font-bold text-green-600">
                {metricas.rag?.documentos_con_embeddings ?? 0}
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">Total Embeddings</div>

              <div className="text-2xl font-bold text-blue-600">
                {metricas.rag?.total_embeddings ?? 0}
              </div>
            </div>

            <div className="col-span-2 rounded-lg border p-4">
              <div className="mb-1 text-sm text-gray-500">
                Última Actualización
              </div>

              <div className="text-lg font-semibold">
                {metricas.rag?.ultima_actualizacion ? (
                  new Date(metricas.rag.ultima_actualizacion).toLocaleString(
                    'es-ES'
                  )
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
          <h4 className="mb-4 font-semibold">Estado General del Sistema</h4>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border bg-blue-50 p-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Fine-tuning</span>

                <Badge
                  variant={
                    metricas.fine_tuning?.modelo_activo
                      ? 'default'
                      : 'secondary'
                  }
                >
                  {metricas.fine_tuning?.modelo_activo ? 'Activo' : 'Inactivo'}
                </Badge>
              </div>
            </div>

            <div className="rounded-lg border bg-green-50 p-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">RAG</span>

                <Badge
                  variant={
                    (metricas.rag?.documentos_con_embeddings ?? 0) > 0
                      ? 'default'
                      : 'secondary'
                  }
                >
                  {(metricas.rag?.documentos_con_embeddings ?? 0) > 0
                    ? 'Configurado'
                    : 'Sin configurar'}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
