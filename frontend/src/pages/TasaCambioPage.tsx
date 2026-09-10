import { TrendingUp } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { AgregarTasaFechaPagoPanel } from '../components/pagos/AgregarTasaFechaPagoPanel'

export default function TasaCambioPage() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-6">
      <ModulePageHeader
        icon={TrendingUp}
        title="Tasa de cambio"
        description="Edite Euro y BCV de cualquier fecha. Al guardar, el cambio queda en el servidor y se actualiza al instante en esta pantalla."
      />

      <AgregarTasaFechaPagoPanel />
    </div>
  )
}
