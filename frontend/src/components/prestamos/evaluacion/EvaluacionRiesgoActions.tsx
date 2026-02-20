import { Calculator, CheckCircle } from 'lucide-react'
import { Button } from '../../../components/ui/button'

interface EvaluacionRiesgoActionsProps {
  resultado: any
  isLoading: boolean
  todasSeccionesCompletas: boolean
  bloqueadoPorMora: boolean
  criteriosFaltantes: string[]
  onClose: () => void
  onSuccess: () => void
  onSubmit: (e: React.FormEvent) => void
}

export function EvaluacionRiesgoActions({
  resultado,
  isLoading,
  todasSeccionesCompletas,
  bloqueadoPorMora,
  criteriosFaltantes,
  onClose,
  onSuccess,
  onSubmit,
}: EvaluacionRiesgoActionsProps) {
  if (!resultado) {
    return (
      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancelar
        </Button>
        <Button
          type="submit"
          disabled={isLoading || !todasSeccionesCompletas || bloqueadoPorMora}
          title={
            !todasSeccionesCompletas
              ? `Complete todos los 7 criterios. Faltan: ${criteriosFaltantes.join(', ')}`
              : bloqueadoPorMora
              ? 'El cliente tiene cuotas en mora'
              : undefined
          }
        >
          <Calculator className="h-4 w-4 mr-2" />
          {isLoading ? 'Evaluando...' : 'Evaluar Riesgo'}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4 pt-4 border-t">
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-lg border-2 border-blue-300">
        <div className="flex items-start gap-3">
          <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-base font-bold text-blue-900 mb-2">
              [OK] FASE 1 COMPLETADA: Evaluación de Riesgo
            </h3>
            <div className="space-y-2 text-sm text-blue-800">
              <p>
                - <strong>Estado actualizado:</strong> El préstamo ahora está marcado como{' '}
                <span className="font-bold text-blue-600">EVALUADO</span>
              </p>
              <p>
                - <strong>Puntuación obtenida:</strong>{' '}
                {resultado.puntuacion_total?.toFixed(2) || 'N/A'}/100 puntos
              </p>
              <p>
                - <strong>Clasificación de riesgo:</strong>{' '}
                <span className="font-semibold">{resultado.clasificacion_riesgo || 'N/A'}</span>
              </p>
              <div className="mt-3 pt-3 border-t border-blue-300">
                <p className="font-semibold text-purple-700 mb-1">✓ SIGUIENTE PASO: Fase 2 - Aprobación</p>
                <p className="text-xs">
                  El icono de <strong>calculadora (Calculator)</strong> en el dashboard desaparecerá y será
                  reemplazado por el icono de <strong>verde (CheckCircle2)</strong> para &quot;Aprobar Crédito&quot;.
                  Haga clic en ese nuevo icono para continuar con la asignación de:
                </p>
                <ul className="list-disc list-inside mt-2 space-y-1 text-xs text-blue-700">
                  <li>Tasa de interés</li>
                  <li>Fecha de desembolso</li>
                  <li>Plazo máximo</li>
                  <li>Observaciones</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            onSuccess()
            onClose()
          }}
        >
          Continuar al Dashboard
        </Button>
      </div>
    </div>
  )
}
