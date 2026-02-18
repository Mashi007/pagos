import { DollarSign, Calendar, TrendingDown } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { usePagosKPIs } from '../../hooks/usePagos'

export function PagosKPIsNuevo() {
  const { data: kpiData, isLoading, error } = usePagosKPIs()

  const kpiDataFinal = kpiData || {
    montoACobrarMes: 0,
    montoCobradoMes: 0,
    morosidadMensualPorcentaje: 0,
    mes: new Date().getMonth() + 1,
    año: new Date().getFullYear(),
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">KPIs de Pagos</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
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

  const isCancelled = (error as any)?.code === 'ERR_CANCELED' || (error as any)?.message?.includes?.('Request aborted')
  if (error && !isCancelled) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">KPIs de Pagos</h2>
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

  const meses = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ]
  const nombreMes = meses[kpiDataFinal.mes - 1]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">KPIs de Pagos (mensuales)</h2>
        <span className="text-sm text-gray-500">
          {nombreMes} {kpiDataFinal.año}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mensual: A cobrar en el mes</CardTitle>
            <Calendar className="h-5 w-5 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              ${kpiDataFinal.montoACobrarMes.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              Cuánto debería cobrarse en {nombreMes} (vencimientos del mes)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mensual: Cobrado / Pagado</CardTitle>
            <DollarSign className="h-5 w-5 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ${kpiDataFinal.montoCobradoMes.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              Cobrado en {nombreMes} (pagos registrados en el mes)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mensual: Pago vencido (%)</CardTitle>
            <TrendingDown className="h-5 w-5 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {Number(kpiDataFinal.morosidadMensualPorcentaje ?? 0).toFixed(1)}%
            </div>
            <p className="text-xs text-gray-600 mt-1">
              Del mes: lo no cobrado sobre lo que venció en {nombreMes}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

