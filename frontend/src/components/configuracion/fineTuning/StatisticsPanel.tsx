import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Info,
  XCircle,
} from 'lucide-react'

import { Card, CardContent } from '../../ui/card'

import { Button } from '../../ui/button'

import { Badge } from '../../ui/badge'

export interface StatisticsPanelProps {
  estadisticasFeedback: any | null

  mostrar: boolean

  onClose: () => void
}

export function StatisticsPanel({
  estadisticasFeedback,

  mostrar,

  onClose,
}: StatisticsPanelProps) {
  if (!mostrar || !estadisticasFeedback) {
    return null
  }

  return (
    <Card className="border-purple-200 bg-gradient-to-r from-purple-50 to-blue-50">
      <CardContent className="pt-6">
        <div className="mb-4 flex items-center justify-between">
          <h4 className="flex items-center gap-2 text-lg font-semibold">
            <BarChart3 className="h-5 w-5 text-purple-600" />
            Estadísticas de Feedback
          </h4>

          <Button variant="ghost" size="sm" onClick={onClose}>
            <XCircle className="h-4 w-4" />
          </Button>
        </div>

        <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Total Conversations */}

          <div className="rounded-lg border bg-white p-4">
            <div className="mb-1 text-sm text-gray-600">
              Total Conversaciones
            </div>

            <div className="text-2xl font-bold text-gray-900">
              {estadisticasFeedback.total_conversaciones}
            </div>
          </div>

          {/* Rated Conversations */}

          <div className="rounded-lg border bg-white p-4">
            <div className="mb-1 text-sm text-gray-600">Calificadas</div>

            <div className="text-2xl font-bold text-blue-600">
              {estadisticasFeedback.conversaciones_calificadas}
            </div>

            <div className="mt-1 text-xs text-gray-500">
              {(
                (estadisticasFeedback.conversaciones_calificadas /
                  estadisticasFeedback.total_conversaciones) *
                100
              ).toFixed(1)}
              %
            </div>
          </div>

          {/* Positive Feedback */}

          <div className="rounded-lg border bg-white p-4">
            <div className="mb-1 flex items-center gap-1 text-sm text-gray-600">
              <TrendingUp className="h-4 w-4 text-green-600" />
              Feedback Positivo
            </div>

            <div className="text-2xl font-bold text-green-600">
              {estadisticasFeedback.feedback_positivo_count || 0}
            </div>

            <div className="mt-1 text-xs text-gray-500">Calificación ≥ 4</div>
          </div>

          {/* Negative Feedback */}

          <div className="rounded-lg border bg-white p-4">
            <div className="mb-1 flex items-center gap-1 text-sm text-gray-600">
              <TrendingDown className="h-4 w-4 text-red-600" />
              Feedback Negativo
            </div>

            <div className="text-2xl font-bold text-red-600">
              {estadisticasFeedback.feedback_negativo_count || 0}
            </div>

            <div className="mt-1 text-xs text-gray-500">Calificación ≤ 2</div>
          </div>
        </div>

        {/* Rating Distribution Chart */}

        {estadisticasFeedback.distribucion_calificaciones && (
          <div className="rounded-lg border bg-white p-4">
            <h5 className="mb-3 text-sm font-medium">
              Distribución de Calificaciones
            </h5>

            <div className="space-y-2">
              {Object.entries(
                estadisticasFeedback.distribucion_calificaciones
              ).map(([star, count]: [string, any]) => {
                const maxCantidad = Math.max(
                  ...Object.values(
                    estadisticasFeedback.distribucion_calificaciones as Record<
                      string,
                      number
                    >
                  )
                )

                const altura = (count / maxCantidad) * 100

                return (
                  <div key={star} className="flex items-center gap-2">
                    <div className="w-12 text-sm font-medium text-gray-600">
                      {star} ★
                    </div>

                    <div className="relative h-6 flex-1 overflow-hidden rounded bg-gray-200">
                      <div
                        className="h-full bg-gradient-to-r from-yellow-400 to-yellow-500 transition-all"
                        style={{ width: `${altura}%` }}
                      />
                    </div>

                    <div className="w-12 text-right text-sm font-medium text-gray-600">
                      {count}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Help Section */}

        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
          <div className="flex gap-2">
            <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-600" />

            <div className="text-sm text-blue-800">
              <p className="mb-1 font-medium">
                Consejos para mejores resultados:
              </p>

              <ul className="list-inside list-disc space-y-1 text-xs opacity-90">
                <li>
                  Califica al menos 50 conversaciones para obtener un modelo
                  representativo
                </li>

                <li>
                  Evita calificaciones muy bajas (1-2 estrellas) para datos de
                  entrenamiento de calidad
                </li>

                <li>
                  El sistema filtra automáticamente feedback muy negativo
                  durante la preparación
                </li>

                <li>
                  Las calificaciones (3+) son consideradas positivas para
                  entrenamiento
                </li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
