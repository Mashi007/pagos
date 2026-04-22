import { TrendingUp } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { AgregarTasaFechaPagoPanel } from '../components/pagos/AgregarTasaFechaPagoPanel'

export default function TasaCambioPage() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-6">
      <ModulePageHeader
        icon={TrendingUp}
        title="Tasa de cambio"
        description="Euro (por defecto), BCV y Binance en Bs./USD por fecha de pago; el cliente elige la fuente al reportar en bolívares"
      />

      <AgregarTasaFechaPagoPanel />
    </div>
  )
}
