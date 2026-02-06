import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, FileDown, User, Loader2 } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Badge } from '../../components/ui/badge'
import { usePrestamosByCedula } from '../../hooks/usePrestamos'
import { prestamoService } from '../../services/prestamoService'
import { pagoService } from '../../services/pagoService'
import { toast } from 'sonner'

export function PagosBuscadorAmortizacion() {
  const [cedulaInput, setCedulaInput] = useState('')
  const [cedulaBuscar, setCedulaBuscar] = useState<string | null>(null)

  const { data: prestamos, isLoading: loadingPrestamos } = usePrestamosByCedula(cedulaBuscar || '')
  const prestamoIds = prestamos?.map((p) => p.id) ?? []
  const prestamoIdsKey = JSON.stringify(prestamoIds.sort((a, b) => a - b))

  const { data: cuotas, isLoading: loadingCuotas } = useQuery({
    queryKey: ['cuotas-amortizacion-cedula', prestamoIdsKey],
    queryFn: async () => {
      const arrays = await Promise.all(
        prestamoIds.map((id) => prestamoService.getCuotasPrestamo(id))
      )
      return arrays.flat()
    },
    enabled: cedulaBuscar !== null && prestamoIds.length > 0,
  })

  const loading = loadingPrestamos || loadingCuotas
  const listaCuotas = cuotas ?? []
  const tieneResultados = cedulaBuscar && (prestamos?.length ?? 0) > 0

  const handleBuscar = () => {
    const ced = cedulaInput?.trim() || ''
    if (!ced) {
      toast.error('Escriba una cédula para buscar')
      return
    }
    setCedulaBuscar(ced)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleBuscar()
  }

  const handleDescargarPDF = async () => {
    if (!cedulaBuscar) return
    try {
      toast.loading('Generando PDF...', { id: 'pdf-amort' })
      const blob = await pagoService.descargarPDFAmortizacion(cedulaBuscar)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `amortizacion_${cedulaBuscar}_${new Date().toISOString().split('T')[0]}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      toast.success('PDF descargado', { id: 'pdf-amort' })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al descargar PDF'
      toast.error(msg, { id: 'pdf-amort' })
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="h-5 w-5" />
          Buscar por cédula – Tabla de amortización
        </CardTitle>
        <p className="text-sm text-gray-600 mt-1">
          Ingrese la cédula del cliente y pulse Buscar para desplegar la tabla de amortización. Puede descargarla en PDF.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 max-w-sm">
            <Input
              placeholder="Cédula del cliente"
              value={cedulaInput}
              onChange={(e) => setCedulaInput(e.target.value)}
              onKeyDown={handleKeyDown}
              aria-label="Cédula"
            />
          </div>
          <Button onClick={handleBuscar} className="shrink-0">
            <Search className="h-4 w-4 mr-2" />
            Buscar
          </Button>
        </div>

        {cedulaBuscar && (
          <>
            {loading ? (
              <div className="flex items-center justify-center py-12 gap-2 text-gray-500">
                <Loader2 className="h-6 w-6 animate-spin" />
                <span>Cargando tabla de amortización...</span>
              </div>
            ) : !tieneResultados ? (
              <div className="py-8 text-center text-gray-600">
                No se encontró cliente con cédula <strong>{cedulaBuscar}</strong> o no tiene préstamos/cuotas.
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <p className="text-sm text-gray-600">
                    Cliente: cédula <strong>{cedulaBuscar}</strong> · {listaCuotas.length} cuota(s)
                  </p>
                  <Button variant="outline" onClick={handleDescargarPDF}>
                    <FileDown className="h-4 w-4 mr-2" />
                    Descargar PDF
                  </Button>
                </div>
                <div className="border rounded-lg overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Préstamo</TableHead>
                        <TableHead>Nº Cuota</TableHead>
                        <TableHead>Fecha venc.</TableHead>
                        <TableHead>Fecha pago</TableHead>
                        <TableHead className="text-right">Monto</TableHead>
                        <TableHead>Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {listaCuotas
                        .sort((a, b) => (a.prestamo_id - b.prestamo_id) || (a.numero_cuota - b.numero_cuota))
                        .map((c) => (
                          <TableRow key={`${c.prestamo_id}-${c.numero_cuota}`}>
                            <TableCell>{c.prestamo_id}</TableCell>
                            <TableCell>{c.numero_cuota}</TableCell>
                            <TableCell>
                              {c.fecha_vencimiento
                                ? new Date(c.fecha_vencimiento).toLocaleDateString('es')
                                : '—'}
                            </TableCell>
                            <TableCell>
                              {c.fecha_pago
                                ? new Date(c.fecha_pago).toLocaleDateString('es')
                                : '—'}
                            </TableCell>
                            <TableCell className="text-right font-medium">
                              ${typeof (c as any).monto_cuota === 'number' ? (c as any).monto_cuota.toFixed(2) : (c as any).monto?.toFixed(2) ?? '—'}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant={c.estado === 'PAGADO' || c.fecha_pago ? 'default' : 'secondary'}
                                className={c.estado === 'PAGADO' || c.fecha_pago ? 'bg-green-600' : ''}
                              >
                                {c.fecha_pago ? 'Pagado' : (c.estado || 'Pendiente')}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </div>
              </>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
