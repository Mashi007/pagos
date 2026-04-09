import { TrendingUp } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { AgregarTasaFechaPagoPanel } from '../components/pagos/AgregarTasaFechaPagoPanel'

export default function TasaCambioPage() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-6">
      <ModulePageHeader
        icon={TrendingUp}
        title="Tasa de cambio"
        description="Tasa oficial Bs./USD por fecha de pago (historial y conversión en pagos en bolívares)"
      />

      <AgregarTasaFechaPagoPanel />
    </div>
  )
}
