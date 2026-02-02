import { EmbudoConcesionarios } from './EmbudoConcesionarios'
import { Target } from 'lucide-react'

export function Ventas() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Target className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold text-gray-900">Ventas</h1>
      </div>
      <EmbudoConcesionarios />
    </div>
  )
}

export default Ventas

