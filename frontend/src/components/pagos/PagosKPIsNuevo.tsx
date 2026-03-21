import { DollarSign, Calendar, TrendingUp } from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

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
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Mensual</h2>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[1, 2, 3].map(i => (
            <Card key={i} className="rounded-xl border border-gray-200/80">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  <div className="h-4 w-24 animate-pulse rounded bg-gray-200" />
                </CardTitle>
              </CardHeader>

              <CardContent>
                <div className="mb-2 h-8 w-32 animate-pulse rounded bg-gray-200" />

                <div className="h-3 w-20 animate-pulse rounded bg-gray-200" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  const isCancelled =
    (error as any)?.code === 'ERR_CANCELED' ||
    (error as any)?.message?.includes?.('Request aborted')

  if (error && !isCancelled) {
    return (
      <div className="space-y-5">
        <h2 className="text-lg font-semibold text-gray-800">Mensual</h2>

        <Card className="rounded-xl border-red-100 bg-red-50/50">
          <CardContent className="pt-6">
            <p className="text-center text-sm text-red-600">
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
    'Enero',
    'Febrero',
    'Marzo',
    'Abril',
    'Mayo',
    'Junio',

    'Julio',
    'Agosto',
    'Septiembre',
    'Octubre',
    'Noviembre',
    'Diciembre',
  ]

  const nombreMes = meses[kpiDataFinal.mes - 1]

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-gray-800">Mensual</h2>

        <span className="rounded-full bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-500">
          {nombreMes}{' '}
          {kpiDataFinal.anio ??
            (kpiDataFinal as any)?.['año'] ??
            new Date().getFullYear()}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="rounded-xl border border-gray-200/80 bg-white shadow-sm transition-shadow hover:shadow-md">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-700">
              A cobrar en el mes
            </CardTitle>

            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-100">
              <Calendar className="h-4 w-4 text-blue-600" />
            </span>
          </CardHeader>

          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-blue-600">
              $
              {kpiDataFinal.montoACobrarMes.toLocaleString('es-US', {
                minimumFractionDigits: 2,

                maximumFractionDigits: 2,
              })}
            </div>

            <p className="mt-1.5 text-xs text-gray-500">Vencimientos del mes</p>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-gray-200/80 bg-white shadow-sm transition-shadow hover:shadow-md">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-700">
              Cobrado / Pagado
            </CardTitle>

            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-100">
              <DollarSign className="h-4 w-4 text-green-600" />
            </span>
          </CardHeader>

          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-green-600">
              $
              {kpiDataFinal.montoCobradoMes.toLocaleString('es-US', {
                minimumFractionDigits: 2,

                maximumFractionDigits: 2,
              })}
            </div>

            <p className="mt-1.5 text-xs text-gray-500">
              Pagos registrados en {nombreMes}
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-xl border border-gray-200/80 bg-white shadow-sm transition-shadow hover:shadow-md">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-700">
              % cobrado
            </CardTitle>

            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-100">
              <TrendingUp className="h-4 w-4 text-emerald-600" />
            </span>
          </CardHeader>

          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-emerald-600">
              {porcentajeCobrado.toFixed(1)}%
            </div>

            <p className="mt-1.5 text-xs text-gray-500">
              Cobrado / a cobrar en el mes
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
