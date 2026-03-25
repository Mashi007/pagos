import { EmbudoConcesionarios } from './EmbudoConcesionarios'

import { Target } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

export function Ventas() {
  return (
    <div className="space-y-6">
      <ModulePageHeader
        icon={Target}
        title="Ventas"
        description="Embudo y seguimiento comercial con concesionarios."
      />

      <EmbudoConcesionarios />
    </div>
  )
}

export default Ventas
