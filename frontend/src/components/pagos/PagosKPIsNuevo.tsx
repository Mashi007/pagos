import { DollarSign, Calendar, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { usePagosKPIs } from '../../hooks/usePagos'

export function PagosKPIsNuevo() {
  const { data: kpiData, isLoading, error } = usePagosKPIs()

  const kpiDataFinal = kpiData || {
    montoACobrarMes: 0,
    montoCobradoMes: 0,
    morosidadMensualPorcentaje: 0,
    mes: new Date().getMonth() + 1,
    anio: new Date().getFullYear(),
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">Mensual</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="rounded-xl border border-gray-200/80">
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
      <div className="space-y-5">
        <h2 className="text-lg font-semibold text-gray-800">Mensual</h2>
        <Card className="rounded-xl border-red-100 bg-red-50/50">
          <CardContent className="pt-6">
            <p className="text-red-600 text-center text-sm">
              Error al cargar los KPIs. Por favor, intenta nuevamente.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const porcentajeCobrado =
    kpiDataFinal.montoACobrarMes > 0
      ? (kpiDataFinal.montoCobradoMes / kpiDataFinal.montoACobrarMes) * 100
      : 0

  const meses = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ]
  const nombreMes = meses[kpiDataFinal.mes - 1]

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <h2 className="text-lg font-semibold text-gray-800">Mensual</h2>
        <span className="text-sm font-medium text-gray-500 bg-gray-100 px-3 py-1.5 rounded-full">
          {nombreMes} {kpiDataFinal.anio ?? (kpiDataFinal as any)?.["año"] ?? new Date().getFullYear()}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="rounded-xl border border-gray-200/80 bg-white shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-700">A cobrar en el mes</CardTitle>
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-100">
              <Calendar className="h-4 w-4 text-blue-600" />
            </span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600 tabular-nums">
              ${kpiDataFinal.montoACobrarMes.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-500 mt-1.5">
              Vencimientos del mes
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-gray-200/80 bg-white shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-700">Cobrado / Pagado</CardTitle>
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-100">
              <DollarSign className="h-4 w-4 text-green-600" />
            </span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600 tabular-nums">
              ${kpiDataFinal.montoCobradoMes.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-500 mt-1.5">
              Pagos registrados en {nombreMes}
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-gray-200/80 bg-white shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-700">% cobrado</CardTitle>
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-100">
              <TrendingUp className="h-4 w-4 text-emerald-600" />
            </span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600 tabular-nums">
              {porcentajeCobrado.toFixed(1)}%
            </div>
            <p className="text-xs text-gray-500 mt-1.5">
              Cobrado / a cobrar en el mes
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}



