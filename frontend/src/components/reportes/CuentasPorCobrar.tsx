import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DollarSign, Loader2, RefreshCw, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { reporteService, type CarteraPorMes, type CarteraPorDiaItem } from '../../services/reporteService'
import { formatCurrency, formatDate } from '../../utils'

const MESES_OPCIONES = [3, 6, 12, 24]

function TablaPorDia({ label, items }: { label: string; items: CarteraPorDiaItem[] }) {
  return (
    <Card className="border-l-4 border-l-green-500">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Calendar className="h-5 w-5 text-green-600" />
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-gray-500 text-sm py-4">No hay cuentas por cobrar en este mes.</p>
        ) : (
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha (cuándo debe cobrar)</TableHead>
                  <TableHead className="text-right">Monto a cobrar</TableHead>
                  <TableHead className="text-right">Cuotas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.fecha}>
                    <TableCell className="font-medium">{formatDate(item.fecha)}</TableCell>
                    <TableCell className="text-right font-medium text-green-700">
                      {formatCurrency(item.monto_cobrar)}
                    </TableCell>
                    <TableCell className="text-right">{item.cantidad_cuotas}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function CuentasPorCobrar() {
  const [mesesAtras, setMesesAtras] = useState(12)
  const [tabActivo, setTabActivo] = useState('')
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['cartera-por-mes', mesesAtras],
    queryFn: () => reporteService.getCarteraPorMes(mesesAtras),
    staleTime: 2 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <Card className="shadow-sm">
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-green-600" />
            <p className="text-gray-600">Cargando cuentas por cobrar...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200 shadow-sm">
        <CardContent className="py-8">
          <p className="text-red-600 text-center">Error al cargar. Intente nuevamente.</p>
          <div className="flex justify-center mt-4">
            <Button variant="outline" onClick={() => refetch()} aria-label="Reintentar cargar cuentas por cobrar">
              <RefreshCw className="h-4 w-4 mr-2" aria-hidden />
              Reintentar
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const meses = data?.meses ?? []
  const valorTabs = tabActivo || meses[0]?.label || ''

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-4">
        <div>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-6 w-6 text-green-600" aria-hidden />
            Cuentas por cobrar
          </CardTitle>
          <CardDescription>
            Una pestaña por mes. Por día: cuándo debe cobrar (fecha vencimiento, monto pendiente).
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Select value={String(mesesAtras)} onValueChange={(v) => setMesesAtras(Number(v))}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Meses" />
            </SelectTrigger>
            <SelectContent>
              {MESES_OPCIONES.map((m) => (
                <SelectItem key={m} value={String(m)}>
                  Últimos {m} meses
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={() => refetch()} aria-label="Actualizar cuentas por cobrar">
            <RefreshCw className="h-4 w-4 mr-2" aria-hidden />
            Actualizar
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {meses.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No hay datos para mostrar.</p>
        ) : (
          <Tabs value={valorTabs} onValueChange={setTabActivo} className="w-full">
            <TabsList className="flex flex-wrap gap-1 mb-4 h-auto">
              {meses.map((m) => (
                <TabsTrigger key={`${m.año}-${m.mes}`} value={m.label}>
                  {m.label}
                </TabsTrigger>
              ))}
            </TabsList>
            {meses.map((m) => (
              <TabsContent key={`${m.año}-${m.mes}`} value={m.label} className="mt-4">
                <TablaPorDia label={m.label} items={m.items} />
              </TabsContent>
            ))}
          </Tabs>
        )}
      </CardContent>
    </Card>
  )
}
