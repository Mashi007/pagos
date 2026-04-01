import { CreditCard } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { PagosList } from '../components/pagos/PagosList'

function PagosPage() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-6">
      <ModulePageHeader
        icon={CreditCard}
        title="Pagos"
        description="Gestión de cobros y conciliación"
      />

      <PagosList />
    </div>
  )
}

export default PagosPage
