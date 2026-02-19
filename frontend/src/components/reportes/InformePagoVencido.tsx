import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, User, DollarSign, Calendar, CreditCard, Loader2, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { reporteService, type MorosidadPorRangos, type MorosidadPorRangosItem } from '../../services/reporteService'
import { formatCurrency, formatDate } from '../../utils'

const RANGOS_ORDER = ['1_dia', '15_dias', '30_dias', '2_meses', '61_dias']

function ViñetaPagoVencido({ item }: { item: MorosidadPorRangosItem }) {
  return (
    <Card className="border-l-4 border-l-amber-500 hover:shadow-md transition-shadow">
      <CardContent className="pt-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-gray-500" />
            <span className="font-medium">{item.cedula}</span>
          </div>
          <div className="font-medium text-gray-900 truncate" title={item.nombres}>
            {item.nombres}
          </div>
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-green-600" />
            <span>Total financiamiento: {formatCurrency(item.total_financiamiento)}</span>
          </div>
          <div className="flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-blue-600" />
            <span>Pagos totales: {formatCurrency(item.pagos_totales)}</span>
          </div>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-amber-600" />
            <span>Saldo: {formatCurrency(item.saldo)}</span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-gray-500" />
            <span>Último pago: {item.ultimo_pago_fecha ? formatDate(item.ultimo_pago_fecha) : '—'}</span>
          </div>
          <div className="flex items-center gap-2 md:col-span-2">
            <Calendar className="h-4 w-4 text-gray-500" />
            <span>Próximo pago: {item.proximo_pago_fecha ? formatDate(item.proximo_pago_fecha) : '—'}</span>
          </div>
        </div>
        <div className="mt-2">
          <Badge variant="secondary" className="text-xs">
            {item.dias_atraso} días atraso · Préstamo #{item.prestamo_id}
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
}

export function InformePagoVencido() {
  const [tabActivo, setTabActivo] = useState(RANGOS_ORDER[0])
  const fechaCorte = new Date().toISOString().split('T')[0]
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['morosidad-por-rangos', fechaCorte],
    queryFn: () => reporteService.getMorosidadPorRangos(fechaCorte),
    staleTime: 2 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
            <p className="text-gray-600">Cargando informe de pago vencido...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <CardContent className="py-8">
          <p className="text-red-600 text-center">Error al cargar el informe. Intente nuevamente.</p>
          <div className="flex justify-center mt-4">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Reintentar
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const rangos = data?.rangos ?? {}

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-amber-600" />
            Informe Pago Vencido
          </CardTitle>
          <CardDescription>
            Clientes con cuotas vencidas por rango de días. Fecha de corte: {data?.fecha_corte ? formatDate(data.fecha_corte) : '—'}
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Actualizar
        </Button>
      </CardHeader>
      <CardContent>
        <Tabs value={tabActivo} onValueChange={setTabActivo} className="w-full">
          <TabsList className="grid w-full grid-cols-2 md:grid-cols-5 mb-4">
            {RANGOS_ORDER.map((key) => {
              const r = rangos[key]
              const count = r?.items?.length ?? 0
              return (
                <TabsTrigger key={key} value={key} className="flex flex-col sm:flex-row gap-1">
                  <span>{r?.label ?? key}</span>
                  {count > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {count}
                    </Badge>
                  )}
                </TabsTrigger>
              )
            })}
          </TabsList>
          {RANGOS_ORDER.map((key) => {
            const r = rangos[key]
            const items = r?.items ?? []
            return (
              <TabsContent key={key} value={key} className="space-y-4 mt-4">
                {items.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No hay registros en este rango.</p>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {items.map((item) => (
                      <ViñetaPagoVencido key={item.prestamo_id} item={item} />
                    ))}
                  </div>
                )}
              </TabsContent>
            )
          })}
        </Tabs>
      </CardContent>
    </Card>
  )
}
