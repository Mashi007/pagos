import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Eye,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  DollarSign,
  Calculator,
  FileText
} from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { prestamoService, Prestamo } from '@/services/prestamoService'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import toast from 'react-hot-toast'

interface PrestamosListProps {
  onShowAmortizacion?: () => void
}

export function PrestamosList({ onShowAmortizacion }: PrestamosListProps) {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [estadoFilter, setEstadoFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showAmortizacion, setShowAmortizacion] = useState(false)
  const [editingPrestamo, setEditingPrestamo] = useState<Prestamo | null>(null)

  // Queries
  const { data: prestamosData, isLoading, error } = useQuery({
    queryKey: ['prestamos-list', searchTerm, estadoFilter],
    queryFn: () => prestamoService.listarPrestamos({
      limit: 100,
      estado: estadoFilter || undefined
    }),
    refetchInterval: 30000
  })

  const prestamos = prestamosData?.items || []

  // Handlers
  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['prestamos-list'] })
    queryClient.invalidateQueries({ queryKey: ['prestamos-stats'] })
    toast.success('🔄 Datos actualizados')
  }

  const handleEdit = (prestamo: Prestamo) => {
    setEditingPrestamo(prestamo)
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (confirm('¿Estás seguro de eliminar este préstamo?')) {
      try {
        await prestamoService.eliminarPrestamo(id)
        toast.success('✅ Préstamo eliminado')
        handleRefresh()
      } catch (error) {
        toast.error('❌ Error al eliminar préstamo')
      }
    }
  }

  const getEstadoBadge = (estado: string) => {
    const estados = {
      'PENDIENTE': { color: 'bg-yellow-100 text-yellow-800', icon: Clock },
      'APROBADO': { color: 'bg-green-100 text-green-800', icon: CheckCircle },
      'ACTIVO': { color: 'bg-blue-100 text-blue-800', icon: CheckCircle },
      'EN_MORA': { color: 'bg-red-100 text-red-800', icon: AlertCircle },
      'COMPLETADO': { color: 'bg-gray-100 text-gray-800', icon: CheckCircle },
      'RECHAZADO': { color: 'bg-red-100 text-red-800', icon: AlertCircle }
    }
    
    const config = estados[estado as keyof typeof estados] || estados.PENDIENTE
    const Icon = config.icon
    
    return (
      <Badge className={config.color}>
        <Icon className="h-3 w-3 mr-1" />
        {estado}
      </Badge>
    )
  }

  const prestamosFiltrados = prestamos.filter(prestamo =>
    prestamo.codigo_prestamo.toLowerCase().includes(searchTerm.toLowerCase()) ||
    prestamo.cliente_id.toString().includes(searchTerm)
  )

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <LoadingSpinner />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <AlertCircle className="h-8 w-8 mx-auto mb-2" />
            <p>Error al cargar préstamos</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center">
            <DollarSign className="mr-2 h-5 w-5" />
            Lista de Préstamos ({prestamosFiltrados.length})
          </CardTitle>
          <div className="flex items-center space-x-2">
            <Button onClick={handleRefresh} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Actualizar
            </Button>
            <Button onClick={() => onShowAmortizacion?.()} variant="outline">
              <Calculator className="h-4 w-4 mr-2" />
              Tabla de Amortización
            </Button>
            <Button onClick={() => setShowForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Nuevo Préstamo
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Filtros */}
        <div className="flex items-center space-x-4 mb-6">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Buscar por código o ID cliente..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          <Select value={estadoFilter} onValueChange={setEstadoFilter}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Filtrar por estado" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todos los estados</SelectItem>
              <SelectItem value="PENDIENTE">Pendiente</SelectItem>
              <SelectItem value="APROBADO">Aprobado</SelectItem>
              <SelectItem value="ACTIVO">Activo</SelectItem>
              <SelectItem value="EN_MORA">En Mora</SelectItem>
              <SelectItem value="COMPLETADO">Completado</SelectItem>
              <SelectItem value="RECHAZADO">Rechazado</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Tabla */}
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Cliente ID</TableHead>
                <TableHead>Monto Total</TableHead>
                <TableHead>Cuotas</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Fecha Aprobación</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {prestamosFiltrados.map((prestamo) => (
                <TableRow key={prestamo.id}>
                  <TableCell className="font-medium">
                    {prestamo.codigo_prestamo}
                  </TableCell>
                  <TableCell>{prestamo.cliente_id}</TableCell>
                  <TableCell>
                    ${prestamo.monto_total.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {prestamo.cuotas_pagadas}/{prestamo.numero_cuotas}
                  </TableCell>
                  <TableCell>
                    {getEstadoBadge(prestamo.estado)}
                  </TableCell>
                  <TableCell>
                    {prestamo.fecha_aprobacion ? 
                      new Date(prestamo.fecha_aprobacion).toLocaleDateString() : 
                      'N/A'
                    }
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(prestamo)}
                        title="Editar préstamo"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(prestamo.id)}
                        className="text-red-600 hover:text-red-700"
                        title="Eliminar préstamo"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {prestamosFiltrados.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <DollarSign className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No se encontraron préstamos</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
