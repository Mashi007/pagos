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
}

export function EvaluacionRiesgoActions({
  resultado,

  isLoading,

  todasSeccionesCompletas,

  bloqueadoPorMora,

  criteriosFaltantes,

  onClose,

  onSuccess,
}: EvaluacionRiesgoActionsProps) {
  if (!resultado) {
    return (
      <div className="flex justify-end gap-3 border-t pt-4">
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
          <Calculator className="mr-2 h-4 w-4" />

          {isLoading ? 'Evaluando...' : 'Evaluar Riesgo'}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4 border-t pt-4">
      <div className="rounded-lg border-2 border-blue-300 bg-gradient-to-r from-blue-50 to-purple-50 p-4">
        <div className="flex items-start gap-3">
          <CheckCircle className="mt-0.5 h-6 w-6 flex-shrink-0 text-green-600" />

          <div className="flex-1">
            <h3 className="mb-2 text-base font-bold text-blue-900">
              [OK] FASE 1 COMPLETADA: Evaluación de Riesgo
            </h3>

            <div className="space-y-2 text-sm text-blue-800">
              <p>
                - <strong>Estado actualizado:</strong> El préstamo ahora está
                marcado como{' '}
                <span className="font-bold text-blue-600">EVALUADO</span>
              </p>

              <p>
                - <strong>Puntuación obtenida:</strong>{' '}
                {resultado.puntuacion_total?.toFixed(2) || 'N/A'}/100 puntos
              </p>

              <p>
                - <strong>Clasificación de riesgo:</strong>{' '}
                <span className="font-semibold">
                  {resultado.clasificacion_riesgo || 'N/A'}
                </span>
              </p>

              <div className="mt-3 border-t border-blue-300 pt-3">
                <p className="mb-1 font-semibold text-purple-700">
                  ✓ SIGUIENTE PASO: Fase 2 - Aprobación
                </p>

                <p className="text-xs">
                  El icono de <strong>calculadora (Calculator)</strong> en el
                  dashboard desaparecerá y será reemplazado por el icono de{' '}
                  <strong>verde (CheckCircle2)</strong> para &quot;Aprobar
                  Crédito&quot;. Haga clic en ese nuevo icono para continuar con
                  la asignación de:
                </p>

                <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-blue-700">
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
