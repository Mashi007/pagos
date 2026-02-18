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

interface StatisticsPanelProps {
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
    <Card className="bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-lg flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-purple-600" />
            Estadísticas de Feedback
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
          >
            <XCircle className="h-4 w-4" />
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {/* Total Conversations */}
          <div className="bg-white rounded-lg p-4 border">
            <div className="text-sm text-gray-600 mb-1">Total Conversaciones</div>
            <div className="text-2xl font-bold text-gray-900">
              {estadisticasFeedback.total_conversaciones}
            </div>
          </div>

          {/* Rated Conversations */}
          <div className="bg-white rounded-lg p-4 border">
            <div className="text-sm text-gray-600 mb-1">Calificadas</div>
            <div className="text-2xl font-bold text-blue-600">
              {estadisticasFeedback.conversaciones_calificadas}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {((estadisticasFeedback.conversaciones_calificadas / estadisticasFeedback.total_conversaciones) * 100).toFixed(1)}%
            </div>
          </div>

          {/* Positive Feedback */}
          <div className="bg-white rounded-lg p-4 border">
            <div className="text-sm text-gray-600 mb-1 flex items-center gap-1">
              <TrendingUp className="h-4 w-4 text-green-600" />
              Feedback Positivo
            </div>
            <div className="text-2xl font-bold text-green-600">
              {estadisticasFeedback.feedback_positivo_count || 0}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Calificación ≥ 4
            </div>
          </div>

          {/* Negative Feedback */}
          <div className="bg-white rounded-lg p-4 border">
            <div className="text-sm text-gray-600 mb-1 flex items-center gap-1">
              <TrendingDown className="h-4 w-4 text-red-600" />
              Feedback Negativo
            </div>
            <div className="text-2xl font-bold text-red-600">
              {estadisticasFeedback.feedback_negativo_count || 0}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Calificación ≤ 2
            </div>
          </div>
        </div>

        {/* Rating Distribution Chart */}
        {estadisticasFeedback.distribucion_calificaciones && (
          <div className="bg-white rounded-lg p-4 border">
            <h5 className="font-medium text-sm mb-3">Distribución de Calificaciones</h5>
            <div className="space-y-2">
              {Object.entries(estadisticasFeedback.distribucion_calificaciones).map(
                ([star, count]: [string, any]) => {
                  const maxCantidad = Math.max(
                    ...Object.values(estadisticasFeedback.distribucion_calificaciones as Record<string, number>)
                  )
                  const altura = (count / maxCantidad) * 100

                  return (
                    <div key={star} className="flex items-center gap-2">
                      <div className="w-12 text-sm font-medium text-gray-600">{star} ★</div>
                      <div className="flex-1 bg-gray-200 rounded h-6 relative overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-yellow-400 to-yellow-500 h-full transition-all"
                          style={{ width: `${altura}%` }}
                        />
                      </div>
                      <div className="w-12 text-right text-sm font-medium text-gray-600">{count}</div>
                    </div>
                  )
                }
              )}
            </div>
          </div>
        )}

        {/* Help Section */}
        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex gap-2">
            <Info className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Consejos para mejores resultados:</p>
              <ul className="text-xs space-y-1 list-disc list-inside opacity-90">
                <li>Califica al menos 50 conversaciones para obtener un modelo representativo</li>
                <li>Evita calificaciones muy bajas (1-2 estrellas) para datos de entrenamiento de calidad</li>
                <li>El sistema filtra automáticamente feedback muy negativo durante la preparación</li>
                <li>Las calificaciones (3+) son consideradas positivas para entrenamiento</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
