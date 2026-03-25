import { CreditCard } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

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

      <Card className="overflow-hidden rounded-xl border border-blue-100/80 bg-gradient-to-br from-blue-50/80 to-white shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base font-semibold text-gray-800">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <CreditCard className="h-4 w-4" />
            </span>
            Gestión de pagos
          </CardTitle>
        </CardHeader>

        <CardContent className="text-sm leading-relaxed text-gray-600">
          <p>
            Registre pagos, consulte por cédula, estado o fecha y descargue
            reportes.
          </p>
        </CardContent>
      </Card>

      <PagosList />
    </div>
  )
}

export default PagosPage
