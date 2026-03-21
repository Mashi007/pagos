import { CreditCard } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { PagosList } from '../components/pagos/PagosList'

function PagosPage() {
  return (
    <div className="space-y-6 p-6 max-w-[1600px] mx-auto">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/25">
            <CreditCard className="h-6 w-6" />
          </span>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 tracking-tight">Pagos</h1>
            <p className="text-sm text-gray-500 mt-0.5">Gestión de cobros y conciliación</p>
          </div>
        </div>
      </header>

      <Card className="border border-blue-100/80 bg-gradient-to-br from-blue-50/80 to-white rounded-xl shadow-sm overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2 font-semibold text-gray-800">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <CreditCard className="h-4 w-4" />
            </span>
            Gestión de pagos
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-gray-600 leading-relaxed">
          <p>Registre pagos, consulte por cédula, estado o fecha y descargue reportes.</p>
        </CardContent>
      </Card>

      <PagosList />
    </div>
  )
}

export default PagosPage