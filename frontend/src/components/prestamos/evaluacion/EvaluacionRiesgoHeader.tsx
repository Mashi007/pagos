import { Calculator, X } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import type { Prestamo } from '../../../types'

interface EvaluacionRiesgoHeaderProps {
  prestamo: Prestamo
  onClose: () => void
}

export function EvaluacionRiesgoHeader({ prestamo, onClose }: EvaluacionRiesgoHeaderProps) {
  return (
    <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 flex justify-between items-center z-10">
      <div className="flex items-center gap-3">
        <Calculator className="h-6 w-6" />
        <div>
          <h2 className="text-xl font-bold">Evaluación de Riesgo</h2>
          <p className="text-sm opacity-90">Préstamo #{prestamo.id} - Sistema 100 Puntos</p>
        </div>
      </div>
      <Button variant="ghost" size="icon" onClick={onClose} className="text-white hover:bg-white/20">
        <X className="h-5 w-5" />
      </Button>
    </div>
  )
}
