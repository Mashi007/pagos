import { CreditCard } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { PagosList } from '../components/pagos/PagosList'

function PagosPage() {
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3 mb-6">
        <CreditCard className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold text-gray-900">Pagos</h1>
      </div>

      {/* Card informativa (mismo formato que Préstamos) */}
      <Card className="border-blue-100 bg-blue-50/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-blue-600" />
            Gestión de pagos
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-gray-700">
          <p>Registre pagos, consulte por cédula, estado o fecha y descargue reportes.</p>
        </CardContent>
      </Card>

      <PagosList />
    </div>
  )
}

export default PagosPage
