import { useState } from 'react'
import { Download, Eye, FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Prestamo } from '@/types'
import { prestamoService } from '@/services/prestamoService'
import { useQuery } from '@tanstack/react-query'
import { formatDate } from '@/utils'
import toast from 'react-hot-toast'

interface Cuota {
  id: number
  numero_cuota: number
  fecha_vencimiento: string
  monto_cuota: number
  monto_capital: number
  monto_interes: number
  saldo_capital_inicial: number
  saldo_capital_final: number
  capital_pagado: number
  interes_pagado: number
  total_pagado: number
  capital_pendiente: number
  interes_pendiente: number
  estado: string
  dias_mora: number
  monto_mora: number
}

interface TablaAmortizacionPrestamoProps {
  prestamo: Prestamo
}

export function TablaAmortizacionPrestamo({ prestamo }: TablaAmortizacionPrestamoProps) {
  const [showFullTable, setShowFullTable] = useState(false)

  // Cargar cuotas del préstamo
  const { data: cuotas, isLoading, error } = useQuery({
    queryKey: ['cuotas-prestamo', prestamo.id],
    queryFn: () => prestamoService.getCuotasPrestamo(prestamo.id),
    enabled: prestamo.estado === 'APROBADO',
  })

  const getEstadoBadge = (estado: string) => {
    const badges = {
      PENDIENTE: 'bg-yellow-100 text-yellow-800',
      PAGADA: 'bg-green-100 text-green-800',
      VENCIDA: 'bg-red-100 text-red-800',
      PARCIAL: 'bg-blue-100 text-blue-800',
    }
    return badges[estado as keyof typeof badges] || badges.PENDIENTE
  }

  const getEstadoLabel = (estado: string) => {
    const labels: Record<string, string> = {
      PENDIENTE: 'Pendiente',
      PAGADA: 'Pagada',
      VENCIDA: 'Vencida',
      PARCIAL: 'Parcial',
    }
    return labels[estado] || estado
  }

  const exportarExcel = () => {
    toast('Función de exportación en desarrollo')
    // TODO: Implementar exportación a Excel
  }

  if (prestamo.estado !== 'APROBADO') {
    return (
      <Card className="border-yellow-200 bg-yellow-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <p className="text-sm text-yellow-800">
              La tabla de amortización solo se puede ver para préstamos APROBADOS.
              Estado actual: <strong>{prestamo.estado}</strong>
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-sm text-gray-600 mt-2">Cargando tabla de amortización...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-sm text-red-800">Error al cargar la tabla de amortización</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!cuotas || cuotas.length === 0) {
    return (
      <Card className="border-yellow-200 bg-yellow-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div>
              <p className="text-sm text-yellow-800 mb-2">
                No hay tabla de amortización generada para este préstamo.
              </p>
              {prestamo.fecha_base_calculo && (
                <Button size="sm" onClick={async () => {
                  try {
                    await prestamoService.generarAmortizacion(prestamo.id)
                    toast.success('Tabla de amortización generada exitosamente')
                    // Refrescar datos
                    window.location.reload()
                  } catch (error: any) {
                    toast.error(error.response?.data?.detail || 'Error al generar amortización')
                  }
                }}>
                  Generar Tabla
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Mostrar solo primeras 5 cuotas por defecto
  const cuotasVisibles = showFullTable ? cuotas : cuotas.slice(0, 5)

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-blue-600" />
          <CardTitle>Tabla de Amortización</CardTitle>
          <Badge variant="secondary">{cuotas.length} cuotas</Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={exportarExcel}>
            <Download className="h-4 w-4 mr-2" />
            Exportar Excel
          </Button>
          {!showFullTable && cuotas.length > 5 && (
            <Button variant="outline" size="sm" onClick={() => setShowFullTable(true)}>
              Ver Todas ({cuotas.length})
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cuota</TableHead>
                <TableHead>Fecha Vencimiento</TableHead>
                <TableHead className="text-right">Capital</TableHead>
                <TableHead className="text-right">Interés</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">Saldo Pendiente</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cuotasVisibles.map((cuota: Cuota) => (
                <TableRow key={cuota.id}>
                  <TableCell className="font-medium">{cuota.numero_cuota}</TableCell>
                  <TableCell>{formatDate(cuota.fecha_vencimiento)}</TableCell>
                  <TableCell className="text-right">
                    ${cuota.monto_capital.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right">
                    ${cuota.monto_interes.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right font-semibold">
                    ${cuota.monto_cuota.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right text-gray-600">
                    ${cuota.saldo_capital_final.toFixed(2)}
                  </TableCell>
                  <TableCell>
                    <Badge className={getEstadoBadge(cuota.estado)}>
                      {getEstadoLabel(cuota.estado)}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
              {!showFullTable && cuotas.length > 5 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-4">
                    <Button variant="ghost" onClick={() => setShowFullTable(true)}>
                      Ver {cuotas.length - 5} cuotas más...
                    </Button>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Resumen */}
        {cuotas.length > 0 && (
          <div className="mt-4 grid grid-cols-4 gap-4">
            <Card className="border-green-200 bg-green-50">
              <CardContent className="pt-4">
                <p className="text-sm text-green-600">Total Capital</p>
                <p className="text-2xl font-bold text-green-700">
                  ${cuotas.reduce((acc, c) => acc + (typeof c.monto_capital === 'number' ? c.monto_capital : 0), 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="pt-4">
                <p className="text-sm text-blue-600">Total Intereses</p>
                <p className="text-2xl font-bold text-blue-700">
                  ${cuotas.reduce((acc, c) => acc + (typeof c.monto_interes === 'number' ? c.monto_interes : 0), 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-purple-200 bg-purple-50">
              <CardContent className="pt-4">
                <p className="text-sm text-purple-600">Monto Total</p>
                <p className="text-2xl font-bold text-purple-700">
                  ${cuotas.reduce((acc, c) => acc + (typeof c.monto_cuota === 'number' ? c.monto_cuota : 0), 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-gray-200 bg-gray-50">
              <CardContent className="pt-4">
                <p className="text-sm text-gray-600">Pagadas</p>
                <p className="text-2xl font-bold text-gray-700">
                  {cuotas.filter((c: Cuota) => c.estado === 'PAGADA').length} / {cuotas.length}
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

