import { FileSpreadsheet } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { CedulasReportarBsPanel } from '../components/pagos/CedulasReportarBsPanel'
import { cn } from '../utils'

export default function PagoBsPage() {
  return (
    <div
      className={cn(
        'mx-auto min-w-0 max-w-[1600px] space-y-8 px-4 py-6 sm:px-6 lg:px-8',
        'bg-gradient-to-b from-slate-50/80 via-white to-slate-50/40'
      )}
    >
      <ModulePageHeader
        className="shadow-sm ring-1 ring-slate-200/60"
        icon={FileSpreadsheet}
        title="Pago Bs."
        description="Cédulas autorizadas para reportar pagos en bolívares en Cobros e Infopagos."
      />

      <CedulasReportarBsPanel showExcelUpload={false} />
    </div>
  )
}
