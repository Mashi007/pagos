import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Users, 
  UserCheck, 
  UserX, 
  UserMinus,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react'

interface ClientesKPIsProps {
  activos: number
  inactivos: number
  finalizados: number
  total: number
  isLoading?: boolean
}

export function ClientesKPIs({ 
  activos, 
  inactivos, 
  finalizados, 
  total, 
  isLoading = false 
}: ClientesKPIsProps) {
  
  // Calcular porcentajes
  const porcentajeActivos = total > 0 ? Math.round((activos / total) * 100) : 0
  const porcentajeInactivos = total > 0 ? Math.round((inactivos / total) * 100) : 0
  const porcentajeFinalizados = total > 0 ? Math.round((finalizados / total) * 100) : 0

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
      {/* Total Clientes */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-600 mb-1">Total Clientes</p>
              <p className="text-2xl font-bold text-blue-700">{total.toLocaleString()}</p>
            </div>
            <div className="p-2 bg-blue-100 rounded-full">
              <Users className="h-5 w-5 text-blue-600" />
            </div>
          </div>
          <div className="mt-2">
            <Badge variant="outline" className="text-blue-700 border-blue-300">
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
              <p className="text-sm font-medium text-green-600 mb-1">Clientes Activos</p>
              <p className="text-2xl font-bold text-green-700">{activos.toLocaleString()}</p>
            </div>
            <div className="p-2 bg-green-100 rounded-full">
              <UserCheck className="h-5 w-5 text-green-600" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-green-700 border-green-300">
              {porcentajeActivos}%
            </Badge>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </div>
        </CardContent>
      </Card>

      {/* Clientes Inactivos */}
      <Card className="border-orange-200 bg-orange-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-600 mb-1">Clientes Inactivos</p>
              <p className="text-2xl font-bold text-orange-700">{inactivos.toLocaleString()}</p>
            </div>
            <div className="p-2 bg-orange-100 rounded-full">
              <UserX className="h-5 w-5 text-orange-600" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-orange-700 border-orange-300">
              {porcentajeInactivos}%
            </Badge>
            <Minus className="h-4 w-4 text-orange-600" />
          </div>
        </CardContent>
      </Card>

      {/* Clientes Finalizados */}
      <Card className="border-gray-200 bg-gray-50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">Clientes Finalizados</p>
              <p className="text-2xl font-bold text-gray-700">{finalizados.toLocaleString()}</p>
            </div>
            <div className="p-2 bg-gray-100 rounded-full">
              <UserMinus className="h-5 w-5 text-gray-600" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-gray-700 border-gray-300">
              {porcentajeFinalizados}%
            </Badge>
            <TrendingDown className="h-4 w-4 text-gray-600" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
