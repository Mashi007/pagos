import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  CreditCard,
  DollarSign,
  TrendingUp,
  CheckCircle,
  Clock,
  AlertTriangle
} from 'lucide-react'
import { formatCurrency } from '@/utils'

interface PagosKPIsProps {
  totalPagos: number
  totalPagado: number
  pagosHoy: number
  cuotasPagadas: number
  cuotasPendientes: number
  cuotasAtrasadas: number
  isLoading?: boolean
}

export function PagosKPIs({
  totalPagos,
  totalPagado,
  pagosHoy,
  cuotasPagadas,
  cuotasPendientes,
  cuotasAtrasadas,
  isLoading = false
}: PagosKPIsProps) {


  // Calcular porcentajes
  const totalCuotas = cuotasPagadas + cuotasPendientes + cuotasAtrasadas
  const porcentajePagadas = totalCuotas > 0 ? Math.round((cuotasPagadas / totalCuotas) * 100) : 0
  const porcentajeAtrasadas = totalCuotas > 0 ? Math.round((cuotasAtrasadas / totalCuotas) * 100) : 0

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, index) => (
          <Card key={index} className="animate-pulse">
            <CardContent className="p-4">
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-8 bg-gray-200 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {/* Total Pagos */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-600 mb-1">Total Pagos</p>
              <p className="text-2xl font-bold text-blue-700">{totalPagos.toLocaleString()}</p>
            </div>
            <div className="p-2 bg-blue-100 rounded-full">
              <CreditCard className="h-5 w-5 text-blue-600" />
            </div>
          </div>
          <div className="mt-2">
            <Badge variant="outline" className="text-blue-700 border-blue-300">
              Registrados
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Total Pagado */}
      <Card className="border-green-200 bg-green-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-600 mb-1">Total Pagado</p>
              <p className="text-2xl font-bold text-green-700">{formatCurrency(totalPagado)}</p>
            </div>
            <div className="p-2 bg-green-100 rounded-full">
              <DollarSign className="h-5 w-5 text-green-600" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-green-700 border-green-300">
              Hoy: {formatCurrency(pagosHoy)}
            </Badge>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </div>
        </CardContent>
      </Card>

      {/* Cuotas Pagadas */}
      <Card className="border-purple-200 bg-purple-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-purple-600 mb-1">Cuotas Pagadas</p>
              <p className="text-2xl font-bold text-purple-700">{cuotasPagadas.toLocaleString()}</p>
            </div>
            <div className="p-2 bg-purple-100 rounded-full">
              <CheckCircle className="h-5 w-5 text-purple-600" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-purple-700 border-purple-300">
              {porcentajePagadas}%
            </Badge>
            <TrendingUp className="h-4 w-4 text-purple-600" />
          </div>
        </CardContent>
      </Card>

      {/* Cuotas Pendientes */}
      <Card className="border-orange-200 bg-orange-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-600 mb-1">Cuotas Atrasadas</p>
              <p className="text-2xl font-bold text-orange-700">{cuotasAtrasadas.toLocaleString()}</p>
            </div>
            <div className="p-2 bg-orange-100 rounded-full">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-orange-700 border-orange-300">
              {porcentajeAtrasadas}% del total
            </Badge>
            <Clock className="h-4 w-4 text-orange-600" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

