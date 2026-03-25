import { Card, CardContent } from '../../components/ui/card'

import { Badge } from '../../components/ui/badge'

import { formatLastSyncDate } from '../../utils'

import {
  Users,
  UserCheck,
  PlusCircle,
  UserMinus,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'

interface ClientesKPIsProps {
  activos: number

  nuevosEsteMes: number

  finalizados: number

  total: number

  ultimaActualizacion?: string | null

  isLoading?: boolean
}

export function ClientesKPIs({
  activos,

  nuevosEsteMes,

  finalizados,

  total,

  ultimaActualizacion,

  isLoading = false,
}: ClientesKPIsProps) {
  // Calcular porcentajes

  const porcentajeActivos = total > 0 ? Math.round((activos / total) * 100) : 0

  const porcentajeFinalizados =
    total > 0 ? Math.round((finalizados / total) * 100) : 0

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
      {/* Total Clientes */}

      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="mb-1 text-sm font-medium text-blue-600">
                Total Clientes
              </p>

              <p className="text-2xl font-bold text-blue-700">
                {total.toLocaleString()}
              </p>
            </div>

            <div className="rounded-full bg-blue-100 p-2">
              <Users className="h-5 w-5 text-blue-600" />
            </div>
          </div>

          <div className="mt-2">
            <Badge variant="outline" className="border-blue-300 text-blue-700">
              Base total
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Clientes Activos */}

      <Card className="border-green-200 bg-green-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="mb-1 text-sm font-medium text-green-600">
                Clientes Activos
              </p>

              <p className="text-2xl font-bold text-green-700">
                {activos.toLocaleString()}
              </p>
            </div>

            <div className="rounded-full bg-green-100 p-2">
              <UserCheck className="h-5 w-5 text-green-600" />
            </div>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <Badge
              variant="outline"
              className="border-green-300 text-green-700"
            >
              {porcentajeActivos}%
            </Badge>

            <TrendingUp className="h-4 w-4 text-green-600" />
          </div>
        </CardContent>
      </Card>

      {/* Nuevos Clientes en este mes */}

      <Card className="border-orange-200 bg-orange-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="mb-1 text-sm font-medium text-orange-600">
                Nuevos Clientes en este mes
              </p>

              <p className="text-2xl font-bold text-orange-700">
                {nuevosEsteMes.toLocaleString()}
              </p>
            </div>

            <div className="rounded-full bg-orange-100 p-2">
              <PlusCircle className="h-5 w-5 text-orange-600" />
            </div>
          </div>

          <div className="mt-2">
            <Badge
              variant="outline"
              className="border-orange-300 text-orange-700"
            >
              Este mes
            </Badge>

            {ultimaActualizacion ? (
              <div className="mt-1 text-xs text-orange-700/80">
                Actualizado: {formatLastSyncDate(ultimaActualizacion)}
              </div>
            ) : (
              <div className="mt-1 text-xs text-orange-700/60">
                Actualizado: -
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Clientes finalizados (estado) o con préstamo liquidado */}

      <Card className="border-gray-200 bg-gray-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="mb-1 text-sm font-medium text-gray-600">
                Clientes Finalizados
              </p>

              <p className="text-2xl font-bold text-gray-700">
                {finalizados.toLocaleString()}
              </p>
            </div>

            <div className="rounded-full bg-gray-100 p-2">
              <UserMinus className="h-5 w-5 text-gray-600" />
            </div>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="border-gray-300 text-gray-700">
              {porcentajeFinalizados}%
            </Badge>

            <TrendingDown className="h-4 w-4 text-gray-600" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
