import { Card, CardContent } from '../../components/ui/card'

import { Badge } from '../../components/ui/badge'

import {
  CreditCard,
  DollarSign,
  TrendingUp,
  CheckCircle,
  Clock,
  AlertTriangle,
} from 'lucide-react'

import { formatCurrency } from '../../utils'

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

  isLoading = false,
}: PagosKPIsProps) {
  // Calcular porcentajes

  const totalCuotas = cuotasPagadas + cuotasPendientes + cuotasAtrasadas

  const porcentajePagadas =
    totalCuotas > 0 ? Math.round((cuotasPagadas / totalCuotas) * 100) : 0

  const porcentajeAtrasadas =
    totalCuotas > 0 ? Math.round((cuotasAtrasadas / totalCuotas) * 100) : 0

  if (isLoading) {
    return (
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        {[...Array(4)].map((_, index) => (
          <Card key={index} className="animate-pulse">
            <CardContent className="p-4">
              <div className="mb-2 h-4 rounded bg-gray-200"></div>

              <div className="h-8 rounded bg-gray-200"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
      {/* Total Pagos */}

      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="mb-1 text-sm font-medium text-blue-600">
                Total Pagos
              </p>

              <p className="text-2xl font-bold text-blue-700">
                {totalPagos.toLocaleString()}
              </p>
            </div>

            <div className="rounded-full bg-blue-100 p-2">
              <CreditCard className="h-5 w-5 text-blue-600" />
            </div>
          </div>

          <div className="mt-2">
            <Badge variant="outline" className="border-blue-300 text-blue-700">
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
              <p className="mb-1 text-sm font-medium text-green-600">
                Total Pagado
              </p>

              <p className="text-2xl font-bold text-green-700">
                {formatCurrency(totalPagado)}
              </p>
            </div>

            <div className="rounded-full bg-green-100 p-2">
              <DollarSign className="h-5 w-5 text-green-600" />
            </div>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <Badge
              variant="outline"
              className="border-green-300 text-green-700"
            >
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
              <p className="mb-1 text-sm font-medium text-purple-600">
                Cuotas Pagadas
              </p>

              <p className="text-2xl font-bold text-purple-700">
                {cuotasPagadas.toLocaleString()}
              </p>
            </div>

            <div className="rounded-full bg-purple-100 p-2">
              <CheckCircle className="h-5 w-5 text-purple-600" />
            </div>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <Badge
              variant="outline"
              className="border-purple-300 text-purple-700"
            >
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
              <p className="mb-1 text-sm font-medium text-orange-600">
                Cuotas Atrasadas
              </p>

              <p className="text-2xl font-bold text-orange-700">
                {cuotasAtrasadas.toLocaleString()}
              </p>
            </div>

            <div className="rounded-full bg-orange-100 p-2">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
            </div>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <Badge
              variant="outline"
              className="border-orange-300 text-orange-700"
            >
              {porcentajeAtrasadas}% del total
            </Badge>

            <Clock className="h-4 w-4 text-orange-600" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
