import { TrendingUp } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { AgregarTasaFechaPagoPanel } from '../components/pagos/AgregarTasaFechaPagoPanel'

export default function TasaCambioPage() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-6">
      <ModulePageHeader
        icon={TrendingUp}
        title="Tasa de cambio"
        description="Carga Euro y BCV un día hábil antes (fecha valor). El BCV puede entrar solo por la tarde; si no, cárguelo a mano para el siguiente hábil."
      />

      <AgregarTasaFechaPagoPanel />
    </div>
  )
}
