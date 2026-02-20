import { Brain, Shield } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Badge } from '../../../components/ui/badge'

interface EvaluacionRiesgoMLSectionProps {
  prediccion_ml: {
    riesgo_level: string
    confidence: number
    recommendation?: string
    modelo_usado?: {
      nombre: string
      version: number
      algoritmo: string
      accuracy?: number
    }
  }
  clasificacion_riesgo: string
  puntuacion_total?: number
}

export function EvaluacionRiesgoMLSection({
  prediccion_ml,
  clasificacion_riesgo,
  puntuacion_total,
}: EvaluacionRiesgoMLSectionProps) {
  return (
    <Card className="border-purple-200 bg-purple-50/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-purple-700">
          <Brain className="h-5 w-5" />
          Predicción de Machine Learning
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-gray-600 mb-1">Nivel de Riesgo ML</div>
            <Badge
              className={`text-lg ${
                prediccion_ml.riesgo_level === 'Bajo'
                  ? 'bg-green-600 text-white'
                  : prediccion_ml.riesgo_level === 'Medio'
                  ? 'bg-yellow-600 text-white'
                  : 'bg-red-600 text-white'
              }`}
            >
              <Shield className="h-4 w-4 mr-1" />
              {prediccion_ml.riesgo_level}
            </Badge>
          </div>
          <div>
            <div className="text-sm text-gray-600 mb-1">Confianza</div>
            <div className="text-2xl font-bold text-purple-600">
              {(prediccion_ml.confidence * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {prediccion_ml.recommendation && (
          <div className="bg-white p-3 rounded border border-purple-200">
            <div className="text-sm font-medium text-gray-700 mb-1">Recomendación ML:</div>
            <p className="text-sm text-gray-600">{prediccion_ml.recommendation}</p>
          </div>
        )}

        {prediccion_ml.modelo_usado && (
          <div className="bg-white p-3 rounded border border-purple-200">
            <div className="text-xs text-gray-500 mb-2">Modelo utilizado:</div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-600">Nombre:</span>{' '}
                <span className="font-semibold">{prediccion_ml.modelo_usado.nombre}</span>
              </div>
              <div>
                <span className="text-gray-600">Versión:</span>{' '}
                <span className="font-semibold">v{prediccion_ml.modelo_usado.version}</span>
              </div>
              <div>
                <span className="text-gray-600">Algoritmo:</span>{' '}
                <span className="font-semibold">{prediccion_ml.modelo_usado.algoritmo}</span>
              </div>
              {prediccion_ml.modelo_usado.accuracy !== undefined && (
                <div>
                  <span className="text-gray-600">Accuracy:</span>{' '}
                  <span className="font-semibold">
                    {(prediccion_ml.modelo_usado.accuracy * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="bg-blue-50 p-3 rounded border border-blue-200">
          <div className="text-xs font-semibold text-blue-900 mb-2">ℹ️ Comparación de Métodos:</div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-gray-600">Sistema 100 Puntos:</div>
              <div className="font-semibold text-blue-700">
                {clasificacion_riesgo} ({puntuacion_total?.toFixed(1) ?? 'N/A'}/100)
              </div>
            </div>
            <div>
              <div className="text-gray-600">Machine Learning:</div>
              <div className="font-semibold text-purple-700">
                {prediccion_ml.riesgo_level} ({(prediccion_ml.confidence * 100).toFixed(1)}% confianza)
              </div>
            </div>
          </div>
          {clasificacion_riesgo === 'A' && prediccion_ml.riesgo_level === 'Bajo' && (
            <div className="mt-2 text-xs text-green-700 bg-green-100 p-2 rounded">
              [OK] Ambos métodos coinciden: Cliente de bajo riesgo
            </div>
          )}
          {clasificacion_riesgo === 'E' && prediccion_ml.riesgo_level === 'Alto' && (
            <div className="mt-2 text-xs text-red-700 bg-red-100 p-2 rounded">
              ⚠️ Ambos métodos coinciden: Cliente de alto riesgo
            </div>
          )}
          {((clasificacion_riesgo === 'A' || clasificacion_riesgo === 'B') &&
            prediccion_ml.riesgo_level === 'Alto') && (
            <div className="mt-2 text-xs text-amber-700 bg-amber-100 p-2 rounded">
              ⚠️ Discrepancia detectada: El ML sugiere mayor riesgo que el sistema de puntos
            </div>
          )}
          {((clasificacion_riesgo === 'D' || clasificacion_riesgo === 'E') &&
            prediccion_ml.riesgo_level === 'Bajo') && (
            <div className="mt-2 text-xs text-amber-700 bg-amber-100 p-2 rounded">
              ⚠️ Discrepancia detectada: El ML sugiere menor riesgo que el sistema de puntos
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
