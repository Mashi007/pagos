import { PrestamosList } from '../components/prestamos/PrestamosList'
import { DollarSign, Bell } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

export function Prestamos() {
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3 mb-6">
        <DollarSign className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold text-gray-900">Préstamos</h1>
      </div>

      {/* Novedades: información para el usuario */}
      <Card className="border-blue-100 bg-blue-50/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4 text-blue-600" />
            Novedades
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-gray-700">
          <p>No hay novedades en este momento.</p>
        </CardContent>
      </Card>

      <PrestamosList />
    </div>
  )
}

export default Prestamos
