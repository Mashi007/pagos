import { FileSpreadsheet } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { CedulasReportarBsPanel } from '../components/pagos/CedulasReportarBsPanel'

export default function PagoBsPage() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-6">
      <ModulePageHeader
        icon={FileSpreadsheet}
        title="Pago Bs."
        description="Cédulas autorizadas para reportar pagos en bolívares en Cobros e Infopagos"
      />

      <CedulasReportarBsPanel />
    </div>
  )
}
