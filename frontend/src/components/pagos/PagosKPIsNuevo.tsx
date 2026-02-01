import { DollarSign, AlertTriangle, CheckCircle, Users } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { usePagosKPIs } from '../../hooks/usePagos'

export function PagosKPIsNuevo() {
  // Obtener KPIs desde el backend (mes/año actual por defecto)
  const { data: kpiData, isLoading, error } = usePagosKPIs()

  // Valores por defecto mientras carga
  const kpiDataFinal = kpiData || {
    montoCobradoMes: 0,
    saldoPorCobrar: 0,
    clientesEnMora: 0,
    clientesAlDia: 0,
    mes: new Date().getMonth() + 1,
    año: new Date().getFullYear(),
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">KPIs de Pagos</h2>
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
      {/* Encabezado */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">KPIs de Pagos</h2>
        <span className="text-sm text-gray-500">
          {nombreMes} {kpiDataFinal.año}
        </span>
      </div>

      {/* Vista General con KPIs principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monto Cobrado en el Mes</CardTitle>
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
              Total cobrado en {nombreMes}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Saldo por Cobrar</CardTitle>
            <DollarSign className="h-5 w-5 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              ${kpiDataFinal.saldoPorCobrar.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">Total pendiente de cobro</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Clientes en Mora</CardTitle>
            <AlertTriangle className="h-5 w-5 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{kpiDataFinal.clientesEnMora}</div>
            <p className="text-xs text-gray-600 mt-1">Con cuotas vencidas</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Clientes al Día</CardTitle>
            <CheckCircle className="h-5 w-5 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{kpiDataFinal.clientesAlDia}</div>
            <p className="text-xs text-gray-600 mt-1">Sin cuotas vencidas</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

