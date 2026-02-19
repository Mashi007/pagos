import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Users, Loader2, RefreshCw, FileText } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { reporteService, type PagosPorMes, type PagoPorMesItem } from '../../services/reporteService'
import { formatCurrency, formatDate } from '../../utils'

const MESES_OPCIONES = [3, 6, 12, 24]

function TablaPagosMes({
  label,
  items,
}: {
  label: string
  items: PagoPorMesItem[]
}) {
  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-600" aria-hidden />
          {label}
          <span className="text-sm font-normal text-gray-500">({items.length} pagos)</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-gray-500 text-sm py-4">No hay pagos en este período.</p>
        ) : (
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>ID Préstamo</TableHead>
                  <TableHead>Cédula</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead className="text-right">Monto pago</TableHead>
                  <TableHead>Documento</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.pago_id ?? `${item.fecha}-${item.cedula}-${item.documento}`}>
                    <TableCell className="whitespace-nowrap">{formatDate(item.fecha)}</TableCell>
                    <TableCell>{item.prestamo_id ?? '—'}</TableCell>
                    <TableCell>{item.cedula}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={item.nombre}>
                      {item.nombre || '—'}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(item.monto_pago)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">{item.documento || '—'}</TableCell>
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

export function ReportePagos() {
  const [mesesAtras, setMesesAtras] = useState(12)
  const [tabActivo, setTabActivo] = useState('')
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['pagos-por-mes', mesesAtras],
    queryFn: () => reporteService.getPagosPorMes(mesesAtras),
    staleTime: 2 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <Card className="shadow-sm">
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
            <p className="text-gray-600">Cargando reporte de pagos...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200 shadow-sm">
        <CardContent className="py-8">
          <p className="text-red-600 text-center">Error al cargar el reporte. Intente nuevamente.</p>
          <div className="flex justify-center mt-4">
            <Button variant="outline" onClick={() => refetch()} aria-label="Reintentar cargar reporte de pagos">
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
            <Users className="h-6 w-6 text-blue-600" aria-hidden />
            Reporte Pagos
          </CardTitle>
          <CardDescription>
            Pagos por mes/año. Columnas: Fecha, ID préstamo, Cédula, Nombre, Monto pago, Documento. Orden descendente por fecha.
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
          <Button variant="outline" size="sm" onClick={() => refetch()} aria-label="Actualizar reporte de pagos">
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
                <TablaPagosMes label={m.label} items={m.items} />
              </TabsContent>
            ))}
          </Tabs>
        )}
      </CardContent>
    </Card>
  )
}
