import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Users, Loader2, RefreshCw, User } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { reporteService, type AsesoresPorMes, type AsesorPorMesItem } from '../../services/reporteService'
import { formatCurrency } from '../../utils'

const MESES_OPCIONES = [3, 6, 12, 24]

function TablaAsesoresMes({ label, items }: { label: string; items: AsesorPorMesItem[] }) {
  return (
    <Card className="border-l-4 border-l-indigo-500">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <User className="h-5 w-5 text-indigo-600" />
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-gray-500 text-sm py-4">No hay morosidad en este período.</p>
        ) : (
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre analista</TableHead>
                  <TableHead className="text-right">Total morosidad</TableHead>
                  <TableHead className="text-right">Total préstamos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.analista}>
                    <TableCell className="font-medium">{item.analista}</TableCell>
                    <TableCell className="text-right text-red-600 font-medium">
                      {formatCurrency(item.morosidad_total)}
                    </TableCell>
                    <TableCell className="text-right">{item.total_prestamos}</TableCell>
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

export function ReporteAsesores() {
  const [mesesAtras, setMesesAtras] = useState(12)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['asesores-por-mes', mesesAtras],
    queryFn: () => reporteService.getAsesoresPorMes(mesesAtras),
    staleTime: 2 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-indigo-600" />
            <p className="text-gray-600">Cargando reporte de asesores...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <CardContent className="py-8">
          <p className="text-red-600 text-center">Error al cargar el reporte. Intente nuevamente.</p>
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

  const meses = data?.meses ?? []

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-6 w-6 text-indigo-600" />
            Reporte Asesores
          </CardTitle>
          <CardDescription>
            Una pestaña por mes. Columnas: Nombre analista, Total morosidad, Total préstamos. Orden descendente por morosidad.
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
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {meses.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No hay datos para mostrar.</p>
        ) : (
          <Tabs defaultValue={meses[0].label} className="w-full">
            <TabsList className="flex flex-wrap gap-1 mb-4 h-auto">
              {meses.map((m) => (
                <TabsTrigger key={`${m.año}-${m.mes}`} value={m.label}>
                  {m.label}
                </TabsTrigger>
              ))}
            </TabsList>
            {meses.map((m) => (
              <TabsContent key={`${m.año}-${m.mes}`} value={m.label} className="mt-4">
                <TablaAsesoresMes label={m.label} items={m.items} />
              </TabsContent>
            ))}
          </Tabs>
        )}
      </CardContent>
    </Card>
  )
}
