import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CreditCard,
  Filter,
  Search,
  Plus,
  Calendar,
  DollarSign,
  AlertCircle,
  Download,
  Upload,
  Edit,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { pagoService, type Pago } from '@/services/pagoService'
import { RegistrarPagoForm } from './RegistrarPagoForm'
import { ExcelUploader } from './ExcelUploader'
import { toast } from 'sonner'

export function PagosList() {
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [filters, setFilters] = useState({
    cedula: '',
    estado: '',
    fechaDesde: '',
    fechaHasta: '',
    analista: '',
  })
  const [showRegistrarPago, setShowRegistrarPago] = useState(false)
  const [showExcelUploader, setShowExcelUploader] = useState(false)
  const queryClient = useQueryClient()

  // Query para obtener pagos
  const { data, isLoading } = useQuery({
    queryKey: ['pagos', page, perPage, filters],
    queryFn: () => pagoService.getAllPagos(page, perPage, filters),
  })

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Módulo de Pagos</h1>
          <p className="text-gray-500 mt-1">Gestión de pagos de clientes</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => setShowExcelUploader(true)}>
            <Upload className="w-5 h-5 mr-2" />
            Cargar Excel
          </Button>
          <Button onClick={() => setShowRegistrarPago(true)}>
            <Plus className="w-5 h-5 mr-2" />
            Registrar Pago
          </Button>
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filtros de Búsqueda
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Input
              placeholder="Cédula de identidad"
              value={filters.cedula}
              onChange={e => handleFilterChange('cedula', e.target.value)}
            />
            <Select value={filters.estado || undefined} onValueChange={value => handleFilterChange('estado', value)}>
              <SelectTrigger>
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PAGADO">Pagado</SelectItem>
                <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                <SelectItem value="ATRASADO">Atrasado</SelectItem>
                <SelectItem value="PARCIAL">Parcial</SelectItem>
                <SelectItem value="ADELANTADO">Adelantado</SelectItem>
              </SelectContent>
            </Select>
            <Input
              type="date"
              placeholder="Fecha desde"
              value={filters.fechaDesde}
              onChange={e => handleFilterChange('fechaDesde', e.target.value)}
            />
            <Input
              type="date"
              placeholder="Fecha hasta"
              value={filters.fechaHasta}
              onChange={e => handleFilterChange('fechaHasta', e.target.value)}
            />
            <Input
              placeholder="Analista"
              value={filters.analista}
              onChange={e => handleFilterChange('analista', e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Tabla de Pagos */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Pagos</CardTitle>
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
                      <th className="px-4 py-3 text-left">ID</th>
                      <th className="px-4 py-3 text-left">Cédula</th>
                      <th className="px-4 py-3 text-left">Cliente</th>
                      <th className="px-4 py-3 text-left">ID Crédito</th>
                      <th className="px-4 py-3 text-left">Estado</th>
                      <th className="px-4 py-3 text-left">Cuotas Atrasadas</th>
                      <th className="px-4 py-3 text-left">Monto</th>
                      <th className="px-4 py-3 text-left">Fecha Pago</th>
                      <th className="px-4 py-3 text-left">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.pagos?.map((pago: Pago) => (
                      <tr key={pago.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3">{pago.id}</td>
                        <td className="px-4 py-3">{pago.cedula_cliente}</td>
                        <td className="px-4 py-3">{pago.cedula_cliente}</td>
                        <td className="px-4 py-3">{pago.prestamo_id || 'N/A'}</td>
                        <td className="px-4 py-3">{getEstadoBadge(pago.estado)}</td>
                        <td className="px-4 py-3">0</td>
                        <td className="px-4 py-3">${pago.monto_pagado.toFixed(2)}</td>
                        <td className="px-4 py-3">{new Date(pago.fecha_pago).toLocaleDateString()}</td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline" title="Registrar Pago">
                              <DollarSign className="w-4 h-4" />
                            </Button>
                            <Button size="sm" variant="outline" title="Editar">
                              <Edit className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Registrar Pago Modal */}
      {showRegistrarPago && (
        <RegistrarPagoForm
          onClose={() => setShowRegistrarPago(false)}
          onSuccess={() => {
            setShowRegistrarPago(false)
            queryClient.invalidateQueries({ queryKey: ['pagos'] })
            toast.success('Pago registrado exitosamente')
          }}
        />
      )}

      {/* Excel Uploader Modal */}
      {showExcelUploader && (
        <ExcelUploader
          onClose={() => setShowExcelUploader(false)}
          onSuccess={() => {
            setShowExcelUploader(false)
            queryClient.invalidateQueries({ queryKey: ['pagos'] })
          }}
        />
      )}
    </div>
  )
}

