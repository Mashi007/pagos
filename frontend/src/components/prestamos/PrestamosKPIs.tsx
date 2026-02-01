import { DollarSign, TrendingUp, Users, CreditCard } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { usePrestamosKPIs } from '../../hooks/usePrestamos'

interface PrestamosKPIsProps {
  // Props opcionales para filtros
  analista?: string
  concesionario?: string
  modelo?: string
  fecha_inicio?: string
  fecha_fin?: string
}

export function PrestamosKPIs({
  analista,
  concesionario,
  modelo,
  fecha_inicio,
  fecha_fin,
}: PrestamosKPIsProps) {
  // Obtener KPIs desde el backend
  const { data: kpiData, isLoading, error } = usePrestamosKPIs({
    analista,
    concesionario,
    modelo,
    fecha_inicio,
    fecha_fin,
  })

  // Valores por defecto mientras carga
  const kpiDataFinal = kpiData || {
    totalFinanciamiento: 0,
    totalPrestamos: 0,
    promedioMonto: 0,
    totalCarteraVigente: 0,
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">KPIs de PrÃ©stamos</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-8 w-32 bg-gray-200 rounded animate-pulse mb-2" />
                <div className="h-3 w-20 bg-gray-200 rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">KPIs de PrÃ©stamos</h2>
        </div>
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600 text-center">
              Error al cargar los KPIs. Por favor, intenta nuevamente.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">KPIs de PrÃ©stamos</h2>
      </div>

      {/* Vista General con KPIs principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Financiamiento</CardTitle>
            <DollarSign className="h-5 w-5 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ${kpiDataFinal.totalFinanciamiento.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              Cartera total aprobada
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total PrÃ©stamos</CardTitle>
            <CreditCard className="h-5 w-5 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{kpiDataFinal.totalPrestamos}</div>
            <p className="text-xs text-gray-600 mt-1">PrÃ©stamos gestionados</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Promedio Monto</CardTitle>
            <TrendingUp className="h-5 w-5 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">
              ${kpiDataFinal.promedioMonto.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">Monto promedio</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cartera por Cobrar</CardTitle>
            <Users className="h-5 w-5 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              ${kpiDataFinal.totalCarteraVigente.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">Saldo pendiente de cobro</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
