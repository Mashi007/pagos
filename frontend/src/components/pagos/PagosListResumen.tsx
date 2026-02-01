import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Download, Filter } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { pagoService } from '../../services/pagoService'
import { toast } from 'sonner'

interface UltimoPago {
  cedula: string
  pago_id: number
  prestamo_id: number | null
  estado_pago: string
  monto_ultimo_pago: number
  fecha_ultimo_pago: string | null
  cuotas_atrasadas: number
  saldo_vencido: number
  total_prestamos: number
}

export function PagosListResumen() {
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [filters, setFilters] = useState({
    cedula: '',
    estado: '',
  })

  // Query para obtener últimos pagos por cédula
  const { data, isLoading } = useQuery({
    queryKey: ['pagos-ultimos', page, perPage, filters],
    queryFn: () => pagoService.getUltimosPagos(page, perPage, filters),
    staleTime: 0,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  })

  const handleFilterChange = (key: string, value: string) => {
    // Convertir "all" a cadena vacía para que el servicio no incluya el filtro
    const filterValue = value === 'all' ? '' : value
    setFilters(prev => ({ ...prev, [key]: filterValue }))
    setPage(1)
  }

  const getEstadoBadge = (estado: string) => {
    const estados: Record<string, { color: string; label: string }> = {
      PAGADO: { color: 'bg-green-500', label: 'Pagado' },
      PENDIENTE: { color: 'bg-yellow-500', label: 'Pendiente' },
      ATRASADO: { color: 'bg-red-500', label: 'Atrasado' },
      PARCIAL: { color: 'bg-blue-500', label: 'Parcial' },
      ADELANTADO: { color: 'bg-purple-500', label: 'Adelantado' },
    }
    const config = estados[estado] || { color: 'bg-gray-500', label: estado }
    return (
      <Badge className={`${config.color} text-white`}>{config.label}</Badge>
    )
  }

  const handleDescargarPDF = async (cedula: string) => {
    try {
      toast.loading('Generando PDF...')
      const blob = await pagoService.descargarPDFPendientes(cedula)

      // Crear URL temporal y descargar
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `pendientes_${cedula}_${new Date().toISOString().split('T')[0]}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      toast.dismiss()
      toast.success('PDF descargado exitosamente')
    } catch (error: unknown) {
      const { getErrorMessage, isAxiosError, getErrorDetail } = await import('../../types/errors')
      let errorMessage = getErrorMessage(error)
      const detail = getErrorDetail(error)
      if (detail) {
        errorMessage = detail
      }
      toast.dismiss()
      console.error('Error descargando PDF:', errorMessage)
      toast.error(errorMessage || 'Error al descargar PDF')
    }
  }

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filtros de Búsqueda
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="Cédula de identidad"
              value={filters.cedula}
              onChange={e => handleFilterChange('cedula', e.target.value)}
            />
            <Select
              value={filters.estado || 'all'}
              onValueChange={value => handleFilterChange('estado', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="PAGADO">Pagado</SelectItem>
                <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                <SelectItem value="ATRASADO">Atrasado</SelectItem>
                <SelectItem value="PARCIAL">Parcial</SelectItem>
                <SelectItem value="ADELANTADO">Adelantado</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tabla de Resumen */}
      <Card>
        <CardHeader>
          <CardTitle>Resumen por Cliente (Ãšltimo Pago)</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-12">Cargando...</div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="px-4 py-3 text-left">Cédula</th>
                      <th className="px-4 py-3 text-left">ID Ãšltimo Pago</th>
                      <th className="px-4 py-3 text-left">Estado</th>
                      <th className="px-4 py-3 text-right">Monto Ãšltimo Pago</th>
                      <th className="px-4 py-3 text-left">Fecha Ãšltimo Pago</th>
                      <th className="px-4 py-3 text-right">Cuotas Atrasadas</th>
                      <th className="px-4 py-3 text-right">Saldo Vencido</th>
                      <th className="px-4 py-3 text-left">Total Préstamos</th>
                      <th className="px-4 py-3 text-left">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.items?.map((item: UltimoPago) => (
                      <tr
                        key={`${item.cedula}-${item.pago_id}`}
                        className="border-b hover:bg-gray-50 cursor-pointer"
                        onClick={() => handleDescargarPDF(item.cedula)}
                      >
                        <td className="px-4 py-3 font-medium">{item.cedula}</td>
                        <td className="px-4 py-3">{item.pago_id}</td>
                        <td className="px-4 py-3">{getEstadoBadge(item.estado_pago)}</td>
                        <td className="px-4 py-3 text-right">
                          ${item.monto_ultimo_pago.toFixed(2)}
                        </td>
                        <td className="px-4 py-3">
                          {item.fecha_ultimo_pago
                            ? new Date(item.fecha_ultimo_pago).toLocaleDateString()
                            : 'N/A'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Badge variant={item.cuotas_atrasadas > 0 ? "destructive" : "default"}>
                            {item.cuotas_atrasadas}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right font-semibold">
                          ${item.saldo_vencido.toFixed(2)}
                        </td>
                        <td className="px-4 py-3">{item.total_prestamos}</td>
                        <td className="px-4 py-3">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDescargarPDF(item.cedula)
                            }}
                            title="Descargar PDF de pendientes"
                          >
                            <FileText className="w-4 h-4 mr-1" />
                            PDF
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Paginación */}
              {data && data.total_pages > 1 && (
                <div className="flex justify-between items-center mt-4">
                  <div className="text-sm text-gray-600">
                    Página {data.page} de {data.total_pages} ({data.total} registros)
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                      disabled={page >= data.total_pages}
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

